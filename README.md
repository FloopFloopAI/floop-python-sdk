# floopfloop

[![PyPI version](https://img.shields.io/pypi/v/floopfloop?logo=pypi&logoColor=white)](https://pypi.org/project/floopfloop/)
[![PyPI downloads](https://img.shields.io/pypi/dm/floopfloop?logo=pypi&logoColor=white)](https://pypi.org/project/floopfloop/)
[![Python versions](https://img.shields.io/pypi/pyversions/floopfloop?logo=python&logoColor=white)](https://pypi.org/project/floopfloop/)
[![CI](https://img.shields.io/github/actions/workflow/status/FloopFloopAI/floop-python-sdk/ci.yml?branch=main&logo=github&label=ci)](https://github.com/FloopFloopAI/floop-python-sdk/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/pypi/l/floopfloop)](./LICENSE)

Official Python SDK for the [FloopFloop](https://www.floopfloop.com) API.
Build a project, refine it, manage secrets and API keys from any Python 3.10+
codebase.

## Install

```bash
pip install floopfloop
```

## Quickstart

Grab an API key via the [floop CLI](https://github.com/FloopFloopAI/floop-cli)
(`floop keys create my-sdk`) or the dashboard → Account → API Keys. Business
plan required to mint new keys.

```python
import os
from floopfloop import FloopClient

floop = FloopClient(api_key=os.environ["FLOOP_API_KEY"])

# Create a project and wait for it to go live.
created = floop.projects.create(
    prompt="A landing page for a cat cafe with a sign-up form",
    name="Cat Cafe",
    subdomain="cat-cafe",
    bot_type="site",
)
live = floop.projects.wait_for_live(created["project"]["id"])
print("Live at:", live["url"])
```

## Streaming progress

```python
for event in floop.projects.stream(project_id):
    print(f"{event['status']} ({event['step']}/{event['total_steps']}) — {event['message']}")
```

## Error handling

Every call raises `FloopError` on non-2xx. Switch on `.code`:

```python
import time
from floopfloop import FloopClient, FloopError

try:
    floop.projects.create(prompt="...")
except FloopError as err:
    if err.code == "RATE_LIMITED":
        time.sleep((err.retry_after_ms or 5000) / 1000)
    elif err.code == "UNAUTHORIZED":
        print("Check your FLOOP_API_KEY.")
    else:
        print(f"[{err.request_id}] {err.code}: {err}")
    raise
```

## Resources

| Namespace           | Methods |
|---|---|
| `floop.projects`    | `create`, `list`, `get`, `status`, `cancel`, `reactivate`, `refine`, `conversations`, `stream`, `wait_for_live` |
| `floop.secrets`     | `list`, `set`, `remove` |
| `floop.api_keys`    | `list`, `create`, `remove` |
| `floop.library`     | `list`, `clone` |
| `floop.subdomains`  | `check`, `suggest` |
| `floop.uploads`     | `create` (for attaching files to `projects.refine`) |
| `floop.usage`       | `summary` |
| `floop.user`        | `me` |

For longer end-to-end patterns — streaming a build, refining mid-deploy, attachment uploads, key rotation, retry-with-backoff — see the [cookbook](docs/recipes.md).

## Authentication

Two token shapes are accepted on `api_key`:

| Prefix       | Source                          | Plan gate         |
|---|---|---|
| `flp_…`      | Dashboard → API Keys, `floop keys create` | Business (to mint) |
| `flp_cli_…`  | `floop login` device token       | Free (unlimited)   |

CLI device tokens (`flp_cli_…`) work here too — handy for local scripts that
already logged in through the CLI.

## Configuration

```python
floop = FloopClient(
    api_key="flp_...",
    base_url="https://www.floopfloop.com",   # override for staging
    timeout=30.0,                             # seconds
    poll_interval=2.0,                        # for wait_for_live / stream
    user_agent="myapp/1.2.3",                 # appended to User-Agent
)
```

Use as a context manager to close the underlying `httpx.Client`:

```python
with FloopClient(api_key="...") as floop:
    floop.projects.list()
```

## Releasing (maintainers only)

This package publishes to PyPI via
[trusted publishing (OIDC)](https://docs.pypi.org/trusted-publishers/) — no
long-lived API token is stored in GitHub Actions.

Before the first release, register the trusted publisher at
<https://pypi.org/manage/project/floopfloop/settings/publishing/>
(or, for a brand-new project, the pending-publisher page):

- **PyPI project name:** `floopfloop`
- **Owner:** `FloopFloopAI`
- **Repository name:** `floop-python-sdk`
- **Workflow name:** `release.yml`
- **Environment name:** leave blank

After that, ship a release by bumping `pyproject.toml` + `src/floopfloop/_version.py`, pushing a `py-v<version>` tag. The release workflow will build, test, and publish.

## License

MIT. See [LICENSE](./LICENSE).

## Related

- [@floopfloop/sdk](https://www.npmjs.com/package/@floopfloop/sdk) — Node.js
  twin of this SDK; same backend surface.
- [floop-cli](https://github.com/FloopFloopAI/floop-cli) — the CLI that ships
  the same backend surface as a terminal UI.
- [Customer docs](https://www.floopfloop.com/docs) — API reference.
