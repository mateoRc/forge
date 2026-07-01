from app.models import Summary

BAR_WIDTH = 15


def render(summary: Summary) -> str:
    lines = [
        "Forge dashboard",
        "",
        f"requests: {summary.requests}",
        f"errors:   {summary.errors}",
        f"avg ms:   {summary.avg_ms:g}",
        "",
        "services:",
        *_bars(summary.services),
        "",
        "commands:",
        *_bars(summary.commands),
    ]
    return "\n".join(lines)


def _bars(values: dict[str, int]) -> list[str]:
    if not values:
        return ["none"]

    largest = max(values.values())
    label_width = max(len(label) for label in values)
    return [
        f"{label:<{label_width}}  {'█' * max(1, round(count / largest * BAR_WIDTH))} {count}"
        for label, count in values.items()
    ]

