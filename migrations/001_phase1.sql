-- Phase 1 reference schema. Apply with a migration role; runtime uses graft_runtime.
CREATE TABLE graft_runs (
  graft_run_id uuid PRIMARY KEY,
  graft_tenant_id uuid NOT NULL,
  graft_principal_id text NOT NULL,
  status text NOT NULL,
  terminal_outcome text,
  finding text,
  tool_classes jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE graft_runs ADD CONSTRAINT graft_runs_id_tenant_key UNIQUE (graft_run_id, graft_tenant_id);

CREATE TABLE graft_run_events (
  graft_event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  graft_run_id uuid NOT NULL,
  graft_tenant_id uuid NOT NULL,
  event_type text NOT NULL,
  event_version integer NOT NULL DEFAULT 1,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (graft_run_id, graft_event_id)
);
ALTER TABLE graft_run_events ADD CONSTRAINT graft_run_events_run_scope_fk
  FOREIGN KEY (graft_run_id, graft_tenant_id) REFERENCES graft_runs(graft_run_id, graft_tenant_id);

CREATE TABLE graft_audit_records (
  graft_audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  graft_tenant_id uuid NOT NULL,
  graft_run_id uuid,
  graft_principal_id text NOT NULL,
  action text NOT NULL,
  outcome text NOT NULL,
  causal_graft_audit_id bigint,
  previous_hash text,
  record_hash text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE graft_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE graft_runs FORCE ROW LEVEL SECURITY;
ALTER TABLE graft_run_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE graft_run_events FORCE ROW LEVEL SECURITY;
ALTER TABLE graft_audit_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE graft_audit_records FORCE ROW LEVEL SECURITY;

CREATE POLICY graft_runs_scope ON graft_runs USING (graft_tenant_id = current_setting('graft.tenant_id', true)::uuid) WITH CHECK (graft_tenant_id = current_setting('graft.tenant_id', true)::uuid);
CREATE POLICY graft_run_events_scope ON graft_run_events USING (graft_tenant_id = current_setting('graft.tenant_id', true)::uuid) WITH CHECK (graft_tenant_id = current_setting('graft.tenant_id', true)::uuid);
CREATE POLICY graft_audit_scope ON graft_audit_records USING (graft_tenant_id = current_setting('graft.tenant_id', true)::uuid) WITH CHECK (graft_tenant_id = current_setting('graft.tenant_id', true)::uuid);

-- Every repository transaction must execute: SET LOCAL graft.tenant_id = '<uuid>'.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'graft_runtime') THEN
    REVOKE UPDATE, DELETE ON graft_audit_records FROM graft_runtime;
  END IF;
END $$;
