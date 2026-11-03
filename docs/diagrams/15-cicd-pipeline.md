# 15 — CI/CD pipeline

สอง workflow ทั้งคู่ trigger `push` (ทุก branch), `pull_request`, `workflow_dispatch`; `permissions: contents: read`; concurrency cancel-in-progress ต่อ ref ไม่มี job ใด deploy

```mermaid
flowchart LR
  T["push / pull_request / workflow_dispatch"] --> CK["check.yml (Check)"]
  T --> SR["shared-runtime.yml (Shared runtime)"]
  subgraph CK1["Check"]
    C1["contract: matrix Python 3.11, 3.12 via ci-python.yml v1.1.1 (87dc5e1), test-command bash scripts/check.sh"]
    C2["python: ci-python.yml v1.1.1, Python 3.12, postgres true, uv locked env, Ruff, mypy, pytest with coverage >= 90, uv build --wheel"]
    C3["security: security.yml v1.1.1"]
  end
  subgraph SR1["Shared runtime"]
    I1["image: checkout (SHA-pinned v4)"] --> I2["docker build --pull --tag platform-developer:ci"]
    I2 --> I3["docker run: import platform_backend_core, platform_developer.app; id -u != 0"]
  end
  CK --> C1 & C2 & C3
  SR --> I1
  C1 & C2 & C3 & I3 --> G{"all green"}
  G --> M["merge to main (local merge, no required checks)"]
  M -.->|"manual, outside CI"| D["railway up --ci from git archive main"]
```

Sources: `.github/workflows/check.yml`, `.github/workflows/shared-runtime.yml`, `scripts/check.sh`, `pyproject.toml` (`[tool.mypy]`, `[tool.coverage.run]`), `docs/gates/BOO-155-template-independence.md` (no branch protection), ops record: book-platforms-status (2026-11-03) deploy recipe

ไม่มี `needs:` ระหว่าง job — ทุก job รันขนานกัน รายละเอียด step ภายใน `ci-python.yml` / `security.yml` อยู่ใน repo `bookchaowalit/platform-ci-workflows` (ไม่ได้อ่านใน pack นี้) ข้อความ "uv locked env, Ruff, mypy" มาจาก comment ใน `check.yml`

## Open questions

- ขั้นตอนที่แน่นอนของ reusable `security.yml` (gitleaks ถูกกล่าวถึงใน `docs/runtime.md`)
- ทำไม Railway ไม่ได้ต่อกับ GitHub (push=deploy) สำหรับ service นี้
