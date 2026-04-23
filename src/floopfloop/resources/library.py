"""``client.library.*`` — browse + clone public community projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote, urlencode

if TYPE_CHECKING:
    from .._client import FloopClient

LibrarySort = Literal["popular", "newest"]


class Library:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def list(
        self,
        *,
        bot_type: str | None = None,
        search: str | None = None,
        sort: LibrarySort | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if bot_type:
            params["botType"] = bot_type
        if search:
            params["search"] = search
        if sort:
            params["sort"] = sort
        if page:
            params["page"] = str(page)
        if limit:
            params["limit"] = str(limit)
        path = "/api/v1/library"
        if params:
            path = f"{path}?{urlencode(params)}"
        data = self._client._request("GET", path)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return list(data["items"])
        return []

    def clone(self, project_id: str, *, subdomain: str) -> dict[str, Any]:
        return self._client._request(
            "POST",
            f"/api/v1/library/{quote(project_id, safe='')}/clone",
            json={"subdomain": subdomain},
        )
