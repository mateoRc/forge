from app.metrics import Metrics
from app.models import Event


def test_aggregates_requests_errors_duration_services_and_commands() -> None:
    metrics = Metrics()
    metrics.record(_event("vault", "grep", 8, 0))
    metrics.record(_event("vault", "cat", 4, 1))
    metrics.record(_event("atlas", "search", 6, 0))

    summary = metrics.summary()

    assert summary.requests == 3
    assert summary.errors == 1
    assert summary.avg_ms == 6
    assert summary.services == {"vault": 2, "atlas": 1}
    assert summary.commands == {"grep": 1, "cat": 1, "search": 1}


def _event(service: str, name: str, duration_ms: int, exit_code: int) -> Event:
    return Event(
        service=service,
        event="request.completed",
        name=name,
        duration_ms=duration_ms,
        exit_code=exit_code,
    )

