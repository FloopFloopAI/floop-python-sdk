# Cookbook

Concrete `floopfloop` patterns you can copy-paste. Every snippet uses only the SDK's public surface — no undocumented endpoints, no private helpers.

For the basics (install, client setup, resource tour) see the [README](../README.md). This file is the **"I know the basics, now how do I actually build X"** layer.

These recipes mirror the [`@floopfloop/sdk` cookbook](https://github.com/FloopFloopAI/floop-node-sdk/blob/main/docs/recipes.md), translated to Python idioms.

---

## 1. Ship a project from prompt to live URL

The canonical one-call flow: create, wait, done. `wait_for_live` raises `FloopError` with code `BUILD_FAILED` / `BUILD_CANCELLED` on non-success terminals, so a plain `try/except` is enough.

```python
import os
from floopfloop import FloopClient, FloopError

client = FloopClient(api_key=os.environ["FLOOP_API_KEY"])


def ship(prompt: str, subdomain: str) -> str:
    created = client.projects.create(
        prompt=prompt,
        subdomain=subdomain,
        bot_type="site",
    )
    project_id = created["project"]["id"]

    try:
        # Polls status every 2s and returns when status == "live".
        live = client.projects.wait_for_live(project_id)
        return live["url"]
    except FloopError as err:
        if err.code == "BUILD_FAILED":
            print(f"Build failed: {err}")
        raise


url = ship(
    "A single-page portfolio for a landscape photographer",
    "landscape-portfolio",
)
print(f"Live at {url}")
```

**Wall-clock timeout.** `wait_for_live` doesn't take a `signal` — Python doesn't have a first-class equivalent. If you need an outside cap, run it in a thread with `concurrent.futures.ThreadPoolExecutor` and `.result(timeout=...)`:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(client.projects.wait_for_live, project_id)
    live = future.result(timeout=600)  # 10 min hard cap
```

The polling loop itself doesn't honour the timeout — it only stops when the build reaches a terminal state — but the future raises `TimeoutError` on the caller side, which is what you want for fail-fast behaviour.

**When to prefer `stream` over `wait_for_live`:** if you want to show progress to a user (spinner, status line). `wait_for_live` only returns at the end — no visibility into what the build is doing.

---

## 2. Watch a build progress in real time

`projects.stream(ref)` is a generator that yields status events as the project changes state. It de-duplicates identical consecutive snapshots (same `status` / `step` / `progress` / `queuePosition`), so iterating it naively doesn't spam the UI on every poll.

```python
import os
from floopfloop import FloopClient

client = FloopClient(api_key=os.environ["FLOOP_API_KEY"])

created = client.projects.create(
    prompt="A recipe blog with a dark theme",
    subdomain="recipe-blog",
    bot_type="site",
)
project_id = created["project"]["id"]

for event in client.projects.stream(project_id):
    progress = f" {event['progress']}%" if event.get("progress") is not None else ""
    step = f" — {event['step']}" if event.get("step") else ""
    print(f"[{event['status']}]{progress}{step}")

    # Iteration ends automatically on terminal state:
    #   live / failed / cancelled / archived

# Fetch the full project once the stream completes:
done = client.projects.get(project_id)
print(f"Live at {done['url']}")
```

**Custom poll cadence.** The default is 2s. Pass `interval=` to slow it down for long builds:

```python
for event in client.projects.stream(project_id, interval=5.0):
    ...
```

---

## 3. Refine a project, even when it's mid-build

`projects.refine()` returns a dict that tells you *what happened* to your follow-up message without re-polling:

- `{"queued": True, "messageId": "..."}` — the project is currently deploying; your message is queued and will be processed when the current build finishes.
- `{"processing": True, "deploymentId": "...", "queuePriority": N}` — your message triggered a new build immediately.
- `{"queued": False}` — the message was saved as a conversation entry without triggering a build.

```python
import os
from floopfloop import FloopClient

client = FloopClient(api_key=os.environ["FLOOP_API_KEY"])

result = client.projects.refine(
    "recipe-blog",
    message="Add a search bar to the header",
)

if result.get("processing"):
    print(f"Build started (deployment {result['deploymentId']})")
    client.projects.wait_for_live("recipe-blog")
elif result.get("queued"):
    print(f"Queued behind current build (message {result['messageId']})")
    # Poll the project once — when it's back to "live", your queued
    # message has already been picked up and processed.
    client.projects.wait_for_live("recipe-blog")
else:
    print("Saved as a chat message, no build triggered")
```

**Shortcut for fire-and-forget.** Pass `wait=True` and `refine` will block until the resulting build finishes (or raise `BUILD_FAILED`). It handles the queued-vs-processing distinction internally:

```python
live_project = client.projects.refine(
    "recipe-blog",
    message="Add a search bar to the header",
    wait=True,
)
```

---

## 4. Upload an image and refine with it as context

Uploads are two-step: `uploads.create()` presigns an S3 URL and does the direct PUT for you, returning the descriptor you pass to the next API call. The descriptor is an opaque dict — don't try to construct one by hand.

```python
import os
from floopfloop import FloopClient

client = FloopClient(api_key=os.environ["FLOOP_API_KEY"])

attachment = client.uploads.create(
    file_name="mockup.png",
    path="./mockup.png",
    # file_type="image/png",  # optional — guessed from the extension
)

client.projects.refine(
    "recipe-blog",
    message="Make the homepage look like this mockup.",
    attachments=[attachment],
    wait=True,
)
```

`uploads.create` accepts either `path=` (filesystem path) **or** `content=` (bytes), but not both — the SDK raises `TypeError` if you pass both or neither.

**Supported types:** `png`, `jpg/jpeg`, `gif`, `svg`, `webp`, `ico`, `pdf`, `txt`, `csv`, `doc`, `docx`. Max 5 MB per upload. The SDK validates client-side before hitting the network, so bad inputs raise `FloopError(code="VALIDATION_ERROR")` with no round-trip.

Attachments only flow through `refine` today — `create` doesn't accept them via the SDK. If you need to anchor a brand-new project against images, create with a prompt first, then refine with the attachments as a follow-up.

---

## 5. Rotate an API key from a CI job

Three-step rotation: create the new key, write it to your secret store, then revoke the old one. The order matters — you must revoke with a **different** key than the one making the call (the backend returns `400 VALIDATION_ERROR` if you try to revoke the key you're authenticated with).

```python
import os
from floopfloop import FloopClient


def rotate(victim_name: str) -> None:
    # Use a long-lived bootstrap key (stored as a CI secret) to do the
    # rotation. Don't use the key we're about to revoke — that hits the
    # self-revoke guard.
    bootstrap = FloopClient(api_key=os.environ["FLOOP_BOOTSTRAP_KEY"])

    # 1. Find the key we want to rotate by its name. (Each name is unique
    #    per account because the dashboard enforces it; matching by name
    #    is more reliable than matching the prefix substring.)
    keys = bootstrap.api_keys.list()
    victim = next((k for k in keys if k["name"] == victim_name), None)
    if victim is None:
        raise RuntimeError(f"key not found: {victim_name}")

    # 2. Mint the replacement.
    fresh = bootstrap.api_keys.create(name=f"{victim_name}-new")
    write_secret("FLOOP_API_KEY", fresh["rawKey"])  # your secret-store helper

    # 3. Revoke the old one. api_keys.remove() accepts an id OR a name.
    bootstrap.api_keys.remove(victim["id"])
```

**Can't I just reuse the bootstrap key forever?** Technically yes — if it's tightly scoped and audited. In practice, a single long-lived "rotator key" is a common compromise: it only has permission to mint/list/revoke keys, never appears in application traffic, and itself gets rotated manually on a rare cadence (annually, or on compromise).

The 5-keys-per-account cap applies to active keys, so make sure to revoke old rotations rather than accumulating them.

---

## 6. Retry with backoff on `RATE_LIMITED` and `NETWORK_ERROR`

`FloopError` carries everything you need to implement backoff correctly:

- `retry_after_ms` — present on 429s, set from the server's `Retry-After` header (parsed from delta-seconds OR HTTP-date).
- `code` — distinguishes retryable (`RATE_LIMITED`, `NETWORK_ERROR`, `TIMEOUT`, `SERVICE_UNAVAILABLE`, `SERVER_ERROR`) from permanent (`UNAUTHORIZED`, `FORBIDDEN`, `VALIDATION_ERROR`, `NOT_FOUND`, `CONFLICT`, `BUILD_FAILED`, `BUILD_CANCELLED`).

```python
import random
import time
from typing import Callable, TypeVar

from floopfloop import FloopError

T = TypeVar("T")

RETRYABLE = frozenset({
    "RATE_LIMITED",
    "NETWORK_ERROR",
    "TIMEOUT",
    "SERVICE_UNAVAILABLE",
    "SERVER_ERROR",
})


def with_retry(fn: Callable[[], T], max_attempts: int = 5) -> T:
    attempt = 0
    while True:
        try:
            return fn()
        except FloopError as err:
            attempt += 1
            if err.code not in RETRYABLE:
                raise
            if attempt >= max_attempts:
                raise

            # Prefer the server's hint; fall back to exponential backoff
            # with jitter capped at 30 s.
            server_hint_ms = err.retry_after_ms
            expo_ms = min(30_000, 250 * (2 ** attempt))
            jitter_ms = random.uniform(0, 250)
            wait_ms = (server_hint_ms or expo_ms) + jitter_ms

            request_id = f" — request {err.request_id}" if err.request_id else ""
            print(
                f"floop: {err.code} (attempt {attempt}/{max_attempts}), "
                f"retrying in {round(wait_ms)}ms{request_id}"
            )
            time.sleep(wait_ms / 1000)


# Wrap any SDK call:
projects = with_retry(lambda: client.projects.list())
```

**Don't retry everything.** `VALIDATION_ERROR`, `UNAUTHORIZED`, and `FORBIDDEN` are not going to fix themselves between attempts — retrying them just burns rate-limit budget and delays the real error reaching your logs.

---

## 7. Make a small change without a full rebuild (`code_edit_only`)

Default `refine()` runs the full 6-step pipeline — replan, regenerate, redeploy. For a copy edit, a colour swap, or a typo fix that doesn't need a redesign, set `code_edit_only=True`. The backend cuts to a 3-step in-place patch and deducts the cheaper code-edit credit cost (roughly half a refinement).

Only meaningful once the project has reached `live` at least once — on a project that hasn't deployed yet, the flag is ignored and you get a normal initial build.

```python
client.projects.refine(
    "recipe-blog",
    message="Change the hero headline from 'Welcome' to 'Hello there.'",
    code_edit_only=True,
    wait=True,
)
```

If the change actually needs a redesign or a new dependency, prefer a plain `refine()` — `code_edit_only` is for surface-level edits only. The backend won't promote a code-edit into a full refinement automatically; it just runs the 3-step patch with the limited tools it has, and you may end up paying for a second `refine()` to redo the change properly.

---

## Got a pattern worth adding?

Open an issue at [FloopFloopAI/floop-python-sdk/issues](https://github.com/FloopFloopAI/floop-python-sdk/issues) describing the use case. Recipes live in this file, not in `src/`, so they're easy to update without an SDK release.
