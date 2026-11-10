# 06 — C4 Container

```mermaid
C4Container
  title developer-api - containers
  System_Ext(caller, "Caller", "MCP hub or other client with a workspace token")
  System_Ext(gw, "Edge API gateway", "Cloudflare + Railway gateway, route /v1/platform-developer")
  System_Ext(identity, "platform-identity JWKS", "RS256 keys")
  Container_Boundary(rw, "Railway service developer-api, asia-southeast1-eqsg3a, sleep on") {
    Container(api, "serve process", "Python 3.12, uvicorn, FastAPI", "python -m platform_developer serve, PORT 8080, UID 65532")
    Container(mig, "migrate one-off", "Python 3.12", "python -m platform_developer migrate with DDL role")
  }
  ContainerDb(db, "Neon PostgreSQL", "PostgreSQL", "feature_flags, platform_schema_migrations")
  System_Ext(sentry, "Sentry", "Error events")
  Rel(caller, gw, "HTTPS /v1/platform-developer/v1/flags (MCP hub)", "Bearer RS256")
  Rel(gw, api, "HTTPS /v1/flags, token passed through")
  Rel(api, identity, "GET JWKS, at most once per 60 s")
  Rel(api, db, "Pool max 8, runtime role NOSUPERUSER NOBYPASSRLS")
  Rel(mig, db, "DDL, advisory locks")
  Rel(api, sentry, "Scrubbed events")
```

Sources: ops record: api-gateway-edge (2026-11-03); `bookchaowalit-backend/platform-api-gateway@51c4711` `routes.json`; `bookchaowalit/platform-mcp-remote-worker@7d127c2` `wrangler.toml` `CELLS` + `src/worker.ts` `PLATFORM_CELLS`, `Dockerfile`, `.railway/railway.ts`, `src/platform_developer/__main__.py`, `src/platform_developer/migrations.py`, `src/platform_developer/_sentry.py`, core `platform_backend_core/db.py` (pool max_size 8, role check) and `auth.py` (JWKS refresh 60 s), `docs/runtime.md`, ops record: book-platforms-status (2026-11-03) for region/sleep/Neon

## Open questions

- migrate ถูกรันบน Railway เป็น one-off หรือรันจากเครื่อง owner — ops record deploy recipe บอกเพียง "migrate with the owner role"
