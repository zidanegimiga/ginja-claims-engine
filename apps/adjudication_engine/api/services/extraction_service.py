import re
import io
import logging
from typing import Any
from datetime import datetime, date

import fitz # PyMuPDF
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# Field patterns
# Each entry: (field_name, [regex patterns], transform_fn)
PATTERNS: list[tuple[str, list[str], Any]] = [
    ("member_id", [
        r"member\s*(?:id|no|number)[:\s#]*([A-Z0-9\-]+)",
        r"MEM[-\s]?(\w+)",
        r"patient\s*id[:\s]*([A-Z0-9\-]+)",
    ], str),

    ("provider_id", [
        r"provider\s*(?:id|no|number|code)[:\s#]*([A-Z0-9\-]+)",
        r"facility\s*(?:id|code)[:\s]*([A-Z0-9\-]+)",
        r"PRV[-\s]?(\w+)",
    ], str),

    ("diagnosis_code", [
        r"diagnosis\s*code[:\s]*([A-Z]\d{2}\.?\d*)",
        r"ICD[-\s]?10[:\s]*([A-Z]\d{2}\.?\d*)",
        r"dx[:\s]*([A-Z]\d{2}\.?\d*)",
    ], str),

    ("procedure_code", [
        r"procedure\s*code[:\s]*(\d{4,5}[A-Z]?)",
        r"CPT[:\s]*(\d{4,5}[A-Z]?)",
        r"treatment\s*code[:\s]*(\d{4,5}[A-Z]?)",
    ], str),

    ("claimed_amount", [
        r"claimed?\s*amount[:\s]*(?:KES|KSH|Ksh)?\.?\s*([\d,]+\.?\d*)",
        r"total\s*(?:amount|billed|charged)[:\s]*(?:KES|KSH|Ksh)?\.?\s*([\d,]+\.?\d*)",
        r"invoice\s*(?:total|amount)[:\s]*(?:KES|KSH|Ksh)?\.?\s*([\d,]+\.?\d*)",
        r"amount\s*(?:due|payable)[:\s]*(?:KES|KSH|Ksh)?\.?\s*([\d,]+\.?\d*)",
    ], lambda v: float(v.replace(",", ""))),

    ("approved_tariff", [
        r"approved\s*tariff[:\s]*(?:KES|KSH|Ksh)?\.?\s*([\d,]+\.?\d*)",
        r"tariff[:\s]*(?:KES|KSH|Ksh)?\.?\s*([\d,]+\.?\d*)",
        r"standard\s*(?:rate|fee)[:\s]*(?:KES|KSH|Ksh)?\.?\s*([\d,]+\.?\d*)",
    ], lambda v: float(v.replace(",", ""))),

    ("date_of_service", [
        r"date\s*of\s*service[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"service\s*date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"(?:visit|treatment|admission)\s*date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"date[:\s]*(\d{4}-\d{2}-\d{2})",
    ], None),  # handled separately

    ("provider_type", [
        r"(?:facility|provider)\s*type[:\s]*(hospital|clinic|pharmacy|laboratory|specialist)",
        r"type\s*of\s*(?:facility|provider)[:\s]*(hospital|clinic|pharmacy|laboratory|specialist)",
    ], lambda v: v.lower()),

    ("location", [
        r"(?:facility\s*)?location[:\s]*([A-Za-z\s,]+?)(?:\n|$|,\s*(?:Kenya|KE))",
        r"(?:city|town|county)[:\s]*([A-Za-z\s]+?)(?:\n|$)",
        r"address[:\s]*([A-Za-z\s,]+?)(?:\n|$)",
    ], lambda v: v.strip().rstrip(",").strip()),

    ("member_age", [
        r"(?:patient\s*)?age[:\s]*(\d{1,3})\s*(?:years?|yrs?)?",
        r"age\s*at\s*(?:service|visit)[:\s]*(\d{1,3})",
    ], int),

    ("invoice_number", [
        r"invoice\s*(?:no|number|#)[:\s]*([A-Z0-9\-\/]+)",
        r"receipt\s*(?:no|number|#)[:\s]*([A-Z0-9\-\/]+)",
        r"ref(?:erence)?\s*(?:no|number|#)?[:\s]*([A-Z0-9\-\/]+)",
    ], str),
]

DATE_FORMATS = [
    "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y-%m-%d",
    "%d/%m/%y", "%m/%d/%y", "%d-%m-%y",
]

PROVIDER_TYPES = {"hospital", "clinic", "pharmacy", "laboratory", "specialist"}


def _parse_date(raw: str) -> str | None:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text using PyMuPDF, fall back to Tesseract OCR per page."""
    text_parts: list[str] = []

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            # Try direct text extraction first
            text = page.get_text("text").strip()

            if len(text) > 50:
                text_parts.append(text)
            else:
                # Scanned page — render to image and OCR
                logger.info("Page %d has sparse text, falling back to OCR", page.number)
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr = pytesseract.image_to_string(img, config="--psm 6")
                text_parts.append(ocr)

    return "\n".join(text_parts)


def _extract_fields(text: str) -> tuple[dict, list[str], set[str]]:
    """
    Run all patterns against the extracted text.
    Returns (extracted_data, warnings, populated_fields).
    """
    text_lower = text.lower()
    data: dict = {}
    warnings: list[str] = []
    populated: set[str] = set()

    for field, patterns, transform in PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, text_lower if field != "invoice_number" else text, re.IGNORECASE | re.MULTILINE)
            if match:
                raw = match.group(1).strip()
                try:
                    if field == "date_of_service":
                        parsed = _parse_date(raw)
                        if parsed:
                            data[field] = parsed
                            populated.add(field)
                    elif field == "provider_type":
                        val = raw.lower()
                        if val in PROVIDER_TYPES:
                            data[field] = val
                            populated.add(field)
                    elif transform:
                        data[field] = transform(raw)
                        populated.add(field)
                    else:
                        data[field] = raw
                        populated.add(field)
                    break
                except (ValueError, TypeError) as e:
                    warnings.append(f"Could not parse {field}: {raw!r} ({e})")

    # Validation warnings for required fields
    required = {
        "member_id", "provider_id", "diagnosis_code",
        "procedure_code", "claimed_amount", "date_of_service",
    }
    missing = required - populated
    for f in missing:
        warnings.append(f"Could not extract required field: {f}")

    return data, warnings, populated


def _compute_confidence(populated: set[str], warnings: list[str]) -> float:
    """
    Score based on how many of the 11 possible fields were populated,
    penalised by the number of warnings.
    """
    total_fields = 11
    base = len(populated) / total_fields
    warning_penalty = min(len(warnings) * 0.05, 0.3)
    return round(max(0.0, base - warning_penalty), 3)


def extract_claim_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Main entry point. Returns a dict matching PdfExtractionResult schema.
    """
    text = _extract_text_from_pdf(pdf_bytes)

    if not text.strip():
        return {
            "extracted_data": {},
            "validation_errors": ["Could not extract any text from PDF"],
            "is_valid": False,
            "extraction_warnings": ["PDF appears to be empty or unreadable"],
            "confidence": 0.0,
            "provider_name": "pymupdf+tesseract",
        }

    data, warnings, populated = _extract_fields(text)

    required = {"member_id", "provider_id", "diagnosis_code", "procedure_code", "claimed_amount", "date_of_service"}
    missing  = required - populated

    validation_errors = [f"Missing required field: {f}" for f in missing]
    is_valid = len(validation_errors) == 0
    confidence = _compute_confidence(populated, warnings)

    return {
        "extracted_data": data,
        "validation_errors": validation_errors,
        "is_valid": is_valid,
        "extraction_warnings": warnings,
        "confidence": confidence,
        "provider_name": "pymupdf+tesseract",
    }
