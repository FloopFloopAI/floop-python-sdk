"""Polling engine tests."""

from __future__ import annotations

from pytest_httpx import HTTPXMock

from floopfloop import FloopClient
from floopfloop._poll import poll_project_status


def _queue_status(httpx_mock: HTTPXMock, status: str, **extra: object) -> None:
    body = {
        "step": 1,
        "totalSteps": 3,
        "status": status,
        "message": f"status={status}",
    }
    body.update(extra)
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p_1/status",
        json={"data": body},
    )


def test_transitions_and_terminal(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    _queue_status(httpx_mock, "queued")
    _queue_status(httpx_mock, "generating", progress=0.3)
    _queue_status(httpx_mock, "generating", progress=0.3)  # dup → deduped
    _queue_status(httpx_mock, "deploying")
    _queue_status(httpx_mock, "live")

    events = [e["status"] for e in poll_project_status(client, "p_1")]
    assert events == ["queued", "generating", "deploying", "live"]


def test_failed_terminal(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    _queue_status(httpx_mock, "failed")
    events = [e["status"] for e in poll_project_status(client, "p_1")]
    assert events == ["failed"]
