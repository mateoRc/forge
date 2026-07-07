from app.dashboard import render
from app.models import Summary


def test_renders_persisted_activity_dashboard() -> None:
    output = render(_summary())

    assert "ACTIVITY · LAST 24 HOURS" in output
    assert "requests       3" in output
    assert "errors         1  (33.3%)" in output
    assert "command time   6 ms avg · 6 ms p50 · 8 ms p95" in output
    assert "vault  " + "█" * 15 + " 2" in output
    assert "atlas  " + "█" * 8 + " 1" in output
    assert "retained events  42" in output
    assert "oldest retained  12 days" in output
    assert "database         23.0 / 128 MiB" in output


def test_uses_configured_bar_width() -> None:
    output = render(_summary(), width=5)

    assert "vault  " + "█" * 5 + " 2" in output


def test_renders_in_memory_empty_storage() -> None:
    summary = _summary()
    summary.database_bytes = None
    summary.oldest_event_age_days = None

    output = render(summary)

    assert "oldest retained  none" in output
    assert "database         in memory" in output


def _summary() -> Summary:
    return Summary(
        window_hours=24,
        requests=3,
        errors=1,
        avg_ms=6,
        median_ms=6,
        p95_ms=8,
        services={"vault": 2, "atlas": 1},
        commands={"grep": 2, "search": 1},
        retained_events=42,
        oldest_event_age_days=12,
        database_bytes=23 * 1024 * 1024,
        database_max_bytes=128 * 1024 * 1024,
    )
