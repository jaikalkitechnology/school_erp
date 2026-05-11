"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, List, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Jaikalki School ERP"
    COMPANY_NAME: str = "Jaikalki Technology Pvt Ltd"
    DEBUG: bool = True
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Database
    # Dev default uses SQLite for fast local iteration; .env switches to MySQL for prod.
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    DATABASE_URL_SYNC: str = "sqlite:///./dev.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    # 2 hours: short enough that compromised tokens have a small blast
    # radius, long enough that a school admin's session survives a coffee
    # break. The refresh-token rotation flow gives indefinite freshness
    # while the user keeps using the app.
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS - Annotated[..., NoDecode] tells pydantic-settings to skip JSON parsing
    # so our custom validator can accept a plain comma-separated string from .env.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
    ]

    # Local file storage
    UPLOAD_DIR: Path = Path("uploads")
    MAX_UPLOAD_SIZE_MB: int = 10
    MAX_IMAGE_WIDTH: int = 1920
    ALLOWED_FILE_TYPES: Annotated[List[str], NoDecode] = ["jpg", "jpeg", "png", "pdf", "docx", "xlsx"]

    # Per-tenant storage limits (MB)
    STORAGE_LIMIT_BASIC: int = 5_120
    STORAGE_LIMIT_STANDARD: int = 25_600
    STORAGE_LIMIT_PREMIUM: int = 102_400

    # Payment gateway (Razorpay)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # SMS (MSG91 / Twilio)
    SMS_PROVIDER: str = "msg91"
    MSG91_AUTH_KEY: str = ""
    MSG91_SENDER_ID: str = "JKLKSC"

    # Email (SendGrid)
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@jaikalki.com"

    # Firebase (push). Path is relative to the backend root by default;
    # override with FIREBASE_CREDENTIALS_PATH in the .env to point at the
    # actual service-account JSON Google Cloud gave you.
    FIREBASE_CREDENTIALS_PATH: str = "./school-jaikalki-firebase-adminsdk-fbsvc-5b1fcf0080.json"

    # Multi-tenant defaults
    DEFAULT_TENANT_LIMIT_STUDENTS: int = 500
    TRIAL_PERIOD_DAYS: int = 30
    PLATFORM_HOSTS: Annotated[List[str], NoDecode] = ["localhost", "127.0.0.1", "admin.jaikalki.com"]

    @field_validator("CORS_ORIGINS", "ALLOWED_FILE_TYPES", "PLATFORM_HOSTS", mode="before")
    @classmethod
    def split_list(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
