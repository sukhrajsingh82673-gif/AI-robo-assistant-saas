/**
 * ZONATA Settings V2 — enterprise settings console (preview).
 *
 * This module is additive.  The legacy console stays mounted at #/settings and
 * keeps working; the redesigned surface lives at #/settings-v2 and is wired to
 * /api/settings/v2 only.  Nothing here invents a control: a setting is editable
 * only when the registry marks it `live`, the caller holds its permission, the
 * current scope is allowed, and the value is not locked.
 *
 * Sections 1–6 are built.  Sections 7–16 show a migration panel that links back
 * to the legacy console instead of rendering a dead end.
 */

(function (root) {
  'use strict';

  const API = '/api/settings/v2';
  const DEFAULT_SECTION = 'general_organization';
  const READY_SECTIONS = [
    'general_organization',
    'companies',
    'team_access',
    'ai_agents_employees',
    'spending_budgets',
    'integrations'
  ];
  const SCOPE_ORDER = ['organization', 'company', 'department', 'agent', 'user'];
  const SCOPE_LABELS = {
    platform: 'Platform',
    organization: 'Organization',
    company: 'Company',
    department: 'Department',
    agent: 'Agent',
    user: 'User'
  };

  const state = {
    booted: false,
    booting: false,
    bootError: '',
    catalog: null,
    capabilities: {},
    sections: [],
    categories: [],
    allSettings: [],
    companies: [],
    departments: [],
    agents: [],
    tenantId: '',
    companyId: '',
    userId: '',
    scope: { type: 'company', id: '' },
    sectionId: DEFAULT_SECTION,
    values: [],
    valuesLoading: false,
    valuesError: '',
    valuesKey: '',
    valuesRequest: 0,
    query: '',
    statusFilter: 'all',
    scopeNotice: '',
    approvals: [],
    approvalsLoading: false,
    audit: [],
    auditLoading: false,
    auditVerification: null,
    drawer: null,
    busy: {},
    pendingRevoke: '',
    pendingFocus: '',
    lastError: ''
  };

  let rootEl = null;
  let eventsBound = false;
  let toastHost = null;

  // ------------------------------------------------------------------ helpers
  function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function scopeLabel(scope) {
    return SCOPE_LABELS[String(scope || '').toLowerCase()] || 'Platform';
  }

  function formatValue(row, definition) {
    if (row && row.secret) {
      const meta = row.secret_metadata || {};
      if (!meta.configured) return 'Not configured';
      return meta.last4 ? 'Configured ····' + meta.last4 : 'Configured';
    }
    const value = row ? row.value : definition ? definition.default : null;
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'boolean') return value ? 'On' : 'Off';
    if (Array.isArray(value)) return value.length ? value.join(', ') : '—';
    if (typeof value === 'object') return JSON.stringify(value);
    const unit = definition && definition.unit ? ' ' + definition.unit : '';
    return String(value) + unit;
  }

  /** The four state labels the console must show, plus secret/action variants. */
  function pillFor(row, definition) {
    if (row && row.secret) {
      const configured = !!(row.secret_metadata && row.secret_metadata.configured);
      return {
        kind: configured ? 'configured' : 'default',
        label: configured ? 'Configured' : 'Not configured',
        detail: configured ? 'Write-only credential' : 'No credential stored'
      };
    }
    if (row && row.status === 'action') {
      return { kind: 'action', label: 'Action', detail: 'Executable, not a value' };
    }
    if (row && row.status === 'coming_soon') {
      return { kind: 'soon', label: 'Coming soon', detail: 'No runtime reader yet' };
    }
    if (row && row.is_locked) {
      return {
        kind: 'locked',
        label: 'Locked',
        detail: row.locked_by_scope
          ? 'Locked by ' + scopeLabel(row.locked_by_scope)
          : 'Locked by a broader scope'
      };
    }
    if (row && row.overridden_here) {
      return {
        kind: 'overridden',
        label: 'Overridden',
        detail: 'Overridden at ' + scopeLabel(row.source_scope)
      };
    }
    if (
      row &&
      row.source_scope === 'platform' &&
      (row.source_id === 'default' || row.source_id === 'env')
    ) {
      return { kind: 'default', label: 'Default', detail: row.provenance || 'Platform default' };
    }
    return {
      kind: 'inherited',
      label: 'Inherited',
      detail: row && row.source_scope ? 'from ' + scopeLabel(row.source_scope) : 'Inherited'
    };
  }

  /** Which renderer a definition gets.  Non-live definitions get none. */
  function controlKindFor(definition) {
    if (!definition) return 'none';
    if (definition.secret) return 'secret';
    if (definition.status !== 'live') return 'none';
    switch (definition.type) {
      case 'toggle':
        return 'toggle';
      case 'select':
      case 'radio':
        return 'select';
      case 'number':
      case 'currency':
        return 'number';
      case 'slider':
        return 'slider';
      case 'multiselect':
        return 'multiselect';
      case 'text':
      case 'token':
        return 'text';
      default:
        return 'text';
    }
  }

  function parseRoute(route) {
    const raw = String(route || '').split('?')[0];
    const clean = raw.replace(/^#?\/?/, '').replace(/^workspace\//, '');
    const parts = clean.split('/').filter(Boolean);
    if (parts[0] !== 'settings-v2' && parts[0] !== 'settings') {
      return { section: '' };
    }
    return { section: parts[1] || '' };
  }

  function buildScopeQuery(scope, companyId, tenantId, userId) {
    const params = new URLSearchParams();
    params.set('scope', scope.type);
    params.set('company_id', companyId);
    if (scope.type === 'department') params.set('department_id', scope.id);
    if (scope.type === 'agent') params.set('agent_id', scope.id);
    if (scope.type === 'user') params.set('user_id', scope.id || userId);
    return params.toString();
  }

  function buildWritePayload(row, value, scope, companyId) {
    return {
      key: row.key,
      value: value,
      scope_type: scope.type,
      scope_id: scope.id,
      company_id: companyId,
      expected_version: row.overridden_here ? Number(row.version || 1) : 0,
      reason: 'Changed from the Settings V2 console.'
    };
  }

  function groupByCategory(definitions, values, categories) {
    const byKey = {};
    (values || []).forEach(function (row) {
      byKey[row.key] = row;
    });
    const order = (categories || []).map(function (category) {
      return category.id;
    });
    const groups = [];
    const index = {};
    (definitions || []).forEach(function (definition) {
      const id = definition.category;
      if (!index[id]) {
        index[id] = { id: id, rows: [] };
        groups.push(index[id]);
      }
      index[id].rows.push({ definition: definition, row: byKey[definition.key] || null });
    });
    groups.sort(function (a, b) {
      const ai = order.indexOf(a.id);
      const bi = order.indexOf(b.id);
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
    });
    return groups;
  }

  function permissionAllows(permission) {
    if (!permission) return true;
    return (state.capabilities.permissions || []).indexOf(permission) !== -1;
  }

  function hasRowAtScope(row) {
    return (
      row &&
      String(row.source_scope) === state.scope.type &&
      String(row.source_id) === String(state.scope.id)
    );
  }

  function canEditRow(row) {
    return !!(
      state.capabilities.can_write &&
      row &&
      row.status === 'live' &&
      !row.is_locked &&
      (row.allowed_scopes || []).indexOf(state.scope.type) !== -1 &&
      permissionAllows(row.required_permission)
    );
  }

  function canLockRow(row) {
    if (!state.capabilities.can_lock || !row || row.status !== 'live') return false;
    if (row.is_locked) {
      return (
        String(row.locked_by_scope) === state.scope.type &&
        String(row.locked_by_id) === String(state.scope.id)
      );
    }
    return hasRowAtScope(row);
  }

  function currentSection() {
    for (let i = 0; i < state.sections.length; i += 1) {
      if (state.sections[i].id === state.sectionId) return state.sections[i];
    }
    return state.sections[0] || { id: DEFAULT_SECTION, name: 'Settings', num: '—' };
  }

  function sectionSettings(sectionId) {
    return state.allSettings.filter(function (definition) {
      return definition.section === sectionId;
    });
  }

  function matchesQuery(definition, query) {
    if (!query) return true;
    const needle = query.toLowerCase();
    return (
      String(definition.label || '').toLowerCase().indexOf(needle) !== -1 ||
      String(definition.key || '').toLowerCase().indexOf(needle) !== -1 ||
      String(definition.description || '').toLowerCase().indexOf(needle) !== -1 ||
      String(definition.category || '').toLowerCase().indexOf(needle) !== -1
    );
  }

  function visibleRows() {
    return sectionSettings(state.sectionId).filter(function (definition) {
      if (state.statusFilter === 'live' && definition.status !== 'live') return false;
      if (state.statusFilter === 'soon' && definition.status !== 'coming_soon') return false;
      return matchesQuery(definition, state.query);
    });
  }

  // --------------------------------------------------------------------- http
  async function api(path, options) {
    const init = Object.assign({ headers: {} }, options || {});
    init.headers = Object.assign({ Accept: 'application/json' }, init.headers || {});
    if (init.body) init.headers['Content-Type'] = 'application/json';
    const response = await fetch(path, init);
    let payload = {};
    try {
      payload = await response.json();
    } catch (err) {
      payload = {};
    }
    if (!response.ok) {
      const error = new Error(payload.error || 'Request failed (' + response.status + ').');
      error.status = response.status;
      error.code = payload.code || '';
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  function toast(message, kind) {
    if (typeof document === 'undefined') return;
    if (!toastHost) {
      toastHost = document.createElement('div');
      toastHost.className = 'sz-toasts';
      toastHost.setAttribute('aria-live', 'polite');
      document.body.appendChild(toastHost);
    }
    const node = document.createElement('div');
    node.className = 'sz-toast sz-toast-' + (kind || 'info');
    node.textContent = message;
    toastHost.appendChild(node);
    window.setTimeout(function () {
      node.classList.add('is-leaving');
      window.setTimeout(function () {
        if (node.parentNode) node.parentNode.removeChild(node);
      }, 220);
    }, 3800);
  }

  // -------------------------------------------------------------------- boot
  function identity() {
    const host = (root.state && root.state.host) || {};
    let storedTenant = '';
    let storedCompany = '';
    try {
      storedTenant = root.localStorage ? root.localStorage.getItem('zonata_active_tenant_id') || '' : '';
      storedCompany = root.localStorage ? root.localStorage.getItem('zonata_active_company_id') || '' : '';
    } catch (err) {
      storedTenant = '';
      storedCompany = '';
    }
    return {
      tenantId: host.tenant_id || storedTenant || 'tnt_primary',
      companyId:
        (root.state && root.state.activeCompanyId) ||
        storedCompany ||
        host.company_id ||
        (state.companies[0] && state.companies[0].id) ||
        '',
      userId: host.user_id || host.userId || host.email || 'self'
    };
  }

  async function boot() {
    state.booting = true;
    state.bootError = '';
    paint();
    try {
      const results = await Promise.all([
        api(API + '/registry'),
        api('/api/companies').catch(function () {
          return { companies: [] };
        })
      ]);
      const payload = results[0] || {};
      const catalog = payload.registry || payload;
      state.catalog = catalog;
      state.capabilities = catalog.capabilities || {};
      state.sections = catalog.sections || [];
      state.categories = catalog.categories || [];
      state.allSettings = (catalog.settings || []).filter(function (definition) {
        return definition.status !== 'hidden';
      });
      state.companies = (results[1] && results[1].companies) || [];
      const ids = identity();
      state.tenantId = ids.tenantId;
      state.companyId = ids.companyId;
      state.userId = ids.userId;
      if (!state.sectionId || !state.sections.some(function (s) { return s.id === state.sectionId; })) {
        state.sectionId = state.sections[0] ? state.sections[0].id : DEFAULT_SECTION;
      }
      if (SCOPE_ORDER.indexOf(state.scope.type) === -1) state.scope.type = 'company';
      state.scope.id = scopeDefaultId(state.scope.type);
      state.booted = true;
      state.booting = false;
      paint();
      ensureValues();
      if (state.capabilities.can_read) {
        loadApprovals().catch(function () {});
      }
    } catch (err) {
      state.booting = false;
      state.bootError = err.status === 403
        ? 'Your role does not include settings.read. The console cannot load.'
        : err.message || 'Could not load the settings catalog.';
      paint();
    }
  }

  function scopeDefaultId(type) {
    if (type === 'organization') return state.tenantId;
    if (type === 'company') return state.companyId;
    if (type === 'department') {
      return state.departments[0] ? state.departments[0].department_id : '';
    }
    if (type === 'agent') {
      const first = state.agents[0];
      return first ? first.agent_id || first.id || '' : '';
    }
    if (type === 'user') return state.userId;
    return state.companyId;
  }

  async function ensureEntities(type) {
    if (type === 'department' && !state.departments.length) {
      const payload = await api(
        '/api/departments?company_id=' + encodeURIComponent(state.companyId)
      ).catch(function () {
        return { departments: [] };
      });
      state.departments = payload.departments || [];
    }
    if (type === 'agent' && !state.agents.length) {
      const payload = await api(
        '/api/agents/stateful?company_id=' + encodeURIComponent(state.companyId)
      ).catch(function () {
        return { agents: [] };
      });
      state.agents = payload.agents || [];
    }
  }

  // ------------------------------------------------------------------ values
  function valueScopeKey() {
    return state.sectionId + '|' + state.scope.type + '|' + state.scope.id + '|' + state.companyId;
  }

  function ensureValues(force) {
    if (!state.booted) return;
    if (READY_SECTIONS.indexOf(state.sectionId) === -1) return;
    if (
      (state.scope.type === 'department' || state.scope.type === 'agent') &&
      !state.scope.id
    ) {
      state.values = [];
      state.valuesLoading = false;
      state.valuesError = '';
      state.scopeNotice =
        'Select a ' + state.scope.type + ' for this company to view its effective values.';
      paint();
      return;
    }
    state.scopeNotice = '';
    const key = valueScopeKey();
    if (!force && state.valuesKey === key) return;
    if (!force && state.valuesLoading) return;
    state.valuesKey = key;
    state.valuesLoading = true;
    state.valuesError = '';
    const request = ++state.valuesRequest;
    paint();
    const query = buildScopeQuery(state.scope, state.companyId, state.tenantId, state.userId);
    api(API + '/values?section=' + encodeURIComponent(state.sectionId) + '&' + query)
      .then(function (payload) {
        if (request !== state.valuesRequest) return;
        state.values = payload.settings || [];
        state.valuesLoading = false;
        paint();
      })
      .catch(function (err) {
        if (request !== state.valuesRequest) return;
        state.valuesLoading = false;
        state.valuesError = err.status === 403
          ? 'You do not have access to this company or scope.'
          : err.message || 'Could not load settings values.';
        paint();
      });
  }

  function reloadValues() {
    state.valuesKey = '';
    return ensureValues(true);
  }

  function rowFor(key) {
    for (let i = 0; i < state.values.length; i += 1) {
      if (state.values[i].key === key) return state.values[i];
    }
    return null;
  }

  async function saveRow(key, value) {
    const row = rowFor(key);
    if (!row || state.busy[key]) return;
    if (!canEditRow(row)) {
      toast('This setting is read-only at the selected scope.', 'warn');
      return;
    }
    state.busy[key] = true;
    markBusy(key, true);
    try {
      const payload = await api(API + '/values', {
        method: 'POST',
        body: JSON.stringify(buildWritePayload(row, value, state.scope, state.companyId))
      });
      if (payload && payload.code === 'APPROVAL_REQUIRED') {
        toast('Queued for human approval. It is not applied yet.', 'info');
        loadApprovals().catch(function () {});
      } else {
        toast('Saved. The effective value has been refreshed.', 'success');
        await reloadValues();
      }
    } catch (err) {
      if (err.status === 202) {
        toast('Queued for human approval. It is not applied yet.', 'info');
        loadApprovals().catch(function () {});
      } else if (err.status === 409) {
        toast('Another change landed first. Reloaded the latest value.', 'warn');
        await reloadValues();
      } else {
        toast(err.message || 'Could not save the setting.', 'error');
      }
    } finally {
      state.busy[key] = false;
      markBusy(key, false);
    }
  }

  async function resetRow(key) {
    const row = rowFor(key);
    if (!row || state.busy[key]) return;
    if (!row.overridden_here) {
      toast('There is no local override to reset.', 'warn');
      return;
    }
    if (row.is_locked) {
      toast('Unlock the setting before resetting it to inherited.', 'warn');
      return;
    }
    state.busy[key] = true;
    markBusy(key, true);
    try {
      const payload = await api(API + '/values/reset', {
        method: 'POST',
        body: JSON.stringify({
          key: key,
          scope_type: state.scope.type,
          scope_id: state.scope.id,
          company_id: state.companyId,
          expected_version: Number(row.version || 1),
          reason: 'Reset to inherited from the Settings V2 console.'
        })
      });
      if (payload && payload.code === 'APPROVAL_REQUIRED') {
        toast('Reset queued for human approval.', 'info');
        loadApprovals().catch(function () {});
      } else {
        toast('Local override removed. The value is inherited again.', 'success');
        await reloadValues();
      }
    } catch (err) {
      if (err.status === 202) {
        toast('Reset queued for human approval.', 'info');
      } else if (err.status === 409) {
        toast('Another change landed first. Reloaded the latest value.', 'warn');
        await reloadValues();
      } else {
        toast(err.message || 'Could not reset the setting.', 'error');
      }
    } finally {
      state.busy[key] = false;
      markBusy(key, false);
    }
  }

  async function toggleLock(key) {
    const row = rowFor(key);
    if (!row || state.busy[key]) return;
    if (!canLockRow(row)) {
      toast('A value must exist at this scope before it can be locked.', 'warn');
      return;
    }
    const next = !row.is_locked;
    state.busy[key] = true;
    markBusy(key, true);
    try {
      await api(API + (next ? '/lock' : '/unlock'), {
        method: 'POST',
        body: JSON.stringify({
          key: key,
          scope_type: state.scope.type,
          scope_id: state.scope.id,
          company_id: state.companyId,
          expected_version: Number(row.version || 1),
          reason: next ? 'Locked from the Settings V2 console.' : 'Unlocked from the Settings V2 console.'
        })
      });
      toast(next ? 'Locked. More specific scopes can no longer override it.' : 'Unlocked.', 'success');
      await reloadValues();
    } catch (err) {
      toast(err.message || 'Could not change the lock.', 'error');
    } finally {
      state.busy[key] = false;
      markBusy(key, false);
    }
  }

  async function saveSecret(key, input, mode) {
    const row = rowFor(key);
    if (!row || state.busy[key]) return;
    const value = input && input.value ? String(input.value) : '';
    if (!value) {
      toast('Enter a credential before saving.', 'warn');
      if (input) input.focus();
      return;
    }
    state.busy[key] = true;
    markBusy(key, true);
    try {
      await api(API + (mode === 'rotate' ? '/secrets/rotate' : '/secrets'), {
        method: 'POST',
        body: JSON.stringify({
          name: key,
          value: value,
          scope_type: state.scope.type,
          scope_id: state.scope.id,
          company_id: state.companyId,
          reason: mode === 'rotate' ? 'Rotated from the Settings V2 console.' : 'Configured from the Settings V2 console.'
        })
      });
      if (input) input.value = '';
      toast(mode === 'rotate' ? 'Secret rotated.' : 'Secret saved. It will not be shown again.', 'success');
      await reloadValues();
    } catch (err) {
      toast(err.message || 'Could not save the secret.', 'error');
    } finally {
      state.busy[key] = false;
      markBusy(key, false);
    }
  }

  async function revokeSecret(key) {
    if (state.pendingRevoke !== key) {
      state.pendingRevoke = key;
      paint();
      return;
    }
    state.pendingRevoke = '';
    state.busy[key] = true;
    markBusy(key, true);
    try {
      await api(API + '/secrets/revoke', {
        method: 'POST',
        body: JSON.stringify({
          name: key,
          scope_type: state.scope.type,
          scope_id: state.scope.id,
          company_id: state.companyId,
          reason: 'Revoked from the Settings V2 console.'
        })
      });
      toast('Secret revoked. Dependent workflows will fail until it is reconfigured.', 'success');
      await reloadValues();
    } catch (err) {
      toast(err.message || 'Could not revoke the secret.', 'error');
    } finally {
      state.busy[key] = false;
      markBusy(key, false);
    }
  }

  // --------------------------------------------------------------- approvals
  async function loadApprovals() {
    state.approvalsLoading = true;
    try {
      const payload = await api(
        API + '/approvals?company_id=' + encodeURIComponent(state.companyId)
      );
      state.approvals = payload.approvals || [];
    } finally {
      state.approvalsLoading = false;
      paint();
    }
  }

  async function decideApproval(approvalId, approve) {
    try {
      const payload = await api(API + '/approvals/' + encodeURIComponent(approvalId) + '/decide', {
        method: 'POST',
        body: JSON.stringify({
          decision: approve ? 'approve' : 'reject',
          reason: approve ? 'Approved in the Settings V2 console.' : 'Rejected in the Settings V2 console.'
        })
      });
      if (approve && payload.applied === false) {
        toast('Approval recorded. A second distinct approver is required.', 'info');
      } else {
        toast(approve ? 'Approved and applied.' : 'Rejected.', 'success');
      }
      await loadApprovals();
      await reloadValues();
    } catch (err) {
      toast(err.message || 'Could not record the decision.', 'error');
    }
  }

  // ------------------------------------------------------------------- audit
  async function loadAudit() {
    state.auditLoading = true;
    state.auditVerification = null;
    try {
      const payload = await api(
        API + '/audit?company_id=' + encodeURIComponent(state.companyId) + '&limit=60'
      );
      state.audit = payload.events || [];
    } finally {
      state.auditLoading = false;
      paint();
    }
  }

  async function verifyAudit() {
    try {
      const payload = await api(API + '/audit/verify?company_id=' + encodeURIComponent(state.companyId));
      state.auditVerification = payload.verification || { ok: false };
    } catch (err) {
      state.auditVerification = { ok: false, error: err.message };
    }
    paint();
  }

  // ------------------------------------------------------------------- paint
  function skeletonHtml() {
    return (
      '<div class="sz-shell sz-shell-loading">' +
      '<div class="sz-skeleton sz-skeleton-nav"></div>' +
      '<div class="sz-skeleton-main">' +
      '<div class="sz-skeleton sz-skeleton-title"></div>' +
      '<div class="sz-skeleton sz-skeleton-row"></div>'.repeat(5) +
      '</div></div>'
    );
  }

  function scopeEntityHtml() {
    const type = state.scope.type;
    if (type === 'organization') {
      return '<span class="sz-scope-fixed">' + esc(state.tenantId) + '</span>';
    }
    if (type === 'company') {
      const options = state.companies.length
        ? state.companies
            .map(function (company) {
              return (
                '<option value="' + esc(company.id) + '"' +
                (company.id === state.scope.id ? ' selected' : '') +
                '>' + esc(company.name || company.id) + '</option>'
              );
            })
            .join('')
        : '<option value="' + esc(state.scope.id) + '">' + esc(state.scope.id) + '</option>';
      return '<select class="sz-select" data-role="scope-entity" aria-label="Company">' + options + '</select>';
    }
    if (type === 'department') {
      if (!state.departments.length) {
        return '<span class="sz-scope-fixed sz-scope-empty">No departments found for this company</span>';
      }
      return (
        '<select class="sz-select" data-role="scope-entity" aria-label="Department">' +
        state.departments
          .map(function (department) {
            const id = department.department_id;
            return (
              '<option value="' + esc(id) + '"' +
              (id === state.scope.id ? ' selected' : '') +
              '>' + esc(department.name || id) + '</option>'
            );
          })
          .join('') +
        '</select>'
      );
    }
    if (type === 'agent') {
      if (!state.agents.length) {
        return '<span class="sz-scope-fixed sz-scope-empty">No agents found for this company</span>';
      }
      return (
        '<select class="sz-select" data-role="scope-entity" aria-label="Agent">' +
        state.agents
          .map(function (agent) {
            const id = agent.agent_id || agent.id;
            return (
              '<option value="' + esc(id) + '"' +
              (id === state.scope.id ? ' selected' : '') +
              '>' + esc(agent.name || agent.agent_name || id) + '</option>'
            );
          })
          .join('') +
        '</select>'
      );
    }
    return '<span class="sz-scope-fixed">' + esc(state.scope.id || state.userId) + '</span>';
  }

  function sidebarHtml() {
    const section = currentSection();
    const ready = READY_SECTIONS.indexOf(section.id) !== -1;
    const nav = state.sections
      .map(function (item) {
        const active = item.id === section.id;
        const isReady = READY_SECTIONS.indexOf(item.id) !== -1;
        return (
          '<button type="button" class="sz-nav-item' + (active ? ' is-active' : '') + '"' +
          ' data-action="section" data-section="' + esc(item.id) + '"' +
          ' aria-current="' + (active ? 'page' : 'false') + '">' +
          '<span class="sz-nav-num">' + esc(item.num) + '</span>' +
          '<span class="sz-nav-body">' +
          '<span class="sz-nav-name">' + esc(item.name) + '</span>' +
          '<span class="sz-nav-meta">' +
          (item.live_count ? '<span class="sz-dot-live"></span>' + item.live_count + ' live' : '') +
          (item.coming_soon_count ? '<span class="sz-nav-soon">' + item.coming_soon_count + ' soon</span>' : '') +
          (!isReady ? '<span class="sz-nav-legacy">legacy</span>' : '') +
          '</span></span></button>'
        );
      })
      .join('');
    return (
      '<aside class="sz-sidebar">' +
      '<div class="sz-brand"><div><strong>Settings</strong><span class="sz-beta">V2 preview</span></div>' +
      '<p>Enterprise control plane</p></div>' +
      '<div class="sz-scope-card">' +
      '<label class="sz-field-label" for="szScopeType">View as</label>' +
      '<select id="szScopeType" class="sz-select" data-role="scope-type" aria-label="Settings scope">' +
      SCOPE_ORDER.map(function (type) {
        return (
          '<option value="' + type + '"' + (type === state.scope.type ? ' selected' : '') + '>' +
          scopeLabel(type) + '</option>'
        );
      }).join('') +
      '</select>' +
      '<div class="sz-scope-entity">' + scopeEntityHtml() + '</div>' +
      '<p class="sz-scope-help">Broadest lock wins, then the most specific value, then the default.</p>' +
      '</div>' +
      '<nav class="sz-nav" aria-label="Settings sections">' + nav + '</nav>' +
      '<div class="sz-sidebar-footer">' +
      '<span class="sz-role">' + esc((state.capabilities.role || 'UNKNOWN').replace(/_/g, ' ')) + '</span>' +
      '<span class="sz-actor">' + esc(state.capabilities.actor_type || 'human') + '</span>' +
      '<a class="sz-legacy-link" href="#/settings" data-action="legacy">Legacy console</a>' +
      '</div>' +
      '</aside>'
    );
  }

  function headerHtml() {
    const section = currentSection();
    const pending = state.approvals.filter(function (item) {
      return item.status === 'pending';
    }).length;
    return (
      '<header class="sz-header">' +
      '<div class="sz-header-titles">' +
      '<span class="sz-eyebrow">Section ' + esc(section.num) + ' · ' + esc(READY_SECTIONS.indexOf(section.id) === -1 ? 'Legacy' : 'Settings V2') + '</span>' +
      '<h1>' + esc(section.name) + '</h1>' +
      '<p>' + esc(section.description || '') + '</p>' +
      '</div>' +
      '<div class="sz-header-actions">' +
      (state.capabilities.can_read
        ? '<button type="button" class="sz-btn" data-action="open-approvals">Approvals' +
          (pending ? '<span class="sz-count">' + pending + '</span>' : '') + '</button>'
        : '') +
      (state.capabilities.can_read_audit
        ? '<button type="button" class="sz-btn" data-action="open-audit">Audit</button>'
        : '') +
      '<a class="sz-btn sz-btn-ghost" href="#/settings" data-action="legacy">Open legacy</a>' +
      '</div></header>'
    );
  }

  function toolbarHtml() {
    const counts = sectionSettings(state.sectionId);
    const live = counts.filter(function (d) { return d.status === 'live'; }).length;
    const soon = counts.filter(function (d) { return d.status === 'coming_soon'; }).length;
    return (
      '<div class="sz-toolbar">' +
      '<div class="sz-search-wrap">' +
      '<input id="szSearch" class="sz-search" type="search" data-role="search" ' +
      'placeholder="Search settings… (Ctrl K)" value="' + esc(state.query) + '" aria-label="Search settings">' +
      '</div>' +
      '<div class="sz-filters" role="group" aria-label="Filter by status">' +
      '<button type="button" class="sz-filter' + (state.statusFilter === 'all' ? ' is-active' : '') + '" data-action="filter" data-filter="all">All ' + counts.length + '</button>' +
      '<button type="button" class="sz-filter' + (state.statusFilter === 'live' ? ' is-active' : '') + '" data-action="filter" data-filter="live">Live ' + live + '</button>' +
      '<button type="button" class="sz-filter' + (state.statusFilter === 'soon' ? ' is-active' : '') + '" data-action="filter" data-filter="soon">Coming soon ' + soon + '</button>' +
      '</div></div>'
    );
  }

  function elsewhereHtml() {
    if (!state.query) return '';
    const matches = state.allSettings.filter(function (definition) {
      return definition.section !== state.sectionId && matchesQuery(definition, state.query);
    });
    if (!matches.length) return '';
    const bySection = {};
    matches.forEach(function (definition) {
      bySection[definition.section] = bySection[definition.section] || [];
      bySection[definition.section].push(definition);
    });
    const chips = Object.keys(bySection).slice(0, 6).map(function (sectionId) {
      const section = state.sections.find(function (item) { return item.id === sectionId; });
      return (
        '<button type="button" class="sz-chip" data-action="section" data-section="' + esc(sectionId) + '">' +
        esc(section ? section.name : sectionId) + ' · ' + bySection[sectionId].length + '</button>'
      );
    }).join('');
    return '<div class="sz-elsewhere"><span>Also found in</span>' + chips + '</div>';
  }

  function pillHtml(row, definition) {
    const pill = pillFor(row, definition);
    return (
      '<span class="sz-pill sz-pill-' + pill.kind + '" title="' + esc(pill.detail) + '">' +
      esc(pill.label) + '</span>'
    );
  }

  function optionValues(definition, current) {
    const options = (definition.validation && definition.validation.options) || [];
    const list = options.slice();
    if (current !== null && current !== undefined && list.indexOf(current) === -1) {
      list.unshift(current);
    }
    return list;
  }

  function controlHtml(row, definition) {
    const key = definition.key;
    const kind = controlKindFor(definition);
    if (kind === 'none') {
      return (
        '<div class="sz-soon">' +
        '<strong>Not configurable here.</strong> ' +
        (definition.status === 'coming_soon'
          ? 'This control becomes available after a runtime reader is implemented and tested.'
          : 'This definition is not an editable value.') +
        '</div>'
      );
    }
    if (kind === 'secret') {
      return secretHtml(row, definition);
    }
    const editable = canEditRow(row);
    const value = row ? row.value : definition.default;
    if (!editable) {
      const reason = !state.capabilities.can_write
        ? 'Your role cannot write settings.'
        : row && row.is_locked
          ? 'Locked by a broader policy.'
          : (row.allowed_scopes || []).indexOf(state.scope.type) === -1
            ? 'Not allowed at ' + scopeLabel(state.scope.type) + ' scope.'
            : 'Requires ' + (row.required_permission || 'a higher permission') + '.';
      return (
        '<div class="sz-readonly">' +
        '<span class="sz-value">' + esc(formatValue(row, definition)) + '</span>' +
        '<span class="sz-hint">' + esc(reason) + '</span>' +
        '</div>'
      );
    }
    if (kind === 'toggle') {
      return (
        '<div class="sz-control">' +
        '<button type="button" class="sz-switch' + (value ? ' is-on' : '') + '"' +
        ' role="switch" aria-checked="' + (value ? 'true' : 'false') + '"' +
        ' aria-label="' + esc(definition.label) + '"' +
        ' data-action="toggle" data-key="' + esc(key) + '">' +
        '<span class="sz-switch-knob"></span>' +
        '<span class="sz-switch-label">' + (value ? 'On' : 'Off') + '</span>' +
        '</button></div>'
      );
    }
    if (kind === 'select') {
      return (
        '<div class="sz-control"><select class="sz-select" data-role="control" data-key="' + esc(key) + '" data-type="select" aria-label="' + esc(definition.label) + '">' +
        optionValues(definition, value).map(function (option) {
          return (
            '<option value="' + esc(option) + '"' + (String(option) === String(value) ? ' selected' : '') + '>' +
            esc(option) + '</option>'
          );
        }).join('') +
        '</select></div>'
      );
    }
    if (kind === 'multiselect') {
      return (
        '<div class="sz-control"><select class="sz-select" multiple size="4" data-role="control" data-key="' + esc(key) + '" data-type="multiselect" aria-label="' + esc(definition.label) + '">' +
        optionValues(definition, null).map(function (option) {
          const selected = Array.isArray(value) && value.indexOf(option) !== -1;
          return '<option value="' + esc(option) + '"' + (selected ? ' selected' : '') + '>' + esc(option) + '</option>';
        }).join('') +
        '</select></div>'
      );
    }
    if (kind === 'number' || kind === 'slider') {
      const validation = definition.validation || {};
      const min = validation.min !== null && validation.min !== undefined ? validation.min : '';
      const max = validation.max !== null && validation.max !== undefined ? validation.max : '';
      const step = validation.integer ? '1' : 'any';
      if (kind === 'slider') {
        return (
          '<div class="sz-control sz-control-slider">' +
          '<input type="range" data-role="control" data-key="' + esc(key) + '" data-type="slider"' +
          ' min="' + esc(min) + '" max="' + esc(max) + '" step="' + step + '" value="' + esc(value) + '"' +
          ' aria-label="' + esc(definition.label) + '">' +
          '<output class="sz-slider-value">' + esc(value) + (definition.unit ? ' ' + esc(definition.unit) : '') + '</output>' +
          '</div>'
        );
      }
      return (
        '<div class="sz-control sz-control-number">' +
        '<input class="sz-input" type="number" data-role="control" data-key="' + esc(key) + '" data-type="' + (kind === 'number' ? 'number' : 'currency') + '"' +
        ' min="' + esc(min) + '" max="' + esc(max) + '" step="' + step + '" value="' + esc(value) + '"' +
        ' aria-label="' + esc(definition.label) + '">' +
        (definition.unit ? '<span class="sz-unit">' + esc(definition.unit) + '</span>' : '') +
        '</div>'
      );
    }
    return (
      '<div class="sz-control"><input class="sz-input" type="' + (definition.type === 'token' ? 'password' : 'text') + '"' +
      ' data-role="control" data-key="' + esc(key) + '" data-type="text"' +
      ' value="' + esc(value) + '" autocomplete="off" aria-label="' + esc(definition.label) + '"></div>'
    );
  }

  function secretHtml(row, definition) {
    const meta = (row && row.secret_metadata) || {};
    const configured = !!meta.configured;
    const key = definition.key;
    const canManage = !!state.capabilities.can_manage_secrets;
    let status = '<span class="sz-secret-state">' + (configured ? 'Configured' : 'Not configured') + '</span>';
    if (configured && meta.last4) {
      status += '<span class="sz-secret-hint">····' + esc(meta.last4) + '</span>';
    }
    if (!canManage) {
      return (
        '<div class="sz-secret">' + status +
        '<span class="sz-hint">Requires secrets.manage to change.</span></div>'
      );
    }
    const input =
      '<input class="sz-input sz-secret-input" type="password" data-role="secret-input" data-key="' + esc(key) + '"' +
      ' placeholder="' + (configured ? 'Enter a new credential to rotate' : 'Enter the credential') + '"' +
      ' autocomplete="new-password" spellcheck="false" aria-label="' + esc(definition.label) + ' value">';
    return (
      '<div class="sz-secret">' +
      status +
      '<div class="sz-secret-row">' + input +
      '<button type="button" class="sz-btn sz-btn-primary" data-action="' + (configured ? 'secret-rotate' : 'secret-save') + '" data-key="' + esc(key) + '">' +
      (configured ? 'Rotate' : 'Save secret') + '</button>' +
      (configured
        ? '<button type="button" class="sz-btn sz-btn-danger" data-action="secret-revoke" data-key="' + esc(key) + '">' +
          (state.pendingRevoke === key ? 'Confirm revoke' : 'Revoke') + '</button>'
        : '') +
      '</div>' +
      '<span class="sz-hint">Write-only. The value is never returned by the API.</span>' +
      '</div>'
    );
  }

  function rowActionsHtml(row) {
    if (!row || row.secret || row.status !== 'live') return '';
    if ((row.allowed_scopes || []).indexOf(state.scope.type) === -1) return '';
    const actions = [];
    if (canLockRow(row)) {
      actions.push(
        '<button type="button" class="sz-link-btn" data-action="lock" data-key="' + esc(row.key) + '">' +
        (row.is_locked ? 'Unlock' : 'Lock') + '</button>'
      );
    }
    if (row.overridden_here && !row.is_locked && canEditRow(row)) {
      actions.push(
        '<button type="button" class="sz-link-btn" data-action="reset" data-key="' + esc(row.key) + '">Reset to inherited</button>'
      );
    }
    if (!actions.length) return '';
    return '<div class="sz-row-actions">' + actions.join('') + '</div>';
  }

  function rowHtml(definition, row) {
    const pill = pillFor(row, definition);
    const risk = String(definition.risk || '').toUpperCase();
    const meta = [];
    meta.push('<span class="sz-code">' + esc(definition.key) + '</span>');
    if (definition.legacy_scope) {
      meta.push('<span>' + esc(definition.legacy_scope) + ' legacy scope</span>');
    }
    if (definition.allowed_scopes && definition.allowed_scopes.length) {
      meta.push('<span>Allowed: ' + definition.allowed_scopes.map(scopeLabel).join(' · ') + '</span>');
    }
    if (definition.enforced_by && definition.status === 'live') {
      meta.push('<span>Enforced by <code>' + esc(definition.enforced_by) + '</code></span>');
    }
    if (definition.requires_restart) meta.push('<span class="sz-warn">Restart required</span>');
    if (row && row.version) meta.push('<span>v' + esc(row.version) + '</span>');
    return (
      '<article class="sz-row' + (state.busy[definition.key] ? ' is-busy' : '') + '"' +
      ' data-key="' + esc(definition.key) + '" id="sz-row-' + esc(definition.key) + '">' +
      '<div class="sz-row-head">' +
      '<h3>' + esc(definition.label) + '</h3>' +
      '<div class="sz-pills">' +
      (risk === 'HIGH' || risk === 'CRITICAL'
        ? '<span class="sz-risk sz-risk-' + risk.toLowerCase() + '">' + esc(risk) + '</span>'
        : '') +
      pillHtml(row, definition) +
      '</div></div>' +
      '<p class="sz-row-desc">' + esc(definition.description) + '</p>' +
      '<div class="sz-row-meta">' + meta.join('') + '</div>' +
      (row && row.provenance && definition.status === 'live'
        ? '<div class="sz-provenance">' + esc(row.provenance) + '</div>'
        : '') +
      controlHtml(row, definition) +
      rowActionsHtml(row) +
      '</article>'
    );
  }

  function legacyPanelHtml() {
    const section = currentSection();
    const definitions = sectionSettings(section.id);
    return (
      '<div class="sz-legacy-panel">' +
      '<span class="sz-legacy-badge">Not migrated yet</span>' +
      '<h2>' + esc(section.name) + ' still uses the legacy console</h2>' +
      '<p>Sections 1–6 are rebuilt on the Settings V2 API. This section has ' +
      definitions.length + ' definitions and is scheduled for the next migration pass.</p>' +
      '<p class="sz-hint">Showing a half-wired control here would be decorative. The link below opens the existing, working console.</p>' +
      '<a class="sz-btn sz-btn-primary" href="#/settings" data-action="legacy">Open the legacy console</a>' +
      '</div>'
    );
  }

  function groupsHtml() {
    if (READY_SECTIONS.indexOf(state.sectionId) === -1) return legacyPanelHtml();
    if (state.bootError) {
      return '<div class="sz-empty"><strong>Settings unavailable</strong><p>' + esc(state.bootError) + '</p></div>';
    }
    if (state.scopeNotice) {
      return '<div class="sz-empty"><strong>Choose a scope</strong><p>' + esc(state.scopeNotice) + '</p></div>';
    }
    if (state.valuesLoading && !state.values.length) {
      return '<div class="sz-loading-rows">' +
        '<div class="sz-skeleton sz-skeleton-row"></div>'.repeat(4) + '</div>';
    }
    if (state.valuesError) {
      return (
        '<div class="sz-empty"><strong>Could not load values</strong><p>' + esc(state.valuesError) + '</p>' +
        '<button type="button" class="sz-btn" data-action="retry-values">Retry</button></div>'
      );
    }
    const rows = visibleRows();
    if (!rows.length) {
      return (
        '<div class="sz-empty"><strong>No settings match</strong>' +
        '<p>Clear the search or change the status filter.</p></div>'
      );
    }
    const groups = groupByCategory(rows, state.values, state.categories);
    return groups.map(function (group) {
      const category = state.categories.find(function (item) { return item.id === group.id; });
      return (
        '<section class="sz-group" aria-labelledby="sz-cat-' + esc(group.id) + '">' +
        '<header class="sz-group-head">' +
        '<h2 id="sz-cat-' + esc(group.id) + '">' + esc(category ? category.name : group.id) + '</h2>' +
        '<span>' + group.rows.length + (group.rows.length === 1 ? ' setting' : ' settings') + '</span>' +
        '</header>' +
        group.rows.map(function (entry) {
          return rowHtml(entry.definition, entry.row);
        }).join('') +
        '</section>'
      );
    }).join('');
  }

  function drawerHtml() {
    if (!state.drawer) return '';
    const title = state.drawer === 'approvals' ? 'Approval inbox' : 'Audit ledger';
    let body = '';
    if (state.drawer === 'approvals') {
      if (state.approvalsLoading && !state.approvals.length) {
        body = '<div class="sz-skeleton sz-skeleton-row"></div>';
      } else if (!state.approvals.length) {
        body = '<p class="sz-hint">No proposals for this company.</p>';
      } else {
        body = state.approvals.map(function (item) {
          const pending = item.status === 'pending';
          return (
            '<article class="sz-approval' + (pending ? ' is-pending' : '') + '">' +
            '<div class="sz-approval-head"><strong>' + esc(item.key) + '</strong>' +
            '<span class="sz-pill sz-pill-' + (pending ? 'soon' : 'overridden') + '">' + esc(item.status) + '</span></div>' +
            '<div class="sz-approval-meta">' +
            '<span>' + esc(scopeLabel(item.scope_type)) + ' · ' + esc(item.scope_id) + '</span>' +
            '<span>Risk: ' + esc(item.risk) + '</span>' +
            '<span>By: ' + esc(item.proposed_by) + ' (' + esc(item.actor_type) + ')</span>' +
            '<span>' + esc(item.required_approvals) + ' approver(s) required</span>' +
            '</div>' +
            '<div class="sz-approval-value">Proposed: <code>' + esc(item.proposed_value) + '</code></div>' +
            (item.reason ? '<p class="sz-hint">' + esc(item.reason) + '</p>' : '') +
            (pending && state.capabilities.is_approver
              ? '<div class="sz-approval-actions">' +
                '<button type="button" class="sz-btn sz-btn-primary" data-action="approve" data-id="' + esc(item.approval_id) + '">Approve</button>' +
                '<button type="button" class="sz-btn sz-btn-danger" data-action="reject" data-id="' + esc(item.approval_id) + '">Reject</button>' +
                '</div>'
              : '') +
            '</article>'
          );
        }).join('');
      }
    } else {
      if (state.auditLoading && !state.audit.length) {
        body = '<div class="sz-skeleton sz-skeleton-row"></div>';
      } else {
        if (state.auditVerification) {
          body +=
            '<div class="sz-verify ' + (state.auditVerification.ok ? 'is-ok' : 'is-bad') + '">' +
            (state.auditVerification.ok
              ? 'Hash chain verified across ' + (state.auditVerification.checked || 0) + ' events.'
              : 'Verification failed: ' + esc(state.auditVerification.error || 'chain break detected.')) +
            '</div>';
        }
        body += state.audit.length
          ? state.audit.map(function (event) {
              return (
                '<article class="sz-audit">' +
                '<div class="sz-audit-head"><strong>' + esc(event.setting_key) + '</strong>' +
                '<span>' + esc(event.actor_type) + ' · ' + esc(event.actor) + '</span></div>' +
                '<div class="sz-audit-meta">' +
                '<span>' + esc(scopeLabel(event.scope_type)) + ' · ' + esc(event.scope_id) + '</span>' +
                '<span>v' + esc(event.version) + '</span>' +
                '<span>' + esc(event.approval_status) + '</span>' +
                '</div>' +
                '<div class="sz-audit-change"><code>' + esc(JSON.stringify(event.old_value)) + '</code>' +
                ' → <code>' + esc(JSON.stringify(event.new_value)) + '</code></div>' +
                (event.reason ? '<p class="sz-hint">' + esc(event.reason) + '</p>' : '') +
                '</article>'
              );
            }).join('')
          : '<p class="sz-hint">No audit events for this company.</p>';
      }
    }
    return (
      '<div class="sz-drawer-backdrop" data-action="close-drawer"></div>' +
      '<aside class="sz-drawer" role="dialog" aria-modal="true" aria-label="' + esc(title) + '">' +
      '<header class="sz-drawer-head"><h2>' + esc(title) + '</h2>' +
      '<button type="button" class="sz-icon-btn" data-action="close-drawer" aria-label="Close">×</button></header>' +
      '<div class="sz-drawer-body">' + body + '</div>' +
      (state.drawer === 'audit'
        ? '<footer class="sz-drawer-foot"><button type="button" class="sz-btn" data-action="verify-audit">Verify hash chain</button></footer>'
        : '') +
      '</aside>'
    );
  }

  function shellHtml() {
    return (
      '<div class="sz-shell">' +
      sidebarHtml() +
      '<main class="sz-main">' +
      headerHtml() +
      '<div class="sz-scroll">' +
      toolbarHtml() +
      '<div id="szElsewhere">' + elsewhereHtml() + '</div>' +
      '<div class="sz-groups" id="szGroups">' + groupsHtml() + '</div>' +
      '</div></main>' +
      drawerHtml() +
      '</div>'
    );
  }

  function paint() {
    if (!rootEl) return;
    if (!state.booted && !state.bootError) {
      rootEl.innerHTML = skeletonHtml();
      return;
    }
    const previous = rootEl.querySelector('.sz-scroll');
    const top = previous ? previous.scrollTop : 0;
    rootEl.innerHTML = shellHtml();
    const next = rootEl.querySelector('.sz-scroll');
    if (next) next.scrollTop = top;
    if (state.pendingFocus) {
      const target = rootEl.querySelector('#sz-row-' + cssEscape(state.pendingFocus));
      state.pendingFocus = '';
      if (target) {
        target.classList.add('is-flash');
        if (target.scrollIntoView) target.scrollIntoView({ block: 'center', behavior: 'smooth' });
        window.setTimeout(function () {
          target.classList.remove('is-flash');
        }, 1400);
      }
    }
  }

  function cssEscape(value) {
    return String(value).replace(/[^a-zA-Z0-9_-]/g, '\\$&');
  }

  function paintGroups() {
    const host = rootEl && rootEl.querySelector('#szGroups');
    if (host) host.innerHTML = groupsHtml();
    const elsewhere = rootEl && rootEl.querySelector('#szElsewhere');
    if (elsewhere) elsewhere.innerHTML = elsewhereHtml();
  }

  function markBusy(key, busy) {
    const row = rootEl && rootEl.querySelector('#sz-row-' + cssEscape(key));
    if (!row) return;
    row.classList.toggle('is-busy', busy);
    row.setAttribute('aria-busy', busy ? 'true' : 'false');
  }

  // ------------------------------------------------------------------ events
  function navigateSection(sectionId) {
    if (!sectionId) return;
    state.sectionId = sectionId;
    state.query = '';
    state.statusFilter = 'all';
    state.drawer = null;
    state.pendingRevoke = '';
    state.scopeNotice = '';
    state.values = [];
    state.valuesKey = '';
    if (root.history && root.history.replaceState) {
      root.history.replaceState(null, '', '#/settings-v2/' + sectionId);
    }
    paint();
    ensureValues();
  }

  async function setScopeType(type) {
    if (SCOPE_ORDER.indexOf(type) === -1) return;
    state.scope.type = type;
    state.values = [];
    state.valuesKey = '';
    try {
      await ensureEntities(type);
    } catch (err) {
      toast('Could not load the scope list.', 'warn');
    }
    state.scope.id = scopeDefaultId(type);
    paint();
    ensureValues();
  }

  function setScopeEntity(id) {
    state.scope.id = id;
    state.values = [];
    state.valuesKey = '';
    paint();
    ensureValues();
  }

  function readControlValue(target) {
    const type = target.getAttribute('data-type');
    if (type === 'multiselect') {
      return Array.prototype.slice.call(target.selectedOptions || []).map(function (option) {
        return option.value;
      });
    }
    if (type === 'number' || type === 'currency' || type === 'slider') {
      const raw = target.value;
      if (raw === '') return '';
      return Number(raw);
    }
    return target.value;
  }

  function onClick(event) {
    const target = event.target.closest('[data-action]');
    if (!target) return;
    const action = target.getAttribute('data-action');
    const key = target.getAttribute('data-key');
    if (action === 'legacy') {
      // Let the anchor navigate; the router picks up #/settings.
      return;
    }
    event.preventDefault();
    if (action === 'section') {
      navigateSection(target.getAttribute('data-section'));
    } else if (action === 'filter') {
      state.statusFilter = target.getAttribute('data-filter');
      paint();
    } else if (action === 'toggle') {
      const row = rowFor(key);
      saveRow(key, !(row && row.value));
    } else if (action === 'lock') {
      toggleLock(key);
    } else if (action === 'reset') {
      resetRow(key);
    } else if (action === 'secret-save' || action === 'secret-rotate') {
      const input = rootEl.querySelector('[data-role="secret-input"][data-key="' + cssEscape(key) + '"]');
      saveSecret(key, input, action === 'secret-rotate' ? 'rotate' : 'set');
    } else if (action === 'secret-revoke') {
      revokeSecret(key);
    } else if (action === 'open-approvals') {
      state.drawer = 'approvals';
      paint();
      loadApprovals().catch(function () {});
    } else if (action === 'open-audit') {
      state.drawer = 'audit';
      paint();
      loadAudit().catch(function () {});
    } else if (action === 'close-drawer') {
      state.drawer = null;
      paint();
    } else if (action === 'approve') {
      decideApproval(target.getAttribute('data-id'), true);
    } else if (action === 'reject') {
      decideApproval(target.getAttribute('data-id'), false);
    } else if (action === 'verify-audit') {
      verifyAudit();
    } else if (action === 'retry-values') {
      reloadValues();
    }
  }

  function onChange(event) {
    const target = event.target;
    const role = target.getAttribute('data-role');
    if (role === 'scope-type') {
      setScopeType(target.value);
      return;
    }
    if (role === 'scope-entity') {
      setScopeEntity(target.value);
      return;
    }
    if (role === 'control') {
      const key = target.getAttribute('data-key');
      const value = readControlValue(target);
      if (value === '') {
        toast('A value is required.', 'warn');
        return;
      }
      saveRow(key, value);
    }
  }

  function onInput(event) {
    const target = event.target;
    const role = target.getAttribute('data-role');
    if (role === 'search') {
      state.query = target.value;
      paintGroups();
      return;
    }
    if (target.getAttribute('data-type') === 'slider') {
      const output = target.parentNode.querySelector('output');
      if (output) output.textContent = target.value;
    }
  }

  function onKeydown(event) {
    if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === 'k') {
      const search = rootEl && rootEl.querySelector('#szSearch');
      if (search) {
        event.preventDefault();
        search.focus();
        search.select();
      }
      return;
    }
    if (event.key === 'Escape') {
      if (state.drawer) {
        state.drawer = null;
        paint();
      }
      return;
    }
    if (event.key === 'Enter' && event.target.getAttribute('data-role') === 'control') {
      event.target.blur();
    }
  }

  function bindEvents() {
    if (eventsBound || !rootEl) return;
    eventsBound = true;
    rootEl.addEventListener('click', onClick);
    rootEl.addEventListener('change', onChange);
    rootEl.addEventListener('input', onInput);
    rootEl.addEventListener('keydown', onKeydown);
  }

  // -------------------------------------------------------------------- entry
  function currentRoute() {
    if (typeof window === 'undefined') return '';
    return window.location.hash || '';
  }

  function render(route) {
    if (typeof document === 'undefined') return;
    const el = document.getElementById('view-settings');
    if (!el) return;
    rootEl = el;
    bindEvents();
    const parsed = parseRoute(route || currentRoute());
    if (parsed.section) state.sectionId = parsed.section;
    if (!state.booted) {
      if (!state.booting) boot();
      else paint();
      return;
    }
    paint();
    ensureValues();
  }

  const apiSurface = {
    render: render,
    reload: function () {
      state.booted = false;
      state.bootError = '';
      state.values = [];
      state.valuesKey = '';
      render('#/settings-v2/' + state.sectionId);
    },
    openSection: navigateSection,
    _test: {
      pillFor: pillFor,
      controlKindFor: controlKindFor,
      parseRoute: parseRoute,
      buildScopeQuery: buildScopeQuery,
      buildWritePayload: buildWritePayload,
      groupByCategory: groupByCategory,
      formatValue: formatValue,
      rowHtml: rowHtml,
      READY_SECTIONS: READY_SECTIONS.slice()
    },
    _state: state
  };

  root.SettingsV2 = apiSurface;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = apiSurface;
  }
})(typeof window !== 'undefined' ? window : globalThis);
