# 19 — Service dependency map

```mermaid
flowchart LR
  subgraph Callers
    HUB["Remote MCP hub cell platform-developer"]
    UPT["platform-uptime-worker"]
    RWH["Railway healthcheck"]
  end
  API["developer-api"]
  subgraph Runtime["Runtime dependencies"]
    NEON[("Neon PostgreSQL platform-developer")]
    IDP["platform-identity JWKS"]
    SEN["Sentry"]
  end
  subgraph Build["Build-time dependencies"]
    CORE["GitHub bookchaowalit-backend/platform-backend-core @ 21d5f44"]
    PYPI["PyPI: uvicorn, sentry-sdk, httpx, transitive"]
    BASE["Docker Hub python:3.12-slim"]
    CIW["GitHub bookchaowalit/platform-ci-workflows @ 87dc5e1 (v1.1.1)"]
  end
  HUB --> API
  UPT --> API
  RWH --> API
  API -->|"required for readyz"| NEON
  API -->|"required for auth when JWKS configured"| IDP
  API -->|"optional, SENTRY_DSN"| SEN
  CORE --> API
  PYPI --> API
  BASE --> API
  CIW -.->|"CI only"| API
```

| Dependency | Failure effect | Evidence |
|---|---|---|
| Neon | `/readyz` 503; API calls 500 (redacted) | core `db.py`, `http.py` |
| identity JWKS | token verification fails → 401 (fail closed) | core `auth.py` |
| Sentry | none on requests (SDK async) | `_sentry.py` |
| contract deps `security`, `observability` | declared in `contract.json` `depends_on`; no runtime call in code | `contract.json`, `src/` |

Sources: `pyproject.toml`, `Dockerfile`, `.github/workflows/check.yml`, `src/platform_developer/*.py`, core `platform_backend_core/*.py`, `contract.json`, ops record: book-platforms-status (2026-11-03) for MCP hub, uptime worker, Neon, identity

## Open questions

- มี service อื่น (นอกจาก MCP hub) เรียก developer-api หรือไม่
