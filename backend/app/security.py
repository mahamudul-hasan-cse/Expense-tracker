from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import get_settings

TokenType = Literal["access", "refresh"]

_hasher = PasswordHasher()
# Verified against when the email doesn't exist, so login timing doesn't reveal accounts
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: Optional[str], password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def create_token(user_id: UUID, token_type: TokenType, version: int) -> tuple[str, int]:
    """Create a signed JWT. Returns (token, lifetime in seconds)."""
    settings = get_settings()
    if token_type == "access":
        lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    else:
        lifetime = timedelta(days=settings.refresh_token_expire_days)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        # Bumped on logout, which invalidates every token issued before it
        "ver": version,
        "iat": now,
        "exp": now + lifetime,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, int(lifetime.total_seconds())


def decode_token(token: str, expected_type: TokenType) -> Optional[dict]:
    """Return the token payload, or None if invalid, expired or the wrong type."""
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "type", "ver", "exp"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload
