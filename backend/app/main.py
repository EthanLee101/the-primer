import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.logging_config import configure_logging
from app.rate_limit import limiter
from app.routers import attempts, children

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="The Primer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait a moment and try again."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full detail server-side only — nothing about the exception (type,
    # message, traceback) is ever included in the response body. FastAPI's
    # own HTTPException handler runs before this (it's more specific), so
    # deliberate 4xx/5xx responses raised via HTTPException are unaffected;
    # this only catches truly unexpected failures.
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Please try again."},
    )


app.include_router(children.router)
app.include_router(attempts.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
