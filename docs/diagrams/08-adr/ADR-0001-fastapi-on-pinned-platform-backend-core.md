# ADR-0001 — FastAPI service built on the pinned platform-backend-core

- Status: accepted (retro-documented)
- Date of evidence: 2026-10-29 (PR #1 merged as `701ebe6`, core pin `21d5f44` in `081cafc`)

## Context

Book Platform service แต่ละตัวเป็นเจ้าของโค้ดของตัวเอง แต่ต้องมี auth, request boundary, readiness และ migration แบบเดียวกัน

## Decision

ใช้ FastAPI ผ่าน `platform_backend_core.create_app('developer', ...)` จาก `platform-backend-core` ที่ pin เป็น Git commit `21d5f44d26220080cbed43b9807979dc84a8533a` ในสามที่พร้อมกัน: `[tool.uv.sources]`, `Dockerfile` และ workflow; serve ด้วย uvicorn (`limit_concurrency=100`, `access_log=False`)

## Evidence

- `src/platform_developer/app.py` (`base_app('developer', database, verifier, max_body_bytes=32768)`)
- `src/platform_developer/__main__.py` (uvicorn.run)
- `pyproject.toml` (`platform-backend-core==0.1.0`, `[tool.uv.sources]` rev)
- `Dockerfile` (pip wheel from the same commit)
- `runtime_tests/test_build_pin.py`, `tests/test_build_hygiene.py::test_core_comes_from_the_ci_pinned_commit`

## Consequences

- อัปเกรด core ต้องแก้สามไฟล์พร้อมกัน ไม่งั้น tests fail
- package ไม่ได้อยู่บน PyPI การ pin Git commit กัน dependency confusion
- พฤติกรรม `/healthz`, `/readyz`, `/metrics`, 413/504/500 มาจาก core ไม่ได้อยู่ใน repo นี้
