/**
 * Settings V2 UI contract tests.
 *
 * The console is vanilla JS with no build step, so these tests exercise the
 * pure decision functions that decide what a user may see and do:
 *
 *   - the four required state labels (Default / Inherited / Overridden / Locked)
 *   - no control for a non-live definition (the anti-decorative rule)
 *   - the real scope parameters sent to the resolver
 *   - optimistic concurrency on writes and resets
 *
 * No DOM is required.  Browser rendering is verified separately against a
 * running server.
 */

const assert = require('assert');
const path = require('path');

const SettingsV2 = require(path.join(__dirname, '..', 'web', 'settings_v2.js'));
const t = SettingsV2._test;

let passed = 0;
function test(name, fn) {
  fn();
  passed += 1;
  console.log('  ok  ' + name);
}

console.log('Settings V2 UI contract');

test('labels Default, Inherited, Overridden, and Locked exactly', () => {
  assert.strictEqual(
    t.pillFor({ source_scope: 'platform', source_id: 'default', provenance: 'Platform default' }).label,
    'Default'
  );
  assert.strictEqual(
    t.pillFor({ source_scope: 'organization', source_id: 't1', provenance: 'Inherited from Organization' }).label,
    'Inherited'
  );
  assert.strictEqual(
    t.pillFor({ source_scope: 'company', source_id: 'c1', overridden_here: true }).label,
    'Overridden'
  );
  assert.strictEqual(
    t.pillFor({ is_locked: true, locked_by_scope: 'company', locked_by_id: 'c1' }).label,
    'Locked'
  );
});

test('lock provenance names the locking scope, not the viewing scope', () => {
  const pill = t.pillFor({ is_locked: true, locked_by_scope: 'organization', locked_by_id: 't1' });
  assert.strictEqual(pill.kind, 'locked');
  assert.ok(pill.detail.indexOf('Organization') !== -1);
});

test('a held value beats the inherited label only at the viewed scope', () => {
  assert.strictEqual(t.pillFor({ source_scope: 'department', source_id: 'd1' }).label, 'Inherited');
  assert.strictEqual(
    t.pillFor({ source_scope: 'department', source_id: 'd1', overridden_here: true }).label,
    'Overridden'
  );
});

test('coming_soon renders no control', () => {
  assert.strictEqual(
    t.controlKindFor({ status: 'coming_soon', type: 'toggle' }),
    'none'
  );
});

test('hidden is not a control either', () => {
  assert.strictEqual(t.controlKindFor({ status: 'hidden', type: 'status' }), 'none');
});

test('live definitions map to real controls', () => {
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'toggle' }), 'toggle');
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'select' }), 'select');
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'radio' }), 'select');
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'number' }), 'number');
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'currency' }), 'number');
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'slider' }), 'slider');
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'text' }), 'text');
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'multiselect' }), 'multiselect');
  assert.strictEqual(t.controlKindFor({ status: 'live', type: 'token', secret: true }), 'secret');
});

test('secret definitions always use the write-only renderer', () => {
  assert.strictEqual(
    t.controlKindFor({ status: 'coming_soon', type: 'text', secret: true }),
    'secret'
  );
});

test('only sections 1-6 are marked ready', () => {
  assert.deepStrictEqual(t.READY_SECTIONS, [
    'general_organization',
    'companies',
    'team_access',
    'ai_agents_employees',
    'spending_budgets',
    'integrations'
  ]);
});

test('routes resolve to a section without swallowing the legacy route', () => {
  assert.strictEqual(t.parseRoute('#/settings-v2/ai_agents_employees').section, 'ai_agents_employees');
  assert.strictEqual(t.parseRoute('/workspace/settings-v2/companies').section, 'companies');
  assert.strictEqual(t.parseRoute('#/settings-v2').section, '');
  assert.strictEqual(t.parseRoute('#/settings/ai_providers').section, 'ai_providers');
});

test('scope queries send the real id for every scope', () => {
  assert.strictEqual(
    t.buildScopeQuery({ type: 'company', id: 'c1' }, 'c1', 't1', 'u1'),
    'scope=company&company_id=c1'
  );
  assert.strictEqual(
    t.buildScopeQuery({ type: 'organization', id: 't1' }, 'c1', 't1', 'u1'),
    'scope=organization&company_id=c1'
  );
  assert.strictEqual(
    t.buildScopeQuery({ type: 'department', id: 'd1' }, 'c1', 't1', 'u1'),
    'scope=department&company_id=c1&department_id=d1'
  );
  assert.strictEqual(
    t.buildScopeQuery({ type: 'agent', id: 'a1' }, 'c1', 't1', 'u1'),
    'scope=agent&company_id=c1&agent_id=a1'
  );
  assert.strictEqual(
    t.buildScopeQuery({ type: 'user', id: 'u1' }, 'c1', 't1', 'u1'),
    'scope=user&company_id=c1&user_id=u1'
  );
});

test('a write creates at version 0 when the value is inherited', () => {
  const payload = t.buildWritePayload(
    { key: 'llm_model', overridden_here: false, version: 7 },
    'gpt-x',
    { type: 'company', id: 'c1' },
    'c1'
  );
  assert.deepStrictEqual(payload, {
    key: 'llm_model',
    value: 'gpt-x',
    scope_type: 'company',
    scope_id: 'c1',
    company_id: 'c1',
    expected_version: 0,
    reason: 'Changed from the Settings V2 console.'
  });
});

test('a write uses the local row version when overridden', () => {
  const payload = t.buildWritePayload(
    { key: 'llm_model', overridden_here: true, version: 7 },
    'gpt-x',
    { type: 'company', id: 'c1' },
    'c1'
  );
  assert.strictEqual(payload.expected_version, 7);
});

test('groups keep category order and attach resolved rows', () => {
  const definitions = [
    { key: 'b', category: 'second' },
    { key: 'a', category: 'first' },
    { key: 'c', category: 'first' }
  ];
  const values = [{ key: 'a', value: 1 }];
  const groups = t.groupByCategory(
    definitions,
    values,
    [{ id: 'first' }, { id: 'second' }]
  );
  assert.deepStrictEqual(groups.map((group) => group.id), ['first', 'second']);
  assert.deepStrictEqual(groups[0].rows.map((row) => row.definition.key), ['a', 'c']);
  assert.strictEqual(groups[0].rows[0].row.value, 1);
  assert.strictEqual(groups[0].rows[1].row, null);
});

test('formatValue is human-readable but never invents a value', () => {
  assert.strictEqual(t.formatValue({ value: true }), 'On');
  assert.strictEqual(t.formatValue({ value: false }), 'Off');
  assert.strictEqual(t.formatValue({ value: ['a', 'b'] }), 'a, b');
  assert.strictEqual(t.formatValue({ value: null }), '—');
  assert.strictEqual(t.formatValue({ value: 5 }, { unit: 'min' }), '5 min');
  assert.strictEqual(
    t.formatValue({ secret: true, secret_metadata: { configured: false } }),
    'Not configured'
  );
  assert.strictEqual(
    t.formatValue({ secret: true, secret_metadata: { configured: true, last4: '1234' } }),
    'Configured ····1234'
  );
});

test('a short secret never renders a last4 hint', () => {
  assert.strictEqual(
    t.formatValue({ secret: true, secret_metadata: { configured: true, last4: '' } }),
    'Configured'
  );
});

// ---------------------------------------------------------------------------
// Rendered row contract (string-level; no DOM needed)
// ---------------------------------------------------------------------------
const st = SettingsV2._state;

function definition(overrides) {
  return Object.assign(
    {
      key: 'wf_max_concurrent_agents',
      label: 'Max concurrent agents',
      description: 'Hard ceiling for concurrent agent execution.',
      status: 'live',
      type: 'number',
      risk: 'MEDIUM',
      allowed_scopes: ['company', 'department', 'agent'],
      legacy_scope: 'Company',
      enforced_by: 'core.agent_factory_runtime',
      requires_restart: false,
      required_permission: 'agents.manage',
      validation: { min: 1, max: 64, integer: true, options: [] },
      unit: '',
      secret: false,
      default: 8
    },
    overrides || {}
  );
}

function configure(overrides) {
  state_set({
    capabilities: {
      can_write: true,
      can_lock: true,
      can_manage_secrets: true,
      permissions: [
        'settings.read',
        'settings.write',
        'settings.lock',
        'secrets.manage',
        'agents.manage'
      ]
    },
    scope: { type: 'company', id: 'c1' },
    busy: {},
    pendingRevoke: ''
  }, overrides);
}

function state_set(base, overrides) {
  Object.keys(st).forEach(function (key) {
    if (!(key in base)) return;
    st[key] = base[key];
  });
  Object.keys(overrides || {}).forEach(function (key) {
    st[key] = overrides[key];
  });
}

test('a live writable number renders a real input', () => {
  configure();
  const html = t.rowHtml(definition(), {
    key: 'wf_max_concurrent_agents',
    value: 12,
    status: 'live',
    source_scope: 'company',
    source_id: 'c1',
    overridden_here: true,
    version: 3,
    allowed_scopes: ['company', 'department', 'agent']
  });
  assert.ok(html.indexOf('type="number"') !== -1, html);
  assert.ok(html.indexOf('Reset to inherited') !== -1, html);
  assert.ok(html.indexOf('Overridden') !== -1, html);
  assert.ok(html.indexOf('Not configurable') === -1, html);
});

test('a coming_soon toggle renders no switch and no input', () => {
  configure();
  const html = t.rowHtml(definition({ status: 'coming_soon', type: 'toggle' }), {
    key: 'wf_max_concurrent_agents',
    value: false,
    status: 'coming_soon',
    source_scope: 'platform',
    source_id: 'default'
  });
  assert.ok(html.indexOf('Not configurable here.') !== -1, html);
  assert.ok(html.indexOf('role="switch"') === -1, html);
  assert.ok(html.indexOf('<input') === -1, html);
});

test('a locked value is read-only and names the locking scope', () => {
  configure();
  const html = t.rowHtml(definition(), {
    key: 'wf_max_concurrent_agents',
    value: 12,
    status: 'live',
    source_scope: 'organization',
    source_id: 't1',
    is_locked: true,
    locked_by_scope: 'organization',
    locked_by_id: 't1',
    version: 4,
    allowed_scopes: ['company', 'department', 'agent']
  });
  assert.ok(html.indexOf('Locked by') !== -1, html);
  assert.ok(html.indexOf('<input') === -1, html);
  assert.ok(html.indexOf('Unlock') === -1, html);
});

test('an observer gets read-only text, not a dead control', () => {
  configure({
    capabilities: {
      can_write: false,
      can_lock: false,
      can_manage_secrets: false,
      permissions: ['settings.read']
    }
  });
  const html = t.rowHtml(definition(), {
    key: 'wf_max_concurrent_agents',
    value: 12,
    status: 'live',
    source_scope: 'company',
    source_id: 'c1',
    overridden_here: true,
    version: 2,
    allowed_scopes: ['company', 'department', 'agent']
  });
  assert.ok(html.indexOf('Your role cannot write settings.') !== -1, html);
  assert.ok(html.indexOf('<input') === -1, html);
  assert.ok(html.indexOf('Reset to inherited') === -1, html);
});

test('an inherited value offers no reset, an overridden one does', () => {
  configure();
  const inherited = t.rowHtml(definition(), {
    key: 'wf_max_concurrent_agents',
    value: 12,
    status: 'live',
    source_scope: 'organization',
    source_id: 't1',
    overridden_here: false,
    version: 2,
    allowed_scopes: ['company', 'department', 'agent']
  });
  assert.ok(inherited.indexOf('Reset to inherited') === -1, inherited);
  assert.ok(inherited.indexOf('Inherited') !== -1, inherited);

  const overridden = t.rowHtml(definition(), {
    key: 'wf_max_concurrent_agents',
    value: 12,
    status: 'live',
    source_scope: 'company',
    source_id: 'c1',
    overridden_here: true,
    version: 2,
    allowed_scopes: ['company', 'department', 'agent']
  });
  assert.ok(overridden.indexOf('Reset to inherited') !== -1, overridden);
});

test('a secret is password-only for a secret manager', () => {
  configure();
  const html = t.rowHtml(
    definition({ key: 'llm_api_key', label: 'Provider API key', type: 'token', secret: true }),
    {
      key: 'llm_api_key',
      status: 'live',
      secret: true,
      source_scope: 'company',
      source_id: 'c1',
      secret_metadata: { configured: true, last4: '1234' }
    }
  );
  assert.ok(html.indexOf('type="password"') !== -1, html);
  assert.ok(html.indexOf('Rotate') !== -1, html);
  assert.ok(html.indexOf('Revoke') !== -1, html);
  assert.ok(html.indexOf('····1234') !== -1, html);
  // The plaintext is never placed in a value attribute.
  assert.ok(html.indexOf('value="Configured') === -1, html);
});

test('a reader without secrets.manage gets no secret input', () => {
  configure({
    capabilities: {
      can_write: true,
      can_lock: true,
      can_manage_secrets: false,
      permissions: ['settings.read', 'settings.write', 'settings.lock']
    }
  });
  const html = t.rowHtml(
    definition({ key: 'llm_api_key', label: 'Provider API key', type: 'token', secret: true }),
    {
      key: 'llm_api_key',
      status: 'live',
      secret: true,
      source_scope: 'company',
      source_id: 'c1',
      secret_metadata: { configured: true, last4: '' }
    }
  );
  assert.ok(html.indexOf('Requires secrets.manage to change.') !== -1, html);
  assert.ok(html.indexOf('type="password"') === -1, html);
  assert.ok(html.indexOf('<input') === -1, html);
});

test('labels and descriptions are escaped', () => {
  configure();
  const html = t.rowHtml(
    definition({
      label: '<img src=x onerror=alert(1)>',
      description: '"><script>alert(2)</script>'
    }),
    {
      key: 'wf_max_concurrent_agents',
      value: 1,
      status: 'live',
      source_scope: 'company',
      source_id: 'c1',
      overridden_here: true,
      version: 1,
      allowed_scopes: ['company']
    }
  );
  assert.ok(html.indexOf('<img src=x') === -1, html);
  assert.ok(html.indexOf('<script>') === -1, html);
  assert.ok(html.indexOf('&lt;img') !== -1, html);
});

console.log('\n' + passed + ' UI contract tests passed.');

