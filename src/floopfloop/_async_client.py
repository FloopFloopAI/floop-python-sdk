"""AsyncFloopClient — the async public entry point.

Mirrors :class:`FloopClient` but uses ``httpx.AsyncClient`` so every method is
``async``. Holds the bearer token and exposes namespaced async resources
(``client.projects``, ``client.secrets``, ...) — same names as the sync
client, different classes (``AsyncProjects``, ``AsyncSecrets``, ...).

Why duplicate instead of share? Python's sync and async syntactic divergence
(``return ...`` vs ``return await ...``) makes a unified base class either
add an ``await`` everywhere or use private dispatch tricks that hide the
real call shape from users. Mature Python SDKs (Anthropic, OpenAI, Stripe)
all duplicate; we follow that pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import httpx

from ._client import (
    DEFAULT_BASE_URL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_TIMEOUT,
    _default_code_for_status,
    _parse_retry_after,
)
from ._version import CURRENT_VERSION
from .errors import FloopError

HttpMethod = Literal["GET", "POST", "PATCH", "DELETE", "PUT"]

if TYPE_CHECKING:
    from .resources.api_keys import AsyncApiKeys
    from .resources.library import AsyncLibrary
    from .resources.projects import AsyncProjects
    from .resources.secrets import AsyncSecrets
    from .resources.subdomains import AsyncSubdomains
    from .resources.subscriptions import AsyncSubscriptions
    from .resources.uploads import AsyncUploads
    from .resources.usage import AsyncUsage
    from .resources.user import AsyncUser


class AsyncFloopClient:
    """Asynchronous FloopFloop API client.

    Example::

        import asyncio
        from floopfloop import AsyncFloopClient

        async def main() -> None:
            async with AsyncFloopClient(api_key="flp_...") as floop:
                created = await floop.projects.create(prompt="a cat cafe landing page")
                live = await floop.projects.wait_for_live(created["project"]["id"])
                print("Live at:", live["url"])

        asyncio.run(main())

    Use ``async with`` to ensure the underlying ``httpx.AsyncClient`` is closed
    on exit. Same arguments as :class:`FloopClient`.
    """

    base_url: str
    poll_interval: float
    projects: AsyncProjects
    secrets: AsyncSecrets
    api_keys: AsyncApiKeys
    library: AsyncLibrary
    subdomains: AsyncSubdomains
    subscriptions: AsyncSubscriptions
    uploads: AsyncUploads
    usage: AsyncUsage
    user: AsyncUser

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        user_agent: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise TypeError("AsyncFloopClient: `api_key` is required")
        self._api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.poll_interval = poll_interval
        self._timeout = timeout
        self._user_agent_suffix = user_agent
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_http = http_client is None

        from .resources.api_keys import AsyncApiKeys
        from .resources.library import AsyncLibrary
        from .resources.projects import AsyncProjects
        from .resources.secrets import AsyncSecrets
        from .resources.subdomains import AsyncSubdomains
        from .resources.subscriptions import AsyncSubscriptions
        from .resources.uploads import AsyncUploads
        from .resources.usage import AsyncUsage
        from .resources.user import AsyncUser

        self.projects = AsyncProjects(self)
        self.secrets = AsyncSecrets(self)
        self.api_keys = AsyncApiKeys(self)
        self.library = AsyncLibrary(self)
        self.subdomains = AsyncSubdomains(self)
        self.subscriptions = AsyncSubscriptions(self)
        self.uploads = AsyncUploads(self)
        self.usage = AsyncUsage(self)
        self.user = AsyncUser(self)

    async def __aenter__(self) -> AsyncFloopClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying async HTTP client (if we own it)."""
        if self._owns_http:
            await self._http.aclose()

    def _user_agent(self) -> str:
        if self._user_agent_suffix:
            return f"floop-sdk-python/{CURRENT_VERSION} {self._user_agent_suffix}"
        return f"floop-sdk-python/{CURRENT_VERSION}"

    async def _request(
        self,
        method: HttpMethod,
        path: str,
        *,
        json: Any = None,
        timeout: float | None = None,
    ) -> Any:
        """Internal async transport. Async resources call this; users shouldn't.

        Returns the response's ``data`` field on success, or raises
        :class:`FloopError` on any failure. Same envelope + error semantics as
        the sync client's ``_request``; only the IO is async.
        """
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": self._user_agent(),
            "Accept": "application/json",
        }
        try:
            resp = await self._http.request(
                method,
                url,
                json=json if json is not None else None,
                headers=headers,
                timeout=timeout if timeout is not None else self._timeout,
            )
        except httpx.TimeoutException as err:
            raise FloopError(
                code="TIMEOUT",
                message=f"Request timed out ({err})",
                status=0,
            ) from err
        except httpx.HTTPError as err:
            raise FloopError(
                code="NETWORK_ERROR",
                message=f"Could not reach {self.base_url} ({err})",
                status=0,
            ) from err

        request_id = resp.headers.get("x-request-id")
        parsed: Any = None
        text = resp.text
        if text:
            try:
                parsed = resp.json()
            except ValueError:
                parsed = None

        if resp.status_code >= 400:
            err_body = (parsed or {}).get("error") if isinstance(parsed, dict) else None
            code = (err_body or {}).get("code") if isinstance(err_body, dict) else None
            message = (
                (err_body or {}).get("message")
                if isinstance(err_body, dict)
                else None
            ) or f"Request failed ({resp.status_code})"
            retry_after_ms = _parse_retry_after(resp.headers.get("retry-after"))
            raise FloopError(
                code=code or _default_code_for_status(resp.status_code),
                message=message,
                status=resp.status_code,
                request_id=request_id,
                retry_after_ms=retry_after_ms,
            )

        if isinstance(parsed, dict) and "data" in parsed:
            return parsed["data"]
        return parsed
