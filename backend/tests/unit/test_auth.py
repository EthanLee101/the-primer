from datetime import UTC, datetime, timedelta

import jwt

from app.auth import create_session_token, decode_session_token, hash_password, verify_password
from app.config import get_settings


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_wrong_password_fails() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_verify_against_missing_account_fails_without_raising() -> None:
    # None simulates "no account with this email" — must fail closed, not raise
    assert verify_password("anything", None) is False


def test_hash_is_never_the_plaintext() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert "correct horse battery staple" not in hashed


def test_session_token_roundtrip() -> None:
    token = create_session_token(parent_id=42)
    assert decode_session_token(token) == 42


def test_tampered_token_is_rejected() -> None:
    token = create_session_token(parent_id=42)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert decode_session_token(tampered) is None


def test_expired_token_is_rejected() -> None:
    settings = get_settings()
    expired = jwt.encode(
        {"sub": "42", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    assert decode_session_token(expired) is None


def test_token_signed_with_wrong_secret_is_rejected() -> None:
    forged = jwt.encode(
        {"sub": "42", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "a-completely-different-secret",
        algorithm="HS256",
    )
    assert decode_session_token(forged) is None
