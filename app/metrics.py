import os
from collections import Counter
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
        service: str | None = None,
        event: str | None = None,
        name: str | None = None,
    ) -> Summary:
        rows = self._store.query(service=service, event=event, name=name)
        requests = len(rows)
        errors = sum(int(row.exit_code != 0) for row in rows)
        durations = [row.duration_ms for row in rows]
        services = Counter(row.service for row in rows)
        commands = Counter(row.name for row in rows)
        average = sum(durations) / requests if requests else 0.0
        median_duration = median(durations) if durations else 0.0
        return Summary(
            requests=requests,
            errors=errors,
            avg_ms=round(average, 2),
            median_ms=round(median_duration, 2),
            services=dict(services.most_common()),
            commands=dict(commands.most_common()),
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
