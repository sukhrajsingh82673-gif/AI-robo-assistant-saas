-- ============================================================================
-- ZONATA Agent Factory — core schema, migration 0013 (SQLite Translation)
-- Authoritative 24 af_* tables, immutability, updated_at, and security triggers
-- ============================================================================

-- ---------- 1. requests & requirements -------------------------------------
CREATE TABLE IF NOT EXISTS af_request (
  id                    TEXT PRIMARY KEY,
  tenant_id             TEXT NOT NULL,
  company_id            TEXT NOT NULL,
  requester_principal_id TEXT NOT NULL,
  requester_kind        TEXT NOT NULL CHECK (requester_kind IN ('ai_employee','human_owner','assistant_on_behalf','ai_ceo','system')),
  on_behalf_of_principal_id TEXT,
  mode                  TEXT NOT NULL CHECK (mode IN ('single','multi','team','hierarchy','from_template','from_scratch','upgrade','import')),
  natural_language      TEXT NOT NULL CHECK (length(natural_language) BETWEEN 10 AND 20000),
  template_ref          TEXT,
  target_agent_id       TEXT,
  source_url            TEXT,
  status                TEXT NOT NULL DEFAULT 'REQUESTED' CHECK (status IN (
                          'REQUESTED','ANALYSING','CLARIFYING','DESIGNING','AWAITING_DESIGN_APPROVAL',
                          'BUILDING','QA','CERTIFYING','AWAITING_RELEASE_APPROVAL','PUBLISHING',
                          'PROVISIONED','PARTIAL','REJECTED','FAILED','CANCELLED','KILLED')),
  risk_tier             TEXT CHECK (risk_tier IN ('R0','R1','R2','R3')),
  budget_cap_usd        REAL CHECK (budget_cap_usd >= 0),
  spent_usd             REAL NOT NULL DEFAULT 0.0,
  idempotency_key       TEXT NOT NULL,
  correlation_id        TEXT NOT NULL,
  failure_reason        TEXT,
  created_at            REAL NOT NULL,
  updated_at            REAL NOT NULL,
  UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS af_request_tenant_status_idx ON af_request (tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS af_request_requester_idx     ON af_request (tenant_id, requester_principal_id, created_at DESC);

CREATE TABLE IF NOT EXISTS af_requirement_spec (
  id            TEXT PRIMARY KEY,
  tenant_id     TEXT NOT NULL,
  request_id    TEXT NOT NULL REFERENCES af_request(id),
  version       INTEGER NOT NULL CHECK (version >= 1),
  body          TEXT NOT NULL,
  body_sha256   TEXT NOT NULL,
  authored_by   TEXT NOT NULL,
  open_questions TEXT NOT NULL DEFAULT '[]',
  created_at    REAL NOT NULL,
  UNIQUE (request_id, version)
);

-- ---------- 2. batches (manufacturing manifest) -----------------------------
CREATE TABLE IF NOT EXISTS af_batch (
  id               TEXT PRIMARY KEY,
  tenant_id        TEXT NOT NULL,
  company_id       TEXT NOT NULL,
  request_id       TEXT NOT NULL REFERENCES af_request(id),
  release_policy   TEXT NOT NULL DEFAULT 'atomic_team' CHECK (release_policy IN ('atomic_team','independent')),
  agent_count      INTEGER NOT NULL CHECK (agent_count BETWEEN 1 AND 500),
  waves            INTEGER NOT NULL DEFAULT 1,
  dependency_graph TEXT NOT NULL,
  manifest_sha256  TEXT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'PLANNED' CHECK (status IN (
                     'PLANNED','BUILDING','TEAM_QA','CERTIFIED','AWAITING_RELEASE_APPROVAL',
                     'RELEASED','PARTIAL','FAILED','CANCELLED','KILLED')),
  team_qa_eval_run_id TEXT,
  created_at       REAL NOT NULL,
  updated_at       REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS af_batch_tenant_status_idx ON af_batch (tenant_id, status);

CREATE TABLE IF NOT EXISTS af_batch_item (
  id             TEXT PRIMARY KEY,
  tenant_id      TEXT NOT NULL,
  batch_id       TEXT NOT NULL REFERENCES af_batch(id),
  agent_key      TEXT NOT NULL,
  role_title     TEXT NOT NULL,
  requirement_spec_id TEXT NOT NULL REFERENCES af_requirement_spec(id),
  depends_on     TEXT NOT NULL DEFAULT '[]',
  wave           INTEGER NOT NULL DEFAULT 0,
  agent_id       TEXT,
  agent_version_id TEXT,
  status         TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN (
                   'PENDING','BLOCKED','READY','BUILDING','BUILT','UNIT_TESTED','QA_PASSED',
                   'CERTIFIED','FAILED','SKIPPED','KILLED')),
  attempts       INTEGER NOT NULL DEFAULT 0,
  last_error     TEXT,
  UNIQUE (batch_id, agent_key)
);

-- ---------- 3. templates & capabilities ------------------------------------
CREATE TABLE IF NOT EXISTS af_template (
  id          TEXT PRIMARY KEY,
  tenant_id   TEXT,
  name        TEXT NOT NULL,
  category    TEXT NOT NULL CHECK (category IN (
                'c_suite','corporate_management','finance','accounting','hr','marketing','sales','operations',
                'research','data_analysis','customer_support','software_engineering','devops','database_engineering',
                'defensive_cybersecurity','browser_automation','document_processing','knowledge_management','custom')),
  default_risk_tier TEXT NOT NULL CHECK (default_risk_tier IN ('R0','R1','R2','R3')),
  status      TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','WITHDRAWN')),
  created_at  REAL NOT NULL,
  UNIQUE (tenant_id, name)
);

CREATE TABLE IF NOT EXISTS af_template_version (
  id            TEXT PRIMARY KEY,
  tenant_id     TEXT,
  template_id   TEXT NOT NULL REFERENCES af_template(id),
  semver        TEXT NOT NULL,
  manifest      TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  compat        TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','IN_REVIEW','APPROVED','REJECTED','WITHDRAWN')),
  approval_id   TEXT,
  source_agent_version_id TEXT,
  created_by    TEXT NOT NULL,
  created_at    REAL NOT NULL,
  UNIQUE (template_id, semver)
);

CREATE TABLE IF NOT EXISTS af_capability (
  id           TEXT PRIMARY KEY,
  tenant_id    TEXT,
  capability_key TEXT NOT NULL,
  semver       TEXT NOT NULL,
  manifest     TEXT NOT NULL,
  risk_tier    TEXT NOT NULL CHECK (risk_tier IN ('R0','R1','R2','R3')),
  status       TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','WITHDRAWN')),
  UNIQUE (tenant_id, capability_key, semver)
);

-- ---------- 4. agent identity, versions, artifacts --------------------------
CREATE TABLE IF NOT EXISTS af_agent (
  id              TEXT PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  company_id      TEXT NOT NULL,
  slug            TEXT NOT NULL,
  display_name    TEXT NOT NULL,
  role_title      TEXT NOT NULL,
  category        TEXT NOT NULL,
  owner_principal_id TEXT NOT NULL,
  agent_principal_id TEXT NOT NULL UNIQUE,
  template_name   TEXT,
  lifecycle       TEXT NOT NULL DEFAULT 'DRAFT' CHECK (lifecycle IN (
                    'DRAFT','BUILT','CERTIFIED','APPROVED','PUBLISHED','ACTIVE','SUSPENDED','DEPRECATED','RETIRED')),
  active_version_id TEXT,
  monitoring_status TEXT NOT NULL DEFAULT 'UNMONITORED' CHECK (monitoring_status IN ('UNMONITORED','HEALTHY','DEGRADED','INCIDENT')),
  created_at      REAL NOT NULL,
  updated_at      REAL NOT NULL,
  UNIQUE (tenant_id, company_id, slug)
);
CREATE INDEX IF NOT EXISTS af_agent_lifecycle_idx ON af_agent (tenant_id, lifecycle);
CREATE INDEX IF NOT EXISTS af_agent_category_idx  ON af_agent (tenant_id, category);

CREATE TABLE IF NOT EXISTS af_agent_version (
  id              TEXT PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  agent_id        TEXT NOT NULL REFERENCES af_agent(id),
  semver          TEXT NOT NULL,
  spec            TEXT NOT NULL,
  spec_sha256     TEXT NOT NULL,
  capability_profile TEXT NOT NULL,
  permission_profile TEXT NOT NULL,
  risk_tier       TEXT NOT NULL CHECK (risk_tier IN ('R0','R1','R2','R3')),
  template_version_id TEXT REFERENCES af_template_version(id),
  parent_version_id TEXT REFERENCES af_agent_version(id),
  package_artifact_id TEXT REFERENCES af_artifact(id),
  package_sha256  TEXT,
  build_id        TEXT,
  status          TEXT NOT NULL DEFAULT 'BUILDING' CHECK (status IN (
                    'BUILDING','BUILT','FAILED_QA','CERTIFIED','APPROVED','PUBLISHED','SUPERSEDED','ROLLED_BACK','WITHDRAWN')),
  created_by      TEXT NOT NULL,
  created_at      REAL NOT NULL,
  UNIQUE (agent_id, semver)
);

CREATE TABLE IF NOT EXISTS af_build (
  id             TEXT PRIMARY KEY,
  tenant_id      TEXT NOT NULL,
  batch_item_id  TEXT REFERENCES af_batch_item(id),
  agent_version_id TEXT REFERENCES af_agent_version(id),
  attempt        INTEGER NOT NULL DEFAULT 1,
  worker_id      TEXT,
  sandbox_profile TEXT NOT NULL DEFAULT 'T0' CHECK (sandbox_profile IN ('T0','T1','T2')),
  stages         TEXT NOT NULL DEFAULT '[]',
  status         TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','KILLED','LOST')),
  heartbeat_at   REAL,
  tokens_in      INTEGER NOT NULL DEFAULT 0,
  tokens_out     INTEGER NOT NULL DEFAULT 0,
  cost_usd       REAL NOT NULL DEFAULT 0.0,
  log_artifact_id TEXT,
  error          TEXT,
  started_at     REAL,
  finished_at    REAL
);
CREATE INDEX IF NOT EXISTS af_build_status_idx ON af_build (tenant_id, status, heartbeat_at);

CREATE TABLE IF NOT EXISTS af_artifact (
  id           TEXT PRIMARY KEY,
  tenant_id    TEXT NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('agent_package','spec','workflow','tool_package','sbom','scan_report','eval_report','certification_bundle','build_log','team_manifest')),
  sha256       TEXT NOT NULL,
  size_bytes   INTEGER NOT NULL CHECK (size_bytes >= 0),
  storage_uri  TEXT NOT NULL,
  signature    TEXT,
  signing_key_id TEXT,
  created_by   TEXT NOT NULL,
  created_at   REAL NOT NULL,
  retain_until REAL,
  UNIQUE (tenant_id, sha256, kind)
);

-- ---------- 5. QA, findings, certification ----------------------------------
CREATE TABLE IF NOT EXISTS af_eval_run (
  id              TEXT PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  subject_kind    TEXT NOT NULL CHECK (subject_kind IN ('agent_version','batch_team')),
  agent_version_id TEXT REFERENCES af_agent_version(id),
  batch_id        TEXT REFERENCES af_batch(id),
  suite           TEXT NOT NULL CHECK (suite IN ('unit','functional','security','integration','performance','regression','team','tenant_isolation')),
  phase           TEXT NOT NULL CHECK (phase IN ('builder_unit','independent_qa')),
  evaluator_principal TEXT NOT NULL,
  dataset_ref     TEXT NOT NULL,
  dataset_sha256  TEXT NOT NULL,
  model_profile   TEXT NOT NULL,
  repeats         INTEGER NOT NULL DEFAULT 1 CHECK (repeats BETWEEN 1 AND 20),
  summary         TEXT NOT NULL DEFAULT '{}',
  status          TEXT NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING','PASSED','FAILED','ERROR','CANCELLED')),
  report_artifact_id TEXT REFERENCES af_artifact(id),
  started_at      REAL NOT NULL,
  finished_at     REAL
);
CREATE INDEX IF NOT EXISTS af_eval_run_subject_idx ON af_eval_run (tenant_id, agent_version_id, suite);

CREATE TABLE IF NOT EXISTS af_eval_result (
  id          TEXT PRIMARY KEY,
  tenant_id   TEXT NOT NULL,
  eval_run_id TEXT NOT NULL REFERENCES af_eval_run(id),
  case_id     TEXT NOT NULL,
  repeat_no   INTEGER NOT NULL DEFAULT 1,
  mandatory   INTEGER NOT NULL DEFAULT 0,
  passed      INTEGER NOT NULL,
  score       REAL,
  checks      TEXT NOT NULL DEFAULT '[]',
  trace_id    TEXT,
  latency_ms  INTEGER,
  tokens      INTEGER,
  cost_usd    REAL,
  UNIQUE (eval_run_id, case_id, repeat_no)
);

CREATE TABLE IF NOT EXISTS af_finding (
  id            TEXT PRIMARY KEY,
  tenant_id     TEXT NOT NULL,
  agent_version_id TEXT NOT NULL REFERENCES af_agent_version(id),
  source        TEXT NOT NULL,
  severity      TEXT NOT NULL CHECK (severity IN ('critical','high','medium','low','info')),
  title         TEXT NOT NULL,
  detail        TEXT NOT NULL DEFAULT '{}',
  status        TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','FIXED','WAIVED','FALSE_POSITIVE')),
  waiver_approval_id TEXT,
  created_at    REAL NOT NULL,
  resolved_at   REAL
);
CREATE INDEX IF NOT EXISTS af_finding_open_idx ON af_finding (tenant_id, agent_version_id);

CREATE TABLE IF NOT EXISTS af_certification (
  id              TEXT PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  subject_kind    TEXT NOT NULL CHECK (subject_kind IN ('agent_version','team')),
  agent_version_id TEXT REFERENCES af_agent_version(id),
  batch_id        TEXT REFERENCES af_batch(id),
  gate_policy_version TEXT NOT NULL,
  gate_results    TEXT NOT NULL,
  all_mandatory_passed INTEGER NOT NULL,
  bundle_artifact_id TEXT NOT NULL REFERENCES af_artifact(id),
  evidence_ledger_ref TEXT NOT NULL,
  issued_by       TEXT NOT NULL,
  issued_at       REAL NOT NULL,
  expires_at      REAL
);

-- ---------- 6. release, team, bindings, assignment, runtime -----------------
CREATE TABLE IF NOT EXISTS af_release (
  id               TEXT PRIMARY KEY,
  tenant_id        TEXT NOT NULL,
  subject_kind     TEXT NOT NULL CHECK (subject_kind IN ('agent_version','team')),
  agent_version_id TEXT REFERENCES af_agent_version(id),
  batch_id         TEXT REFERENCES af_batch(id),
  certification_id TEXT NOT NULL REFERENCES af_certification(id),
  approval_id      TEXT,
  submitted_by     TEXT NOT NULL,
  decision         TEXT NOT NULL DEFAULT 'PENDING' CHECK (decision IN ('PENDING','APPROVED','REJECTED','EXPIRED','REVOKED')),
  decided_by_principal TEXT,
  decided_at       REAL,
  channel          TEXT NOT NULL DEFAULT 'production' CHECK (channel IN ('staging','canary','production')),
  rollback_of_release_id TEXT REFERENCES af_release(id),
  created_at       REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS af_team (
  id            TEXT PRIMARY KEY,
  tenant_id     TEXT NOT NULL,
  company_id    TEXT NOT NULL,
  batch_id      TEXT REFERENCES af_batch(id),
  name          TEXT NOT NULL,
  department    TEXT,
  supervisor_agent_id TEXT REFERENCES af_agent(id),
  version       INTEGER NOT NULL DEFAULT 1,
  manifest_artifact_id TEXT REFERENCES af_artifact(id),
  lifecycle     TEXT NOT NULL DEFAULT 'DRAFT' CHECK (lifecycle IN ('DRAFT','CERTIFIED','PUBLISHED','ACTIVE','SUSPENDED','RETIRED')),
  UNIQUE (tenant_id, company_id, name, version)
);

CREATE TABLE IF NOT EXISTS af_team_member (
  id            TEXT PRIMARY KEY,
  tenant_id     TEXT NOT NULL,
  team_id       TEXT NOT NULL REFERENCES af_team(id),
  agent_id      TEXT NOT NULL REFERENCES af_agent(id),
  agent_version_id TEXT NOT NULL REFERENCES af_agent_version(id),
  role_in_team  TEXT NOT NULL CHECK (role_in_team IN ('supervisor','specialist','reporter','shared_service')),
  reports_to_agent_id TEXT REFERENCES af_agent(id),
  max_delegation_depth INTEGER NOT NULL DEFAULT 2 CHECK (max_delegation_depth BETWEEN 0 AND 5),
  UNIQUE (team_id, agent_id)
);

CREATE TABLE IF NOT EXISTS af_tool_binding (
  id               TEXT PRIMARY KEY,
  tenant_id        TEXT NOT NULL,
  agent_version_id TEXT NOT NULL REFERENCES af_agent_version(id),
  binding_kind     TEXT NOT NULL CHECK (binding_kind IN ('builtin_tool','mcp_server','mcp_tool','a2a_peer','knowledge_collection','memory_store','database_view')),
  target_ref       TEXT NOT NULL,
  scopes           TEXT NOT NULL DEFAULT '[]',
  constraints      TEXT NOT NULL DEFAULT '{}',
  grant_approval_id TEXT,
  secret_refs      TEXT NOT NULL DEFAULT '[]',
  UNIQUE (agent_version_id, binding_kind, target_ref)
);

CREATE TABLE IF NOT EXISTS af_assignment (
  id              TEXT PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  company_id      TEXT NOT NULL,
  agent_id        TEXT NOT NULL REFERENCES af_agent(id),
  agent_version_id TEXT NOT NULL REFERENCES af_agent_version(id),
  assignee_kind   TEXT NOT NULL CHECK (assignee_kind IN ('ai_employee','department','team','assistant')),
  assignee_id     TEXT NOT NULL,
  assigned_by     TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REASSIGNED','REVOKED')),
  created_at      REAL NOT NULL,
  ended_at        REAL
);

CREATE TABLE IF NOT EXISTS af_runtime_instance (
  id              TEXT PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  agent_id        TEXT NOT NULL REFERENCES af_agent(id),
  agent_version_id TEXT NOT NULL REFERENCES af_agent_version(id),
  channel         TEXT NOT NULL CHECK (channel IN ('staging','canary','production')),
  traffic_percent INTEGER NOT NULL DEFAULT 100 CHECK (traffic_percent BETWEEN 0 AND 100),
  runtime_ref     TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'STARTING' CHECK (status IN ('STARTING','RUNNING','SUSPENDED','STOPPED','FAILED','KILLED')),
  started_at      REAL NOT NULL,
  stopped_at      REAL
);

-- ---------- 7. lifecycle, feedback, quotas ----------------------------------
CREATE TABLE IF NOT EXISTS af_lifecycle_event (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id     TEXT NOT NULL,
  subject_kind  TEXT NOT NULL,
  subject_id    TEXT NOT NULL,
  from_state    TEXT,
  to_state      TEXT NOT NULL,
  actor         TEXT NOT NULL,
  reason        TEXT,
  evidence_ledger_id TEXT NOT NULL,
  correlation_id TEXT,
  created_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS af_lifecycle_subject_idx ON af_lifecycle_event (tenant_id, subject_kind, subject_id, id);

CREATE TABLE IF NOT EXISTS af_feedback (
  id            TEXT PRIMARY KEY,
  tenant_id     TEXT NOT NULL,
  agent_id      TEXT NOT NULL REFERENCES af_agent(id),
  agent_version_id TEXT REFERENCES af_agent_version(id),
  from_principal TEXT NOT NULL,
  rating        INTEGER CHECK (rating BETWEEN 1 AND 5),
  category      TEXT CHECK (category IN ('quality','speed','safety','cost','missing_capability','other')),
  comment       TEXT,
  task_ref      TEXT,
  created_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS af_quota_usage (
  tenant_id     TEXT NOT NULL,
  period        TEXT NOT NULL,
  metric        TEXT NOT NULL CHECK (metric IN ('builds','agents_published','tokens','cost_usd','sandbox_seconds','concurrent_builds')),
  used          REAL NOT NULL DEFAULT 0.0,
  limit_value   REAL NOT NULL,
  PRIMARY KEY (tenant_id, period, metric)
);

-- ---------- SQLite Triggers: Immutability -----------------------------------
CREATE TRIGGER IF NOT EXISTS af_artifact_immutable_u BEFORE UPDATE ON af_artifact
BEGIN
  SELECT RAISE(ABORT, 'af: table af_artifact is immutable (UPDATE blocked)');
END;

CREATE TRIGGER IF NOT EXISTS af_artifact_immutable_d BEFORE DELETE ON af_artifact
BEGIN
  SELECT RAISE(ABORT, 'af: table af_artifact is immutable (DELETE blocked)');
END;

CREATE TRIGGER IF NOT EXISTS af_certification_immutable_u BEFORE UPDATE ON af_certification
BEGIN
  SELECT RAISE(ABORT, 'af: table af_certification is immutable (UPDATE blocked)');
END;

CREATE TRIGGER IF NOT EXISTS af_certification_immutable_d BEFORE DELETE ON af_certification
BEGIN
  SELECT RAISE(ABORT, 'af: table af_certification is immutable (DELETE blocked)');
END;

CREATE TRIGGER IF NOT EXISTS af_lifecycle_immutable_u BEFORE UPDATE ON af_lifecycle_event
BEGIN
  SELECT RAISE(ABORT, 'af: table af_lifecycle_event is immutable (UPDATE blocked)');
END;

CREATE TRIGGER IF NOT EXISTS af_lifecycle_immutable_d BEFORE DELETE ON af_lifecycle_event
BEGIN
  SELECT RAISE(ABORT, 'af: table af_lifecycle_event is immutable (DELETE blocked)');
END;

CREATE TRIGGER IF NOT EXISTS af_eval_result_immutable_u BEFORE UPDATE ON af_eval_result
BEGIN
  SELECT RAISE(ABORT, 'af: table af_eval_result is immutable (UPDATE blocked)');
END;

CREATE TRIGGER IF NOT EXISTS af_eval_result_immutable_d BEFORE DELETE ON af_eval_result
BEGIN
  SELECT RAISE(ABORT, 'af: table af_eval_result is immutable (DELETE blocked)');
END;

-- ---------- SQLite Triggers: Freeze Agent Version ---------------------------
CREATE TRIGGER IF NOT EXISTS af_agent_version_freeze_d BEFORE DELETE ON af_agent_version
BEGIN
  SELECT RAISE(ABORT, 'af: agent versions are never deleted (withdraw instead)');
END;

CREATE TRIGGER IF NOT EXISTS af_agent_version_freeze_u BEFORE UPDATE ON af_agent_version
WHEN OLD.status != 'BUILDING' AND (
  NEW.spec != OLD.spec OR NEW.spec_sha256 != OLD.spec_sha256 OR
  NEW.permission_profile != OLD.permission_profile OR NEW.risk_tier != OLD.risk_tier
)
BEGIN
  SELECT RAISE(ABORT, 'af: agent version is frozen once it leaves BUILDING');
END;

-- ---------- SQLite Triggers: Prevent Self-Approval & Enforce Gates ----------
CREATE TRIGGER IF NOT EXISTS af_release_freeze_after_decision BEFORE UPDATE ON af_release
WHEN OLD.decision != 'PENDING'
BEGIN
  SELECT RAISE(ABORT, 'af: release already decided (cannot be mutated)');
END;

CREATE TRIGGER IF NOT EXISTS af_release_approval_checks BEFORE UPDATE OF decision ON af_release
WHEN NEW.decision = 'APPROVED' AND (NEW.decided_by_principal IS NULL OR NEW.approval_id IS NULL)
BEGIN
  SELECT RAISE(ABORT, 'af: approval requires decided_by_principal and ApprovalEngine approval_id');
END;

CREATE TRIGGER IF NOT EXISTS af_release_self_approval_block BEFORE UPDATE OF decision ON af_release
WHEN NEW.decision = 'APPROVED' AND NEW.decided_by_principal IN (
  SELECT r.requester_principal_id FROM af_request r JOIN af_batch b ON b.request_id = r.id
  WHERE b.id = NEW.batch_id OR b.id IN (SELECT bi.batch_id FROM af_batch_item bi WHERE bi.agent_version_id = NEW.agent_version_id)
)
BEGIN
  SELECT RAISE(ABORT, 'af: requester cannot approve own release');
END;

-- ---------- SQLite Triggers: Independent QA Evaluator != Builder -----------
CREATE TRIGGER IF NOT EXISTS af_eval_independence_block BEFORE INSERT ON af_eval_run
WHEN NEW.phase = 'independent_qa' AND NEW.agent_version_id IS NOT NULL AND NEW.evaluator_principal IN (
  SELECT created_by FROM af_agent_version WHERE id = NEW.agent_version_id
)
BEGIN
  SELECT RAISE(ABORT, 'af: independent QA evaluator must differ from builder');
END;
