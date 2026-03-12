from abc import ABC, abstractmethod


class BaseVisionProvider(ABC):
    """
    Abstract base class for all vision providers.

    Every provider i.e. Gemini, Ollama, Qwen, Tesseract, must implement the extract() method.
    """

    @abstractmethod
    def extract(self, pdf_path: str) -> dict:
        """
        Extracts structured claim fields from a PDF file.
        pdf_path: absolute or relative path to the PDF file
        Returns a dictionary with these fields where found:
        {
            "claim_id": str or None,
            "member_id": str or None,
            "provider_id": str or None,
            "diagnosis_code":  str or None,
            "procedure_code":  str or None,
            "claimed_amount":  float or None,
            "approved_tariff": float or None,
            "date_of_service": str or None,
            "provider_type":   str or None,
            "location": str or None,
            "member_age": int or None,
            "raw_text": str, # full extracted text
            "provider_name": str or None, # extraction metadata
            "confidence": str, # high / medium / low
            "extraction_warnings": list[str], # any issues found
        }
        """
        pass

    def _empty_result(self) -> dict:
        """
        Returns an empty result template.
        Used when extraction fails completely.
        """
        return {
            "claim_id": None,
            "member_id": None,
            "provider_id": None,
            "diagnosis_code": None,
            "procedure_code": None,
            "claimed_amount": None,
            "approved_tariff": None,
            "date_of_service": None,
            "provider_type": None,
            "location": None,
            "member_age": None,
            "raw_text": "",
            "provider_name": self.__class__.__name__,
            "confidence": "low",
            "extraction_warnings": ["Extraction failed completely"],
        }