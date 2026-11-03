# 14 — Backup and DR

## ข้อมูลที่มี

| Data | Where | Persisted? | Source |
|---|---|---|---|
| `feature_flags` rows (per workspace) | Neon project `platform-developer` | yes | `src/platform_developer/migrations.py`, ops record |
| `platform_schema_migrations` | same database | yes | core `migrations.py` |
| HTTP metrics counters | process memory | no, reset on restart/sleep | core `http.py` |
| Secrets (DATABASE_URL, JWT config, SENTRY_DSN) | Infisical `/platform-developer` + Railway variables | managed outside repo | ops record |

## Backup / restore reality

```mermaid
flowchart TD
  DB[("Neon platform-developer: feature_flags")] -.->|"not confirmed for this service"| BK["Central logical backup ops-backups/db-backup to R2 (architecture ADR-0002)"]
  DB -.->|"provider feature, window not recorded"| PITR["Neon restore / branch"]
  RB["Rollback (runtime.md)"] --> S1["Stop the runtime, restore consumers to previous adapter"]
  S1 --> S2["Never downgrade applied SQL or overwrite live DB"]
  S2 --> S3["Restore into a new isolated database"]
  S3 --> S4["Verify synthetic workspace reads, then cut over"]
```

Sources: `docs/runtime.md` (Verification and release gate, Staging plan step 4), [architecture-docs ADR-0002 production baseline](https://github.com/bookchaowalit/architecture-docs/blob/main/docs/architecture/decisions/ADR-0002-production-baseline-monitoring-backups.md), ops record: book-platforms-status (2026-11-03)

- ใน repo ไม่มี backup workflow หรือ script: `docs/runtime.md` บอกว่า "Runtime role and backup/restore provisioning remain operator release work" และ "no scheduled deletion or backup credential access is implemented here"
- Staging plan step 4 (rollback drill: restore backup ไป database ใหม่) — ไม่พบบันทึกว่าทำแล้ว
- **RTO: not defined. RPO: not defined.**

## Open questions

- Neon `platform-developer` อยู่ใน target list ของ `ops-backups/db-backup` และมี `db_backup` role แล้วหรือยัง
- เคยทำ restore drill ของ developer หรือไม่
- Neon free plan restore window ของ project นี้
- กำหนด RTO/RPO (flag data เล็ก แต่ถ้า consumer พึ่ง evaluate การหายของ row = flag off)
