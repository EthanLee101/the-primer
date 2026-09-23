"""LLM explanation layer — Gemini generates a warm, age-appropriate
explanation when a child answers incorrectly. Deliberately kept out of the
grading path entirely: app/problems.py already decided correctness before
this ever runs, and every failure mode here (missing key, network error,
quota exceeded, malformed response) degrades to "no bonus explanation this
time" rather than breaking the answer-submission response the child is
waiting on.
"""

import logging

from google import genai
from google.genai import errors, types

from app.config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are a warm, encouraging tutor for a child aged 5 to 9 who is learning "
    "arithmetic. The child just answered a problem incorrectly. In one or two "
    "short, simple sentences, gently explain why their answer was wrong and "
    "what the correct answer is. Use kind, age-appropriate language. Never be "
    "sarcastic or make the child feel bad. Do not mention anything beyond this "
    "one problem."
)

_MODEL = "gemini-flash-latest"


def generate_explanation(prompt: str, submitted_answer: int, correct_answer: int) -> str | None:
    """Returns None on any failure. The caller must treat a missing
    explanation as "nothing extra this time," never as a request failure —
    grading has already succeeded by the time this is called."""
    settings = get_settings()

    if settings.llm_provider == "fake":
        # deterministic, no network call — used in dev/tests so the suite
        # never depends on a real API key or a live network call
        return f"Not quite — {prompt} is {correct_answer}, not {submitted_answer}."

    if not settings.gemini_api_key:
        logger.error("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set")
        return None

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=_MODEL,
            contents=(
                f"Problem: {prompt}\nChild's answer: {submitted_answer}\n"
                f"Correct answer: {correct_answer}"
            ),
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                # this model spends output tokens on internal "thinking"
                # before the visible answer, and a 0 budget doesn't fully
                # suppress that — found by inspecting a truncated response's
                # usage_metadata (thoughts_token_count was eating the whole
                # budget, finish_reason=MAX_TOKENS, response.text=None).
                # Disabling thinking plus a generous headroom keeps a short
                # 1-2 sentence reply well clear of the limit.
                max_output_tokens=200,
                temperature=0.7,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        if not response.text:
            finish_reason = response.candidates[0].finish_reason if response.candidates else None
            logger.warning("Gemini returned no text (finish_reason=%s)", finish_reason)
            return None
        return response.text
    except errors.APIError as exc:
        logger.error("Gemini API error (code=%s): %s", exc.code, exc.message)
        return None
    except Exception:
        # broad on purpose: this is optional enrichment after grading has
        # already succeeded, so no exception here may propagate and turn a
        # successful answer submission into a failed request
        logger.exception("Unexpected error calling Gemini")
        return None
