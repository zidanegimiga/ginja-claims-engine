from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "production", "test"] = "development"

    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "ginja_claims"

    JWT_SECRET_KEY: str = ""
    API_KEY_PRIMARY: str = ""
    API_KEY_SECONDARY: str = ""

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "ginja-claims"

    VISION_PROVIDER: str = "tesseract"
    VISION_MODEL: str = ""
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_VISION_MODEL: str = "llava"
    QWEN_VISION_MODEL:  str = "qwen2-vl"

    MODEL_PATH: str = "model/artifacts/xgboost_model.json"
    FRAUD_THRESHOLD_PASS: float = 0.3
    FRAUD_THRESHOLD_FAIL: float = 0.7

    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def r2_endpoint_url(self) -> str:
        return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        origins = [self.FRONTEND_URL]
        if self.ENVIRONMENT == "development":
            origins += [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        return list(set(origins))

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
