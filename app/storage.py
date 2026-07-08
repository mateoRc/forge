import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Literal

from app.models import Event

DEFAULT_DATABASE_PATH = ":memory:"
DEFAULT_RETENTION_DAYS = 30
DEFAULT_MAX_DATABASE_BYTES = 128 * 1024 * 1024
MINIMUM_DATABASE_BYTES = 64 * 1024
SIZE_REDUCTION_BATCH = 500


@dataclass(frozen=True)
class StoredSummary:
    requests: int
    errors: int
    user_errors: int
    average_ms: float
    durations: tuple[int, ...]
    services: dict[str, int]
    commands: dict[str, int]
    retained_events: int
    oldest_event_at: str | None
    database_bytes: int | None
    database_max_bytes: int


class SQLiteEventStore:
    def __init__(
        self,
        database_path: str | Path,
        retention_days: int,
        max_database_bytes: int,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if retention_days < 1:
            raise ValueError("retention_days must be positive")
        if max_database_bytes < MINIMUM_DATABASE_BYTES:
            raise ValueError(
                f"max_database_bytes must be at least {MINIMUM_DATABASE_BYTES}"
            )

        self._database_path = str(database_path)
        self._retention = timedelta(days=retention_days)
        self._max_database_bytes = max_database_bytes
        self._now = now or (lambda: datetime.now(UTC))
        self._lock = Lock()
        self._connection = self._open()
        self._migrate()
        self._checkpoint()
        self._enforce_limits()

    def record(self, event: Event) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO events (
                    recorded_at,
                    service,
                    event,
                    name,
                    duration_ms,
                    exit_code
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    _utc_text(self._now()),
                    event.service,
                    event.event,
                    event.name,
                    event.duration_ms,
                    event.exit_code,
                ),
            )
            self._connection.commit()
            self._enforce_limits()

    def summary(
        self,
        window_hours: int,
        service: str | None = None,
        event: str | None = None,
        name: str | None = None,
    ) -> StoredSummary:
        now = self._now()
        since = _utc_text(now - timedelta(hours=window_hours))
        where, parameters = _where_clause(since, service, event, name)
        with self._lock:
            self._enforce_limits()
            runtime_error = _runtime_error_condition()
            totals = self._connection.execute(
                f"""
                SELECT
                    COUNT(*) AS requests,
                    COALESCE(SUM(CASE WHEN {runtime_error} THEN 1 ELSE 0 END), 0)
                        AS errors,
                    COALESCE(SUM(CASE
                        WHEN exit_code != 0 AND NOT ({runtime_error})
                        THEN 1 ELSE 0 END), 0) AS user_errors,
                    COALESCE(AVG(duration_ms), 0) AS average_ms
                FROM events
                """
                + where,
                parameters,
            ).fetchone()
            durations = tuple(
                row["duration_ms"]
                for row in self._connection.execute(
                    "SELECT duration_ms FROM events"
                    + where
                    + " ORDER BY duration_ms",
                    parameters,
                )
            )
            services = self._counts("service", where, parameters)
            commands = self._counts(
                "name",
                _and_where_clause(
                    where,
                    "event IN ('command.executed', 'command.runtime_error')",
                ),
                parameters,
            )
            retained = self._connection.execute(
                "SELECT COUNT(*) AS count, MIN(recorded_at) AS oldest FROM events"
            ).fetchone()
        return StoredSummary(
            requests=totals["requests"],
            errors=totals["errors"],
            user_errors=totals["user_errors"],
            average_ms=totals["average_ms"],
            durations=durations,
            services=services,
            commands=commands,
            retained_events=retained["count"],
            oldest_event_at=_utc_label(retained["oldest"]),
            database_bytes=(
                None
                if self._database_path == DEFAULT_DATABASE_PATH
                else self._database_size()
            ),
            database_max_bytes=self._max_database_bytes,
        )

    def reset(self) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM events")
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _open(self) -> sqlite3.Connection:
        if self._database_path != DEFAULT_DATABASE_PATH:
            Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self._database_path,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        if self._database_path != DEFAULT_DATABASE_PATH:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def _counts(
        self,
        column: Literal["service", "name"],
        where: str,
        parameters: tuple[str, ...],
    ) -> dict[str, int]:
        rows = self._connection.execute(
            f"""
            SELECT {column} AS label, COUNT(*) AS requests, MIN(id) AS first_id
            FROM events
            {where}
            GROUP BY {column}
            ORDER BY requests DESC, first_id
            """,
            parameters,
        )
        return {row["label"]: row["requests"] for row in rows}

    def _migrate(self) -> None:
        migrations = sorted(Path(__file__).with_name("migrations").glob("*.sql"))
        if not migrations:
            raise RuntimeError("no database migrations found")
        for migration in migrations:
            version_text, separator, _ = migration.name.partition("_")
            if not separator or not version_text.isdigit():
                raise ValueError(f"invalid migration filename: {migration.name}")
            version = int(version_text)
            current = self._connection.execute("PRAGMA user_version").fetchone()[0]
            if version <= current:
                continue
            if version != current + 1:
                raise ValueError(
                    f"missing database migration between {current} and {version}"
                )
            script = migration.read_text(encoding="utf-8")
            self._connection.executescript(
                f"BEGIN;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;"
            )

    def _enforce_limits(self) -> None:
        cutoff = _utc_text(self._now() - self._retention)
        self._connection.execute(
            "DELETE FROM events WHERE recorded_at < ?",
            (cutoff,),
        )
        self._connection.commit()

        while self._database_size() > self._max_database_bytes:
            event_count = self._connection.execute(
                "SELECT COUNT(*) FROM events"
            ).fetchone()[0]
            batch_size = min(
                SIZE_REDUCTION_BATCH,
                max(1, event_count // 10),
            )
            deleted = self._connection.execute(
                """
                DELETE FROM events
                WHERE id IN (
                    SELECT id FROM events ORDER BY id LIMIT ?
                )
                """,
                (batch_size,),
            ).rowcount
            self._connection.commit()
            self._compact()
            if deleted == 0:
                raise RuntimeError(
                    "database schema exceeds FORGE_MAX_DATABASE_BYTES"
                )

    def _database_size(self) -> int:
        if self._database_path == DEFAULT_DATABASE_PATH:
            return 0
        path = Path(self._database_path)
        wal_path = Path(f"{self._database_path}-wal")
        return _file_size(path) + _file_size(wal_path)

    def _compact(self) -> None:
        self._checkpoint()
        self._connection.execute("VACUUM")

    def _checkpoint(self) -> None:
        if self._database_path != DEFAULT_DATABASE_PATH:
            self._connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _where_clause(
    since: str,
    service: str | None,
    event: str | None,
    name: str | None,
) -> tuple[str, tuple[str, ...]]:
    filters = ["recorded_at >= ?"]
    parameters = [since]
    for column, value in (("service", service), ("event", event), ("name", name)):
        if value is not None:
            filters.append(f"{column} = ?")
            parameters.append(value)
    where = f" WHERE {' AND '.join(filters)}" if filters else ""
    return where, tuple(parameters)


def _and_where_clause(where: str, condition: str) -> str:
    if where:
        return f"{where} AND {condition}"
    return f" WHERE {condition}"


def _runtime_error_condition() -> str:
    return "event IN ('command.runtime_error', 'runtime.error') OR exit_code >= 128"


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("event timestamp must include a timezone")
    return value.astimezone(UTC).isoformat(timespec="seconds")


def _utc_label(value: str | None) -> str | None:
    if value is None:
        return None
    recorded_at = datetime.fromisoformat(value)
    return recorded_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0
