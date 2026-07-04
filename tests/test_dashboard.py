from app.dashboard import render
from app.models import Summary


def test_renders_ascii_dashboard() -> None:
    output = render(
        Summary(
            requests=3,
            errors=1,
            avg_ms=6,
            median_ms=6,
            services={"vault": 2, "atlas": 1},
            commands={"grep": 2, "search": 1},
        )
    )

    assert "LIVE ACTIVITY\n=============" in output
    assert "requests      3" in output
    assert "errors        1" in output
    assert "error rate    33.3%" in output
    assert "median (p50)  6 ms" in output
    assert "vault  " + "█" * 15 + " 2" in output
    assert "atlas  " + "█" * 8 + " 1" in output


def test_uses_configured_bar_width() -> None:
    output = render(
        Summary(
            requests=1,
            errors=0,
            avg_ms=1,
            median_ms=1,
            services={"vault": 1},
            commands={"grep": 1},
        ),
        width=5,
    )

    assert "vault  " + "█" * 5 + " 1" in output
