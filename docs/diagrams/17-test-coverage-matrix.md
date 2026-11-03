# 17 — Test coverage matrix

ระดับ test ในรีโปนี้:
- **unit** = `tests/` (unittest, stdlib only, รันใน `scripts/check.sh`) และ pytest ใน `runtime_tests/` ที่ไม่ต้องใช้ DB
- **integration** = `runtime_tests/` ที่ต้องมี `PLATFORM_TEST_DSN` (PostgreSQL จริง, role NOSUPERUSER NOBYPASSRLS, JWT signature จริง, HTTP ผ่าน TestClient); skip ถ้าไม่มี DSN
- **e2e** = ไม่มี (ไม่มี test ที่เรียก service ที่ deploy แล้ว)

| Feature | Unit | Integration | E2E | Files |
|---|---|---|---|---|
| Contract schema validation | yes | — | — | `tests/test_contract_check.py` |
| Schema pin drift | yes | — | — | `tests/test_drift_checks.py` |
| Registry alignment | yes | — | — | `tests/test_drift_checks.py` |
| BOO-155 independence + clean checkout | yes | — | — | `tests/test_independence.py` |
| Dockerfile / workflow pin hygiene | yes | — | — (CI `image` job builds) | `tests/test_build_hygiene.py` |
| Core commit pin | yes | — | — | `runtime_tests/test_build_pin.py` |
| Flag create / update / version conflict | — | yes | **gap** | `runtime_tests/test_runtime.py`, `test_http.py` |
| Concurrent update single winner | — | yes | — | `runtime_tests/test_runtime.py` |
| Delete with version | — | yes | **gap** | `runtime_tests/test_runtime.py` |
| Rollout bucket + allowlist determinism | — | yes | **gap** | `runtime_tests/test_runtime.py` |
| Workspace isolation / FORCE RLS | — | yes | **gap** | `test_runtime.py`, `test_http.py`, `test_pool_reuse.py` |
| 401 / 403 scope auth | — | yes | **gap** | `runtime_tests/test_http.py` |
| JWKS fetch path | **gap** (tests use `JWT_PUBLIC_KEY` style `public_key`) | **gap** | **gap** | — |
| Input validation 422 vs redacted 500 | yes (`_NoDatabase` stub) | — | — | `runtime_tests/test_error_mapping.py` |
| Readiness: migrations checksum, each grant, missing schema | — | yes | **gap** | `runtime_tests/test_http.py` |
| `migrate` CLI then ready | — | yes (subprocess) | — | `runtime_tests/test_http.py` |
| Pool reuse after conflict / rollback | — | yes | — | `runtime_tests/test_pool_reuse.py` |
| Sentry init, scrubbing, no free text (51 cases), CaptureErrors | yes (real client, local transport) | — | **gap** (no check against live Sentry) | `runtime_tests/test_sentry.py` |
| 413 body limit / 504 timeout | **gap** in this repo (core behaviour) | **gap** | — | — |
| `/metrics` output | **gap** | **gap** | — | — |

Coverage gate: `check.yml` job `python` `coverage-threshold: "90"` (comment: measured 90.71% on 2026-11-03) over `src/platform_developer` and `scripts`

Sources: `tests/*.py`, `runtime_tests/*.py`, `scripts/check.sh`, `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.run]`), `.github/workflows/check.yml`, ops record: book-platforms-status (2026-11-03) (51-case test)

## Open questions

- smoke test หลัง deploy (staging plan step 3) เคยรันและบันทึกผลหรือไม่
