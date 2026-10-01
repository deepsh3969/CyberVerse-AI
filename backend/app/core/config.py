import os
import secrets
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Application settings loaded from environment variables.

    No secret is ever hard-coded. Everything degrades gracefully when unset so
    the product still runs in DEMO MODE with no database and no auth provider.
    """

    def __init__(self) -> None:
        load_dotenv()
        self.app_name: str = "CyberVerse AI"
        self.api_prefix: str = "/api"
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.is_production: bool = self.environment == "production"
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
            ).split(",")
            if o.strip()
        ]

        # ------------------------------------------------------------ storage
        # Empty DATABASE_URL keeps the in-memory demo store (no durability).
        self.database_url: str = os.getenv("DATABASE_URL", "").strip()
        self.db_autocreate: bool = _bool("DB_AUTOCREATE", "true")
        self.db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_events_retained: int = int(os.getenv("MAX_EVENTS_RETAINED", "5000"))
        self.db_events_loaded: int = int(os.getenv("DB_EVENTS_LOADED", "2000"))

        # -------------------------------------------------------------- auth
        self.auth_enabled: bool = _bool("AUTH_ENABLED", "true")
        self.auth_require_read: bool = _bool("AUTH_REQUIRE_READ", "false")
        self.jwt_secret: str = os.getenv("JWT_SECRET", "").strip()
        self._ephemeral_secret = not self.jwt_secret
        if self._ephemeral_secret:
            # Development fallback: a fresh secret per process. Production must
            # set JWT_SECRET explicitly (enforced by `validate()` at startup).
            self.jwt_secret = secrets.token_urlsafe(48)
        self.jwt_algorithm: str = "HS256"
        self.access_token_ttl: int = int(os.getenv("ACCESS_TOKEN_TTL", "900"))
        self.refresh_token_ttl: int = int(os.getenv("REFRESH_TOKEN_TTL", "604800"))
        self.seed_admin_email: str = os.getenv("SEED_ADMIN_EMAIL", "admin@cyberverse.local")
        self.seed_admin_password: str = os.getenv("SEED_ADMIN_PASSWORD", "")
        self.bcrypt_rounds: int = int(os.getenv("BCRYPT_ROUNDS", "12"))
        self.auth_login_limit_per_minute: int = int(os.getenv("AUTH_LOGIN_LIMIT_PER_MINUTE", "10"))

        # ------------------------------------------------------- observability
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format: str = (
            os.getenv("LOG_FORMAT", "").strip()
            or ("json" if self.is_production else "text")
        ).lower()
        self.metrics_enabled: bool = _bool("METRICS_ENABLED", "true")
        self.max_body_bytes: int = int(os.getenv("MAX_BODY_BYTES", "1048576"))
        self.trust_proxy: bool = _bool("TRUST_PROXY", "true")

        # ----------------------------------------------------------------- AI
        self.ai_api_key: str = os.getenv("AI_API_KEY", "")
        self.ai_api_base: str = os.getenv("AI_API_BASE", "https://api.openai.com/v1")
        self.ai_model: str = os.getenv("AI_MODEL", "gpt-4o-mini")
        self.ai_provider: str = os.getenv("AI_PROVIDER", "local")

        # --------------------------------------------------------------- abuse
        self.rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "240"))

        self.model_path: str = os.getenv(
            "MODEL_PATH",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "models", "isolation_forest.joblib"),
        )

    # ------------------------------------------------------------- properties
    @property
    def db_enabled(self) -> bool:
        return bool(self.database_url)

    @property
    def auth_active(self) -> bool:
        """Authentication is only enforced when a database backs it."""
        return self.auth_enabled and self.db_enabled

    @property
    def llm_enabled(self) -> bool:
        return bool(self.ai_api_key) and self.ai_provider in {"openai", "anthropic", "custom"}

    @property
    def jwt_secret_ephemeral(self) -> bool:
        """True when JWT_SECRET was not provided (dev-only convenience)."""
        return self._ephemeral_secret

    @property
    def cookies_secure(self) -> bool:
        return _bool("COOKIES_SECURE", "true" if self.is_production else "false")

    def validate(self) -> list[str]:
        """Return fatal configuration problems (empty list == healthy)."""
        problems: list[str] = []
        if self.is_production:
            if self._ephemeral_secret:
                problems.append("JWT_SECRET must be set explicitly in production")
            if len(self.jwt_secret) < 32:
                problems.append("JWT_SECRET must be at least 32 characters")
            if self.auth_enabled and not self.seed_admin_password:
                problems.append("SEED_ADMIN_PASSWORD must be set when AUTH_ENABLED=true in production")
            if self.auth_enabled and not self.database_url:
                problems.append("DATABASE_URL must be set when AUTH_ENABLED=true in production")
            if not self.cors_origins or self.cors_origins == ["*"]:
                problems.append("CORS_ORIGINS must list explicit origins in production")
        return problems


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
