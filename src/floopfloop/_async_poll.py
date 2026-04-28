"""Async polling helper. Mirror of :func:`_poll.poll_project_status`."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from ._types import TERMINAL_PROJECT_STATUSES, ProjectStatusEvent
from .errors import FloopError

if TYPE_CHECKING:
    from ._async_client import AsyncFloopClient


async def poll_project_status_async(
    client: AsyncFloopClient,
    project_id: str,
    *,
    interval: float | None = None,
    max_polls: int | None = None,
) -> AsyncIterator[ProjectStatusEvent]:
    """Yield project status events until a terminal state is reached.

    Same semantics as :func:`poll_project_status` (consecutive-snapshot
    de-dup, terminal-status set, ``max_polls`` safety cap) but uses
    ``asyncio.sleep`` so it cooperates with the event loop instead of
    blocking it.

    Args:
        client: The :class:`AsyncFloopClient` to poll through.
        project_id: Project id or subdomain.
        interval: Seconds between polls. Defaults to the client's
            ``poll_interval``.
        max_polls: Safety cap on total polls; ``None`` = unbounded.

    Raises:
        FloopError: Propagated from the transport on any failed poll, or
            with code ``TIMEOUT`` if ``max_polls`` is exceeded.
    """
    sleep = interval if interval is not None else client.poll_interval
    previous: str | None = None
    count = 0

    while True:
        if max_polls is not None and count >= max_polls:
            raise FloopError(
                code="TIMEOUT",
                message=f"Polling exceeded {max_polls} iterations without terminal state",
                status=0,
            )
        count += 1

        snap: dict[str, Any] = await client._request(
            "GET", f"/api/v1/projects/{_quote(project_id)}/status"
        )

        status = str(snap.get("status") or "")
        key = "|".join(
            [
                status,
                str(snap.get("step") or ""),
                str(snap.get("progress") or ""),
                str(snap.get("queuePosition") or ""),
            ]
        )
        if key != previous:
            previous = key
            event: ProjectStatusEvent = {
                "status": status,  # type: ignore[typeddict-item]
                "step": int(snap.get("step") or 0),
                "total_steps": int(snap.get("totalSteps") or 0),
                "message": str(snap.get("message") or ""),
            }
            if snap.get("progress") is not None:
                event["progress"] = float(snap["progress"])
            if snap.get("queuePosition") is not None:
                event["queue_position"] = int(snap["queuePosition"])
            yield event

        if status in TERMINAL_PROJECT_STATUSES:
            return
        await asyncio.sleep(sleep)


def _quote(s: str) -> str:
    from urllib.parse import quote

    return quote(s, safe="")


__all__ = ["poll_project_status_async"]
