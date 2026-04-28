"""Official Python SDK for the FloopFloop API.

Quickstart (sync)::

    from floopfloop import FloopClient

    floop = FloopClient(api_key="flp_...")
    created = floop.projects.create(prompt="a cat cafe landing page")
    live = floop.projects.wait_for_live(created["project"]["id"])
    print("Live at:", live["url"])

Quickstart (async)::

    import asyncio
    from floopfloop import AsyncFloopClient

    async def main() -> None:
        async with AsyncFloopClient(api_key="flp_...") as floop:
            created = await floop.projects.create(prompt="a cat cafe landing page")
            live = await floop.projects.wait_for_live(created["project"]["id"])
            print("Live at:", live["url"])

    asyncio.run(main())
"""

from ._async_client import AsyncFloopClient
from ._client import FloopClient
from ._types import BotType, ProjectStatus, ProjectStatusEvent
from ._version import CURRENT_VERSION
from .errors import FloopError, FloopErrorCode, KnownFloopErrorCode

__all__ = [
    "CURRENT_VERSION",
    "AsyncFloopClient",
    "BotType",
    "FloopClient",
    "FloopError",
    "FloopErrorCode",
    "KnownFloopErrorCode",
    "ProjectStatus",
    "ProjectStatusEvent",
]
