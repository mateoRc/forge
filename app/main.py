import time
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse

from app.auth import require_service_token
from app.dashboard import render
from app.metrics import Metrics
from app.models import Event, Summary, Visit

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


@app.post(
    "/visits",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_service_token)],
)
def record_visit(visit: Visit) -> Response:
    metrics.record_visit(visit.visitor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


OptionalFilter = Annotated[
    str | None,
    Query(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
TimeWindow = Annotated[int | None, Query()]


def selected_window(hours: int | None, window: str | None) -> int | None:
    if hours is not None and hours not in (24, 168, 720):
        raise HTTPException(status_code=422, detail="hours must be 24, 168, or 720")
    if window == "all":
        if hours is not None:
            raise HTTPException(status_code=422, detail="Use either hours or window=all")
        return None
    return 24 if hours is None else hours


@app.get("/summary", dependencies=[Depends(require_service_token)])
def summary(
    hours: TimeWindow = None,
    window: Literal["all"] | None = None,
    service: OptionalFilter = None,
    event: OptionalFilter = None,
    name: OptionalFilter = None,
    include_invalid: bool = False,
) -> Summary:
    return metrics.summary(
        window_hours=selected_window(hours, window),
        service=service,
        event=event,
        name=name,
        include_invalid=include_invalid,
    )


@app.get(
    "/dashboard",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_service_token)],
)
def dashboard(
    width: Annotated[int, Query(ge=1, le=100)] = 15,
    hours: TimeWindow = None,
    window: Literal["all"] | None = None,
    service: OptionalFilter = None,
    event: OptionalFilter = None,
    name: OptionalFilter = None,
    include_invalid: bool = False,
) -> str:
    return render(
        metrics.summary(
            window_hours=selected_window(hours, window),
            service=service,
            event=event,
            name=name,
            include_invalid=include_invalid,
        ),
        width=width,
    )
