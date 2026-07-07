import time
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Query, Response, status
from fastapi.responses import PlainTextResponse

from app.auth import require_service_token
from app.dashboard import render
from app.metrics import Metrics
from app.models import Event, Summary

app = FastAPI(title="Forge")
metrics = Metrics.from_environment()
STARTED_AT = time.monotonic()


@app.get("/healthz", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.get("/status")
def service_status() -> dict[str, int | str]:
    return {
        "status": "ok",
        "uptime_seconds": int(time.monotonic() - STARTED_AT),
    }


@app.post(
    "/events",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_service_token)],
)
def record_event(event: Event) -> Response:
    metrics.record(event)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


OptionalFilter = Annotated[
    str | None,
    Query(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
TimeWindow = Annotated[Literal[24, 168, 720], Query()]


@app.get("/summary", dependencies=[Depends(require_service_token)])
def summary(
    hours: TimeWindow = 24,
    service: OptionalFilter = None,
    event: OptionalFilter = None,
    name: OptionalFilter = None,
) -> Summary:
    return metrics.summary(
        window_hours=hours,
        service=service,
        event=event,
        name=name,
    )


@app.get(
    "/dashboard",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_service_token)],
)
def dashboard(
    width: Annotated[int, Query(ge=1, le=100)] = 15,
    hours: TimeWindow = 24,
    service: OptionalFilter = None,
    event: OptionalFilter = None,
    name: OptionalFilter = None,
) -> str:
    return render(
        metrics.summary(
            window_hours=hours,
            service=service,
            event=event,
            name=name,
        ),
        width=width,
    )
