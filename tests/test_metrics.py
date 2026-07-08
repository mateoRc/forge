import sqlite3
import tempfile
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.metrics import Metrics
from app.models import Event
from app.storage import MINIMUM_DATABASE_BYTES


def test_aggregates_requests_errors_duration_services_and_commands() -> None:
    metrics = Metrics()
    metrics.record(_event("vault", "grep", 8, 0))
    metrics.record(_event("vault", "cat", 4, 1))
    metrics.record(_event("vault", "search", 3, 0))
    metrics.record(_atlas_search_event())
    metrics.record(
        Event(
            service="vault",
            event="command.runtime_error",
            name="panic",
            duration_ms=10,
            exit_code=1,
        )
    )

    summary = metrics.summary()

    assert summary.requests == 5
    assert summary.errors == 1
    assert summary.user_errors == 1
    assert summary.avg_ms == 6.2
    assert summary.median_ms == 6
    assert summary.p95_ms == 10
    assert summary.services == {"vault": 4, "atlas": 1}
    assert summary.commands == {"grep": 1, "cat": 1, "search": 1, "panic": 1}


def test_commands_exclude_backend_service_events_with_the_same_name() -> None:
    metrics = Metrics()
    metrics.record(_event("vault", "search", 4, 0))
    metrics.record(_atlas_search_event())

    summary = metrics.summary()

    assert summary.requests == 2
    assert summary.services == {"vault": 1, "atlas": 1}
    assert summary.commands == {"search": 1}


def test_filters_events_and_recalculates_aggregates() -> None:
    metrics = Metrics()
    metrics.record(_event("vault", "grep", 8, 0))
    metrics.record(_event("vault", "cat", 4, 1))
    metrics.record(_atlas_search_event())

    summary = metrics.summary(service="vault", name="cat")

    assert summary.requests == 1
    assert summary.errors == 0
    assert summary.user_errors == 1
    assert summary.avg_ms == 4
    assert summary.median_ms == 4
    assert summary.services == {"vault": 1}
    assert summary.commands == {"cat": 1}


def test_accepts_and_filters_unknown_event_types() -> None:
    metrics = Metrics()
    metrics.record(
        Event(
            service="vault",
            event="plugin.custom",
            name="compile",
            duration_ms=8,
            exit_code=0,
        )
    )

    assert metrics.summary(event="plugin.custom").requests == 1


def test_median_is_not_distorted_by_an_outlier() -> None:
    metrics = Metrics()
    metrics.record(_event("vault", "grep", 1, 0))
    metrics.record(_event("vault", "grep", 2, 0))
    metrics.record(_event("vault", "grep", 100, 0))

    summary = metrics.summary()

    assert summary.avg_ms == 34.33
    assert summary.median_ms == 2


def test_events_survive_database_reopen() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "forge.db"
        first = Metrics(database)
        first.record(_event("vault", "grep", 8, 0))
        first.close()

        second = Metrics(database)
        summary = second.summary()
        second.close()

    assert summary.requests == 1
    assert summary.commands == {"grep": 1}


def test_applies_all_database_migrations() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "forge.db"
        metrics = Metrics(database)
        metrics.close()
        with closing(sqlite3.connect(database)) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            indexes = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'index' AND tbl_name = 'events'
                    """
                )
            }

    assert version == 2
    assert indexes == {"events_recorded_at_idx", "events_dimensions_idx"}


def test_records_server_generated_utc_timestamp() -> None:
    recorded_at = datetime(2026, 7, 6, 12, 30, tzinfo=UTC)
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "forge.db"
        metrics = Metrics(database, now=lambda: recorded_at)
        metrics.record(_event("vault", "grep", 8, 0))
        metrics.close()
        with closing(sqlite3.connect(database)) as connection:
            stored = connection.execute(
                "SELECT recorded_at FROM events"
            ).fetchone()[0]

    assert stored == "2026-07-06T12:30:00+00:00"


def test_retention_removes_expired_events() -> None:
    current = [datetime(2026, 7, 1, tzinfo=UTC)]
    metrics = Metrics(retention_days=1, now=lambda: current[0])
    metrics.record(_event("vault", "old", 8, 0))
    current[0] += timedelta(days=2)
    metrics.record(_event("vault", "current", 4, 0))

    summary = metrics.summary()

    assert summary.requests == 1
    assert summary.commands == {"current": 1}


def test_summary_applies_selected_time_window() -> None:
    current = [datetime(2026, 7, 1, tzinfo=UTC)]
    metrics = Metrics(retention_days=30, now=lambda: current[0])
    metrics.record(_event("vault", "older", 8, 0))
    current[0] += timedelta(days=2)
    metrics.record(_event("vault", "current", 4, 0))

    daily = metrics.summary(window_hours=24)
    weekly = metrics.summary(window_hours=168)

    assert daily.commands == {"current": 1}
    assert weekly.commands == {"older": 1, "current": 1}
    assert daily.retained_events == 2
    assert daily.oldest_event_at == "2026-07-01 00:00 UTC"


def test_database_size_limit_removes_oldest_events() -> None:
    event_count = 800
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "forge.db"
        metrics = Metrics(
            database,
            max_database_bytes=MINIMUM_DATABASE_BYTES,
        )
        for index in range(event_count):
            metrics.record(
                _event("vault", f"command-{index:04d}", index, 0)
            )
        retained = metrics.summary()
        metrics.close()
        size = database.stat().st_size
        wal = Path(f"{database}-wal")
        if wal.exists():
            size += wal.stat().st_size

    assert 0 < retained.requests < event_count
    assert size <= MINIMUM_DATABASE_BYTES


def _event(service: str, name: str, duration_ms: int, exit_code: int) -> Event:
    return Event(
        service=service,
        event="command.executed",
        name=name,
        duration_ms=duration_ms,
        exit_code=exit_code,
    )


def _atlas_search_event() -> Event:
    return Event(
        service="atlas",
        event="search.executed",
        name="search",
        duration_ms=6,
        exit_code=0,
    )
