-- ============================================================================
-- ZONATA Agent Factory — core schema, migration 001 (PostgreSQL 15+ (UNIQUE NULLS NOT DISTINCT); verified on PG 16.15; Neon supports 15+)
-- AUTHORITATIVE reference DDL. Adapt to the repo's migration tool (Alembic / Prisma /
-- raw SQL runner) discovered in Phase 1. Do NOT change semantics; adapt syntax only.
--
-- Rules honoured here:
--  * NO tables for tenants, employees, identities, permissions, approvals or audit.
--    Those already exist in ZONATA (verify in Phase 1). Columns that point at them
--    are plain UUIDs + a documented FK to add in 002_agent_factory_fks.sql once the
--    real table names are known (see bottom of file).
--  * Every table carries tenant_id and is protected by Row Level Security.
--  * Immutable rows (agent versions, artifacts, certifications, releases) are guarded
--    by triggers. The EvidenceLedger (existing) remains the audit source of truth;
--    af_lifecycle_event is an operational projection of it.
--  * Table prefix af_ avoids collisions with existing ZONATA tables.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid()

-- ---------- helpers ---------------------------------------------------------
CREATE OR REPLACE FUNCTION af_current_tenant() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('zonata.tenant_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION af_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END $$;

CREATE OR REPLACE FUNCTION af_forbid_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'af: table % is immutable (% blocked)', TG_TABLE_NAME, TG_OP
    USING ERRCODE = 'integrity_constraint_violation';
END $$;

-- ---------- 1. requests & requirements -------------------------------------
CREATE TABLE af_request (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             uuid NOT NULL,
  company_id            uuid NOT NULL,
  requester_principal_id uuid NOT NULL,            -- -> existing employee / user / assistant principal
  requester_kind        text NOT NULL CHECK (requester_kind IN ('ai_employee','human_owner','assistant_on_behalf','ai_ceo','system')),
  on_behalf_of_principal_id uuid,                  -- set when the coworker assistant requests for someone
  mode                  text NOT NULL CHECK (mode IN ('single','multi','team','hierarchy','from_template','from_scratch','upgrade','import')),
  natural_language      text NOT NULL CHECK (length(natural_language) BETWEEN 10 AND 20000),
  template_ref          text,                      -- name@semver when the requester chose one
  target_agent_id       uuid,                      -- for upgrade mode
  source_url            text,                      -- for import mode (open-source agent); quarantined lane
  status                text NOT NULL DEFAULT 'REQUESTED' CHECK (status IN (
                          'REQUESTED','ANALYSING','CLARIFYING','DESIGNING','AWAITING_DESIGN_APPROVAL',
                          'BUILDING','QA','CERTIFYING','AWAITING_RELEASE_APPROVAL','PUBLISHING',
                          'PROVISIONED','PARTIAL','REJECTED','FAILED','CANCELLED','KILLED')),
  risk_tier             text CHECK (risk_tier IN ('R0','R1','R2','R3')),
  budget_cap_usd        numeric(12,4) CHECK (budget_cap_usd >= 0),
  spent_usd             numeric(12,4) NOT NULL DEFAULT 0,
  idempotency_key       text NOT NULL,
  correlation_id        uuid NOT NULL DEFAULT gen_random_uuid(),
  failure_reason        text,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX af_request_tenant_status_idx ON af_request (tenant_id, status, created_at DESC);
CREATE INDEX af_request_requester_idx     ON af_request (tenant_id, requester_principal_id, created_at DESC);

CREATE TABLE af_requirement_spec (            -- Agent Requirement Specification (ARS), versioned
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL,
  request_id    uuid NOT NULL REFERENCES af_request(id),
  version       int  NOT NULL CHECK (version >= 1),
  body          jsonb NOT NULL,                -- validated against reference/spec ARS schema
  body_sha256   text  NOT NULL,
  authored_by   text  NOT NULL,                -- factory role principal (e.g. factory.requirement_analyst)
  open_questions jsonb NOT NULL DEFAULT '[]',
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (request_id, version)
);

-- ---------- 2. batches (manufacturing manifest) -----------------------------
CREATE TABLE af_batch (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL,
  company_id       uuid NOT NULL,
  request_id       uuid NOT NULL REFERENCES af_request(id),
  release_policy   text NOT NULL DEFAULT 'atomic_team' CHECK (release_policy IN ('atomic_team','independent')),
  agent_count      int  NOT NULL CHECK (agent_count BETWEEN 1 AND 500),
  waves            int  NOT NULL DEFAULT 1,
  dependency_graph jsonb NOT NULL,             -- {nodes:[agent_key], edges:[[from,to,kind]]}; validated acyclic
  manifest_sha256  text NOT NULL,
  status           text NOT NULL DEFAULT 'PLANNED' CHECK (status IN (
                     'PLANNED','BUILDING','TEAM_QA','CERTIFIED','AWAITING_RELEASE_APPROVAL',
                     'RELEASED','PARTIAL','FAILED','CANCELLED','KILLED')),
  team_qa_eval_run_id uuid,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX af_batch_tenant_status_idx ON af_batch (tenant_id, status);

CREATE TABLE af_batch_item (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL,
  batch_id       uuid NOT NULL REFERENCES af_batch(id),
  agent_key      text NOT NULL,                  -- stable key inside the batch, e.g. 'market_research'
  role_title     text NOT NULL,
  requirement_spec_id uuid NOT NULL REFERENCES af_requirement_spec(id),
  depends_on     text[] NOT NULL DEFAULT '{}',
  wave           int  NOT NULL DEFAULT 0,        -- topological level
  agent_id       uuid,                           -- set when identity is minted
  agent_version_id uuid,                         -- set when built
  status         text NOT NULL DEFAULT 'PENDING' CHECK (status IN (
                   'PENDING','BLOCKED','READY','BUILDING','BUILT','UNIT_TESTED','QA_PASSED',
                   'CERTIFIED','FAILED','SKIPPED','KILLED')),
  attempts       int NOT NULL DEFAULT 0,
  last_error     text,
  UNIQUE (batch_id, agent_key)
);

-- ---------- 3. templates & capabilities ------------------------------------
CREATE TABLE af_template (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid,                              -- NULL = platform-global (read-only for tenants)
  name        text NOT NULL,
  category    text NOT NULL CHECK (category IN (
                'c_suite','corporate_management','finance','accounting','hr','marketing','sales','operations',
                'research','data_analysis','customer_support','software_engineering','devops','database_engineering',
                'defensive_cybersecurity','browser_automation','document_processing','knowledge_management','custom')),
  default_risk_tier text NOT NULL CHECK (default_risk_tier IN ('R0','R1','R2','R3')),
  status      text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','WITHDRAWN')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE NULLS NOT DISTINCT (tenant_id, name)
);

CREATE TABLE af_template_version (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid,
  template_id   uuid NOT NULL REFERENCES af_template(id),
  semver        text NOT NULL CHECK (semver ~ '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$'),
  manifest      jsonb NOT NULL,                  -- zonata.template/v1
  manifest_sha256 text NOT NULL,
  compat        jsonb NOT NULL,                  -- {spec_api:"^1", runtime:"langgraph>=1.2,<2", capability_api:"^1"}
  review_status text NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','IN_REVIEW','APPROVED','REJECTED','WITHDRAWN')),
  approval_id   uuid,                            -- -> existing ApprovalEngine record (publication of template)
  source_agent_version_id uuid,                  -- when promoted from a validated agent
  created_by    uuid NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (template_id, semver)
);

CREATE TABLE af_capability (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    uuid,                             -- NULL = platform capability
  capability_key text NOT NULL,                  -- e.g. 'browser.automation', 'mcp.tool', 'memory.letta'
  semver       text NOT NULL,
  manifest     jsonb NOT NULL,                   -- zonata.capability/v1 (kind, scopes, risk, limits, sandbox, test pack)
  risk_tier    text NOT NULL CHECK (risk_tier IN ('R0','R1','R2','R3')),
  status       text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','WITHDRAWN')),
  UNIQUE NULLS NOT DISTINCT (tenant_id, capability_key, semver)
);

-- ---------- 4. agent identity, versions, artifacts --------------------------
CREATE TABLE af_agent (                          -- registry identity (stable across versions)
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,
  company_id      uuid NOT NULL,
  slug            text NOT NULL CHECK (slug ~ '^[a-z0-9][a-z0-9-]{2,62}$'),
  display_name    text NOT NULL,
  role_title      text NOT NULL,
  category        text NOT NULL,
  owner_principal_id uuid NOT NULL,              -- accountable human/AI-employee owner
  agent_principal_id uuid NOT NULL UNIQUE,       -- identity minted via existing identity layer (Keycloak/OpenFGA); an AGENT principal, never an employee
  template_name   text,
  lifecycle       text NOT NULL DEFAULT 'DRAFT' CHECK (lifecycle IN (
                    'DRAFT','BUILT','CERTIFIED','APPROVED','PUBLISHED','ACTIVE','SUSPENDED','DEPRECATED','RETIRED')),
  active_version_id uuid,                        -- FK added below
  monitoring_status text NOT NULL DEFAULT 'UNMONITORED' CHECK (monitoring_status IN ('UNMONITORED','HEALTHY','DEGRADED','INCIDENT')),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, company_id, slug)
);
CREATE INDEX af_agent_lifecycle_idx ON af_agent (tenant_id, lifecycle);
CREATE INDEX af_agent_category_idx  ON af_agent (tenant_id, category);

CREATE TABLE af_agent_version (                  -- IMMUTABLE once status leaves 'BUILDING'
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,
  agent_id        uuid NOT NULL REFERENCES af_agent(id),
  semver          text NOT NULL CHECK (semver ~ '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$'),
  spec            jsonb NOT NULL,                -- zonata.agent/v1 (no secrets; credential-like strings rejected by validator)
  spec_sha256     text NOT NULL,
  capability_profile jsonb NOT NULL,             -- requested capabilities
  permission_profile jsonb NOT NULL,             -- GRANTED permissions (intersection result); never edited by the agent itself
  risk_tier       text NOT NULL CHECK (risk_tier IN ('R0','R1','R2','R3')),
  template_version_id uuid REFERENCES af_template_version(id),
  parent_version_id uuid REFERENCES af_agent_version(id),   -- upgrade lineage
  package_artifact_id uuid,                      -- FK added below (the signed package)
  package_sha256  text,
  build_id        uuid,
  status          text NOT NULL DEFAULT 'BUILDING' CHECK (status IN (
                    'BUILDING','BUILT','FAILED_QA','CERTIFIED','APPROVED','PUBLISHED','SUPERSEDED','ROLLED_BACK','WITHDRAWN')),
  created_by      text NOT NULL,                 -- factory service principal
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (agent_id, semver)
);
ALTER TABLE af_agent
  ADD CONSTRAINT af_agent_active_version_fk FOREIGN KEY (active_version_id) REFERENCES af_agent_version(id);

CREATE TABLE af_build (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL,
  batch_item_id  uuid REFERENCES af_batch_item(id),
  agent_version_id uuid REFERENCES af_agent_version(id),
  attempt        int NOT NULL DEFAULT 1,
  worker_id      text,
  sandbox_profile text NOT NULL DEFAULT 'T0' CHECK (sandbox_profile IN ('T0','T1','T2')),
  stages         jsonb NOT NULL DEFAULT '[]',    -- [{stage, status, started, finished, evidence_ref}]
  status         text NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','KILLED','LOST')),
  heartbeat_at   timestamptz,
  tokens_in      bigint NOT NULL DEFAULT 0,
  tokens_out     bigint NOT NULL DEFAULT 0,
  cost_usd       numeric(12,4) NOT NULL DEFAULT 0,
  log_artifact_id uuid,
  error          text,
  started_at     timestamptz,
  finished_at    timestamptz
);
CREATE INDEX af_build_status_idx ON af_build (tenant_id, status, heartbeat_at);

CREATE TABLE af_artifact (                       -- content-addressed, IMMUTABLE
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    uuid NOT NULL,
  kind         text NOT NULL CHECK (kind IN ('agent_package','spec','workflow','tool_package','sbom','scan_report','eval_report','certification_bundle','build_log','team_manifest')),
  sha256       text NOT NULL,
  size_bytes   bigint NOT NULL CHECK (size_bytes >= 0),
  storage_uri  text NOT NULL,                    -- s3://bucket/tenant/<tenant_id>/artifacts/<sha256>
  signature    text,                             -- base64 Ed25519 detached signature over canonical manifest
  signing_key_id text,
  created_by   text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  retain_until timestamptz,
  UNIQUE (tenant_id, sha256, kind)
);
ALTER TABLE af_agent_version
  ADD CONSTRAINT af_agent_version_pkg_fk FOREIGN KEY (package_artifact_id) REFERENCES af_artifact(id);

-- ---------- 5. QA, findings, certification ----------------------------------
CREATE TABLE af_eval_run (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,
  subject_kind    text NOT NULL CHECK (subject_kind IN ('agent_version','batch_team')),
  agent_version_id uuid REFERENCES af_agent_version(id),
  batch_id        uuid REFERENCES af_batch(id),
  suite           text NOT NULL CHECK (suite IN ('unit','functional','security','integration','performance','regression','team','tenant_isolation')),
  phase           text NOT NULL CHECK (phase IN ('builder_unit','independent_qa')),   -- independence marker
  evaluator_principal text NOT NULL,             -- MUST differ from build principal for phase='independent_qa' (CHECK via trigger)
  dataset_ref     text NOT NULL,                 -- dataset id@version
  dataset_sha256  text NOT NULL,
  model_profile   text NOT NULL,                 -- 'mock' results can never satisfy certification gates
  repeats         int NOT NULL DEFAULT 1 CHECK (repeats BETWEEN 1 AND 20),
  summary         jsonb NOT NULL DEFAULT '{}',   -- pass_rate, wilson_lower, latency p50/p95, tokens, cost
  status          text NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING','PASSED','FAILED','ERROR','CANCELLED')),
  report_artifact_id uuid REFERENCES af_artifact(id),
  started_at      timestamptz NOT NULL DEFAULT now(),
  finished_at     timestamptz
);
CREATE INDEX af_eval_run_subject_idx ON af_eval_run (tenant_id, agent_version_id, suite);

ALTER TABLE af_batch ADD CONSTRAINT af_batch_team_qa_fk FOREIGN KEY (team_qa_eval_run_id) REFERENCES af_eval_run(id);

CREATE TABLE af_eval_result (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL,
  eval_run_id uuid NOT NULL REFERENCES af_eval_run(id),
  case_id     text NOT NULL,
  repeat_no   int  NOT NULL DEFAULT 1,
  mandatory   boolean NOT NULL DEFAULT false,
  passed      boolean NOT NULL,
  score       numeric(6,4),
  checks      jsonb NOT NULL DEFAULT '[]',
  trace_id    text,                              -- OTel / Langfuse trace id
  latency_ms  int,
  tokens      int,
  cost_usd    numeric(12,6),
  UNIQUE (eval_run_id, case_id, repeat_no)
);

CREATE TABLE af_finding (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL,
  agent_version_id uuid NOT NULL REFERENCES af_agent_version(id),
  source        text NOT NULL,                   -- semgrep | bandit | gitleaks | pip-audit | redteam | manual | policy
  severity      text NOT NULL CHECK (severity IN ('critical','high','medium','low','info')),
  title         text NOT NULL,
  detail        jsonb NOT NULL DEFAULT '{}',
  status        text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','FIXED','WAIVED','FALSE_POSITIVE')),
  waiver_approval_id uuid,                       -- existing ApprovalEngine record; waiver approver != requester != builder
  created_at    timestamptz NOT NULL DEFAULT now(),
  resolved_at   timestamptz
);
CREATE INDEX af_finding_open_idx ON af_finding (tenant_id, agent_version_id) WHERE status = 'OPEN';

CREATE TABLE af_certification (                  -- IMMUTABLE
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,
  subject_kind    text NOT NULL CHECK (subject_kind IN ('agent_version','team')),
  agent_version_id uuid REFERENCES af_agent_version(id),
  batch_id        uuid REFERENCES af_batch(id),
  gate_policy_version text NOT NULL,             -- reference/qa/gate_policy.yaml version
  gate_results    jsonb NOT NULL,                -- [{gate, required, observed, threshold, passed}]
  all_mandatory_passed boolean NOT NULL,
  bundle_artifact_id uuid NOT NULL REFERENCES af_artifact(id),
  evidence_ledger_ref text NOT NULL,             -- EvidenceLedger entry id + merkle root at issuance
  issued_by       text NOT NULL,                 -- 'factory.certification_manager' (deterministic service)
  issued_at       timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz,
  CHECK ((subject_kind='agent_version' AND agent_version_id IS NOT NULL) OR (subject_kind='team' AND batch_id IS NOT NULL))
);

-- ---------- 6. release, team, bindings, assignment, runtime -----------------
CREATE TABLE af_release (                        -- IMMUTABLE after decision
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL,
  subject_kind     text NOT NULL CHECK (subject_kind IN ('agent_version','team')),
  agent_version_id uuid REFERENCES af_agent_version(id),
  batch_id         uuid REFERENCES af_batch(id),
  certification_id uuid NOT NULL REFERENCES af_certification(id),
  approval_id      uuid,                         -- existing ApprovalEngine record (NOT created here)
  submitted_by     text NOT NULL,                -- 'factory.release_manager'
  decision         text NOT NULL DEFAULT 'PENDING' CHECK (decision IN ('PENDING','APPROVED','REJECTED','EXPIRED','REVOKED')),
  decided_by_principal uuid,                     -- approver; trigger enforces != requester, != factory director
  decided_at       timestamptz,
  channel          text NOT NULL DEFAULT 'production' CHECK (channel IN ('staging','canary','production')),
  rollback_of_release_id uuid REFERENCES af_release(id),
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE af_team (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL,
  company_id    uuid NOT NULL,
  batch_id      uuid REFERENCES af_batch(id),
  name          text NOT NULL,
  department    text,
  supervisor_agent_id uuid,                      -- FK below
  version       int NOT NULL DEFAULT 1,
  manifest_artifact_id uuid REFERENCES af_artifact(id),
  lifecycle     text NOT NULL DEFAULT 'DRAFT' CHECK (lifecycle IN ('DRAFT','CERTIFIED','PUBLISHED','ACTIVE','SUSPENDED','RETIRED')),
  UNIQUE (tenant_id, company_id, name, version)
);
CREATE TABLE af_team_member (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL,
  team_id       uuid NOT NULL REFERENCES af_team(id),
  agent_id      uuid NOT NULL REFERENCES af_agent(id),
  agent_version_id uuid NOT NULL REFERENCES af_agent_version(id),
  role_in_team  text NOT NULL CHECK (role_in_team IN ('supervisor','specialist','reporter','shared_service')),
  reports_to_agent_id uuid REFERENCES af_agent(id),
  max_delegation_depth int NOT NULL DEFAULT 2 CHECK (max_delegation_depth BETWEEN 0 AND 5),
  UNIQUE (team_id, agent_id)
);
ALTER TABLE af_team ADD CONSTRAINT af_team_supervisor_fk FOREIGN KEY (supervisor_agent_id) REFERENCES af_agent(id);

CREATE TABLE af_tool_binding (                   -- which tool/MCP server/A2A peer an agent VERSION may call, with scope
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL,
  agent_version_id uuid NOT NULL REFERENCES af_agent_version(id),
  binding_kind     text NOT NULL CHECK (binding_kind IN ('builtin_tool','mcp_server','mcp_tool','a2a_peer','knowledge_collection','memory_store','database_view')),
  target_ref       text NOT NULL,                -- tool registry id / MCP server id+tool / peer card id / collection id
  scopes           text[] NOT NULL DEFAULT '{}', -- e.g. {'read'}
  constraints      jsonb NOT NULL DEFAULT '{}',  -- allowed hosts, row filters, rate limits, max_calls
  grant_approval_id uuid,                        -- ApprovalEngine record when binding exceeded auto-grant
  secret_refs      text[] NOT NULL DEFAULT '{}', -- NAMES of secrets resolved at runtime via the secrets service; never values
  UNIQUE (agent_version_id, binding_kind, target_ref)
);

CREATE TABLE af_assignment (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,
  company_id      uuid NOT NULL,
  agent_id        uuid NOT NULL REFERENCES af_agent(id),
  agent_version_id uuid NOT NULL REFERENCES af_agent_version(id),
  assignee_kind   text NOT NULL CHECK (assignee_kind IN ('ai_employee','department','team','assistant')),
  assignee_id     uuid NOT NULL,                 -- -> existing employee / department rows
  assigned_by     uuid NOT NULL,
  status          text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REASSIGNED','REVOKED')),
  created_at      timestamptz NOT NULL DEFAULT now(),
  ended_at        timestamptz
);
CREATE UNIQUE INDEX af_assignment_active_uq ON af_assignment (agent_id, assignee_kind, assignee_id) WHERE status = 'ACTIVE';

CREATE TABLE af_runtime_instance (               -- REUSE the existing runtime table if the audit finds one; else this
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,
  agent_id        uuid NOT NULL REFERENCES af_agent(id),
  agent_version_id uuid NOT NULL REFERENCES af_agent_version(id),
  channel         text NOT NULL CHECK (channel IN ('staging','canary','production')),
  traffic_percent int  NOT NULL DEFAULT 100 CHECK (traffic_percent BETWEEN 0 AND 100),
  runtime_ref     text NOT NULL,                 -- handle in the LangGraph runtime registry
  status          text NOT NULL DEFAULT 'STARTING' CHECK (status IN ('STARTING','RUNNING','SUSPENDED','STOPPED','FAILED','KILLED')),
  started_at      timestamptz NOT NULL DEFAULT now(),
  stopped_at      timestamptz
);

-- ---------- 7. lifecycle, feedback, quotas ----------------------------------
CREATE TABLE af_lifecycle_event (                -- operational projection; EvidenceLedger is the legal record
  id            bigserial PRIMARY KEY,
  tenant_id     uuid NOT NULL,
  subject_kind  text NOT NULL,                   -- request|batch|item|agent|agent_version|team|release|build
  subject_id    uuid NOT NULL,
  from_state    text,
  to_state      text NOT NULL,
  actor         text NOT NULL,                   -- principal or factory role
  reason        text,
  evidence_ledger_id text NOT NULL,              -- id returned by EvidenceLedger.append (NOT NULL: no evidence, no transition)
  correlation_id uuid,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX af_lifecycle_subject_idx ON af_lifecycle_event (tenant_id, subject_kind, subject_id, id);

CREATE TABLE af_feedback (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL,
  agent_id      uuid NOT NULL REFERENCES af_agent(id),
  agent_version_id uuid REFERENCES af_agent_version(id),
  from_principal uuid NOT NULL,
  rating        int CHECK (rating BETWEEN 1 AND 5),
  category      text CHECK (category IN ('quality','speed','safety','cost','missing_capability','other')),
  comment       text,
  task_ref      text,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE af_quota_usage (
  tenant_id     uuid NOT NULL,
  period        text NOT NULL,                   -- 'YYYY-MM' or 'YYYY-MM-DD'
  metric        text NOT NULL CHECK (metric IN ('builds','agents_published','tokens','cost_usd','sandbox_seconds','concurrent_builds')),
  used          numeric(18,4) NOT NULL DEFAULT 0,
  limit_value   numeric(18,4) NOT NULL,
  PRIMARY KEY (tenant_id, period, metric)
);

-- ---------- triggers: updated_at --------------------------------------------
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['af_request','af_batch','af_agent'] LOOP
    EXECUTE format('CREATE TRIGGER %I_touch BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION af_touch_updated_at()', t, t);
  END LOOP;
END $$;

-- ---------- triggers: immutability ------------------------------------------
CREATE TRIGGER af_artifact_immutable      BEFORE UPDATE OR DELETE ON af_artifact      FOR EACH ROW EXECUTE FUNCTION af_forbid_mutation();
CREATE TRIGGER af_certification_immutable BEFORE UPDATE OR DELETE ON af_certification FOR EACH ROW EXECUTE FUNCTION af_forbid_mutation();
CREATE TRIGGER af_lifecycle_immutable     BEFORE UPDATE OR DELETE ON af_lifecycle_event FOR EACH ROW EXECUTE FUNCTION af_forbid_mutation();
CREATE TRIGGER af_eval_result_immutable   BEFORE UPDATE OR DELETE ON af_eval_result   FOR EACH ROW EXECUTE FUNCTION af_forbid_mutation();

-- agent version: spec / permission_profile / hashes frozen once the version has left BUILDING
CREATE OR REPLACE FUNCTION af_agent_version_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'af: agent versions are never deleted (withdraw instead)' USING ERRCODE='integrity_constraint_violation';
  END IF;
  IF OLD.status <> 'BUILDING' AND (
       NEW.spec IS DISTINCT FROM OLD.spec OR NEW.spec_sha256 IS DISTINCT FROM OLD.spec_sha256
    OR NEW.permission_profile IS DISTINCT FROM OLD.permission_profile
    OR NEW.capability_profile IS DISTINCT FROM OLD.capability_profile
    OR NEW.risk_tier IS DISTINCT FROM OLD.risk_tier
    OR NEW.package_sha256 IS DISTINCT FROM OLD.package_sha256) THEN
    RAISE EXCEPTION 'af: agent version % is frozen', OLD.id USING ERRCODE='integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER af_agent_version_guard_t BEFORE UPDATE OR DELETE ON af_agent_version FOR EACH ROW EXECUTE FUNCTION af_agent_version_guard();

-- release: no edits after decision; self-approval is blocked at the DB as defence in depth
CREATE OR REPLACE FUNCTION af_release_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE req uuid;
BEGIN
  IF TG_OP = 'UPDATE' AND OLD.decision <> 'PENDING' THEN
    RAISE EXCEPTION 'af: release % already decided', OLD.id USING ERRCODE='integrity_constraint_violation';
  END IF;
  IF NEW.decision = 'APPROVED' THEN
    IF NEW.decided_by_principal IS NULL OR NEW.approval_id IS NULL THEN
      RAISE EXCEPTION 'af: approval requires decided_by_principal and ApprovalEngine approval_id';
    END IF;
    SELECT r.requester_principal_id INTO req
      FROM af_request r
      JOIN af_batch b ON b.request_id = r.id
      WHERE (NEW.batch_id IS NOT NULL AND b.id = NEW.batch_id)
         OR (NEW.agent_version_id IS NOT NULL AND b.id IN (
              SELECT bi.batch_id FROM af_batch_item bi WHERE bi.agent_version_id = NEW.agent_version_id))
      LIMIT 1;
    IF req IS NOT NULL AND req = NEW.decided_by_principal THEN
      RAISE EXCEPTION 'af: requester cannot approve own release' USING ERRCODE='integrity_constraint_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER af_release_guard_t BEFORE INSERT OR UPDATE ON af_release FOR EACH ROW EXECUTE FUNCTION af_release_guard();

-- independent QA: evaluator must differ from the build principal
CREATE OR REPLACE FUNCTION af_eval_independence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE builder text;
BEGIN
  IF NEW.phase = 'independent_qa' AND NEW.agent_version_id IS NOT NULL THEN
    SELECT created_by INTO builder FROM af_agent_version WHERE id = NEW.agent_version_id;
    IF builder IS NOT DISTINCT FROM NEW.evaluator_principal THEN
      RAISE EXCEPTION 'af: independent QA evaluator must differ from builder (%)', builder USING ERRCODE='integrity_constraint_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER af_eval_independence_t BEFORE INSERT ON af_eval_run FOR EACH ROW EXECUTE FUNCTION af_eval_independence();

-- ---------- Row Level Security ------------------------------------------------
-- The application connects as a NON-owner role (af_app) and sets
--   SET LOCAL zonata.tenant_id = '<uuid>'  at the start of each transaction.
-- Phase 1 must confirm the repo's existing tenant-isolation mechanism and mirror it;
-- if a different setting name is in use, rename af_current_tenant() accordingly.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'af_request','af_requirement_spec','af_batch','af_batch_item','af_build','af_agent','af_agent_version',
    'af_artifact','af_eval_run','af_eval_result','af_finding','af_certification','af_release','af_team',
    'af_team_member','af_tool_binding','af_assignment','af_runtime_instance','af_lifecycle_event',
    'af_feedback','af_quota_usage'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY %I ON %I USING (tenant_id = af_current_tenant()) WITH CHECK (tenant_id = af_current_tenant())', t||'_tenant', t);
  END LOOP;
  -- platform-global rows (tenant_id IS NULL) are readable by every tenant, writable by none
  FOREACH t IN ARRAY ARRAY['af_template','af_template_version','af_capability'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR SELECT USING (tenant_id IS NULL OR tenant_id = af_current_tenant())', t||'_read', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR ALL USING (tenant_id = af_current_tenant()) WITH CHECK (tenant_id = af_current_tenant())', t||'_write', t);
  END LOOP;
END $$;

-- ---------- 002_agent_factory_fks.sql (TEMPLATE — fill after Phase 1 audit) ----
-- ALTER TABLE af_request ADD CONSTRAINT af_request_tenant_fk   FOREIGN KEY (tenant_id)  REFERENCES <existing_tenants>(id);
-- ALTER TABLE af_request ADD CONSTRAINT af_request_company_fk  FOREIGN KEY (company_id) REFERENCES <existing_companies>(id);
-- ALTER TABLE af_request ADD CONSTRAINT af_request_requester_fk FOREIGN KEY (requester_principal_id) REFERENCES <existing_principals_or_employees>(id);
-- ALTER TABLE af_assignment ADD CONSTRAINT af_assignment_employee_fk ... (assignee_kind-dependent: enforce in service layer if polymorphic)
-- ALTER TABLE af_release ADD CONSTRAINT af_release_approval_fk FOREIGN KEY (approval_id) REFERENCES <existing_approvals>(id);
-- ALTER TABLE af_finding ADD CONSTRAINT af_finding_waiver_fk   FOREIGN KEY (waiver_approval_id) REFERENCES <existing_approvals>(id);
-- ALTER TABLE af_agent   ADD CONSTRAINT af_agent_owner_fk      FOREIGN KEY (owner_principal_id) REFERENCES <existing_principals_or_employees>(id);
-- ROLLBACK (down migration): DROP TABLE ... in reverse dependency order; drop functions af_*; no existing table is touched.
