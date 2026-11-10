# 21 — Incident response

ช่องทาง alert ที่พบ: (1) platform-uptime-worker ตรวจ `/readyz` รายชั่วโมงและแจ้ง Telegram (ADR-0002 กลาง + ops record), (2) Sentry project `platform-developer` (ops record), (3) Railway restart อัตโนมัติ `ON_FAILURE` สูงสุด 3 ครั้ง (`.railway/railway.ts`) ไม่มี runbook เฉพาะ service ใน repo — ขั้น rollback มาจาก `docs/runtime.md`

```mermaid
flowchart TD
  A1["Uptime worker: /readyz not 200"] --> TG["Telegram alert to owner"]
  A2["Sentry unhandled error event"] --> SN["Sentry issue (alert routing unknown)"]
  A3["Process crash"] --> RR["Railway restart ON_FAILURE, max 3"]
  RR -->|"still failing"| A1
  TG & SN --> TR["Triage by owner / agent"]
  TR --> Q1{"readyz 503?"}
  Q1 -- yes --> C1["Check Neon quota / suspended compute, runtime role grants, migration history"]
  Q1 -- no --> C2["Read Sentry type + stack + route (no message text)"]
  C1 & C2 --> FIX{"Code fix or config?"}
  FIX -- code --> PR["Branch, PR, CI green, local merge"] --> DEP["railway up --ci from git archive main"]
  FIX -- config --> VAR["Railway variables from Infisical /platform-developer, redeploy"]
  DEP & VAR --> VER["Verify /readyz 200"]
  FIX -- "bad release" --> RB["Rollback: stop runtime, restore consumers; never downgrade SQL; restore DB only into a new database"]
  VER --> PM["Postmortem: not defined in repo"]
  RB --> PM
```

Sources: `.railway/railway.ts`, `docs/runtime.md` (Verification and release gate, rollback), `src/platform_developer/_sentry.py`, `src/platform_developer/store.py` (`ready`), [architecture-docs ADR-0002](https://github.com/bookchaowalit/architecture-docs/blob/main/docs/architecture/decisions/ADR-0002-production-baseline-monitoring-backups.md), ops record: book-platforms-status (2026-11-03) (uptime target, Sentry project, deploy recipe, Neon quota note)

## Open questions

- Sentry alert ไปที่ช่องทางใด (email / Telegram)
- มี postmortem template หรือที่เก็บ incident record สำหรับ platform services หรือไม่
- ไม่มี on-call / severity definition ใน repo
