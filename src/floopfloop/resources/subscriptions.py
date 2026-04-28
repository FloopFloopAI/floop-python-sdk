"""``client.subscriptions.current()`` — plan + credit-balance snapshot.

Distinct from :class:`Usage` — ``usage.summary()`` returns current-period
consumption (credits remaining + builds used + storage), while
``subscriptions.current()`` returns the plan tier itself (price, billing
period, cancel state). They overlap on ``monthlyCredits`` and ``maxProjects``
but serve different audiences: ``usage.summary()`` for "am I about to hit
my limits?", ``current()`` for "what plan is this user on, and when does it
renew?".

Both ``subscription`` and ``credits`` on the response can be ``None``
independently — a user may exist without a subscription (mid-signup,
cancelled with no grace credits).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._client import FloopClient


class Subscriptions:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def current(self) -> dict[str, Any]:
        """Fetch the authenticated user's current subscription + credit-balance.

        Returns the full ``{"subscription": {...} | None, "credits": {...} | None}``
        hash. Not wrapped in a dataclass — stays forward-compatible if the
        backend adds fields.
        """
        return self._client._request("GET", "/api/v1/subscriptions/current")
