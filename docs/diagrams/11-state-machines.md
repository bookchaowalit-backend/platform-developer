# 11 — State machines

`feature_flags` ไม่มีคอลัมน์ status แต่มี lifecycle ผ่าน `version` (optimistic concurrency) และ `enabled` / `rollout`

## Flag row lifecycle (version)

```mermaid
stateDiagram-v2
  [*] --> Absent
  Absent --> V1: PUT without version (INSERT ON CONFLICT DO NOTHING)
  Absent --> Absent: PUT with version / DELETE gives 409
  V1 --> VN: PUT with version = current (version + 1)
  VN --> VN: PUT with version = current
  V1 --> V1: PUT stale version or PUT without version gives 409
  VN --> VN: PUT stale version gives 409
  V1 --> Absent: DELETE ?version=current (204)
  VN --> Absent: DELETE ?version=current (204)
```

## Evaluation outcome per subject

```mermaid
stateDiagram-v2
  [*] --> Lookup
  Lookup --> Off: row missing
  Lookup --> Off: enabled false
  Lookup --> Allowlist: enabled true
  Allowlist --> On: subject in subjects
  Allowlist --> Bucket: not listed
  Bucket --> On: bucket < rollout
  Bucket --> Off: bucket >= rollout
  On --> [*]
  Off --> [*]
```

## Service readiness

```mermaid
stateDiagram-v2
  [*] --> Unavailable
  Unavailable --> Ready: DB reachable, migrations 0001 checksum match, RLS forced, every grant present
  Ready --> Unavailable: grant revoked, history changed, DB unreachable
```

Sources: `src/platform_developer/store.py` (`put`, `delete`, `evaluate`, `ready`), `src/platform_developer/migrations.py`, `runtime_tests/test_runtime.py`, `runtime_tests/test_http.py`, `docs/runtime.md`
