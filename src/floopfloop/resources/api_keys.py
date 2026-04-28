"""``client.api_keys.*`` — programmatic ``flp_...`` keys for CI / scripts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from ..errors import FloopError

if TYPE_CHECKING:
    from .._async_client import AsyncFloopClient
    from .._client import FloopClient


class ApiKeys:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def list(self) -> list[dict[str, Any]]:
        data = self._client._request("GET", "/api/v1/api-keys")
        return list(data.get("keys", [])) if isinstance(data, dict) else []

    def create(self, *, name: str) -> dict[str, Any]:
        return self._client._request("POST", "/api/v1/api-keys", json={"name": name})

    def remove(self, id_or_name: str) -> dict[str, Any]:
        """Revoke a key by id OR name (we list + match on either field).

        The backend refuses to revoke the key making the call; that error
        propagates as a :class:`FloopError`.
        """
        all_keys = self.list()
        match = next(
            (k for k in all_keys if k.get("id") == id_or_name or k.get("name") == id_or_name),
            None,
        )
        if match is None:
            raise FloopError(
                code="NOT_FOUND",
                message=f"API key not found: {id_or_name}",
                status=404,
            )
        return self._client._request(
            "DELETE", f"/api/v1/api-keys/{quote(match['id'], safe='')}"
        )


class AsyncApiKeys:
    def __init__(self, client: AsyncFloopClient) -> None:
        self._client = client

    async def list(self) -> list[dict[str, Any]]:
        data = await self._client._request("GET", "/api/v1/api-keys")
        return list(data.get("keys", [])) if isinstance(data, dict) else []

    async def create(self, *, name: str) -> dict[str, Any]:
        return await self._client._request("POST", "/api/v1/api-keys", json={"name": name})

    async def remove(self, id_or_name: str) -> dict[str, Any]:
        """Async mirror of :meth:`ApiKeys.remove`."""
        all_keys = await self.list()
        match = next(
            (k for k in all_keys if k.get("id") == id_or_name or k.get("name") == id_or_name),
            None,
        )
        if match is None:
            raise FloopError(
                code="NOT_FOUND",
                message=f"API key not found: {id_or_name}",
                status=404,
            )
        return await self._client._request(
            "DELETE", f"/api/v1/api-keys/{quote(match['id'], safe='')}"
        )
