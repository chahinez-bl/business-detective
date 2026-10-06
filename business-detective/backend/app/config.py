"""Central configuration. Every deploy-time value comes from environment variables (see .env.example)."""
import os
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    def __init__(self) -> None:
        self.env = os.getenv("APP_ENV", "development").lower()          # development | staging | production
        self.database_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'businessdetective.sqlite'}")
        if self.database_url.startswith("postgres://"):                   # some hosts still hand out the legacy scheme
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        self.secret_key = os.getenv("SECRET_KEY", "")
        self.token_ttl_minutes = int(os.getenv("TOKEN_TTL_MINUTES", "720"))
        self.cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
        self.max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "15"))
        self.max_rows = int(os.getenv("MAX_ROWS", "300000"))
        self.storage_dir = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
        self.auto_create_tables = _bool("AUTO_CREATE_TABLES", self.env == "development")
        self.frontend_dist = os.getenv("FRONTEND_DIST", "")               # optional: serve the built SPA from the API process
        # Optional external AI (OFF by default; only aggregated analytical facts are ever sent, never raw rows)
        self.ai_provider = os.getenv("AI_PROVIDER", "rules").lower()      # rules | openai_compatible
        self.ai_api_url = os.getenv("AI_API_URL", "")
        self.ai_api_key = os.getenv("AI_API_KEY", "")
        self.ai_model = os.getenv("AI_MODEL", "")
        self.default_currency = os.getenv("DEFAULT_CURRENCY", "DZD")
        self.login_max_failures = int(os.getenv("LOGIN_MAX_FAILURES", "8"))

        if not self.secret_key:
            if self.env == "production":
                raise RuntimeError("SECRET_KEY must be set in production (use a long random value).")
            self.secret_key = "dev-only-insecure-secret-change-me-0123456789"   # development fallback only
        if self.env == "production" and len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be at least 32 characters in production.")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
