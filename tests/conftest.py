"""Shared fixtures: build a FloopClient wired to ``pytest-httpx``."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from floopfloop import FloopClient


@pytest.fixture
def client(httpx_mock: HTTPXMock) -> FloopClient:  # noqa: ARG001 - fixture wiring
    """A FloopClient pointed at the default base URL; all HTTP is mocked."""
    return FloopClient(
        api_key="flp_test",
        poll_interval=0.01,
        timeout=5.0,
    )
