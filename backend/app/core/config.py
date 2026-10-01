import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables.

    No secret is ever hard-coded. Everything degrades gracefully when unset.
    """

    def __init__(self) -> None:
        load_dotenv()
        self.app_name: str = "CyberVerse AI"
        self.api_prefix: str = "/api"
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
            ).split(",")
            if o.strip()
        ]
        self.mongodb_uri: str = os.getenv("MONGODB_URI", "")
        self.mongodb_db: str = os.getenv("MONGODB_DB", "cyberverse")
        self.ai_api_key: str = os.getenv("AI_API_KEY", "")
        self.ai_api_base: str = os.getenv("AI_API_BASE", "https://api.openai.com/v1")
        self.ai_model: str = os.getenv("AI_MODEL", "gpt-4o-mini")
        self.ai_provider: str = os.getenv("AI_PROVIDER", "local")
        self.rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "240"))
        self.max_events_retained: int = int(os.getenv("MAX_EVENTS_RETAINED", "5000"))
        self.model_path: str = os.getenv(
            "MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "models", "isolation_forest.joblib")
        )

    @property
    def mongo_enabled(self) -> bool:
        return bool(self.mongodb_uri)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.ai_api_key) and self.ai_provider in {"openai", "anthropic", "custom"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
