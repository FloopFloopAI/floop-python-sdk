"""``client.secrets.*`` — per-project write-only environment variables."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

if TYPE_CHECKING:
    from .._async_client import AsyncFloopClient
    from .._client import FloopClient


class Secrets:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def list(self, project_ref: str) -> list[dict[str, Any]]:
        data = self._client._request(
            "GET", f"/api/v1/projects/{quote(project_ref, safe='')}/secrets"
        )
        return list(data.get("secrets", [])) if isinstance(data, dict) else []

    def set(self, project_ref: str, key: str, value: str) -> dict[str, Any]:
        data = self._client._request(
            "POST",
            f"/api/v1/projects/{quote(project_ref, safe='')}/secrets",
            json={"key": key, "value": value},
        )
        return dict(data.get("secret", {})) if isinstance(data, dict) else {}

    def remove(self, project_ref: str, key: str) -> dict[str, Any]:
        return self._client._request(
            "DELETE",
            f"/api/v1/projects/{quote(project_ref, safe='')}/secrets/{quote(key, safe='')}",
        )


class AsyncSecrets:
    def __init__(self, client: AsyncFloopClient) -> None:
        self._client = client

    async def list(self, project_ref: str) -> list[dict[str, Any]]:
        data = await self._client._request(
            "GET", f"/api/v1/projects/{quote(project_ref, safe='')}/secrets"
        )
        return list(data.get("secrets", [])) if isinstance(data, dict) else []

    async def set(self, project_ref: str, key: str, value: str) -> dict[str, Any]:
        data = await self._client._request(
            "POST",
            f"/api/v1/projects/{quote(project_ref, safe='')}/secrets",
            json={"key": key, "value": value},
        )
        return dict(data.get("secret", {})) if isinstance(data, dict) else {}

    async def remove(self, project_ref: str, key: str) -> dict[str, Any]:
        return await self._client._request(
            "DELETE",
            f"/api/v1/projects/{quote(project_ref, safe='')}/secrets/{quote(key, safe='')}",
        )
