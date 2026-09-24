"""Password hashing and JWT session tokens for parent auth.

Sessions are Bearer tokens (JWT in an Authorization header), not cookies.
The frontend/backend are separate origins, and cross-origin cookies require
SameSite=None, which disables SameSite's CSRF protection — you'd then need a
separate CSRF-token scheme to stay safe. A bearer token sidesteps this
entirely: browsers don't auto-attach headers to cross-site requests the way
they auto-attach cookies, so CSRF isn't a relevant attack surface here.
Trade-off: the frontend must hold the token in memory (never localStorage,
which is readable by any injected script), so a page refresh logs the parent
out — deliberate for v1, not an oversight.
"""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Parent

_hasher = PasswordHasher()

# a real (but unusable — no one knows this password) hash to verify against
# when an email isn't registered, so a login attempt against a nonexistent
# account takes the same time as one against a real account with a wrong
# password. Without this, response timing alone could reveal which emails
# are registered.
_DUMMY_HASH = _hasher.hash("not-a-real-account-timing-safety-only")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        _hasher.verify(password_hash or _DUMMY_HASH, password)
    except Exception:
        # fail closed: any verification error (wrong password, malformed
        # hash, anything) means "not authenticated," never "authenticated"
        return False
    return password_hash is not None


# Same dummy-hash timing-safety trick as _DUMMY_HASH, for the PIN unlock
# path (POST /parents/pin-login).
_DUMMY_PIN_HASH = _hasher.hash("not-a-real-pin-timing-safety-only")


def hash_pin(pin: str) -> str:
    return _hasher.hash(pin)


def verify_pin(pin: str, pin_hash: str | None) -> bool:
    # pin_hash is None in two distinct cases: the parent doesn't exist, or
    # they exist but never set a PIN. Both must fail identically — timing,
    # status code, and response body — so pin-login can't be used to probe
    # which case it is.
    try:
        _hasher.verify(pin_hash or _DUMMY_PIN_HASH, pin)
    except Exception:
        return False
    return pin_hash is not None


def create_session_token(parent_id: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    return jwt.encode(
        {"sub": str(parent_id), "exp": expires_at}, settings.jwt_secret_key, algorithm="HS256"
    )


def decode_session_token(token: str) -> int | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        return int(payload["sub"])
    except jwt.PyJWTError:
        return None


def get_current_parent(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> Parent:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    parent_id = decode_session_token(authorization.removeprefix("Bearer "))
    if parent_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    parent = db.get(Parent, parent_id)
    if parent is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return parent


def get_current_parent_optional(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> Parent | None:
    """For endpoints usable both logged-out and logged-in — e.g. child
    creation still works with no session, but links to the parent when one
    is active."""
    if authorization is None:
        return None
    try:
        return get_current_parent(authorization=authorization, db=db)
    except HTTPException:
        return None
