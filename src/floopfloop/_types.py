"""Shared type aliases and small literal unions used across resources."""

from __future__ import annotations

from typing import Literal, TypedDict

ProjectStatus = Literal[
    "draft",
    "queued",
    "generating",
    "generated",
    "deploying",
    "live",
    "failed",
    "cancelled",
    "archived",
]

BotType = Literal["site", "app", "bot", "api", "internal", "game"]

TERMINAL_PROJECT_STATUSES: frozenset[str] = frozenset(
    {"live", "failed", "cancelled", "archived"}
)


class ProjectStatusEvent(TypedDict, total=False):
    """One snapshot of build progress yielded by ``projects.stream()``."""

    status: ProjectStatus
    step: int
    total_steps: int
    message: str
    progress: float
    queue_position: int
    url: str
