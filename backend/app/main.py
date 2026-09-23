from fastapi import FastAPI

from app.routers import attempts, children

app = FastAPI(title="The Primer API")
app.include_router(children.router)
app.include_router(attempts.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
