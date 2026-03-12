import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from extraction.providers.base import BaseVisionProvider


class TesseractProvider(BaseVisionProvider):
    """
    Offline PDF extraction using PyMuPDF + Tesseract OCR.

    Works well for: digitally typed PDFs
    Works poorly for: handwritten forms, low quality scans

    No API key required. Runs entirely on your machine.
    Best case: As fallback when cloud providers are unavailable.
    """

    def extract(self, pdf_path: str) -> dict:
        result   = self._empty_result()
        raw_text = ""

        try:
            doc = fitz.open(pdf_path)

            for page in doc:
                # First try direct text extraction (fastest, works on digital PDFs)
                page_text = page.get_text()

                if len(page_text.strip()) < 50:
                    # Not enough text, probably a scanned image
                    # Fall back to OCR
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    page_text = pytesseract.image_to_string(img)

                raw_text += page_text + "\n"

            doc.close()
            result["raw_text"] = raw_text

            # Parse fields from extracted text using patterns
            result.update(self._parse_fields(raw_text))
            result["provider_name"] = "tesseract"
            result["confidence"] = "medium" if len(raw_text) > 100 else "low"

        except Exception as e:
            result["extraction_warnings"].append(f"Tesseract extraction error: {e}")

        return result

    def _parse_fields(self, text: str) -> dict:
        """
        Uses regular expressions to find structured fields
        in the extracted text.

        Regular expressions are patterns that match text —
        for example r'\d{2}/\d{2}/\d{4}' matches dates
        in DD/MM/YYYY format.
        """
        fields = {}

        # Claim ID — looks for patterns like CLM-XXXXX or Claim No: 12345
        claim_match = re.search(
            r'(?:claim[^\w]?(?:id|no|number)[:\s#]*)([\w\-]+)',
            text, re.IGNORECASE
        )
        if claim_match:
            fields["claim_id"] = claim_match.group(1).strip()

        # Member ID
        member_match = re.search(
            r'(?:member[^\w]?(?:id|no|number)[:\s#]*)([\w\-]+)',
            text, re.IGNORECASE
        )
        if member_match:
            fields["member_id"] = member_match.group(1).strip()

        # Amount — looks for currency patterns like KES 4,500 or 4500.00
        amount_match = re.search(
            r'(?:amount[^\w]*claimed|claimed[^\w]*amount|total[^\w]*amount)[:\s]*'
            r'(?:KES|Ksh|USD)?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if amount_match:
            amount_str = amount_match.group(1).replace(",", "")
            try:
                fields["claimed_amount"] = float(amount_str)
            except ValueError:
                pass

        # Date of service
        date_match = re.search(
            r'(?:date[^\w]*(?:of[^\w]*)?service|service[^\w]*date|DOS)[:\s]*'
            r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
            text, re.IGNORECASE
        )
        if date_match:
            fields["date_of_service"] = date_match.group(1).strip()

        # ICD-10 diagnosis code — format like J06.9 or B50.9
        icd_match = re.search(
            r'(?:diagnosis[^\w]*code|ICD[^\w]*10)[:\s]*([A-Z]\d{2}\.?\d*)',
            text, re.IGNORECASE
        )
        if icd_match:
            fields["diagnosis_code"] = icd_match.group(1).strip()

        # CPT procedure code — 5 digit number
        cpt_match = re.search(
            r'(?:procedure[^\w]*code|CPT)[:\s]*(\d{5})',
            text, re.IGNORECASE
        )
        if cpt_match:
            fields["procedure_code"] = cpt_match.group(1).strip()

        # Location
        location_match = re.search(
            r'(?:location|facility[^\w]*location|city)[:\s]*([A-Za-z\s]+?)(?:\n|,)',
            text, re.IGNORECASE
        )
        if location_match:
            fields["location"] = location_match.group(1).strip()

        return fields