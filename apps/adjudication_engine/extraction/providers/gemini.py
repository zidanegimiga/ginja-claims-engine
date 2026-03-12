import os
import re
import json
import base64
from dotenv import load_dotenv
from extraction.providers.base import BaseVisionProvider

load_dotenv()

EXTRACTION_PROMPT = """
You are a healthcare claims data extraction specialist working with East African medical documents.

Analyse this claim form or invoice carefully and extract every piece of structured information.

Return ONLY a valid JSON object with these exact keys.
If a field is not found, use null. Do not include any explanation outside the JSON.

{
  "claim_id": "claim number, invoice number, receipt number, or any reference number",
  "member_id": "insurance member number, policy number, or patient ID",
  "provider_id": "hospital code, facility code, or provider number if present",
  "hospital_name": "full name of the hospital, clinic, or medical facility",
  "hospital_address": "full address of the facility if present",
  "hospital_phone": "phone number of the facility if present",
  "patient_name": "full name of the patient",
  "patient_dob": "date of birth if present",
  "diagnosis_code": "ICD-10 code e.g. J06.9, B50.9 — null if not explicitly coded",
  "diagnosis_description": "written diagnosis, condition, or reason for visit",
  "procedure_code": "CPT code e.g. 99214 — null if not explicitly coded",
  "procedure_description": "written description of procedures, treatments, or services rendered",
  "claimed_amount": "total amount billed as a number only, no currency symbol",
  "approved_tariff": "approved or insurance amount if different from claimed, else null",
  "date_of_service": "date treatment was provided in ISO format YYYY-MM-DDTHH:MM:SS",
  "provider_type": "one of: hospital, clinic, pharmacy, laboratory, specialist",
  "location": "city or region where the facility is located",
  "member_age": "patient age as integer if present",
  "insurance_company": "name of insurance company if mentioned",
  "visit_type": "inpatient, outpatient, emergency, or dental etc.",
  "line_items": [
    {
      "description": "service or item name",
      "quantity": "number",
      "unit_price": "price per unit",
      "total": "line total"
    }
  ],
  "notes": "any other clinically or financially relevant information",
  "extraction_warnings": [
    "list any fields that were unclear, ambiguous, or missing from the document"
  ]
}

Critical instructions:
- For Kenyan and Rwandan claims, amounts are in KES or RWF respectively
- Convert all dates to ISO format: YYYY-MM-DDTHH:MM:SS
- ICD-10 codes look like: J06.9, B50.9, E11.9, A01.0
- CPT codes are 5-digit numbers: 99213, 71046, 43239
- If the document has a hospital letterhead, logo, or stamp — extract the name from it
- Hospital reference numbers, visit numbers, and receipt numbers should go in claim_id
- If diagnosis is written in plain English rather than coded, put it in diagnosis_description
- Extract ALL line items from the invoice table if one exists
- If handwriting is unclear, note the field in extraction_warnings
"""


class GeminiProvider(BaseVisionProvider):
    """
    Cloud-based PDF extraction using Google Gemini Vision.

    Uses the new google-genai SDK (replacing deprecated
    google-generativeai). Handles both digital and
    handwritten claim forms.
    """

    def __init__(self, model_name: str = None):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Add it to your .env file."
            )

        # New SDK import and initialisation
        from google import genai
        self.client     = genai.Client(api_key=api_key)
        # self.model_name = "gemini-3-flash-preview"
        self.model_name =  model_name or os.getenv(
            "VISION_MODEL", "gemini-3-flash-preview"
        )

    def extract(self, pdf_path: str, model_name: str = None) -> dict:
        result       = self._empty_result()
        active_model = model_name or self.model_name

        try:
            import fitz
            doc    = fitz.open(pdf_path)
            images = []

            for page in doc:
                pix       = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                img_b64   = base64.b64encode(img_bytes).decode("utf-8")
                images.append(img_b64)

            doc.close()

            from google.genai import types

            # Build content parts — prompt + all page images
            parts = [types.Part.from_text(text=EXTRACTION_PROMPT)]
            for img_b64 in images:
                parts.append(types.Part.from_bytes(
                    data       = base64.b64decode(img_b64),
                    mime_type  = "image/png",
                ))

            response = self.client.models.generate_content(
                model    = active_model,
                contents = [types.Content(
                    role  = "user",
                    parts = parts,
                )],
            )

            raw_text = response.text.strip()
            raw_text = re.sub(r"```json|```", "", raw_text).strip()

            extracted = json.loads(raw_text)
            result.update(extracted)
            result["provider_name"] = f"gemini:{active_model}"
            result["confidence"]    = "high"
            result["raw_text"]      = raw_text

        except json.JSONDecodeError as e:
            result["extraction_warnings"].append(
                f"Gemini returned invalid JSON: {e}"
            )
        except Exception as e:
            result["extraction_warnings"].append(
                f"Gemini extraction error: {e}"
            )

        return result