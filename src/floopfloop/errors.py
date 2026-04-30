"""Single exception type raised by every SDK call on non-2xx responses
(and on network/timeout failures).

Unknown backend codes pass through in ``.code`` as raw strings so callers
can add handling without waiting for an SDK update.
"""

from __future__ import annotations

from typing import Literal

KnownFloopErrorCode = Literal[
    "VALIDATION_ERROR",
    "UNAUTHORIZED",
    "FORBIDDEN",
    "NOT_FOUND",
    "CONFLICT",
    "RATE_LIMITED",
    "SERVER_ERROR",
    "SERVICE_UNAVAILABLE",
    "NETWORK_ERROR",
    "TIMEOUT",
    "BUILD_FAILED",
    "BUILD_CANCELLED",
    "INSUFFICIENT_CREDITS",
    "PAYMENT_FAILED",
    "UNKNOWN",
]

# Note: ``FloopErrorCode`` is intentionally a plain ``str`` alias. Unknown server
# codes are acceptable; ``KnownFloopErrorCode`` above documents the ones we
# actively handle.
FloopErrorCode = str


class FloopError(Exception):
    """Base exception raised by every SDK call on failure.

    Attributes:
        code: Short machine-readable error code (see ``KnownFloopErrorCode``).
        status: HTTP status code; 0 for network / timeout failures.
        request_id: Server-side request id (from the ``x-request-id`` header)
            for correlating with support / logs. ``None`` if not provided.
        retry_after_ms: Populated on 429 from the ``Retry-After`` header.
    """

    code: FloopErrorCode
    status: int
    request_id: str | None
    retry_after_ms: int | None

    def __init__(
        self,
        *,
        code: FloopErrorCode,
        message: str,
        status: int,
        request_id: str | None = None,
        retry_after_ms: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.request_id = request_id
        self.retry_after_ms = retry_after_ms

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"FloopError(code={self.code!r}, status={self.status}, "
            f"request_id={self.request_id!r}, message={str(self)!r})"
        )
