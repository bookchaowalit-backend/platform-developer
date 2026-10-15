# BOO-155 gate evidence: templates and boundary checks independent of product source

## Next gate (verbatim)

> Keep repository templates and boundary checks independent from product source code.

Source: `solo-empire` `repository-catalog/registries/system-repositories.yaml:678`
(`developer-platform` entry, lines 655-678; `source_paths: [.github, infra/tasks, repository-catalog]`).

## Contract answered

`bookchaowalit/architecture-docs` `systems/architecture/repository-boundaries.md`:

- `#core-rule` (lines 16-24): each repository must be understood, tested and
  deployed on its own, with its own `.git`, dependencies and tests.
- `#current-migration-direction` (lines 127-144): product checks move into the
  owning repository; parent checks keep only consumer-contract coverage;
  `--require-checkouts` is a local-only mode and parent CI must work without the
  ignored product checkouts.
- `#scaling-rules` (lines 224-226): shared code is cross-domain only; a domain
  adapter, schema or rule belongs in its domain repository.

Applied to this repository the gate means: the templates and boundary checks in
`platform-developer` must import nothing from a product repository, must not
hard-code where any product source lives, and must pass from a clean checkout
that has no sibling repositories.

## What enforces it

`scripts/check_independence.py` (run by `scripts/check.sh`, so by CI):

| Rule | How it is checked |
|---|---|
| Imports | AST of every `.py` in scope; every import root must be in `sys.stdlib_module_names` or be a module in `scripts/` / `tests/`; any `sys.path` use fails. |
| Product source paths | Every line in scope is matched against: Book Dev clone folder, sibling traversal, absolute home path, solo-empire control-plane source trees (`infra/scripts`, `infra/tasks`, ...), solo-empire checkout path. Negative-test input may carry `# independence: allow` in `tests/` only; those lines are pinned in the fixture. |
| Runtime reads | Each default-gate script from `scripts/check.sh` (`check.py`, `check_schema_pin.py`) runs in `python3 -I` under `sys.addaudithook`; any `open` outside the repository root or Python installation, any process start and any socket connection fails. `BOOK_BACKEND_CORE_DIR` is dropped. |
| Clean checkout | `tests/test_independence.py::CleanCheckoutTests` copies the repository alone into an empty directory, with an empty `HOME`, and runs the full `bash scripts/check.sh` there. |

Scope (`SCOPE_GLOBS`): `scripts/*.py`, `scripts/*.sh`, `tests/*.py`,
`.github/workflows/*.yml`. The machine-readable mapping is
[`fixtures/gates/template-independence.json`](../../fixtures/gates/template-independence.json);
`GateFixtureTests` fail when the file list, default gate, CI flags, allowed
lines or rule labels drift from the code.

## Inventory: platform-developer (origin/main `44a9a3c` + this change)

| File | Role | In CI | External input |
|---|---|---|---|
| `.github/workflows/check.yml` | CI template | yes | none (`actions/checkout` of this repo only, check.yml:26-37) |
| `scripts/check.sh` | CI entrypoint | yes | none (cds to its own root, check.sh:3-4) |
| `scripts/check.py` | boundary check | yes | none (`ROOT` from `__file__`, check.py:28) |
| `scripts/check_schema_pin.py` | boundary check | yes | optional `--canonical` / `BOOK_BACKEND_CORE_DIR` (platform core schema, check_schema_pin.py:99-103); not used by the default gate |
| `scripts/check_registry_alignment.py` | boundary check | no | explicit `--solo-empire PATH`, reads the registry file only (check_registry_alignment.py:25,106-111) |
| `scripts/check_independence.py` | boundary check | yes | none |
| `tests/test_contract_check.py`, `tests/test_drift_checks.py`, `tests/test_independence.py` | tests | yes | temp copies only |

Result: all 9 files pass; the default gate opens nothing outside the repository.

## Inventory: solo-empire (read-only, `63efeeb`)

`product_source` = the item reads or stats files inside product/platform
checkouts (Book Dev clone folder) or the knowledge-base checkout.

| Path | Kind | Present | Product source | Evidence |
|---|---|---|---|---|
| `.github/workflows/*` | CI template | no | - | removed in `5f034945` ("CI workflows and dependabot dropped") |
| `.github/dependabot.yml` | config | no | - | removed in `5f034945` |
| `infra/tasks/*.yml` | task adapters | no | unknown | removed in `5f034945`, moved to `bookchaowalit/solo-ops` (not inspected) |
| `.github/ISSUE_TEMPLATE/*.yml` | repo template | yes | no | no path references |
| `.github/agents/*` | agent config | yes | no | `roles.yaml` has no product paths |
| `.github/hooks/solo-empire-lifecycle.json` | hook config | yes | no (control plane) | :7 runs `infra/scripts/agent/copilot_hooks.py` |
| `.github/hooks/impeccable.json` | hook config | yes | no | :8 runs an untracked `.github/skills` script if present |
| `infra/scripts/utils/registry_check.py` | check runner | yes | **yes** (transitive) | :23-33 runs all guards below |
| `infra/scripts/utils/book_dev_structure_guard.py` | boundary check | yes | **yes** | :21,103 walks the clone folder |
| `infra/scripts/utils/module_boundary_guard.py` | boundary check | yes | **yes** | :25-27,168-176,181-190 knowledge-base checkout, product entrypoints |
| `infra/scripts/utils/system_repository_guard.py` | boundary check | yes | **yes** | :28-30,152-155 stats product checkout paths |
| `infra/scripts/utils/platform_repository_guard.py` | boundary check | yes | **yes** | :242-245,329-335 reads each platform checkout's `contract.json` |
| `infra/scripts/utils/repo_roadmap_guard.py` | boundary check | yes | **yes** | :87-90 resolves documents in sibling checkouts |
| `infra/scripts/platform/systems_status.py` | boundary check | yes | **yes** | :81-83 stats system source paths |
| `infra/scripts/utils/_env.py`, `sibling_paths.py` | path helpers | yes | **yes** | `_env.py`:26,128-133; `sibling_paths.py`:6,10 |
| `infra/scripts/utils/repo_roadmap_seed.py` | boundary check | yes | no | :46,276 prefix match on registry data only |
| `infra/scripts/utils/repository_catalog_guard.py` | boundary check | yes | no | :173 hub `git ls-files` only |
| `infra/scripts/utils/workspace_boundary_guard.py` | boundary check | yes | no | hub manifests and `first-party.yaml` |
| `repository-catalog/registries/*.yaml` | registry data | yes | no | data only |

Most solo-empire guards degrade to warnings when checkouts are missing
(`--require-checkouts` makes them errors), so they run in a clone without
siblings, but their full verdict still depends on product checkouts.

## Gaps

1. `contract.json` still names `.github` and `infra/tasks` as the current
   implementation, with interface sources `.github/workflows/ci.yml`,
   `.github/workflows/platform-validate.yml` and `.github/dependabot.yml`. None
   exist in solo-empire `63efeeb`
   (`check_registry_alignment.py --solo-empire` warns on all four). The
   registry (`platforms.yaml:196`) has the same stale `source_paths`. Not
   changed here: it needs a registry change first.
2. `infra/tasks` moved to `bookchaowalit/solo-ops`; its independence is not
   inspected or checked here.
3. Nine solo-empire boundary-check items still read product/platform checkouts
   (table above). They are hub registry guards, not templates in this
   repository; moving or splitting them is an owner decision.
4. The `developer.workflow.platform-check` interface (reusable check) is still
   copied into each platform repository; it is not a `workflow_call` yet
   (UPGRADE-PLAN P0).
5. Open PR #1 (`codex/shared-infrastructure-20261015`) adds
   `.github/workflows/shared-runtime.yml`, which enters this check's scope. A
   static run against that branch passes except the two negative-test lines this
   change marks. `src/` and `runtime_tests/` from that PR are runtime code and
   outside this gate's scope.

## Owner decision — PROPOSED, NOT ACCEPTED

The owner is asked to accept:

1. `scripts/check_independence.py` in `scripts/check.sh` is the gate check for
   "templates and boundary checks independent from product source" in
   `platform-developer`; a failure blocks merge.
2. Boundary checks owned by `platform-developer` may read another checkout only
   through an explicit argument, never by default and never in CI.
3. The solo-empire guards that read product checkouts stay in the hub as
   registry guards (not developer-platform templates) and are not migrated here;
   the `developer-platform` `source_paths` in `platforms.yaml` and
   `system-repositories.yaml` are updated to the surviving paths
   (`.github/ISSUE_TEMPLATE`, `.github/agents`, `.github/hooks`) in a separate
   registry change, after which `contract.json` follows.

Nothing here claims an accepted decision, a status change, a runtime move or a
production cutover.

## Local verification

```bash
bash scripts/check.sh
python3 scripts/check_independence.py --static-only   # skip the runtime trace
```
