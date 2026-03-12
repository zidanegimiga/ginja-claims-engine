import os
import re
import json
import base64
import requests
from extraction.providers.base import BaseVisionProvider


EXTRACTION_PROMPT = """You are a healthcare claims data extraction specialist.
Analyse this claim form image and extract all structured fields.

Return ONLY a valid JSON object with these exact keys.
If a field is not found, use null.
Do not include any explanation outside the JSON.

{
  "claim_id": null,
  "member_id": null,
  "provider_id": null,
  "patient_name": null,
  "diagnosis_code": null,
  "procedure_code": null,
  "claimed_amount": null,
  "approved_tariff": null,
  "date_of_service": null,
  "provider_name": null,
  "provider_type": null,
  "location": null,
  "member_age": null,
  "extraction_warnings": []
}"""


class OllamaProvider(BaseVisionProvider):
    """
    Offline vision extraction using Ollama.

    Ollama runs open-source vision models locally on your machine.
    No API key needed, no data leaves your computer.
    Ideal for: privacy-sensitive environments, offline deployments,
               areas with unreliable internet connectivity.

    Supports any Ollama vision model — llava, qwen2-vl, etc.
    The model is passed as a parameter making it fully swappable.

    Default model: llava
    For Qwen: pass model="qwen2-vl"
    """

    def __init__(self, model: str = None):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model    = model or os.getenv("OLLAMA_VISION_MODEL", "llava")

    def extract(self, pdf_path: str, model: str = None) -> dict:
        """
        Extracts claim fields using a local Ollama vision model.

        Converts PDF pages to base64 images and sends them
        to the Ollama API running on localhost.

        model: optionally override the model at call time
               e.g. extract(pdf_path, model="qwen2-vl")
        """
        result      = self._empty_result()
        active_model = model or self.model

        try:
            import fitz
            doc = fitz.open(pdf_path)
            images = []

            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                images.append(img_b64)

            doc.close()

            # Ollama API accepts images as base64 strings
            payload = {
                "model":  active_model,
                "prompt": EXTRACTION_PROMPT,
                "images": images,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # low temperature === more consistent output
                }
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json = payload,
                timeout = 120,
            )
            response.raise_for_status()

            raw_text = response.json().get("response", "")
            raw_text = re.sub(r"```json|```", "", raw_text).strip()

            extracted = json.loads(raw_text)
            result.update(extracted)
            result["provider_name"] = f"ollama:{active_model}"
            result["confidence"] = "medium"
            result["raw_text"] = raw_text

        except requests.exceptions.ConnectionError:
            result["extraction_warnings"].append(
                "Ollama is not running. Start it with: ollama serve"
            )
        except json.JSONDecodeError as e:
            result["extraction_warnings"].append(
                f"Ollama returned invalid JSON: {e}"
            )
        except Exception as e:
            result["extraction_warnings"].append(
                f"Ollama extraction error: {e}"
            )

        return result


class QwenProvider(OllamaProvider):
    """
    Qwen vision model via Ollama.

    Qwen2-VL is a strong multilingual vision model from Alibaba.
    It handles mixed English/Swahili text well, relevant for Kenyan healthcare forms that may mix both languages.
    """

    def __init__(self):
        super().__init__(
            model=os.getenv("QWEN_VISION_MODEL", "qwen2-vl")
        )
        self.provider_label = "qwen"