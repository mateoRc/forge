from fastapi import FastAPI, Response, status
from fastapi.responses import PlainTextResponse

from app.dashboard import render
from app.metrics import Metrics
from app.models import Event, Summary

app = FastAPI(title="Forge")
metrics = Metrics()


@app.get("/healthz", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.post("/events", status_code=status.HTTP_204_NO_CONTENT)
def record_event(event: Event) -> Response:
    metrics.record(event)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/summary")
def summary() -> Summary:
    return metrics.summary()


@app.get("/dashboard", response_class=PlainTextResponse)
def dashboard() -> str:
    return render(metrics.summary())
