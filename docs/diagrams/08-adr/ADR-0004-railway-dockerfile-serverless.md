# ADR-0004 — Railway Dockerfile deploy, serverless sleep, /readyz healthcheck

- Status: accepted (retro-documented)

## Decision

- `.railway/railway.ts`: builder `DOCKERFILE`, `healthcheckPath = "/readyz"`, timeout 30, restart `ON_FAILURE` สูงสุด 3 ครั้ง
- image สองขั้น (`python:3.12-slim`), runtime ไม่มี git/build tools, รันเป็น UID 65532
- deploy ด้วย CLI `railway up --ci` จาก `git archive main` ไม่ใช่ GitHub-connected deploy

## Evidence

- `.railway/railway.ts`, `Dockerfile`, `.dockerignore`, `tests/test_build_hygiene.py`
- `.github/workflows/shared-runtime.yml` (build only, never pushes)
- ops record: book-platforms-status (2026-11-03): `developer-api-production-2fad`, region `asia-southeast1-eqsg3a`, sleep on, developer main `6ffbb1f` CLI-deployed

## Consequences

- cold start หลัง sleep + Neon resume (core pool wait 20 s, connect timeout 15 s)
- git/gh ไม่มีบันทึก deploy (ดู 22-dora)
- `docs/runtime.md` และ `README.md` ยังเขียนว่า "not deployed" — doc drift
