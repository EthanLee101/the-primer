from unittest.mock import MagicMock, patch

from app.config import get_settings
from app.llm import generate_explanation

_GEMINI_ENV = {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "fake-key-for-test"}


def test_fake_provider_returns_deterministic_explanation() -> None:
    result = generate_explanation("4 + 7", submitted_answer=12, correct_answer=11)
    assert result is not None
    assert "11" in result
    assert "12" in result


def test_gemini_provider_without_api_key_returns_none() -> None:
    get_settings.cache_clear()
    with patch.dict("os.environ", {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": ""}):
        result = generate_explanation("4 + 7", submitted_answer=12, correct_answer=11)
    get_settings.cache_clear()
    assert result is None


def test_gemini_client_exception_is_caught_and_returns_none() -> None:
    get_settings.cache_clear()
    with patch.dict("os.environ", _GEMINI_ENV), patch("app.llm.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("network exploded")
        mock_client_cls.return_value = mock_client

        result = generate_explanation("4 + 7", submitted_answer=12, correct_answer=11)
    get_settings.cache_clear()

    assert result is None


def test_gemini_success_path_returns_model_text() -> None:
    get_settings.cache_clear()
    with patch.dict("os.environ", _GEMINI_ENV), patch("app.llm.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = MagicMock(text="You were close!")
        mock_client_cls.return_value = mock_client

        result = generate_explanation("4 + 7", submitted_answer=12, correct_answer=11)
    get_settings.cache_clear()

    assert result == "You were close!"


def test_no_visible_text_returns_none_without_crashing() -> None:
    """Regression test: a real call once came back with response.text=None and
    finish_reason=MAX_TOKENS — the model's internal "thinking" tokens ate the
    entire output budget before any visible answer was produced. Confirmed by
    inspecting usage_metadata.thoughts_token_count on a live truncated
    response. Must degrade to None, not raise, and not return an empty/junk
    string."""
    get_settings.cache_clear()
    with patch.dict("os.environ", _GEMINI_ENV), patch("app.llm.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_candidate = MagicMock(finish_reason="MAX_TOKENS")
        mock_client.models.generate_content.return_value = MagicMock(
            text=None, candidates=[mock_candidate]
        )
        mock_client_cls.return_value = mock_client

        result = generate_explanation("4 + 7", submitted_answer=12, correct_answer=11)
    get_settings.cache_clear()

    assert result is None


def test_disables_thinking_and_sets_output_token_headroom() -> None:
    """Regression test: pins the fix for the truncation bug above — thinking
    must stay disabled and the token budget generous, so a future edit can't
    silently reintroduce the truncation."""
    get_settings.cache_clear()
    with patch.dict("os.environ", _GEMINI_ENV), patch("app.llm.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = MagicMock(text="ok")
        mock_client_cls.return_value = mock_client

        generate_explanation("4 + 7", submitted_answer=12, correct_answer=11)
    get_settings.cache_clear()

    _, kwargs = mock_client.models.generate_content.call_args
    config = kwargs["config"]
    assert config.thinking_config.thinking_budget == 0
    assert config.max_output_tokens >= 150
