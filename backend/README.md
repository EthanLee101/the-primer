# The Primer — Backend

FastAPI service for the adaptive arithmetic tutor: deterministic problem
generation, per-skill mastery tracking, and an LLM explanation layer for wrong
answers. See `../adaptive_tutor_handoff.md` for product context.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run Postgres locally

```bash
docker compose up -d
```

## Database migrations

Schema is managed with Alembic. Models live in `app/models.py`.

```bash
alembic upgrade head                              # apply migrations
alembic revision --autogenerate -m "description"  # generate a new one after model changes
```

In production, `DATABASE_URL` points at Neon instead of the local Docker
container — see `.env.example` for the connection string format.

## Run the API

```bash
uvicorn app.main:app --reload
curl localhost:8000/health
```

## LLM explanations (Gemini)

`.env`'s `LLM_PROVIDER` defaults to `fake` — deterministic, no network call,
no API key needed. To try real Gemini-generated explanations manually:

```bash
# in .env
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your key from Google AI Studio>
```

The automated test suite always forces `LLM_PROVIDER=fake` regardless of
`.env` (see `tests/conftest.py`), so running `pytest` never makes real,
billed API calls even with a real key configured for manual testing.

## Test

```bash
pytest
ruff check .
mypy app
```
