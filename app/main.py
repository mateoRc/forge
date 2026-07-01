from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI(title="Forge")


@app.get("/healthz", response_class=PlainTextResponse)
def health() -> str:
    return "ok"

