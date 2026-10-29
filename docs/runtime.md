# Developer runtime pilot

Status: implemented, verified locally and in CI on Python 3.12/PostgreSQL 16;
deployment artifacts staged only (see the staging plan at the end).
Correlation: `SHARED-INFRA-2026-10-15`. No production activation or provider
acceptance is claimed. The legacy contract's scaffolded migration marker stays
unchanged because its guard requires activation evidence.

## Installation and lifecycle

Python >=3.12, PostgreSQL >=16. Nothing is published to PyPI. Local editing
uses `pip install -e . --no-deps` after installing the reviewed core and runtime
dependencies. `railway.toml` is a reference release asset; no Railway deployment
has been executed here.

### Container image

`docker build .` works from a clean checkout; no pre-staged `wheelhouse/` is
needed. The `Dockerfile` is two stages:

1. `build` (`python:3.12-slim` plus `git`): `pip wheel` builds this service's wheel
   and `platform-backend-core` from the same reviewed commit CI installs
   (`88306b28228f789eecd214a11ca8a0640e9d6233`), with all transitive dependencies.
2. `runtime` (`python:3.12-slim`, no git, no build tools): installs only those
   wheels with `--no-index`, runs as UID/GID `65532`, `PORT=8080`, and keeps
   `CMD ["python", "-m", "platform_developer", "serve"]`. Run `migrate` as a
   separate one-off with the DDL-role `DATABASE_URL` (same image, command override).

`.dockerignore` keeps `.git`, `.venv`, build output and `.env*` out of the build
context. CI job `image` in `shared-runtime.yml` runs `docker build` on every push
and pull request, then checks that the image imports the service and runs as a
non-root user. It never pushes or deploys. `tests/test_build_hygiene.py` (part of
`scripts/check.sh`) fails if the Dockerfile copies a git-ignored path, stops being
multi-stage, pins a core commit other than the workflow's, runs the final stage as
root or changes the CMD, if CI stops building the image, or if any workflow `uses:`
is not pinned to a 40-hex commit SHA (tags go in a trailing comment). Upgrading
the core means changing the commit in the workflow, the Dockerfile and
`[tool.uv.sources]` together; the tests fail on any mismatch.

- `python -m platform_developer migrate`: explicit migration with DDL-role `DATABASE_URL`.
- `python -m platform_developer serve`: separate nonowner, NOSUPERUSER NOBYPASSRLS
  runtime `DATABASE_URL`; `PORT` defaults to 8080. Maximum API concurrency 100,
  pool 8, SQL timeout 10 seconds, HTTP boundary 30 seconds.
- Configure `JWT_ISSUER`, `JWT_AUDIENCE`, and exactly one `JWT_PUBLIC_KEY`
  (public PEM) or `JWT_JWKS_URL` (trusted HTTPS). Credentials never come from
  files or token-supplied URLs. Use the shared-core workspace RS256 profile.
- `GET /healthz`, `/readyz`, `/metrics` use shared redacted diagnostics.
  Readiness checks exact applied migration versions/checksums, table RLS, effective
  schema USAGE/history SELECT and every required table operation individually;
  missing schema returns generic 503. Setup and serving are separate commands.
- Python interface `platform_developer.app:create_app(database, verifier)` and
  `platform_developer.migrations.MIGRATIONS` support explicit dependency injection.

The DDL role owns the schema. Grant runtime schema USAGE, SELECT on
`platform_schema_migrations`, and only needed table permissions below. Do not
grant ownership, CREATE, TRUNCATE, schema-history writes or migration execution.
Use a dedicated database per service; no other service's tables are imported.
Runtime role and backup/restore provisioning remain operator release work.
All workspace authority comes from JWT `ws`, actor from JWT `sub`; body/header
workspace fields never select tenant context. API validation errors are generic.
Only request-schema errors and the store's domain `InvalidInput` (a `ValueError`
subclass) return 422 `Invalid input`; any other exception, including an unexpected
`ValueError`, is a server bug and returns the shared core's redacted 500.

## Verification and release gate

Run original `bash scripts/check.sh`, then `PLATFORM_TEST_DSN=<explicit disposable
local admin DSN> python -m pytest -q`. Without that DSN the PostgreSQL cases
visibly skip and provide no durability evidence. Runtime tests use unique
throwaway databases and NOSUPERUSER NOBYPASSRLS roles, real JWT signatures,
concurrent independent connections, and HTTP requests. Tests never call live
providers. The 2026-10-15 record below used Python 3.14/PostgreSQL 18; the
3.12/16 floor was executed on 2026-10-29 (see that record). One upstream Starlette/httpx deprecation
warning remains. Production load, backup restore, credential rotation, ingress
policy and full provider acceptance belong to integration/release gates.

Rollback stops this optional runtime and restores consumers to the previous
adapter. Do not downgrade applied SQL or overwrite a live database. Restore
only to a new isolated database and verify synthetic workspace reads before
cutover. Coordinate retention and backup encryption with the owning operator;
no scheduled deletion or backup credential access is implemented here.

## Flag API

Grant runtime SELECT, INSERT, UPDATE, DELETE on `feature_flags` only.

- `PUT /v1/flags/{name}` (`flags:write`): `enabled` boolean, `rollout` integer
  0..10000 basis points, optional `subjects` array <=100 allowlisted strings,
  optional positive `version`. Omit version for create; exact current version
  for update. A stale/create conflict returns 409. Version increments atomically.
- `GET /v1/flags` and `GET /v1/flags/{name}` (`flags:read`). `limit` 1..100;
  `after` is the last name. Cross-workspace IDs return 404.
- `DELETE /v1/flags/{name}?version=N` (`flags:write`) requires exact version.
- `POST /v1/flags/{name}/evaluate` (`flags:read`) accepts `subject`.

Identifiers match `[a-z][a-z0-9_.-]{0,63}`. Subjects match
`[A-Za-z0-9_:@.-]{1,128}`. Disabled/missing returns false; otherwise an explicit
allowlisted subject or rollout admits the request. The bucket is the first
8 SHA256 bytes, unsigned big-endian, of UTF-8 `workspace:flag:subject`, modulo
10000. It depends only on durable data and identifiers, so replicas/restarts
agree. There are no arbitrary expressions or process-local assignments. The
flag row version is also its configuration version; no separate incoherent
configuration store is advertised.

## Local verification record — 2026-10-15

- Initial runtime suite was RED during collection because the new service
  package/store did not exist. This is missing-interface evidence, not an
  assertion-level behavioral failure.
- An assertion-level regression test removed applied migration history and
  observed the developer readiness endpoint incorrectly return 200; after
  adding exact checksum/version checks it returns 503. The same history
  checks are present in all three services.
- Final full suite: `42 passed`, no database skips, one upstream warning.
- Original `bash scripts/check.sh`: passed, 36 legacy unit tests.
- Isolated wheel build and import: passed. No wheel publication, container
  build, live provider operation, push or deployment was performed.

## Independent review correction — 2026-10-15

Round 1 reproduced 4 assertion-level failures before fixes in this service.
Readiness now checks effective `public` schema USAGE, history SELECT, and
separate SELECT/INSERT/UPDATE privileges for writable tables, plus DELETE for
feature flags. It does not interpret comma-separated privilege lists as an
all-required check (PostgreSQL treats those as any privilege). Each required
privilege is revoked independently in a disposable runtime role: ready changes
200 to 503, then returns to 200 after restoration. All audit forbidden
UPDATE/DELETE/TRUNCATE checks remain; each is also granted independently in
regression tests and correctly makes security not ready.

Full PostgreSQL-backed suite after correction: `49 passed`, no database
skips, one unchanged upstream Starlette/httpx warning. Original offline check
also passed. Migration 0001 SQL/checksum is unchanged.

The documented `python -m platform_developer migrate` now shares the canonical
`MIGRATION_NAMESPACE='flags'` constant with readiness. A subprocess regression
test invokes that exact CLI against a fresh database, grants runtime access,
then verifies HTTP `/readyz` is 200 and stored namespace/checksum are correct.
Previously this flow stored namespace `developer` and returned 503. Existing
`flags` migration history is preserved; no migration history rewrite or SQL
backfill is performed.

## Pooled connection reuse

Store queries that return mappings use cursor-scoped `dict_row`; they do not
change the pooled connection row factory. Single-connection PostgreSQL
regressions cover successful traffic, conflicts, rollback and foreign-workspace
reads followed by repeated service and shared-core readiness checks.

## Verification 2026-10-29 (branch `developer-runtime`)

PR #1 (`codex/shared-infrastructure-20261015`, closed by decision D8 with the
branch kept) rebased onto `main` `ac888fa` without conflicts, keeping `main`'s
contract, BOO-155 independence gate and shared CI v1.1.1 (Ruff, `scripts/check.sh`,
security scans incl. gitleaks). Scope stays the feature-flag API above; no flag
behaviour changed.

Changes beyond the rebase:

- BOO-155 gap 5 closed: the fixture's `present_on: pending ...` marker for
  `.github/workflows/shared-runtime.yml` is removed now that the file lands, and
  `GateFixtureTests.test_present_files_carry_no_pending_marker` fails if an
  existing file keeps a pending marker. The pending-tolerance test uses a
  synthetic not-landed file so it still exercises the rule.
- Reproducible build gate: `[tool.uv.sources]` pins `platform-backend-core` to the
  commit `shared-runtime.yml` installs (`88306b28`; the name is not on PyPI, so this
  blocks dependency confusion). `runtime_tests/test_build_pin.py` checks the pin
  matches the workflow and the dependency stays exact.
- Ruff 0.17.1 clean: `extend-immutable-calls` for FastAPI markers and
  `require_scope`, sorted/unused imports, the RLS regression asserts
  `InsufficientPrivilege` instead of any exception, a copy-pasted
  communication-adapter branch removed from two readiness tests, and the CLI's
  redacting `except` carries a `noqa: BLE001` reason.
- `runtime_tests/test_pool_reuse.py` skips visibly without `PLATFORM_TEST_DSN`
  (it raised `KeyError`), as this document already promised.

Environment: Python 3.12, PostgreSQL 16.2 (local `pgserver`; CI uses the
`postgres:16` service), `platform-backend-core` at `88306b28`, no network calls,
no credentials. `PLATFORM_TEST_DSN` pointed at the disposable local server.

RED (each test written first and run before the change):

- `python3 -m unittest tests.test_independence`: 2 failures,
  `test_present_files_carry_no_pending_marker` (`['.github/workflows/shared-runtime.yml'] != []`)
  and the clean-checkout copy failing on the same test.
- `pytest runtime_tests/test_build_pin.py`: 1 failed, 1 passed
  (`assert None == {'git': ..., 'rev': '88306b28...'}`).
- `pytest runtime_tests` without a DSN: 2 errors (`KeyError: 'PLATFORM_TEST_DSN'`).

GREEN after the changes:

- `PLATFORM_TEST_DSN=... python -m pytest -q`: 74 passed, 27 subtests, no
  database skips, one upstream Starlette/httpx deprecation warning.
- `pytest runtime_tests` without a DSN: 2 passed, 15 skipped.
- `bash scripts/check.sh`: contract, schema pin, independence gate, 57 unit tests OK.
- `ruff check .` (0.17.1): clean. `gitleaks git` 8.30.1 over full history: no leaks.

Not done here (deliberately): deployment, a container build, owner-only
BOO-155 follow-ups (branch protection on `main`, dropping the
`BOOK_BACKEND_CORE_DIR` default, the registry `source_paths` change), and any
flag feature beyond PR #1 (targeting rules, audit history, SDK caching).

## Review follow-ups 2026-10-29 (branch `developer-followups`)

Three low-severity review findings on `main` `701ebe6`:

1. The app mapped every `ValueError` to 422, hiding server bugs. The store now
   raises a domain `InvalidInput(ValueError)` and only that maps to 422.
2. `shared-runtime.yml` used `actions/checkout@v4` and `actions/setup-python@v5`
   by tag. Both are pinned to commit SHAs (`11d5960a...` = v4, `a26af69b...` = v5,
   lightweight tags resolved with `gh api .../git/ref/tags/...`), tag in a comment.
3. The `Dockerfile` copied the git-ignored `wheelhouse/`, so it could not build
   from a clone. It is now the multi-stage build under "Container image", and CI
   builds it.

RED (tests written first, run before the change; Python 3.12, PostgreSQL 16 `pgserver`):

- `pytest runtime_tests/test_error_mapping.py`: collection error, `InvalidInput`
  missing. With a temporary `InvalidInput = ValueError` alias:
  `test_unexpected_value_error_is_redacted_500` failed `assert 422 == 500`, 7 passed.
- `python3 -m unittest tests.test_build_hygiene`: 5 of 7 failed (unpinned
  `actions/checkout@v4` / `actions/setup-python@v5`; `wheelhouse` in the Dockerfile;
  one `FROM`; no core commit in the Dockerfile; no `docker build` step). The
  checker self-test and the existing non-root `USER` passed.

GREEN: `PLATFORM_TEST_DSN=... pytest -q` 89 passed, 27 subtests, no database
skips, one upstream warning; `bash scripts/check.sh` 64 unit tests OK; `ruff check .`
(0.17.3) clean. The image build is verified only by the CI `image` job (no local
Docker). Nothing was pushed to a registry or deployed.

## Staging plan (not executed) — first possible date 2026-11-01

Blocked until then: the Neon `empire-platform` free compute quota is exhausted
until 2026-11-01 and Railway deploys stop at an approval step. Each step needs
the owner's go; nothing has been deployed.

1. Database: a dedicated database for this service (no shared tables), a DDL role
   for `migrate` and a separate NOSUPERUSER NOBYPASSRLS runtime role with schema
   USAGE, `platform_schema_migrations` SELECT and `feature_flags`
   SELECT/INSERT/UPDATE/DELETE. Both connection strings go to Infisical
   `/platform-developer`.
2. Image: `docker build .` (see "Container image"; CI already builds it on every push)
   and deploy one Railway service for
   `serve` with `DATABASE_URL` (runtime role), JWT issuer `empire-platform`,
   audience and `JWT_JWKS_URL` or `JWT_PUBLIC_KEY`. Run `migrate` once with the
   DDL role. Approve the pending deployment through GraphQL.
3. Smoke test with a service token (`flags:read flags:write`): `/readyz` 200; PUT
   a `smoke.check` flag (rollout 0, one allowlisted subject); evaluate returns
   true for that subject and false for another; a stale-version PUT returns 409; a
   token for another workspace gets 404; DELETE with the current version.
4. Rollback drill: stop the service and restore a backup into a new database
   (never over the live one), then repeat the smoke reads.
5. Then add Sentry and the uptime monitor, and only after that move a first
   consumer (owner to pick) with a rollback to its current configuration.
