# Product

<!-- impeccable:product-schema 1 -->

## Platform

contract (Book Platform boundary, `book-platform.contract.v1`)

## Users

- The owner and the agents that change the Book Platform: they read this boundary before
  touching the `developer` capability anywhere else.
- Other platform repositories and cells, which may depend on this boundary only through its
  versioned API or event contracts, never its database or private modules.

## Product Purpose

Own the `developer` capability (repository templates, CI/CD, config, feature flags) as a written, checked contract, so the capability can move
out of the `solo-empire` control plane later without consumers noticing.

Success: the contract stays valid against the pinned shared schema, the registry entry matches
it, and every gate in `fixtures/gates/` passes in CI.

## Positioning

A boundary contract with offline evidence, not a running service. The template-independence gate (`scripts/check_independence.py`): generated repositories must not import the hub or hard-code sibling checkouts.

## Operating Context

- Status: `scaffolded`; DOCPACK verdict: `template`. The runtime is not activated; the current
  implementation is `.github` in the parent registry.
- Feature-flag runtime pilot (`src/platform_developer`, PR #1 rebased as `developer-runtime`):
  workspace flags in PostgreSQL with forced RLS, see [docs/runtime.md](docs/runtime.md).
  Built and tested only; not deployed, so the boundary status stays `scaffolded`.
- CI: shared `ci-python` (Ruff and `scripts/check.sh` on Python 3.11 and 3.12), the shared
  security workflow, and `Shared runtime` (pytest against PostgreSQL 16 on Python 3.12, wheel
  build), on GitHub-hosted runners (public repository).
- Sentry does not apply: nothing runs in production. Add it in the change that deploys the
  runtime (staging plan in docs/runtime.md).

## Capabilities and Constraints

- `scripts/check.py`: validates `contract.json` against the vendored schema;
  `scripts/check_schema_pin.py`: the vendored schema matches the pinned canonical hash.
- No production provider integration, database writer, credential or customer payload.
- Out of scope: running the capability; it stays in its current implementation until parity
  and rollback evidence permit a cutover.

## Measures

- `scripts/check.sh` green on `main` (target: always).
- Drift between `contract.json` and the registry entry (target: 0).
- [ต้องยืนยัน] The cutover criteria for activating the runtime.
