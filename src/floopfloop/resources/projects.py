"""``client.projects.*`` — create, list, status, refine, wait-for-live."""

from __future__ import annotations

import builtins
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode

from .._async_poll import poll_project_status_async
from .._poll import poll_project_status
from .._types import ProjectStatusEvent
from ..errors import FloopError

if TYPE_CHECKING:
    from .._async_client import AsyncFloopClient
    from .._client import FloopClient


class Projects:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def create(
        self,
        *,
        prompt: str,
        name: str | None = None,
        subdomain: str | None = None,
        bot_type: str | None = None,
        is_auth_protected: bool | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a project. Returns ``{project, deployment}`` immediately;
        call :meth:`wait_for_live` to await completion."""
        body: dict[str, Any] = {"prompt": prompt}
        if name is not None:
            body["name"] = name
        if subdomain is not None:
            body["subdomain"] = subdomain
        if bot_type is not None:
            body["botType"] = bot_type
        if is_auth_protected is not None:
            body["isAuthProtected"] = is_auth_protected
        if team_id is not None:
            body["teamId"] = team_id
        return self._client._request("POST", "/api/v1/projects", json=body)

    def list(self, *, team_id: str | None = None) -> list[dict[str, Any]]:
        """List projects."""
        path = "/api/v1/projects"
        if team_id:
            path = f"{path}?{urlencode({'teamId': team_id})}"
        return self._client._request("GET", path)

    def get(self, ref: str, *, team_id: str | None = None) -> dict[str, Any]:
        """Fetch one project by id or subdomain.

        There is no dedicated GET route; we filter the list.
        """
        all_ = self.list(team_id=team_id)
        for p in all_:
            if p.get("id") == ref or p.get("subdomain") == ref:
                return p
        raise FloopError(
            code="NOT_FOUND", message=f"Project not found: {ref}", status=404
        )

    def status(self, ref: str) -> dict[str, Any]:
        return self._client._request(
            "GET", f"/api/v1/projects/{quote(ref, safe='')}/status"
        )

    def cancel(self, ref: str) -> Any:
        return self._client._request(
            "POST", f"/api/v1/projects/{quote(ref, safe='')}/cancel"
        )

    def reactivate(self, ref: str) -> Any:
        return self._client._request(
            "POST", f"/api/v1/projects/{quote(ref, safe='')}/reactivate"
        )

    def refine(
        self,
        ref: str,
        *,
        message: str,
        attachments: builtins.list[dict[str, Any]] | None = None,
        code_edit_only: bool | None = None,
        wait: bool = False,
    ) -> Any:
        """Queue a refinement. If ``wait=True``, block until the follow-up
        build reaches a terminal state."""
        body: dict[str, Any] = {"message": message}
        if attachments is not None:
            body["attachments"] = attachments
        if code_edit_only is not None:
            body["codeEditOnly"] = code_edit_only
        result = self._client._request(
            "POST", f"/api/v1/projects/{quote(ref, safe='')}/refine", json=body
        )
        if not wait:
            return result
        return self.wait_for_live(ref)

    def conversations(
        self, ref: str, *, limit: int | None = None
    ) -> dict[str, Any]:
        path = f"/api/v1/projects/{quote(ref, safe='')}/conversations"
        if limit is not None:
            path = f"{path}?{urlencode({'limit': limit})}"
        return self._client._request("GET", path)

    def stream(
        self, ref: str, *, interval: float | None = None
    ) -> Iterator[ProjectStatusEvent]:
        """Yield status transitions until a terminal state."""
        return poll_project_status(self._client, ref, interval=interval)

    def wait_for_live(
        self, ref: str, *, interval: float | None = None
    ) -> dict[str, Any]:
        """Block until the project reaches ``live``.

        Raises :class:`FloopError` with code ``BUILD_FAILED`` /
        ``BUILD_CANCELLED`` on the other terminals.
        """
        last: ProjectStatusEvent | None = None
        for event in poll_project_status(self._client, ref, interval=interval):
            last = event
        if last is None:
            raise FloopError(
                code="UNKNOWN",
                message="wait_for_live: poll yielded no events",
                status=0,
            )
        if last.get("status") == "failed":
            raise FloopError(
                code="BUILD_FAILED",
                message=last.get("message") or "Build failed",
                status=0,
            )
        if last.get("status") == "cancelled":
            raise FloopError(
                code="BUILD_CANCELLED",
                message=last.get("message") or "Build cancelled",
                status=0,
            )
        return self.get(ref)


class AsyncProjects:
    """Async mirror of :class:`Projects`. Same methods, all coroutines."""

    def __init__(self, client: AsyncFloopClient) -> None:
        self._client = client

    async def create(
        self,
        *,
        prompt: str,
        name: str | None = None,
        subdomain: str | None = None,
        bot_type: str | None = None,
        is_auth_protected: bool | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"prompt": prompt}
        if name is not None:
            body["name"] = name
        if subdomain is not None:
            body["subdomain"] = subdomain
        if bot_type is not None:
            body["botType"] = bot_type
        if is_auth_protected is not None:
            body["isAuthProtected"] = is_auth_protected
        if team_id is not None:
            body["teamId"] = team_id
        return await self._client._request("POST", "/api/v1/projects", json=body)

    async def list(self, *, team_id: str | None = None) -> list[dict[str, Any]]:
        path = "/api/v1/projects"
        if team_id:
            path = f"{path}?{urlencode({'teamId': team_id})}"
        return await self._client._request("GET", path)

    async def get(self, ref: str, *, team_id: str | None = None) -> dict[str, Any]:
        all_ = await self.list(team_id=team_id)
        for p in all_:
            if p.get("id") == ref or p.get("subdomain") == ref:
                return p
        raise FloopError(
            code="NOT_FOUND", message=f"Project not found: {ref}", status=404
        )

    async def status(self, ref: str) -> dict[str, Any]:
        return await self._client._request(
            "GET", f"/api/v1/projects/{quote(ref, safe='')}/status"
        )

    async def cancel(self, ref: str) -> Any:
        return await self._client._request(
            "POST", f"/api/v1/projects/{quote(ref, safe='')}/cancel"
        )

    async def reactivate(self, ref: str) -> Any:
        return await self._client._request(
            "POST", f"/api/v1/projects/{quote(ref, safe='')}/reactivate"
        )

    async def refine(
        self,
        ref: str,
        *,
        message: str,
        attachments: builtins.list[dict[str, Any]] | None = None,
        code_edit_only: bool | None = None,
        wait: bool = False,
    ) -> Any:
        body: dict[str, Any] = {"message": message}
        if attachments is not None:
            body["attachments"] = attachments
        if code_edit_only is not None:
            body["codeEditOnly"] = code_edit_only
        result = await self._client._request(
            "POST", f"/api/v1/projects/{quote(ref, safe='')}/refine", json=body
        )
        if not wait:
            return result
        return await self.wait_for_live(ref)

    async def conversations(
        self, ref: str, *, limit: int | None = None
    ) -> dict[str, Any]:
        path = f"/api/v1/projects/{quote(ref, safe='')}/conversations"
        if limit is not None:
            path = f"{path}?{urlencode({'limit': limit})}"
        return await self._client._request("GET", path)

    def stream(
        self, ref: str, *, interval: float | None = None
    ) -> AsyncIterator[ProjectStatusEvent]:
        """Yield status transitions until a terminal state.

        Returns an async iterator (not a coroutine) — use
        ``async for ev in client.projects.stream(ref):``.
        """
        return poll_project_status_async(self._client, ref, interval=interval)

    async def wait_for_live(
        self, ref: str, *, interval: float | None = None
    ) -> dict[str, Any]:
        """Async mirror of :meth:`Projects.wait_for_live`."""
        last: ProjectStatusEvent | None = None
        async for event in poll_project_status_async(
            self._client, ref, interval=interval
        ):
            last = event
        if last is None:
            raise FloopError(
                code="UNKNOWN",
                message="wait_for_live: poll yielded no events",
                status=0,
            )
        if last.get("status") == "failed":
            raise FloopError(
                code="BUILD_FAILED",
                message=last.get("message") or "Build failed",
                status=0,
            )
        if last.get("status") == "cancelled":
            raise FloopError(
                code="BUILD_CANCELLED",
                message=last.get("message") or "Build cancelled",
                status=0,
            )
        return await self.get(ref)
