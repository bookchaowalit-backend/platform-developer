# 02 — Use cases

Actors คือสิทธิ์ที่ service ตรวจจริง ไม่ใช่หน้า UI: token RS256 ที่ `TokenVerifier` ยอมรับ (issuer + audience จาก env, ต้องมี `sub`, `ws`, `iat`, `exp`, `jti`) และ scope ใน claim `scope` ที่ `require_scope` ตรวจ (`flags:read`, `flags:write`) โดย workspace มาจาก `ws` เท่านั้น ส่วน probe endpoints ไม่ต้องใช้ token

```mermaid
flowchart LR
  subgraph Actors
    RD["Token with flags:read"]
    WR["Token with flags:write"]
    HUB["MCP hub service client (ops record)"]
    PROBE["Unauthenticated probe (Railway healthcheck, uptime worker)"]
    OPS["Operator with DDL-role DATABASE_URL"]
    DEV["Contributor / CI"]
  end
  subgraph "developer-api"
    UC1(["List flags"])
    UC2(["Get one flag"])
    UC3(["Evaluate flag for subject"])
    UC4(["Create flag"])
    UC5(["Update flag with version"])
    UC6(["Delete flag with version"])
    UC7(["healthz / readyz / metrics"])
    UC8(["migrate schema"])
  end
  subgraph "Repository gate"
    UC9(["Run scripts/check.sh"])
    UC10(["Registry alignment check (local)"])
  end
  RD --> UC1 & UC2 & UC3
  WR --> UC4 & UC5 & UC6
  HUB --> UC1 & UC2 & UC3
  PROBE --> UC7
  OPS --> UC8
  DEV --> UC9 & UC10
```

Sources: `src/platform_developer/app.py`, `src/platform_developer/__main__.py`, `scripts/check.sh`, `scripts/check_registry_alignment.py`, core `platform_backend_core/auth.py` + `http.py` (pinned commit `21d5f44`, see `pyproject.toml`), ops record: book-platforms-status (2026-11-03)

หมายเหตุ: token ที่มีทั้งสอง scope (`flags:read flags:write`) ทำได้ทุก use case ของ API — tests ใช้แบบนั้น (`runtime_tests/test_http.py`). Token ที่มี claim `del` หรือ `obo` (delegation) ถูกปฏิเสธเสมอ

## Open questions

- MCP hub ถือ scope ใดของ developer (`flags:read` อย่างเดียว หรือ `flags:write` ด้วย) — ops record บอกเพียงว่า call_cell developer ได้ 200
- person token (Google login ผ่าน identity) ยังเปิดไม่ได้จนกว่า owner ตั้ง `IDENTITY_GOOGLE_CLIENT_IDS` (ops record) — ยังไม่มี person caller จริง
- ไม่มี role "owner" แยกในโค้ด service นี้: สิทธิ์ทั้งหมดคือ scope ต่อ workspace
