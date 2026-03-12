import os
from extraction.providers.base import BaseVisionProvider


def get_vision_provider(
    provider: str = None,
    model:    str = None,
) -> BaseVisionProvider:
    """
    Factory function: returns the correct vision provider
    based on configuration or the provider parameter.

    This is the only place in the codebase that knows about
    all the different providers. Everything else just calls
    get_vision_provider() and uses the result.

    provider: "gemini" | "ollama" | "qwen" | "tesseract"
              defaults to VISION_PROVIDER env variable
              defaults to "tesseract" if not set

    model:    optional model name override
              e.g. model="qwen2-vl" when provider="ollama"
              e.g. model="gemini-1.5-pro" when provider="gemini"

    Usage examples:
        provider = get_vision_provider()
        provider = get_vision_provider("gemini")
        provider = get_vision_provider("ollama", model="llava")
        provider = get_vision_provider("ollama", model="qwen2-vl")
    """
    selected = (
        provider or
        os.getenv("VISION_PROVIDER", "tesseract")
    ).lower()

    if selected == "gemini":
        from extraction.providers.gemini import GeminiProvider
        return GeminiProvider(model_name=model)

    elif selected == "qwen":
        from extraction.providers.qwen import QwenProvider
        return QwenProvider()

    elif selected == "ollama":
        from extraction.providers.ollama import OllamaProvider
        return OllamaProvider(model=model)

    elif selected == "tesseract":
        from extraction.providers.tesseract import TesseractProvider
        return TesseractProvider()

    else:
        raise ValueError(
            f"Unknown vision provider: '{selected}'. "
            f"Valid options: gemini, ollama, qwen, tesseract"
        )