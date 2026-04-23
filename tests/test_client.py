"""Transport layer tests with ``pytest-httpx``."""

from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from floopfloop import CURRENT_VERSION, FloopClient, FloopError


def test_bearer_user_agent_and_data_unwrap(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/ping",
        json={"data": {"hello": "world"}},
    )
    out = client._request("GET", "/api/v1/ping")
    assert out == {"hello": "world"}

    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["Authorization"] == "Bearer flp_test"
    assert req.headers["User-Agent"] == f"floop-sdk-python/{CURRENT_VERSION}"


def test_post_attaches_json_body(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(json={"data": {"ok": True}})
    client._request("POST", "/x", json={"foo": 1})
    req = httpx_mock.get_request()
    assert req is not None
    assert req.read() == b'{"foo":1}'
    assert req.headers["Content-Type"].startswith("application/json")


def test_error_envelope_becomes_floop_error(
    httpx_mock: HTTPXMock, client: FloopClient
) -> None:
    httpx_mock.add_response(
        status_code=404,
        headers={"x-request-id": "req_1"},
        json={"error": {"code": "NOT_FOUND", "message": "no such project"}},
    )
    with pytest.raises(FloopError) as exc:
        client._request("GET", "/x")
    assert exc.value.code == "NOT_FOUND"
    assert exc.value.status == 404
    assert exc.value.request_id == "req_1"
    assert str(exc.value) == "no such project"


def test_retry_after_on_429(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        status_code=429,
        headers={"retry-after": "5"},
        json={"error": {"code": "RATE_LIMITED", "message": "slow down"}},
    )
    with pytest.raises(FloopError) as exc:
        client._request("GET", "/x")
    assert exc.value.retry_after_ms == 5000


def test_network_error_maps_to_floop_error(
    httpx_mock: HTTPXMock, client: FloopClient
) -> None:
    httpx_mock.add_exception(httpx.ConnectError("ECONNREFUSED"))
    with pytest.raises(FloopError) as exc:
        client._request("GET", "/x")
    assert exc.value.code == "NETWORK_ERROR"
    assert exc.value.status == 0


def test_non_json_5xx_falls_back_to_server_error(
    httpx_mock: HTTPXMock, client: FloopClient
) -> None:
    httpx_mock.add_response(status_code=500, text="upstream crashed")
    with pytest.raises(FloopError) as exc:
        client._request("GET", "/x")
    assert exc.value.code == "SERVER_ERROR"
    assert exc.value.status == 500


def test_custom_base_url() -> None:
    c = FloopClient(
        api_key="flp_test",
        base_url="https://staging.floopfloop.com/",
    )
    assert c.base_url == "https://staging.floopfloop.com"
    c.close()


def test_empty_api_key_rejected() -> None:
    with pytest.raises(TypeError, match="api_key"):
        FloopClient(api_key="")
