import math
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from statistics import median

from app.models import Event, Summary
from app.storage import (
    DEFAULT_DATABASE_PATH,
    DEFAULT_MAX_DATABASE_BYTES,
    DEFAULT_RETENTION_DAYS,
    SQLiteEventStore,
)


class Metrics:
    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE_PATH,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        max_database_bytes: int = DEFAULT_MAX_DATABASE_BYTES,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = SQLiteEventStore(
            database_path=database_path,
            retention_days=retention_days,
            max_database_bytes=max_database_bytes,
            now=now,
        )

    @classmethod
    def from_environment(cls) -> "Metrics":
        return cls(
            database_path=os.getenv("FORGE_DATABASE_PATH", DEFAULT_DATABASE_PATH),
            retention_days=_positive_environment_integer(
                "FORGE_RETENTION_DAYS",
                DEFAULT_RETENTION_DAYS,
            ),
            max_database_bytes=_positive_environment_integer(
                "FORGE_MAX_DATABASE_BYTES",
                DEFAULT_MAX_DATABASE_BYTES,
            ),
        )

    def record(self, event: Event) -> None:
        self._store.record(event)

    def summary(
        self,
        window_hours: int = 24,
        service: str | None = None,
        event: str | None = None,
        name: str | None = None,
    ) -> Summary:
        stored = self._store.summary(
            window_hours=window_hours,
            service=service,
            event=event,
            name=name,
        )
        median_duration = median(stored.durations) if stored.durations else 0.0
        return Summary(
            window_hours=window_hours,
            requests=stored.requests,
            errors=stored.errors,
            avg_ms=round(stored.average_ms, 2),
            median_ms=round(median_duration, 2),
            p95_ms=_percentile(stored.durations, 0.95),
            services=stored.services,
            commands=stored.commands,
            retained_events=stored.retained_events,
            oldest_event_age_days=stored.oldest_event_age_days,
            database_bytes=stored.database_bytes,
            database_max_bytes=stored.database_max_bytes,
        )

    def reset(self) -> None:
        self._store.reset()

    def close(self) -> None:
        self._store.close()


def _positive_environment_integer(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if parsed < 1:
        raise ValueError(f"{name} must be positive")
    return parsed


def _percentile(values: tuple[int, ...], percentile: float) -> float:
    if not values:
        return 0.0
    index = max(0, math.ceil(len(values) * percentile) - 1)
    return round(float(values[index]), 2)
