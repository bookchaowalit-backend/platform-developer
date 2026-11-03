# Core 22 SDLC diagram pack — platform-developer

ชุด diagram 22 รายการตาม SDLC Diagram Catalog v2 (knowledge-base `knowledge/tech/core-cs/sdlc-diagram-catalog.md`) วาดจากโค้ดและ config จริงของ repo นี้ (main `ed1b6d3`) ทุกไฟล์มี `Sources:` ใต้ diagram และ "Open questions" สำหรับสิ่งที่ยืนยันไม่ได้

ข้อเท็จจริงด้าน hosting ที่ไม่อยู่ใน repo อ้างจาก `ops record: book-platforms-status (2026-11-03)` เฉพาะบรรทัดที่ระบุ developer; core `platform_backend_core` อ่านจาก commit ที่ pin ไว้ `21d5f44` (`pyproject.toml`)

| # | Item | Status | File | Sources read |
|---|---|---|---|---|
| 01 | Business process (As-Is / To-Be) | done | [01-business-process.md](01-business-process.md) | `scripts/check.sh`, `check.yml`, `app.py`, `store.py`, `PRODUCT.md`, `docs/UPGRADE-PLAN.md`, `docs/runtime.md` |
| 02 | Use cases | done | [02-use-cases.md](02-use-cases.md) | `app.py`, `__main__.py`, core `auth.py`/`http.py`, ops record |
| 03 | User flows (API call flows) | done | [03-user-flows.md](03-user-flows.md) | `app.py`, `store.py`, core `http.py`, `runtime_tests/test_http.py` |
| 04 | Traceability (RTM) | done | [04-traceability.md](04-traceability.md) | `PRODUCT.md`, `docs/runtime.md`, BOO-155 gate, tests, workflows |
| 05 | C4 Context | done | [05-c4-context.md](05-c4-context.md) | `src/`, workflows, `contract.json`, ops record |
| 06 | C4 Container | done | [06-c4-container.md](06-c4-container.md) | `Dockerfile`, `railway.toml`, `__main__.py`, core `db.py`/`auth.py` |
| 07 | C4 Component | done | [07-c4-component.md](07-c4-component.md) | `src/platform_developer/*.py`, core `http.py`/`auth.py`/`db.py` |
| 08 | ADRs (5, retro-documented) | done | [08-adr/](08-adr/) | see each ADR's Evidence |
| 09 | ERD | done | [09-erd.md](09-erd.md) | `migrations.py`, `store.py`, core `migrations.py`/`db.py` |
| 10 | Sequences | done | [10-sequences.md](10-sequences.md) | `app.py`, `store.py`, `_sentry.py`, core `http.py`/`auth.py` |
| 11 | State machines | done | [11-state-machines.md](11-state-machines.md) | `store.py`, `migrations.py`, runtime tests |
| 12 | API and integrations | done (reuses [docs/runtime.md](../runtime.md), [docs/CONTRACT-SURFACE.md](../CONTRACT-SURFACE.md)) | [12-api-integration.md](12-api-integration.md) | `app.py`, `store.py`, core `http.py`/`auth.py`, `pyproject.toml` |
| 13 | Threat model | done | [13-threat-model.md](13-threat-model.md) | `src/`, core, `Dockerfile`, workflows, BOO-155 gate |
| 14 | Backup and DR | done (gaps marked) | [14-backup-dr.md](14-backup-dr.md) | `docs/runtime.md`, central ADR-0002, ops record |
| 15 | CI/CD pipeline | done | [15-cicd-pipeline.md](15-cicd-pipeline.md) | `.github/workflows/check.yml`, `shared-runtime.yml`, `scripts/check.sh` |
| 16 | Deployment | done | [16-deployment.md](16-deployment.md) | `railway.toml`, `Dockerfile`, `__main__.py`, `_sentry.py`, ops record |
| 17 | Test coverage matrix | done | [17-test-coverage-matrix.md](17-test-coverage-matrix.md) | `tests/`, `runtime_tests/`, `pyproject.toml`, `check.yml` |
| 18 | Git and release workflow | done | [18-git-release-workflow.md](18-git-release-workflow.md) | `git log`, `gh pr list`, workflows, ops record |
| 19 | Service dependency map | done | [19-service-dependency-map.md](19-service-dependency-map.md) | `pyproject.toml`, `Dockerfile`, `src/`, core, `contract.json`, ops record |
| 20 | Observability | done | [20-observability.md](20-observability.md) | core `http.py`, `_sentry.py`, `railway.toml`, central ADR-0002, ops record |
| 21 | Incident response | done | [21-incident-response.md](21-incident-response.md) | `railway.toml`, `docs/runtime.md`, `_sentry.py`, central ADR-0002, ops record |
| 22 | DORA metrics | done (proxies; deploy-based values not computable) | [22-dora.md](22-dora.md) | `git log`, `gh pr list`, `gh run list`, ops record |

## Existing docs reused (not copied)

- [docs/runtime.md](../runtime.md) — API, lifecycle, staging plan, verification records
- [docs/CONTRACT-SURFACE.md](../CONTRACT-SURFACE.md) — legacy boundary interfaces
- [docs/gates/BOO-155-template-independence.md](../gates/BOO-155-template-independence.md) — independence gate
- [docs/UPGRADE-PLAN.md](../UPGRADE-PLAN.md) — backlog (To-Be)
- Central: [C4-DIAGRAMS.md](https://github.com/bookchaowalit/architecture-docs/blob/main/docs/architecture/C4-DIAGRAMS.md), [ERD-DIAGRAMS.md](https://github.com/bookchaowalit/architecture-docs/blob/main/docs/architecture/ERD-DIAGRAMS.md), [ATTACK-PATH-DIAGRAMS.md](https://github.com/bookchaowalit/architecture-docs/blob/main/docs/architecture/ATTACK-PATH-DIAGRAMS.md), [ADR-0002](https://github.com/bookchaowalit/architecture-docs/blob/main/docs/architecture/decisions/ADR-0002-production-baseline-monitoring-backups.md) — ไม่มีส่วนเฉพาะ developer

## Validate

```bash
node ~/work/core22/tools/validate.mjs docs/diagrams/*.md docs/diagrams/08-adr/*.md
```
