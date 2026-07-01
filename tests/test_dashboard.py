from app.dashboard import render
from app.models import Summary


def test_renders_ascii_dashboard() -> None:
    output = render(
        Summary(
            requests=3,
            errors=1,
            avg_ms=6,
            services={"vault": 2, "atlas": 1},
            commands={"grep": 2, "search": 1},
        )
    )

    assert "Forge dashboard" in output
    assert "requests: 3" in output
    assert "errors:   1" in output
    assert "vault  ███████████████ 2" in output
    assert "atlas  ████████ 1" in output

