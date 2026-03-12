import os
import re
import json
import base64
import google.generativeai as genai
from extraction.providers.base import BaseVisionProvider


EXTRACTION_PROMPT = """
You are a healthcare claims data extraction specialist.
Analyse this claim form or invoice image and extract all structured fields.

Return ONLY a valid JSON object with these exact keys.
If a field is not found, use null.
Do not include any explanation or text outside the JSON.

{
  "claim_id": "string or null",
  "member_id": "string or null",
  "provider_id": "string or null",
  "patient_name": "string or null",
  "diagnosis_code": "ICD-10 code string or null",
  "diagnosis_description": "string or null",
  "procedure_code": "CPT code string or null",
  "procedure_description": "string or null",
  "claimed_amount": "number or null",
  "approved_tariff": "number or null",
  "date_of_service": "ISO date string or null",
  "provider_name": "string or null",
  "provider_type": "hospital/clinic/pharmacy/laboratory/specialist or null",
  "location": "city or region string or null",
  "member_age": "integer or null",
  "notes": "any other relevant information as string or null",
  "extraction_warnings": ["list of any unclear or ambiguous fields"]
}

Important notes:
- For Kenyan claims, amounts are in KES (Kenyan Shillings)
- Dates should be converted to ISO format: YYYY-MM-DDTHH:MM:SS
- ICD-10 codes follow format like J06.9, B50.9, E11.9
- CPT codes are 5-digit numbers like 99213, 71046
- If handwriting is unclear, include the field in extraction_warnings
"""


class GeminiProvider(BaseVisionProvider):
    """
    Cloud-based PDF extraction using Google Gemini Vision.

    Works well for: both digital and handwritten forms
    Requires: GEMINI_API_KEY environment variable
    Cost: free tier generous enough for prototyping

    Gemini receives the PDF pages as images and uses
    its vision capability to read and understand them —
    including handwritten text, stamps, and tables.
    """

    def __init__(self, model_name: str = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=api_key)
        self.model_name = model_name or os.getenv("VISION_MODEL", "gemini-1.5-flash")
        self.model = genai.GenerativeModel(self.model_name)

    def extract(self, pdf_path: str, model_name: str = None) -> dict:
        """
        Extracts claim fields from a PDF using Gemini Vision.

        Converts each PDF page to an image, sends them all
        to Gemini with the extraction prompt, and parses
        the JSON response.

        model_name: optionally override the model at call time
        """
        result = self._empty_result()

        try:
            import fitz
            doc = fitz.open(pdf_path)
            images = []

            for page in doc:
                # Render page at 200 DPI — good balance of quality vs size
                pix  = page.get_pixmap(dpi=200)
                img_bytes  = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                images.append({
                    "mime_type": "image/png",
                    "data": img_b64,
                })

            doc.close()

            # Use override model if provided
            model = self.model
            if model_name and model_name != self.model_name:
                model = genai.GenerativeModel(model_name)

            # Send all page images + prompt to Gemini
            content  = [EXTRACTION_PROMPT] + [
                {"inline_data": img} for img in images
            ]
            response = model.generate_content(content)
            raw_text = response.text.strip()

            # Clean up response,remove markdown code fences if present
            raw_text = re.sub(r"```json|```", "", raw_text).strip()

            extracted = json.loads(raw_text)

            result.update(extracted)
            result["provider_name"] = f"gemini:{self.model_name}"
            result["confidence"] = "high"
            result["raw_text"] = raw_text

        except json.JSONDecodeError as e:
            result["extraction_warnings"].append(
                f"Gemini returned invalid JSON: {e}"
            )
        except Exception as e:
            result["extraction_warnings"].append(
                f"Gemini extraction error: {e}"
            )

        return result