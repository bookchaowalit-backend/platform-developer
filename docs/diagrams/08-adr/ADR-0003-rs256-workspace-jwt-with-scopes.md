# ADR-0003 — RS256 workspace JWT with per-route scopes

- Status: accepted (retro-documented)

## Context

caller หลายแบบ (service client, person token ในอนาคต) ต้องเข้าถึง flag ของ workspace ตัวเองเท่านั้น

## Decision

- `TokenVerifier(issuer=JWT_ISSUER, audience=JWT_AUDIENCE, public_key=JWT_PUBLIC_KEY | jwks_url=JWT_JWKS_URL)` — ตั้งได้อย่างเดียวจาก env
- RS256 เท่านั้น, ต้องมี `sub`, `ws`, `iat`, `exp`, `jti`, `iss`, `aud`; อายุ token ≤ 3600 s; claim `del`/`obo` ถูกปฏิเสธ
- route อ่านต้องมี `flags:read`, route เขียนต้องมี `flags:write`

## Evidence

- `src/platform_developer/__main__.py`, `src/platform_developer/app.py`
- core `platform_backend_core/auth.py`, `http.py` (`require_scope`)
- `runtime_tests/test_http.py` (401 ไม่มี token, 403 ไม่มี scope)
- ops record: book-platforms-status (2026-11-03): services trust the platform-identity issuer since 2026-10-29

## Consequences

- JWKS ถูก refresh ได้ไม่เกินหนึ่งครั้งต่อ 60 s; ถ้า refresh ล้มเหลว cache ว่างจนรอบถัดไป (fail closed)
- ไม่มี revocation ใน service นี้ (core comment: "Shared services cannot enforce delegation status or revocation")
