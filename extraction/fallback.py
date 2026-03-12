import os
from dotenv import load_dotenv
from extraction.validator import validate_extracted_claim

load_dotenv()


def extract_with_fallback(
    pdf_path: str,
    provider: str = None,
    model:    str = None,
) -> dict:
    """
    Attempts PDF extraction using a chain of providers.
    If the primary provider fails or returns incomplete data,
    it automatically tries the next provider in the chain.

    This is called the 'Chain of Responsibility' pattern.
    Each provider gets a chance to handle the request.
    If it can't, it passes to the next.

    Fallback chain:
    1. Requested provider (or env default)
    2. Gemini (cloud, best quality)
    3. Tesseract (offline, digital PDFs only)

    This ensures the system degrades gracefully rather
    than failing completely when a provider is unavailable.
    Critically important for emerging markets where
    internet connectivity may be intermittent.
    """
    from extraction.factory import get_vision_provider

    # Build the provider chain
    # Primary provider is always first
    primary  = provider or os.getenv("VISION_PROVIDER", "gemini")
    chain    = _build_chain(primary)
    attempts = []

    for provider_name in chain:
        try:
            print(f"  Trying provider: {provider_name}")
            vision_provider = get_vision_provider(
                provider_name,
                model=model if provider_name == primary else None
            )
            extracted = vision_provider.extract(pdf_path)
            validated = validate_extracted_claim(extracted)

            attempts.append({
                "provider": provider_name,
                "success":  True,
                "valid":    validated["is_valid"],
            })

            # Track which providers were attempted
            validated["fallback_attempts"] = attempts
            validated["provider_used"]     = provider_name

            # If valid for adjudication, return immediately
            if validated["is_valid"]:
                print(f"  Extraction succeeded with: {provider_name}")
                return validated

            # If partially extracted, keep going to see if
            # another provider does better
            print(
                f"  {provider_name} extracted partially — "
                f"missing: {validated['validation_errors']}"
            )

            # Store best partial result in case all fail
            if provider_name == chain[0]:
                best_partial = validated

        except Exception as e:
            print(f"  {provider_name} failed: {e}")
            attempts.append({
                "provider": provider_name,
                "success":  False,
                "error":    str(e),
            })
            continue

    # All providers failed or returned incomplete data
    # Return the best partial result we got
    print("  All providers exhausted — returning best partial result")
    if "best_partial" in locals():
        best_partial["fallback_attempts"] = attempts
        return best_partial

    # Complete failure — return empty result with audit trail
    return {
        "is_valid":           False,
        "validation_errors":  ["All extraction providers failed"],
        "fallback_attempts":  attempts,
        "extraction_warnings": [
            "Extraction failed across all providers. "
            "Manual data entry required."
        ],
    }


def _build_chain(primary: str) -> list[str]:
    """
    Builds the fallback chain starting from the primary provider.
    Removes duplicates while preserving order.

    Example: primary="ollama" → ["ollama", "gemini", "tesseract"]
    Example: primary="gemini" → ["gemini", "tesseract"]
    """
    full_chain = ["gemini", "tesseract"]

    # Insert primary at the front if not already first
    if primary not in full_chain:
        return [primary] + full_chain
    elif primary != full_chain[0]:
        full_chain.remove(primary)
        return [primary] + full_chain

    return full_chain