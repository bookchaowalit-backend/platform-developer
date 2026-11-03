# 10 — Sequences

## 1. Update a flag (PUT with version)

```mermaid
sequenceDiagram
  participant C as Caller
  participant B as core _Boundary
  participant R as app put route
  participant V as TokenVerifier
  participant J as identity JWKS
  participant S as FlagStore
  participant D as PostgreSQL
  C->>B: PUT /v1/flags/pilot (Bearer, JSON body)
  B->>B: body <= 32768 bytes, start 30 s timer
  B->>R: replay body
  R->>V: verify(Authorization)
  opt key cache older than 60 s
    V->>J: GET JWKS (5 s timeout, no redirects)
    J-->>V: keys
  end
  V-->>R: Principal(actor, workspace, scopes)
  R->>R: flags:write in scopes else 403
  R->>S: put(workspace, name, enabled, rollout, subjects, version)
  S->>D: BEGIN, set_config app.workspace_id
  S->>D: UPDATE feature_flags SET ..., version=version+1 WHERE name AND version RETURNING
  alt row returned
    D-->>S: row
    S-->>R: row
    R-->>C: 200 row
  else no row
    S-->>R: Conflict
    R-->>C: 409 Version conflict
  end
  B->>B: metrics[(route,status)] += 1, log route status correlation_id
```

## 2. Evaluate a flag

```mermaid
sequenceDiagram
  participant C as Caller
  participant R as app evaluate route
  participant S as FlagStore
  participant D as PostgreSQL
  C->>R: POST /v1/flags/pilot/evaluate {subject}
  R->>R: require_scope flags:read
  R->>S: evaluate(workspace, name, subject)
  S->>S: validate subject regex
  S->>D: SELECT name, enabled, rollout, subjects, version WHERE name (RLS by workspace)
  D-->>S: row or none
  alt missing or disabled
    S-->>R: false
  else enabled
    S->>S: bucket = sha256(workspace:name:subject)[0:8] mod 10000
    S-->>R: subject in subjects or bucket < rollout
  end
  R-->>C: 200 {"enabled": bool}
```

## 3. Readiness probe

```mermaid
sequenceDiagram
  participant P as Railway healthcheck / uptime worker
  participant A as core readyz
  participant DB as core Database.ready
  participant S as FlagStore.ready
  participant D as PostgreSQL
  P->>A: GET /readyz
  A->>DB: SELECT 1
  DB->>D: query
  A->>S: flags_schema check
  S->>D: has_schema_privilege / has_table_privilege each
  S->>D: SELECT version, checksum FROM platform_schema_migrations WHERE namespace flags
  S->>D: relrowsecurity AND relforcerowsecurity
  S->>D: SELECT name, version FROM feature_flags LIMIT 0
  alt every check true
    A-->>P: 200 {"status":"ready"}
  else any false or error
    A-->>P: 503 {"status":"unavailable"}
  end
```

## 4. Unhandled error to Sentry

```mermaid
sequenceDiagram
  participant B as core _Boundary
  participant CE as CaptureErrors
  participant R as route
  participant SN as Sentry
  B->>CE: ASGI call
  CE->>R: ASGI call
  R--xCE: exception
  opt client active and transport set
    CE->>CE: event_from_exception (handled false)
    CE->>SN: capture_event after _scrub_event drops free text
  end
  CE--xB: re-raise
  B-->>B: 500 internal server error (redacted)
```

Sources: `src/platform_developer/app.py`, `src/platform_developer/store.py`, `src/platform_developer/_sentry.py`, core `platform_backend_core/http.py`, `auth.py`, `db.py`, `runtime_tests/test_http.py`, `runtime_tests/test_sentry.py`
