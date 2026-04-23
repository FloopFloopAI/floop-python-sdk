"""Polling helper shared by ``projects.stream()`` and ``projects.wait_for_live()``."""

from __future__ import annotations

import time
from collections.abc import Generator, Iterator
from typing import TYPE_CHECKING, Any

from ._types import TERMINAL_PROJECT_STATUSES, ProjectStatusEvent
from .errors import FloopError

if TYPE_CHECKING:
    from ._client import FloopClient


def poll_project_status(
    client: FloopClient,
    project_id: str,
    *,
    interval: float | None = None,
    max_polls: int | None = None,
) -> Iterator[ProjectStatusEvent]:
    """Yield project status events until a terminal state is reached.

    De-duplicates identical consecutive snapshots (same status / step /
    progress / queue_position) so callers don't see dozens of identical
    "queued" events while a build waits.

    Args:
        client: The :class:`FloopClient` to poll through.
        project_id: Project id or subdomain.
        interval: Seconds between polls. Defaults to the client's
            ``poll_interval``.
        max_polls: Safety cap on total polls, to bound generator lifetime
            in pathological cases (e.g. backend never returns terminal).
            ``None`` = unbounded.

    Raises:
        FloopError: Propagated from the transport on any failed poll.
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

        snap: dict[str, Any] = client._request(
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
        time.sleep(sleep)


def _quote(s: str) -> str:
    # Match JS encodeURIComponent on the characters we actually use.
    from urllib.parse import quote

    return quote(s, safe="")


__all__ = ["poll_project_status"]

# Silence "unused" lint on the Generator import; exported for type hints by
# users that want to annotate their own wrappers.
_ = Generator
