import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app, metrics
from app.models import Event


def test_event_summary_and_dashboard_endpoints() -> None:
    asyncio.run(_test_event_summary_and_dashboard_endpoints())


async def _test_event_summary_and_dashboard_endpoints() -> None:
    metrics.reset()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://forge",
    ) as client:
        event_response = await client.post(
            "/events",
            json={
                "service": "vault",
                "event": "command.executed",
                "name": "grep",
                "duration_ms": 8,
                "exit_code": 0,
            },
        )
        summary_response = await client.get("/summary")
        dashboard_response = await client.get("/dashboard")

    assert event_response.status_code == 204
    assert summary_response.json() == {
        "requests": 1,
        "errors": 0,
        "avg_ms": 8.0,
        "services": {"vault": 1},
        "commands": {"grep": 1},
    }
    assert dashboard_response.status_code == 200
    assert "grep  " + "█" * 15 + " 1" in dashboard_response.text


def test_rejects_invalid_event() -> None:
    asyncio.run(_test_rejects_invalid_event())


async def _test_rejects_invalid_event() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://forge",
    ) as client:
        response = await client.post(
            "/events",
            json={
                "service": "",
                "event": "command.executed",
                "name": "grep",
                "duration_ms": -1,
                "exit_code": 0,
            },
        )

    assert response.status_code == 422


def test_filtered_summary_and_configurable_dashboard() -> None:
    asyncio.run(_test_filtered_summary_and_configurable_dashboard())


async def _test_filtered_summary_and_configurable_dashboard() -> None:
    metrics.reset()
    metrics.record(
        Event(
            service="vault",
            event="plugin.custom",
            name="compile",
            duration_ms=3,
            exit_code=0,
        )
    )
    metrics.record(
        Event(
            service="atlas",
            event="search.executed",
            name="search",
            duration_ms=9,
            exit_code=1,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://forge",
    ) as client:
        summary_response = await client.get(
            "/summary",
            params={"event": "plugin.custom"},
        )
        dashboard_response = await client.get(
            "/dashboard",
            params={"service": "vault", "width": 5},
        )

    assert summary_response.json()["commands"] == {"compile": 1}
    assert "vault  " + "█" * 5 + " 1" in dashboard_response.text
