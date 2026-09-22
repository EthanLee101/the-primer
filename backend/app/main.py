from fastapi import FastAPI

app = FastAPI(title="The Primer API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
