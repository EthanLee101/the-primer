from unittest.mock import patch

from app.config import Settings


def test_jwt_secret_key_falls_back_when_unset() -> None:
    with patch.dict("os.environ", {}, clear=False):
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert len(settings.jwt_secret_key) > 0


def test_jwt_secret_key_falls_back_when_present_but_empty() -> None:
    """Regression test: JWT_SECRET_KEY= (present, empty) in .env is a
    different case from the var being absent entirely — pydantic-settings
    takes an empty string literally, so default_factory alone doesn't cover
    it. Without the field_validator in app/config.py, this would silently
    produce an empty JWT signing secret (every token forgeable)."""
    with patch.dict("os.environ", {"JWT_SECRET_KEY": ""}):
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.jwt_secret_key != ""
    assert len(settings.jwt_secret_key) >= 32


def test_jwt_secret_key_respects_a_real_configured_value() -> None:
    with patch.dict("os.environ", {"JWT_SECRET_KEY": "a-real-configured-secret"}):
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.jwt_secret_key == "a-real-configured-secret"
