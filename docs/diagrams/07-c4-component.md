# 07 — C4 Component (serve process)

ลำดับ middleware: `_Boundary` (core, ชั้นนอก) → `CaptureErrors` (ชั้นในสุดของ user middleware) → FastAPI routes

```mermaid
C4Component
  title developer-api serve process - components
  Container_Boundary(api, "serve process") {
    Component(main, "__main__.main", "argparse", "serve or migrate, redacts config errors")
    Component(boundary, "core _Boundary", "ASGI middleware", "32 KiB body limit, 30 s timeout, x-request-id, metrics, redacted 500")
    Component(capture, "CaptureErrors", "ASGI middleware", "Reports unhandled exceptions to Sentry then re-raises")
    Component(routes, "app.create_app routes", "FastAPI", "/v1/flags list, get, put, delete, evaluate")
    Component(probes, "core probes", "FastAPI", "/healthz, /readyz, /metrics")
    Component(scope, "core require_scope", "Dependency", "TokenVerifier.verify, scope check")
    Component(verifier, "core TokenVerifier", "PyJWT", "RS256, iss, aud, ws, sub, lifetime <= 3600 s")
    Component(store, "FlagStore", "psycopg", "put, get, list, delete, evaluate, ready")
    Component(dbc, "core Database", "psycopg_pool", "transaction(workspace) sets app.workspace_id")
    Component(sentry, "_sentry.init_sentry and _scrub_event", "sentry-sdk", "No-op without SENTRY_DSN")
  }
  ContainerDb(pg, "PostgreSQL", "Neon")
  Rel(main, boundary, "uvicorn.run(app)")
  Rel(boundary, capture, "ASGI call")
  Rel(capture, routes, "ASGI call")
  Rel(routes, scope, "Depends")
  Rel(scope, verifier, "verify(Authorization)")
  Rel(routes, store, "calls")
  Rel(probes, store, "readiness_checks flags_schema")
  Rel(store, dbc, "transaction(workspace)")
  Rel(dbc, pg, "SQL")
  Rel(capture, sentry, "capture_event")
```

Sources: `src/platform_developer/__main__.py`, `src/platform_developer/app.py`, `src/platform_developer/store.py`, `src/platform_developer/_sentry.py`, `src/platform_developer/__init__.py`, core `platform_backend_core/http.py`, `auth.py`, `db.py` (commit `21d5f44`)
