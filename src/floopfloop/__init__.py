"""Official Python SDK for the FloopFloop API.

Quickstart::

    from floopfloop import FloopClient

    floop = FloopClient(api_key="flp_...")
    created = floop.projects.create(prompt="a cat cafe landing page")
    live = floop.projects.wait_for_live(created["project"]["id"])
    print("Live at:", live["url"])
"""

from ._client import FloopClient
from ._types import BotType, ProjectStatus, ProjectStatusEvent
from ._version import CURRENT_VERSION
from .errors import FloopError, FloopErrorCode, KnownFloopErrorCode

__all__ = [
    "CURRENT_VERSION",
    "BotType",
    "FloopClient",
    "FloopError",
    "FloopErrorCode",
    "KnownFloopErrorCode",
    "ProjectStatus",
    "ProjectStatusEvent",
]
