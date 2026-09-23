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

## Parent accounts

`POST /parents` registers, `POST /parents/login` logs in — both return an
`access_token` (JWT). Send it as `Authorization: Bearer <token>` on
`GET /parents/me` and `GET /parents/me/children`. There's no login UI yet
(that's increment 10); test it directly, e.g.:

```bash
curl -X POST localhost:8000/parents \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "at least 8 characters"}'
```

Sessions are bearer tokens, not cookies — see `app/auth.py` for why (short
version: this API and the frontend are different origins, and cross-origin
cookies need `SameSite=None`, which disables SameSite's CSRF protection).
The frontend will hold the token in memory once increment 10 builds the
login UI, so a page refresh will require logging in again — deliberate,
not a bug.

Set `JWT_SECRET_KEY` in `.env` before deploying anywhere real — see the
comment in `.env.example` for why an unset one is fine for local dev but
not for production.

## Test

```bash
pytest
ruff check .
mypy app
```
