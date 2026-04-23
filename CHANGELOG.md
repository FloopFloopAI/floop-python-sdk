# Changelog

All notable changes to `floopfloop` (Python SDK) are documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This SDK follows [PEP 440](https://peps.python.org/pep-0440/) / SemVer-ish
versioning — alpha releases use the `aN` suffix (e.g. `0.1.0a1`).

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
