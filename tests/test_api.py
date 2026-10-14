import asyncio
import os

from httpx import ASGITransport, AsyncClient

from app.main import app, metrics
from app.models import Event

AUTH_HEADERS = {"Authorization": "Bearer test-forge-token"}
os.environ["FORGE_AUTH_TOKEN"] = "test-forge-token"


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
            headers=AUTH_HEADERS,
            json={
                "service": "vault",
                "event": "command.executed",
                "name": "grep",
                "duration_ms": 8,
                "exit_code": 0,
            },
        )
        summary_response = await client.get("/summary", headers=AUTH_HEADERS)
        dashboard_response = await client.get("/dashboard", headers=AUTH_HEADERS)

    assert event_response.status_code == 204
    summary = summary_response.json()
    oldest_event_at = summary.pop("oldest_event_at")
    assert len(oldest_event_at) == 20
    assert oldest_event_at.endswith(" UTC")
    assert summary == {
        "window_hours": 24,
        "unique_visitors": 0,
        "requests": 1,
        "errors": 0,
        "user_errors": 0,
        "avg_ms": 8.0,
        "median_ms": 8.0,
        "p95_ms": 8.0,
        "services": {"vault": 1},
        "commands": {"grep": 1},
        "retained_events": 1,
        "database_bytes": None,
        "database_max_bytes": 268435456,
    }
    assert dashboard_response.status_code == 200
    assert "grep  " + "█" * 15 + " 1" in dashboard_response.text


def test_rejects_invalid_event() -> None:
    asyncio.run(_test_rejects_invalid_event())


def test_visits_require_auth_and_validate_visitor_ids() -> None:
    asyncio.run(_test_visits_require_auth_and_validate_visitor_ids())


async def _test_visits_require_auth_and_validate_visitor_ids() -> None:
    metrics.reset()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://forge",
    ) as client:
        unauthorized = await client.post(
            "/visits",
            json={"visitor_id": "12345678-1234-4123-8123-123456789abc"},
        )
        invalid = await client.post(
            "/visits",
            headers=AUTH_HEADERS,
            json={"visitor_id": "not-a-visitor-id"},
        )
        valid = await client.post(
            "/visits",
            headers=AUTH_HEADERS,
            json={"visitor_id": "12345678-1234-4123-8123-123456789abc"},
        )
        dashboard = await client.get("/dashboard", headers=AUTH_HEADERS)

    assert unauthorized.status_code in (401, 403)
    assert invalid.status_code == 422
    assert valid.status_code == 204
    assert "unique visitors 1" in dashboard.text


async def _test_rejects_invalid_event() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://forge",
    ) as client:
        response = await client.post(
            "/events",
            headers=AUTH_HEADERS,
            json={
                "service": "",
                "event": "command.executed",
                "name": "grep",
                "duration_ms": -1,
                "exit_code": 0,
            },
        )

    assert response.status_code == 422


def test_rejects_unknown_event_fields() -> None:
    asyncio.run(_test_rejects_unknown_event_fields())


async def _test_rejects_unknown_event_fields() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://forge",
    ) as client:
        response = await client.post(
            "/events",
            headers=AUTH_HEADERS,
            json={
                "service": "vault",
                "event": "command.executed",
                "name": "grep",
                "duration_ms": 8,
                "exit_code": 0,
                "token": "must-not-be-accepted",
            },
        )

    assert response.status_code == 422


def test_rejects_out_of_range_numeric_fields() -> None:
    asyncio.run(_test_rejects_out_of_range_numeric_fields())


async def _test_rejects_out_of_range_numeric_fields() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://forge",
    ) as client:
        response = await client.post(
            "/events",
            headers=AUTH_HEADERS,
            json={
                "service": "vault",
                "event": "command.executed",
                "name": "grep",
                "duration_ms": 86400001,
                "exit_code": 256,
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
            headers=AUTH_HEADERS,
            params={"event": "plugin.custom"},
        )
        dashboard_response = await client.get(
            "/dashboard",
            headers=AUTH_HEADERS,
            params={"service": "vault", "width": 5},
        )

    assert summary_response.json()["commands"] == {}
    assert "vault  " + "█" * 5 + " 1" in dashboard_response.text


def test_all_retained_window_and_invalid_name_flag() -> None:
    asyncio.run(_test_all_retained_window_and_invalid_name_flag())


async def _test_all_retained_window_and_invalid_name_flag() -> None:
    metrics.reset()
    metrics.record(Event(service="vault", event="command.executed", name="grep", duration_ms=8, exit_code=0))
    metrics.record(Event(service="vault", event="command.executed", name="rude_word", duration_ms=2, exit_code=127))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://forge") as client:
        default = await client.get("/dashboard", headers=AUTH_HEADERS)
        weekly = await client.get("/dashboard", headers=AUTH_HEADERS, params={"hours": 168})
        all_time = await client.get("/dashboard", headers=AUTH_HEADERS, params={"window": "all"})
        including_invalid = await client.get(
            "/dashboard", headers=AUTH_HEADERS,
            params={"window": "all", "include_invalid": "true"},
        )
        summary = await client.get("/summary", headers=AUTH_HEADERS, params={"window": "all"})
        summary_with_invalid = await client.get(
            "/summary", headers=AUTH_HEADERS,
            params={"window": "all", "include_invalid": "true"},
        )
        ambiguous = await client.get(
            "/dashboard", headers=AUTH_HEADERS, params={"window": "all", "hours": 24},
        )

    assert default.status_code == 200 and "LAST 24 HOURS" in default.text
    assert weekly.status_code == 200 and "LAST 7 DAYS" in weekly.text
    assert "rude_word" not in default.text
    assert all_time.status_code == 200 and "ALL TIME" in all_time.text
    assert "rude_word" not in all_time.text
    assert including_invalid.status_code == 200 and "rude_word" in including_invalid.text
    assert summary.json()["window_hours"] is None
    assert summary.json()["requests"] == 2
    assert summary.json()["commands"] == {"grep": 1}
    assert summary_with_invalid.json()["commands"] == {"grep": 1, "rude_word": 1}
    assert ambiguous.status_code == 422


def test_requires_authentication_but_leaves_health_public() -> None:
    asyncio.run(_test_requires_authentication_but_leaves_health_public())


async def _test_requires_authentication_but_leaves_health_public() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://forge",
    ) as client:
        summary_response = await client.get("/summary")
        health_response = await client.get("/healthz")

    assert summary_response.status_code == 401
    assert summary_response.headers["www-authenticate"] == "Bearer"
    assert health_response.status_code == 200
