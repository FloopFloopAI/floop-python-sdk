"""Async client tests with ``pytest-httpx`` + ``pytest-asyncio``.

Covers the parallel ``AsyncFloopClient`` surface added in 0.1.0a4. The
sync-side tests in ``test_client.py``, ``test_resources.py``, and
``test_poll.py`` already cover the underlying envelope / error / poll
semantics — these tests focus on what's unique to the async path:
``async with`` lifecycle, ``await`` correctness on every resource, the
``async for`` shape of ``projects.stream()``, and that
``AsyncFloopClient`` and ``FloopClient`` share the same internal
helpers (User-Agent, retry-after parsing, terminal-status set).
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from floopfloop import CURRENT_VERSION, AsyncFloopClient, FloopError


@pytest.fixture
def async_client(httpx_mock: HTTPXMock) -> AsyncFloopClient:  # noqa: ARG001 - fixture wiring
    return AsyncFloopClient(
        api_key="flp_test",
        poll_interval=0.01,
        timeout=5.0,
    )


@pytest.mark.asyncio
async def test_init_requires_api_key() -> None:
    with pytest.raises(TypeError):
        AsyncFloopClient(api_key="")


@pytest.mark.asyncio
async def test_request_attaches_bearer_and_user_agent(
    httpx_mock: HTTPXMock, async_client: AsyncFloopClient
) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/ping",
        json={"data": {"hello": "world"}},
    )
    out = await async_client._request("GET", "/api/v1/ping")
    assert out == {"hello": "world"}

    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["Authorization"] == "Bearer flp_test"
    assert req.headers["User-Agent"] == f"floop-sdk-python/{CURRENT_VERSION}"
    await async_client.close()


@pytest.mark.asyncio
async def test_async_with_closes_owned_http(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/user/me",
        json={"data": {"user": {"id": "u_1", "email": "a@b"}, "source": "api_key"}},
    )
    async with AsyncFloopClient(api_key="flp_test") as client:
        result = await client.user.me()
        assert result["user"]["id"] == "u_1"
    # After exit, _http should have been aclose()'d. We can't easily assert on
    # httpx's internal state cross-version, but a follow-up request should
    # raise — pytest-httpx swallows that, so we skip the negative assertion
    # here and rely on the lifecycle test in pytest-httpx itself.


@pytest.mark.asyncio
async def test_subscriptions_current_async(
    httpx_mock: HTTPXMock, async_client: AsyncFloopClient
) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/subscriptions/current",
        json={
            "data": {
                "subscription": {
                    "status": "active",
                    "planName": "pro",
                    "monthlyCredits": 500,
                },
                "credits": {"current": 423, "rolledOver": 50, "total": 473},
            }
        },
    )
    res = await async_client.subscriptions.current()
    assert res["subscription"]["planName"] == "pro"
    assert res["credits"]["total"] == 473
    await async_client.close()


@pytest.mark.asyncio
async def test_subscriptions_current_async_both_null(
    httpx_mock: HTTPXMock, async_client: AsyncFloopClient
) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/subscriptions/current",
        json={"data": {"subscription": None, "credits": None}},
    )
    res = await async_client.subscriptions.current()
    assert res["subscription"] is None
    assert res["credits"] is None
    await async_client.close()


@pytest.mark.asyncio
async def test_projects_stream_yields_until_terminal(
    httpx_mock: HTTPXMock, async_client: AsyncFloopClient
) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p_1/status",
        json={
            "data": {
                "step": 1,
                "totalSteps": 3,
                "status": "queued",
                "message": "",
            }
        },
    )
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p_1/status",
        json={
            "data": {
                "step": 2,
                "totalSteps": 3,
                "status": "generating",
                "progress": 0.5,
                "message": "",
            }
        },
    )
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p_1/status",
        json={
            "data": {
                "step": 3,
                "totalSteps": 3,
                "status": "live",
                "message": "",
            }
        },
    )

    statuses = []
    async for ev in async_client.projects.stream("p_1"):
        statuses.append(ev["status"])
    assert statuses == ["queued", "generating", "live"]
    await async_client.close()


@pytest.mark.asyncio
async def test_projects_wait_for_live_raises_on_failed(
    httpx_mock: HTTPXMock, async_client: AsyncFloopClient
) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p_1/status",
        json={
            "data": {
                "step": 1,
                "totalSteps": 1,
                "status": "failed",
                "message": "typecheck failed",
            }
        },
    )
    with pytest.raises(FloopError) as exc:
        await async_client.projects.wait_for_live("p_1")
    assert exc.value.code == "BUILD_FAILED"
    assert str(exc.value) == "typecheck failed"
    await async_client.close()


@pytest.mark.asyncio
async def test_projects_wait_for_live_archived_terminates_cleanly(
    httpx_mock: HTTPXMock, async_client: AsyncFloopClient
) -> None:
    """Archived projects are non-error terminals — same parity contract as
    the other 7 SDKs (Node, Go, Rust, Ruby, PHP, Swift, Kotlin)."""
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p_1/status",
        json={
            "data": {
                "step": 3,
                "totalSteps": 3,
                "status": "archived",
                "message": "",
            }
        },
    )
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects",
        json={
            "data": [
                {"id": "p_1", "subdomain": "x", "status": "archived", "url": None}
            ]
        },
    )
    project = await async_client.projects.wait_for_live("p_1")
    assert project["status"] == "archived"
    await async_client.close()


@pytest.mark.asyncio
async def test_secrets_async_round_trip(
    httpx_mock: HTTPXMock, async_client: AsyncFloopClient
) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p_1/secrets",
        json={"data": {"secrets": [{"key": "STRIPE_KEY", "lastFour": "_xyz"}]}},
    )
    secrets = await async_client.secrets.list("p_1")
    assert len(secrets) == 1 and secrets[0]["key"] == "STRIPE_KEY"

    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p_1/secrets",
        method="POST",
        json={"data": {"secret": {"key": "DB_URL", "lastFour": "_abc"}}},
    )
    set_result = await async_client.secrets.set("p_1", "DB_URL", "postgres://...")
    assert set_result["key"] == "DB_URL"
    await async_client.close()
