import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from extraction.factory import get_vision_provider
from extraction.validator import validate_extracted_claim
import json

# Test PDF path
pdf_path = "data/samples/Sharma Siddharth Claim Form.pdf"

def test_provider(provider_name: str, model: str = None):
    print(f"\n[ Provider: {provider_name.upper()} ]")
    print("-" * 40)
    try:
        provider  = get_vision_provider(provider_name, model=model)
        extracted = provider.extract(pdf_path)
        validated = validate_extracted_claim(extracted)

        print(f"Valid for adjudication : {validated['is_valid']}")
        print(f"Confidence             : {validated['confidence']}")

        if validated["extraction_warnings"]:
            print(f"Warnings:")
            for w in validated["extraction_warnings"]:
                print(f"  ⚠ {w}")

        if validated["validation_errors"]:
            print(f"Validation errors:")
            for e in validated["validation_errors"]:
                print(f"  ✗ {e}")

        print(f"\nExtracted fields:")
        skip = {"raw_text", "extraction_warnings", "validation_errors", "is_valid"}
        for key, value in validated.items():
            if key not in skip:
                status = "✓" if value else "✗"
                print(f"  {status} {key:<25} {value}")

        return validated

    except Exception as e:
        print(f"  Provider error: {e}")
        return None


print("=" * 55)
print("PDF EXTRACTION COMPARISON TEST")
print(f"File: {pdf_path}")
print("=" * 55)

# Test Tesseract
test_provider("tesseract")

# Test Gemini
test_provider("gemini")