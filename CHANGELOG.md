# Changelog

All notable changes to `floopfloop` (Python SDK) are documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This SDK follows [PEP 440](https://peps.python.org/pep-0440/) / SemVer-ish
versioning — alpha releases use the `aN` suffix (e.g. `0.1.0a1`).

## [Unreleased]

## [0.1.0a3] — 2026-04-28

### Added
- **`floop.subscriptions.current()`** — new resource accessor that returns the
  authenticated user's plan + credit-balance snapshot. Wraps
  `GET /api/v1/subscriptions/current`. Distinct from `usage.summary()` —
  `usage.summary()` covers current-period consumption (credits remaining,
  builds used, storage), while `subscriptions.current()` returns the plan
  tier itself (price, billing period, cancel state). They overlap on
  `monthlyCredits` and `maxProjects` but serve different audiences ("am I
  about to hit my limits?" vs "what plan is this user on, and when does it
  renew?").
- Both `subscription` and `credits` keys on the response can be `None`
  independently — a user may exist without a subscription (mid-signup,
  cancelled with no grace credits).

### Tests
- Two new cases in `tests/test_resources.py` covering the populated-response
  shape and the both-null edge case.

### Notes
- Mirrors [`@floopfloop/sdk` PR #6](https://github.com/FloopFloopAI/floop-node-sdk/pull/6)
  (Node `0.1.0-alpha.3`) — cross-SDK parity drop.

## [0.1.0a2] — 2026-04-24

### Fixed
- `_parse_retry_after` now handles the RFC 7231 HTTP-date form in addition to
  `delta-seconds`, so `Retry-After: Wed, 21 Oct 2026 07:28:00 GMT` produces a
  usable `retry_after_ms` instead of `None`. Matches the Node SDK fix in
  [`@floopfloop/sdk` `b11bc20`](https://github.com/FloopFloopAI/floop-node-sdk/commit/b11bc20).

## [0.1.0a1] — 2026-04-23

### Added
- `FloopClient` with bearer auth, configurable base URL, per-request timeouts,
  configurable poll interval, context-manager close, injectable
  `httpx.Client` for proxies / tests.
- `FloopError` exception with typed `.code`, `.status`, `.request_id`,
  `.retry_after_ms` — and pass-through for unknown server codes.
- Resources: `projects`, `secrets`, `api_keys`, `library`, `subdomains`,
  `uploads`, `usage`, `user` — full parity with the FloopFloop CLI and Node SDK.
- `projects.stream()` generator + `projects.wait_for_live()` built on a
  shared polling engine that de-duplicates unchanged snapshots.
- Unit tests with `pytest-httpx` covering transport, polling, every resource.
