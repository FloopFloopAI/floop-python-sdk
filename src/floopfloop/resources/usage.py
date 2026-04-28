"""``client.usage.summary()`` — plan + credit balance + current-period."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._async_client import AsyncFloopClient
    from .._client import FloopClient


class Usage:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def summary(self) -> dict[str, Any]:
        return self._client._request("GET", "/api/v1/usage/summary")


class AsyncUsage:
    def __init__(self, client: AsyncFloopClient) -> None:
        self._client = client

    async def summary(self) -> dict[str, Any]:
        return await self._client._request("GET", "/api/v1/usage/summary")
