# 01 — Business process (As-Is / To-Be)

Repository นี้มีสองกระบวนการที่เห็นได้จากโค้ดวันนี้:

1. **Boundary contract gate** — ทุก push/PR ต้องผ่าน `scripts/check.sh` (contract, schema pin, independence gate, unit tests) เพื่อให้ `developer` capability ย้ายออกจาก `solo-empire` ได้ภายหลังโดย consumer ไม่รู้ตัว
2. **Feature-flag runtime pilot** — workspace เก็บ feature flag ใน PostgreSQL (forced RLS) แล้ว caller ประเมิน (evaluate) flag ต่อ subject แบบ deterministic

## As-Is: contract gate (จากโค้ด)

```mermaid
flowchart LR
  A["Owner / agent edits repo"] --> B["git push or pull_request"]
  B --> C["check.yml: scripts/check.sh"]
  C --> C1["check.py: contract.json vs vendored schema"]
  C --> C2["check_schema_pin.py: schema sha256 pin"]
  C --> C3["check_independence.py: BOO-155 gate"]
  C --> C4["unittest discover tests/"]
  C1 & C2 & C3 & C4 --> D{"All green?"}
  D -- no --> A
  D -- yes --> E["Merge to main (no branch protection yet)"]
  E --> F["Registry alignment: check_registry_alignment.py (local only, read-only)"]
```

Sources: `scripts/check.sh`, `.github/workflows/check.yml`, `scripts/check_registry_alignment.py`, `docs/gates/BOO-155-template-independence.md`, `README.md`

## As-Is: feature-flag lifecycle (จากโค้ด)

```mermaid
flowchart TD
  W["Caller with flags:write"] -->|"PUT /v1/flags/{name} (no version)"| V1["Flag created, version 1"]
  V1 -->|"PUT with exact current version"| VN["Flag updated, version + 1"]
  VN -->|"PUT with exact current version"| VN
  V1 & VN -->|"DELETE ?version=N"| X["Flag removed"]
  R["Caller with flags:read"] -->|"POST /v1/flags/{name}/evaluate"| E{"enabled?"}
  E -- "missing or disabled" --> F["enabled: false"]
  E -- "subject in allowlist" --> T["enabled: true"]
  E -- "sha256 bucket < rollout" --> T
  E -- otherwise --> F
```

Sources: `src/platform_developer/app.py`, `src/platform_developer/store.py`, `docs/runtime.md` (Flag API)

## To-Be (จาก PRODUCT.md / docs/UPGRADE-PLAN.md / docs/runtime.md เท่านั้น)

```mermaid
flowchart LR
  P0["P0: check.yml as reusable workflow_call for every platform repo"] --> P1["P1: schema from backend-core package or reusable workflow"]
  P1 --> P2["P1: solo-empire guard compares capabilities, depends_on, source_paths"]
  S1["Staging plan 1-4: DB roles, image, smoke test, rollback drill"] --> S5["Staging plan 5: Sentry + uptime, then first consumer (owner picks)"]
  S5 --> CUT["Cutover from solo-empire after parity + rollback evidence"]
```

Sources: `docs/UPGRADE-PLAN.md` (Backlog P0/P1/P2), `docs/runtime.md` (Staging plan), `PRODUCT.md` (Measures, Capabilities and Constraints)

## Open questions

- PRODUCT.md ระบุ "[ต้องยืนยัน] The cutover criteria for activating the runtime" — ยังไม่มีเกณฑ์ cutover
- consumer แรกของ flag API คือใคร (runtime.md step 5: "owner to pick")
- ยังไม่มี issue หรือ spec ที่กำหนด To-Be ของ feature-flag เกิน PR #1 (targeting rules, audit history, SDK caching ถูกระบุว่า "not done")
