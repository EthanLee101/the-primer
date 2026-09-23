"""Test configuration.

Forces LLM_PROVIDER=fake regardless of what's in the developer's local .env.
Once a real GEMINI_API_KEY + LLM_PROVIDER=gemini are set for manual testing,
an unguarded test suite would otherwise make real, billed Gemini calls every
time `pytest` runs — this must be set before app.config.get_settings() (via
any import of app.main) is ever evaluated, hence the import ordering below.
"""

import os

os.environ["LLM_PROVIDER"] = "fake"

import pytest  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    # the rate limiter's storage is shared process-wide (app.state.limiter),
    # so without this, unrelated tests would pollute each other's request
    # counts and start failing with 429s depending on run order
    app.state.limiter.reset()
