# Contract surface: book-developer-platform

This page documents the API, event, CLI, storage and configuration surface that
`book-developer-platform` owns or consumes. The machine-readable list is `interfaces` in
[`contract.json`](../contract.json); `scripts/check.py` fails when an interface
listed there is missing from this page.

- Platform: `developer` (contract `book-platform.contract.v1`, API `v1`)
- Status: `scaffolded`; source status: `current-implementation-in-solo-empire`
- Current implementation: `solo-empire` at `.github`, `infra/tasks`
- Depends on: `security`, `observability`

Interfaces marked `current-in-solo-empire` are served by the `solo-empire`
control plane today. This repository does not serve them yet; they are the
compatibility surface a migration must preserve. The `source` column is a path
in the implementing repository.

## Interfaces

| ID | Kind | Direction | Interface | Contract | Auth | Source | Status |
|---|---|---|---|---|---|---|---|
| `developer.workflow.ci` | workflow | provides | GitHub Actions CI (push, pull_request) | - | - | `.github/workflows/ci.yml` | current-in-solo-empire |
| `developer.workflow.platform-validate` | workflow | provides | Platform Validate workflow for infra/platform assets (no deploy) | - | - | `.github/workflows/platform-validate.yml` | current-in-solo-empire |
| `developer.config.dependabot` | config | provides | Dependabot update policy | - | - | `.github/dependabot.yml` | current-in-solo-empire |
| `developer.config.agent-roles` | config | provides | Sub-agent role registry shared by Copilot, Claude Code and Codex | - | - | `.github/agents/roles.yaml` | current-in-solo-empire |
| `developer.workflow.platform-check` | workflow | provides | Reusable offline contract check (scripts/check.sh + .github/workflows/check.yml in each platform) | - | - | `none` | implemented |

## Behaviour notes

Derived from the current source; re-check the source before changing a
consumer.

- The Developer platform publishes conventions, not runtime APIs. It is not a
  runtime dependency of business requests.
- Each Book Platform repository carries the same offline contract gate:
  `schema/book-platform.contract.v1.schema.json`, `scripts/check.py`,
  `scripts/check.sh`, `tests/test_contract_check.py` and
  `.github/workflows/check.yml`. The canonical schema lives in
  `bookchaowalit-backend-core/contracts/`.

## Migration gates

- reproducible build
- secret scan
- rollback documentation

## Out of scope

No production provider integration, credential, database writer or customer
payload lives in this repository. Record parity, privacy and rollback evidence
in the parent platform registry before any cutover.
