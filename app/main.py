from typing import Annotated

from fastapi import FastAPI, Query, Response, status
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


OptionalFilter = Annotated[str | None, Query(min_length=1)]


@app.get("/summary")
def summary(
    service: OptionalFilter = None,
    event: OptionalFilter = None,
    name: OptionalFilter = None,
) -> Summary:
    return metrics.summary(service=service, event=event, name=name)


@app.get("/dashboard", response_class=PlainTextResponse)
def dashboard(
    width: Annotated[int, Query(ge=1, le=100)] = 15,
    service: OptionalFilter = None,
    event: OptionalFilter = None,
    name: OptionalFilter = None,
) -> str:
    return render(
        metrics.summary(service=service, event=event, name=name),
        width=width,
    )
