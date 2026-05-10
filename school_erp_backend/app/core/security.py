"""Password hashing + JWT helpers. Auth flows are wired in Phase 2."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def _create_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(data: Dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    minutes = expires_minutes or settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    return _create_token({**data, "type": "access"}, timedelta(minutes=minutes))


def create_refresh_token(data: Dict[str, Any]) -> str:
    return _create_token({**data, "type": "refresh"}, timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
