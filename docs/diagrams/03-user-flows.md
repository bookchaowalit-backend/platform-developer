# 03 — User flows (API call flows per caller)

Service นี้ไม่มีหน้าเว็บ "user flow" จึงเป็นลำดับการเรียก API ของแต่ละ caller

## Writer (flags:write): create → update → delete

```mermaid
flowchart TD
  S["Bearer token, scope flags:write, ws = workspace"] --> P1["PUT /v1/flags/pilot body enabled, rollout, subjects (no version)"]
  P1 -->|"200 row version 1"| P2["PUT /v1/flags/pilot with version 1"]
  P1 -->|"409 Version conflict (name exists)"| G["GET /v1/flags/pilot to read current version (needs flags:read)"]
  G --> P2
  P2 -->|"200 version 2"| D["DELETE /v1/flags/pilot?version=2"]
  P2 -->|"409 stale version"| G
  D -->|"204"| END["Done"]
  D -->|"409 wrong version"| G
  P1 -->|"422 Invalid input (name, rollout, subjects)"| FIX["Fix request"]
```

## Reader (flags:read): list and evaluate

```mermaid
flowchart TD
  R["Bearer token, scope flags:read"] --> L["GET /v1/flags?limit=1..100&after=lastName"]
  L -->|"200 page sorted by name"| MORE{"page full?"}
  MORE -- yes --> L
  MORE -- no --> EV["POST /v1/flags/{name}/evaluate body subject"]
  EV -->|"200 enabled true/false"| USE["Caller gates its feature"]
  R --> ONE["GET /v1/flags/{name}"]
  ONE -->|"404 missing or other workspace"| NF["Treat as absent"]
```

## Error branches common to every call

```mermaid
flowchart LR
  REQ["Request"] --> B{"Body > 32768 bytes?"}
  B -- yes --> E413["413 request too large"]
  B -- no --> A{"Token valid?"}
  A -- no --> E401["401 unauthorized"]
  A -- yes --> SC{"Scope present?"}
  SC -- no --> E403["403 forbidden"]
  SC -- yes --> H["Handler"]
  H -->|"over 30 s"| E504["504 request timeout"]
  H -->|"unexpected exception"| E500["500 internal server error (redacted)"]
```

Sources: `src/platform_developer/app.py`, `src/platform_developer/store.py`, core `platform_backend_core/http.py` (`_Boundary`, `require_scope`), `runtime_tests/test_http.py`, `runtime_tests/test_error_mapping.py`, `docs/runtime.md`

หมายเหตุ: evaluate ของ flag ที่ไม่มีอยู่คืน `{"enabled": false}` (200) ไม่ใช่ 404 — `store.evaluate` คืน False เมื่อ row เป็น None

## Open questions

- ยังไม่พบ consumer จริงที่เรียก evaluate ในงาน production (ดู 01 To-Be)
