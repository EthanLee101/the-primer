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

## Run the API

```bash
uvicorn app.main:app --reload
curl localhost:8000/health
```

## Test

```bash
pytest
ruff check .
mypy app
```
