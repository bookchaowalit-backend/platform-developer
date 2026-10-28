from platform_backend_core import Migration

MIGRATION_NAMESPACE='flags'
MIGRATIONS=[Migration('0001',"""
CREATE TABLE feature_flags(workspace_id uuid NOT NULL,name text NOT NULL,enabled boolean NOT NULL,rollout integer NOT NULL CHECK(rollout BETWEEN 0 AND 10000),subjects jsonb NOT NULL,version bigint NOT NULL DEFAULT 1,PRIMARY KEY(workspace_id,name));
ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_flags FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace ON feature_flags USING(workspace_id=nullif(current_setting('app.workspace_id',true),'')::uuid) WITH CHECK(workspace_id=nullif(current_setting('app.workspace_id',true),'')::uuid);
""")]
