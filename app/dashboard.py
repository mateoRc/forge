from app.models import Summary

DEFAULT_BAR_WIDTH = 15


def render(summary: Summary, width: int = DEFAULT_BAR_WIDTH) -> str:
    lines = [
        "Forge dashboard",
        "",
        f"requests: {summary.requests}",
        f"errors:   {summary.errors}",
        f"avg ms:   {summary.avg_ms:g}",
        "",
        "services:",
        *_bars(summary.services, width),
        "",
        "commands:",
        *_bars(summary.commands, width),
    ]
    return "\n".join(lines)


def _bars(values: dict[str, int], width: int) -> list[str]:
    if not values:
        return ["none"]

    largest = max(values.values())
    label_width = max(len(label) for label in values)
    return [
        f"{label:<{label_width}}  {'█' * max(1, round(count / largest * width))} {count}"
        for label, count in values.items()
    ]
