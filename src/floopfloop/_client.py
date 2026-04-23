"""FloopClient — the public entry point.

Holds the bearer token and exposes namespaced resources
(``client.projects``, ``client.secrets``, ...). The internal transport is a
thin wrapper around ``httpx.Client`` that handles the ``{data}``/``{error}``
envelope and translates non-2xx responses into :class:`FloopError`.

Resources are attached in ``__init__`` after everything is imported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import httpx

from ._version import CURRENT_VERSION
from .errors import FloopError

DEFAULT_BASE_URL = "https://www.floopfloop.com"
DEFAULT_TIMEOUT = 30.0
DEFAULT_POLL_INTERVAL = 2.0

HttpMethod = Literal["GET", "POST", "PATCH", "DELETE", "PUT"]

if TYPE_CHECKING:
    from .resources.api_keys import ApiKeys
    from .resources.library import Library
    from .resources.projects import Projects
    from .resources.secrets import Secrets
    from .resources.subdomains import Subdomains
    from .resources.uploads import Uploads
    from .resources.usage import Usage
    from .resources.user import User


class FloopClient:
    """Synchronous FloopFloop API client.

    Example::

        from floopfloop import FloopClient

        floop = FloopClient(api_key="flp_...")
        created = floop.projects.create(prompt="a cat cafe landing page")
        live = floop.projects.wait_for_live(created["project"]["id"])
        print("Live at:", live["url"])

    Args:
        api_key: ``flp_...`` or ``flp_cli_...`` bearer token. Required.
        base_url: Override for staging / local dev. Defaults to
            ``https://www.floopfloop.com``.
        timeout: Per-request timeout in seconds. Defaults to 30.
        poll_interval: Default wait between status polls in
            :meth:`Projects.wait_for_live` and :meth:`Projects.stream`.
            Defaults to 2 seconds.
        user_agent: Appended after ``floop-sdk-python/<v>`` in the User-Agent
            header. Useful for app attribution.
        http_client: Bring-your-own ``httpx.Client`` (for proxies, retries,
            test fixtures). If omitted, a default client is constructed.
    """

    base_url: str
    poll_interval: float
    projects: Projects
    secrets: Secrets
    api_keys: ApiKeys
    library: Library
    subdomains: Subdomains
    uploads: Uploads
    usage: Usage
    user: User

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        user_agent: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise TypeError("FloopClient: `api_key` is required")
        self._api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.poll_interval = poll_interval
        self._timeout = timeout
        self._user_agent_suffix = user_agent
        self._http = http_client or httpx.Client(timeout=timeout)
        self._owns_http = http_client is None

        # Import here to avoid a circular at module import time.
        from .resources.api_keys import ApiKeys
        from .resources.library import Library
        from .resources.projects import Projects
        from .resources.secrets import Secrets
        from .resources.subdomains import Subdomains
        from .resources.uploads import Uploads
        from .resources.usage import Usage
        from .resources.user import User

        self.projects = Projects(self)
        self.secrets = Secrets(self)
        self.api_keys = ApiKeys(self)
        self.library = Library(self)
        self.subdomains = Subdomains(self)
        self.uploads = Uploads(self)
        self.usage = Usage(self)
        self.user = User(self)

    def __enter__(self) -> FloopClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client (if we own it)."""
        if self._owns_http:
            self._http.close()

    def _user_agent(self) -> str:
        if self._user_agent_suffix:
            return f"floop-sdk-python/{CURRENT_VERSION} {self._user_agent_suffix}"
        return f"floop-sdk-python/{CURRENT_VERSION}"

    def _request(
        self,
        method: HttpMethod,
        path: str,
        *,
        json: Any = None,
        timeout: float | None = None,
    ) -> Any:
        """Internal transport. Resources call this; users shouldn't.

        Returns the response's ``data`` field on success, or raises
        :class:`FloopError` on any failure.
        """
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": self._user_agent(),
            "Accept": "application/json",
        }
        try:
            resp = self._http.request(
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


def _default_code_for_status(status: int) -> str:
    if status == 401:
        return "UNAUTHORIZED"
    if status == 403:
        return "FORBIDDEN"
    if status == 404:
        return "NOT_FOUND"
    if status == 409:
        return "CONFLICT"
    if status == 422:
        return "VALIDATION_ERROR"
    if status == 429:
        return "RATE_LIMITED"
    if status == 503:
        return "SERVICE_UNAVAILABLE"
    if status >= 500:
        return "SERVER_ERROR"
    return "UNKNOWN"


def _parse_retry_after(header: str | None) -> int | None:
    if header is None:
        return None
    try:
        seconds = float(header)
    except ValueError:
        return None
    if seconds < 0:
        return None
    return round(seconds * 1000)
