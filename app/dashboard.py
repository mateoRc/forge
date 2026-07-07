from app.models import Summary

DEFAULT_BAR_WIDTH = 15
MEBIBYTE = 1024 * 1024


def render(summary: Summary, width: int = DEFAULT_BAR_WIDTH) -> str:
    error_rate = summary.errors / summary.requests if summary.requests else 0
    lines = [
        f"ACTIVITY · {_window_label(summary.window_hours)}",
        "========================",
        f"requests       {summary.requests}",
        f"errors         {summary.errors}  ({error_rate:.1%})",
        (
            f"command time   {summary.avg_ms:g} ms avg · "
            f"{summary.median_ms:g} ms p50 · {summary.p95_ms:g} ms p95"
        ),
        "",
        "SERVICES",
        "========",
        *_bars(summary.services, width),
        "",
        "POPULAR OPERATIONS",
        "==================",
        *_bars(summary.commands, width),
        "",
        "STORAGE",
        "=======",
        f"retained events  {summary.retained_events}",
        f"oldest event     {_oldest_label(summary.oldest_event_age_days)}",
        f"database         {_database_label(summary)}",
    ]
    return "\n".join(lines)


def _window_label(hours: int) -> str:
    labels = {
        24: "LAST 24 HOURS",
        168: "LAST 7 DAYS",
        720: "LAST 30 DAYS",
    }
    return labels.get(hours, f"LAST {hours} HOURS")


def _oldest_label(age_days: int | None) -> str:
    if age_days is None:
        return "none"
    if age_days == 0:
        return "today"
    return f"{age_days} day{'s' if age_days != 1 else ''}"


def _database_label(summary: Summary) -> str:
    if summary.database_bytes is None:
        return "in memory"
    used = summary.database_bytes / MEBIBYTE
    limit = summary.database_max_bytes / MEBIBYTE
    return f"{used:.1f} / {limit:g} MiB"


def _bars(values: dict[str, int], width: int) -> list[str]:
    if not values:
        return ["none"]

    largest = max(values.values())
    label_width = max(len(label) for label in values)
    return [
        f"{label:<{label_width}}  {'█' * max(1, round(count / largest * width))} {count}"
        for label, count in values.items()
    ]
