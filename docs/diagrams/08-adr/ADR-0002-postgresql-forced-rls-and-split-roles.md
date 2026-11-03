# ADR-0002 — PostgreSQL with forced RLS per workspace and separate DDL / runtime roles

- Status: accepted (retro-documented)
- Date of evidence: 2026-10-29 (`701ebe6`)

## Context

flag เป็นข้อมูลของแต่ละ workspace และ workspace ต้องมาจาก token เท่านั้น

## Decision

- ตาราง `feature_flags` มี `ENABLE` + `FORCE ROW LEVEL SECURITY` และ policy `workspace` เทียบ `workspace_id` กับ `current_setting('app.workspace_id')`
- core `Database.transaction(workspace)` ตั้ง `app.workspace_id` ต่อ transaction จาก `Principal.workspace` (JWT `ws`)
- `migrate` ใช้ DDL role; `serve` ใช้ runtime role ที่ต้องเป็น NOSUPERUSER NOBYPASSRLS (core `_configure` ปฏิเสธ role อื่น) และได้สิทธิ์เฉพาะ SELECT/INSERT/UPDATE/DELETE บน `feature_flags`
- ใช้ database แยกต่อ service

## Evidence

- `src/platform_developer/migrations.py`
- `src/platform_developer/store.py` (`ready` ตรวจทีละสิทธิ์ + RLS)
- core `platform_backend_core/db.py`
- `runtime_tests/test_runtime.py::test_delete_version_and_force_rls` (InsufficientPrivilege เมื่อ insert workspace อื่น)
- `docs/runtime.md` (Installation and lifecycle, Flag API)
- ops record: book-platforms-status (2026-11-03): Neon project `platform-<svc>` แยกต่อ service

## Consequences

- readiness 503 ถ้าสิทธิ์หรือ migration checksum ไม่ตรง
- ไม่มี downgrade SQL: rollback คือ restore ไป database ใหม่
