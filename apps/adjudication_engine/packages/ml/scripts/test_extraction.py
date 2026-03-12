import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from extraction.fallback import extract_with_fallback
import json

pdf_path = "data/samples/Sharma Siddharth Claim Form.pdf"

print("=" * 55)
print("PDF EXTRACTION WITH FALLBACK CHAIN")
print(f"File: {pdf_path}")
print("=" * 55)

result = extract_with_fallback(pdf_path, provider="gemini")

print(f"\nFinal result:")
print(f"  Valid for adjudication : {result['is_valid']}")
print(f"  Provider used          : {result.get('provider_used')}")
print(f"  Confidence             : {result.get('confidence')}")

print(f"\nFallback attempts:")
for attempt in result.get("fallback_attempts", []):
    status = "✓" if attempt.get("success") else "✗"
    print(f"  {status} {attempt['provider']}")

print(f"\nExtracted fields:")
skip = {"raw_text", "extraction_warnings", "validation_errors",
        "is_valid", "fallback_attempts", "provider_used"}
for key, value in result.items():
    if key not in skip and value is not None:
        print(f"  ✓ {key:<25} {value}")

if result.get("extraction_warnings"):
    print(f"\nWarnings:")
    for w in result["extraction_warnings"]:
        print(f"  ⚠ {w}")

if result.get("validation_errors"):
    print(f"\nValidation errors:")
    for e in result["validation_errors"]:
        print(f"  ✗ {e}")