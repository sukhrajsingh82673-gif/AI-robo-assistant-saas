-- Behavioural verification of 001_agent_factory_core.sql. Run as superuser on a scratch database:
--   psql -v ON_ERROR_STOP=1 -d scratch -f 001_agent_factory_core.sql -f 001_verify.sql
-- Every check prints PASS or raises. OpenCode must re-run this against the repo's real migration output.
\set ON_ERROR_STOP on
DROP ROLE IF EXISTS af_app;
CREATE ROLE af_app NOLOGIN;
GRANT USAGE ON SCHEMA public TO af_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO af_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO af_app;

CREATE TEMP TABLE _ids(k text PRIMARY KEY, v uuid);
GRANT ALL ON _ids TO af_app;
SET ROLE af_app;

-- tenants A and B
\set A '''aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'''
\set B '''bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'''
\set CO '''cccccccc-cccc-cccc-cccc-cccccccccccc'''
\set REQ '''11111111-1111-1111-1111-111111111111'''
\set APR '''22222222-2222-2222-2222-222222222222'''

-- 1. RLS: tenant A writes, tenant B cannot see
SET zonata.tenant_id = :A;
INSERT INTO af_request(tenant_id, company_id, requester_principal_id, requester_kind, mode, natural_language, idempotency_key)
VALUES (:A, :CO, :REQ, 'ai_employee', 'single', 'Build a market research agent', 'idem-1');
SET zonata.tenant_id = :B;
DO $$ BEGIN
  IF (SELECT count(*) FROM af_request) <> 0 THEN RAISE EXCEPTION 'FAIL rls-read: tenant B sees tenant A rows'; END IF;
  RAISE NOTICE 'PASS rls-read: tenant B sees 0 rows of tenant A';
END $$;

-- 2. RLS: cross-tenant write is rejected
DO $$ BEGIN
  BEGIN
    INSERT INTO af_request(tenant_id, company_id, requester_principal_id, requester_kind, mode, natural_language, idempotency_key)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','cccccccc-cccc-cccc-cccc-cccccccccccc','11111111-1111-1111-1111-111111111111','ai_employee','single','Cross tenant insert attempt','idem-x');
    RAISE EXCEPTION 'FAIL rls-write: cross-tenant insert allowed';
  EXCEPTION WHEN insufficient_privilege OR check_violation THEN
    RAISE NOTICE 'PASS rls-write: cross-tenant insert rejected';
  END;
END $$;

-- 3. No tenant context => zero rows (fail closed)
RESET zonata.tenant_id;
DO $$ BEGIN
  IF (SELECT count(*) FROM af_request) <> 0 THEN RAISE EXCEPTION 'FAIL rls-fail-closed'; END IF;
  RAISE NOTICE 'PASS rls-fail-closed: no tenant context sees nothing';
END $$;

-- build a chain as tenant A
SET zonata.tenant_id = :A;
INSERT INTO af_agent(tenant_id, company_id, slug, display_name, role_title, category, owner_principal_id, agent_principal_id)
VALUES (:A, :CO, 'market-research', 'Market Research Agent', 'Market Researcher', 'research', :REQ, gen_random_uuid());
INSERT INTO af_agent_version(tenant_id, agent_id, semver, spec, spec_sha256, capability_profile, permission_profile, risk_tier, created_by)
SELECT :A, id, '1.0.0', '{"k":1}', 'abc', '{}', '{}', 'R1', 'factory.agent_developer' FROM af_agent WHERE slug='market-research';

-- 4. agent version frozen after leaving BUILDING
UPDATE af_agent_version SET status='BUILT';
DO $$ BEGIN
  BEGIN
    UPDATE af_agent_version SET spec='{"k":2}';
    RAISE EXCEPTION 'FAIL freeze: spec mutated after BUILT';
  EXCEPTION WHEN integrity_constraint_violation THEN
    RAISE NOTICE 'PASS freeze: spec immutable after BUILT';
  END;
  BEGIN
    UPDATE af_agent_version SET permission_profile='{"admin":true}';
    RAISE EXCEPTION 'FAIL self-grant: permission_profile mutated after BUILT';
  EXCEPTION WHEN integrity_constraint_violation THEN
    RAISE NOTICE 'PASS self-grant: permission_profile immutable after BUILT';
  END;
  BEGIN
    DELETE FROM af_agent_version;
    RAISE EXCEPTION 'FAIL delete: version deleted';
  EXCEPTION WHEN integrity_constraint_violation THEN
    RAISE NOTICE 'PASS no-delete: agent versions cannot be deleted';
  END;
END $$;

-- 5. artifacts / certifications immutable
INSERT INTO af_artifact(tenant_id, kind, sha256, size_bytes, storage_uri, created_by)
VALUES (:A, 'certification_bundle', 'deadbeef', 10, 's3://b/t/a/deadbeef', 'factory.certification_manager');
DO $$ BEGIN
  BEGIN
    UPDATE af_artifact SET sha256='feed';
    RAISE EXCEPTION 'FAIL artifact-immutable';
  EXCEPTION WHEN integrity_constraint_violation THEN RAISE NOTICE 'PASS artifact-immutable'; END;
END $$;

INSERT INTO af_certification(tenant_id, subject_kind, agent_version_id, gate_policy_version, gate_results, all_mandatory_passed, bundle_artifact_id, evidence_ledger_ref, issued_by)
SELECT :A, 'agent_version', v.id, '1.0.0', '[]', true, a.id, 'ledger:1', 'factory.certification_manager'
FROM af_agent_version v, af_artifact a LIMIT 1;
DO $$ BEGIN
  BEGIN
    UPDATE af_certification SET all_mandatory_passed=false;
    RAISE EXCEPTION 'FAIL cert-immutable';
  EXCEPTION WHEN integrity_constraint_violation THEN RAISE NOTICE 'PASS cert-immutable'; END;
END $$;

-- 6. self-approval blocked: requester 1111.. is the batch's request owner
INSERT INTO af_batch(tenant_id, company_id, request_id, agent_count, dependency_graph, manifest_sha256)
SELECT :A, :CO, id, 1, '{"nodes":["market_research"],"edges":[]}', 'm1' FROM af_request;
INSERT INTO af_requirement_spec(tenant_id, request_id, version, body, body_sha256, authored_by)
SELECT :A, id, 1, '{}', 'x', 'factory.requirement_analyst' FROM af_request;
INSERT INTO af_batch_item(tenant_id, batch_id, agent_key, role_title, requirement_spec_id, agent_version_id)
SELECT :A, b.id, 'market_research', 'Market Researcher', s.id, v.id FROM af_batch b, af_requirement_spec s, af_agent_version v;
DO $$
DECLARE cert uuid; BEGIN
  SELECT id INTO cert FROM af_certification LIMIT 1;
  BEGIN
    INSERT INTO af_release(tenant_id, subject_kind, agent_version_id, certification_id, approval_id, submitted_by, decision, decided_by_principal)
    SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','agent_version', v.id, cert, '22222222-2222-2222-2222-222222222222','factory.release_manager','APPROVED','11111111-1111-1111-1111-111111111111'
    FROM af_agent_version v;
    RAISE EXCEPTION 'FAIL self-approval: requester approved own release';
  EXCEPTION WHEN integrity_constraint_violation THEN RAISE NOTICE 'PASS self-approval blocked at DB layer'; END;
  -- a different approver succeeds
  INSERT INTO af_release(tenant_id, subject_kind, agent_version_id, certification_id, approval_id, submitted_by, decision, decided_by_principal)
  SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','agent_version', v.id, cert, '22222222-2222-2222-2222-222222222222','factory.release_manager','APPROVED','33333333-3333-3333-3333-333333333333'
  FROM af_agent_version v;
  RAISE NOTICE 'PASS release approved by a different principal';
  -- approval without ApprovalEngine id rejected
  BEGIN
    INSERT INTO af_release(tenant_id, subject_kind, agent_version_id, certification_id, submitted_by, decision, decided_by_principal)
    SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','agent_version', v.id, cert,'factory.release_manager','APPROVED','33333333-3333-3333-3333-333333333333' FROM af_agent_version v;
    RAISE EXCEPTION 'FAIL approval-without-engine-id';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM LIKE 'FAIL%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS approval requires ApprovalEngine approval_id';
  END;
END $$;
DO $$ BEGIN
  BEGIN
    UPDATE af_release SET decision='REVOKED';
    RAISE EXCEPTION 'FAIL release-immutable';
  EXCEPTION WHEN integrity_constraint_violation THEN RAISE NOTICE 'PASS decided release is immutable'; END;
END $$;

-- 7. independent QA evaluator must differ from builder
DO $$ BEGIN
  BEGIN
    INSERT INTO af_eval_run(tenant_id, subject_kind, agent_version_id, suite, phase, evaluator_principal, dataset_ref, dataset_sha256, model_profile)
    SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','agent_version', id,'functional','independent_qa','factory.agent_developer','ds@1','h','standard' FROM af_agent_version;
    RAISE EXCEPTION 'FAIL eval-independence';
  EXCEPTION WHEN integrity_constraint_violation THEN RAISE NOTICE 'PASS builder cannot be the independent evaluator'; END;
  INSERT INTO af_eval_run(tenant_id, subject_kind, agent_version_id, suite, phase, evaluator_principal, dataset_ref, dataset_sha256, model_profile)
  SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','agent_version', id,'functional','independent_qa','factory.qa_director','ds@1','h','standard' FROM af_agent_version;
  RAISE NOTICE 'PASS distinct evaluator accepted';
END $$;

-- 8. platform-global templates: readable by tenants, not writable
RESET ROLE;
INSERT INTO af_template(tenant_id, name, category, default_risk_tier) VALUES (NULL, 'research-agent', 'research', 'R1');
SET ROLE af_app;
SET zonata.tenant_id = :B;
DO $$ BEGIN
  IF (SELECT count(*) FROM af_template WHERE name='research-agent') <> 1 THEN RAISE EXCEPTION 'FAIL global-template-read'; END IF;
  RAISE NOTICE 'PASS global template readable by tenant B';
  BEGIN
    UPDATE af_template SET status='WITHDRAWN' WHERE name='research-agent';
    IF FOUND THEN RAISE EXCEPTION 'FAIL global-template-write'; END IF;
    RAISE NOTICE 'PASS global template not writable by tenant (0 rows updated)';
  EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'PASS global template write blocked'; END;
END $$;

-- 9. idempotency uniqueness
SET zonata.tenant_id = :A;
DO $$ BEGIN
  BEGIN
    INSERT INTO af_request(tenant_id, company_id, requester_principal_id, requester_kind, mode, natural_language, idempotency_key)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa','cccccccc-cccc-cccc-cccc-cccccccccccc','11111111-1111-1111-1111-111111111111','ai_employee','single','Duplicate idempotent request','idem-1');
    RAISE EXCEPTION 'FAIL idempotency';
  EXCEPTION WHEN unique_violation THEN RAISE NOTICE 'PASS idempotency key unique per tenant'; END;
END $$;
RESET ROLE;
