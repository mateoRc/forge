from app.models import Summary

DEFAULT_BAR_WIDTH = 15


def render(summary: Summary, width: int = DEFAULT_BAR_WIDTH) -> str:
    error_rate = summary.errors / summary.requests if summary.requests else 0
    lines = [
        "LIVE ACTIVITY",
        "=============",
        f"requests      {summary.requests}",
        f"errors        {summary.errors}",
        f"error rate    {_ratio_bar(error_rate, width)} {error_rate:.1%}",
        f"avg latency   {summary.avg_ms:g} ms",
        "",
        "REQUESTS BY SERVICE",
        "===================",
        *_bars(summary.services, width),
        "",
        "POPULAR COMMANDS",
        "================",
        *_bars(summary.commands, width),
    ]
    return "\n".join(lines)


def _bars(values: dict[str, int], width: int) -> list[str]:
    if not values:
        return ["none"]

    largest = max(values.values())
    label_width = max(len(label) for label in values)
    return [
        f"{label:<{label_width}}  {_ratio_bar(count / largest, width)} {count}"
        for label, count in values.items()
    ]


def _ratio_bar(ratio: float, width: int) -> str:
    filled = round(max(0, min(1, ratio)) * width)
    return f"[{'#' * filled}{'.' * (width - filled)}]"
