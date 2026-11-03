# ADR-0005 — Sentry errors only, no free text

- Status: accepted (retro-documented)
- Date of evidence: 2026-11-03 (PR #15, `6ffbb1f`)

## Context

PR #5–#14 พยายาม scrub ข้อความด้วย pattern แต่ review พบทางเลี่ยงทุกรอบ service นี้รับ credential (JWT, DB URL)

## Decision

- `init_sentry()` เป็น no-op ถ้าไม่มี `SENTRY_DSN`
- `traces_sample_rate=None`, `trace_propagation_targets=[]`, `send_default_pii=False`, `include_local_variables=False`, `max_request_body_size="never"`, logging integration ปิด
- `_scrub_event` ลบ exception value, message, logentry, breadcrumbs, extra, user, request (เหลือ method), dynamic_sampling_context
- `CaptureErrors` เป็น middleware ชั้นในสุดเพราะ core `_Boundary` กลืน exception เป็น 500

## Evidence

- `src/platform_developer/_sentry.py`, `src/platform_developer/app.py`, `src/platform_developer/__init__.py`
- `runtime_tests/test_sentry.py` (`test_no_exception_text_leaves_the_process`)
- ops record: book-platforms-status (2026-11-03)

## Consequences

- event มีแค่ type, stack, route, tags, release — debug ต้องอาศัย stack
- owner revert ได้ถ้าต้องการข้อความ (ops record)
