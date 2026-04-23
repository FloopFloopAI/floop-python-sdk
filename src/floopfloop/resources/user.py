"""``client.user.me()`` — identity of the bearer on the current call."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._client import FloopClient


class User:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def me(self) -> dict[str, Any]:
        return self._client._request("GET", "/api/v1/user/me")
