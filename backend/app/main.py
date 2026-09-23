from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import attempts, children

app = FastAPI(title="The Primer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(children.router)
app.include_router(attempts.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
