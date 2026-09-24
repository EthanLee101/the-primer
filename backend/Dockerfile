FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY alembic ./alembic

RUN pip install --no-cache-dir .

EXPOSE 8000

# Shell form (not exec-form array) deliberately — needed for both $PORT
# expansion (the host sets this dynamically; 8000 is just the local
# fallback) and the && chain. Migrations run as part of every container
# start, not as a separate deploy hook, so this image is correct on any
# host regardless of whether that host offers a pre/release-deploy step —
# idempotent (alembic upgrade head is a no-op once already at head), so
# this is safe to repeat on every restart, not just on real deploys.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
