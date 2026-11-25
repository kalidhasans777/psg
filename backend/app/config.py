from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "MEDORA"
    APP_TAGLINE: str = "One Patient. One Permanent ID. A Complete Medical Journey."
    APP_ENV: str = "development"
    DEBUG: bool = True

    SECRET_KEY: str = "medora-dev-secret-key-change-in-production-32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Default uses SQLite only when no PostgreSQL URL is configured; production & Docker use PostgreSQL
    DATABASE_URL: str = f"sqlite:///{(BASE_DIR / 'medora_dev.db').as_posix()}"

    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 15

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    VOICE_PROVIDER: str = "auto"
    GOOGLE_CLOUD_SPEECH_API_KEY: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = "centralindia"

    RATE_LIMIT_PER_MINUTE: int = 180
    AUTH_RATE_LIMIT_PER_MINUTE: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    return settings
