"""``client.subdomains.*`` — check / suggest helpers for scripted flows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

if TYPE_CHECKING:
    from .._client import FloopClient


class Subdomains:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def check(self, slug: str) -> dict[str, Any]:
        path = f"/api/v1/subdomains/check?{urlencode({'subdomain': slug})}"
        return self._client._request("GET", path)

    def suggest(self, prompt: str) -> dict[str, Any]:
        path = f"/api/v1/subdomains/suggest?{urlencode({'prompt': prompt})}"
        return self._client._request("GET", path)
