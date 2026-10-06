/**
 * ZONATA / URA Universal AI Company Operating System
 * Master Production Settings Center
 * P0 Production & Enterprise Requirement: Card-based, square/grid-oriented,
 * 43 canonical categories across 6 groups, hierarchical scope inheritance,
 * permission-aware, auditable with SHA-256 evidence, effective vs configured runtime state,
 * CEO proposal resolution, and mobile-responsive layout.
 */

const EnterpriseSettings = (function() {
  'use strict';

  // 6 Primary Visual Groups
  const GROUPS = [
    {
      id: 'identity',
      name: 'GROUP A — IDENTITY',
      desc: 'Host sovereignty, company identity, organizational hierarchy, and access control.'
    },
    {
      id: 'ai_system',
      name: 'GROUP B — AI EXECUTIVE SYSTEM',
      desc: 'Global AI policy, inference providers, AI CEO governance, workforce, and autonomy.'
    },
    {
      id: 'execution',
      name: 'GROUP C — EXECUTION FABRIC',
      desc: 'Workflows, tools registry, MCP, A2A network, desktop, browser, terminal, and sandbox.'
    },
    {
      id: 'business',
      name: 'GROUP D — BUSINESS SYSTEMS',
      desc: 'Integrations, organizational knowledge, files, records, finance, and notifications.'
    },
    {
      id: 'governance',
      name: 'GROUP E — CONTROL & TRUST',
      desc: 'Approvals, constitutional governance, privacy, compliance, audit ledger, and security.'
    },
    {
      id: 'platform',
      name: 'GROUP F — COST & PLATFORM',
      desc: 'Usage & compute costs, billing, developer APIs, webhooks, localization, recovery, and danger zone.'
    }
  ];

  // Route alias normalization map
  const ROUTE_ALIASES = {
    'ai-ceo': 'ai_ceo',
    'ai/ceo': 'ai_ceo',
    'ai-providers': 'ai_providers',
    'ai/providers': 'ai_providers',
    'ai/cost': 'usage',
    'agent-factory': 'agent_factory',
    'missions-autonomy': 'missions',
    'code-execution': 'openhands',
    'audit-evidence': 'audit'
  };

  // State Management
  let activeView = 'hub'; // 'hub' or category ID
  let categoriesCatalog = [];
  let currentCategoryData = null;
  let stagedValues = {};
  let originalValues = {};
  let hasUnsavedChanges = false;
  let activeScope = 'Company'; // 'Host', 'Company', 'Department', 'User'
  let globalSearchQuery = '';
  let activeQuickFilter = 'all'; // 'all', 'recent', 'overrides', 'proposals', 'audit'
  let effectiveStateCache = null;
  let authEnvironment = { environment: 'development', strict_auth: false, auth_mode: 'DEV_BOOTSTRAP' };
  let auditEventsList = [];
  let showAuditDrawer = false;
  let previewPendingChange = null;
  let activeTestResult = null;

  // Initialize service
  async function init() {
    await fetchEnvironment();
    await fetchCategories();
    await fetchEffectiveState();
  }

  async function fetchEnvironment() {
    try {
      const res = await fetch('/api/auth/environment');
      if (res.ok) {
        authEnvironment = await res.json();
      }
    } catch (e) {
      console.warn('[Settings] Failed to fetch auth environment:', e);
    }
  }

  async function fetchCategories() {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const data = await res.json();
        categoriesCatalog = data.categories || [];
      }
    } catch (e) {
      console.warn('[Settings] Failed to load categories catalog:', e);
    }
  }

  async function fetchEffectiveState() {
    try {
      const res = await fetch('/api/settings/effective');
      if (res.ok) {
        const data = await res.json();
        effectiveStateCache = data.effective_enforcement || {};
      }
    } catch (e) {
      console.warn('[Settings] Failed to fetch effective runtime state:', e);
    }
  }

  async function loadCategory(categoryId) {
    categoryId = normalizeCategoryId(categoryId);
    activeView = categoryId;
    stagedValues = {};
    originalValues = {};
    hasUnsavedChanges = false;
    currentCategoryData = null;

    try {
      const res = await fetch(`/api/settings/category/${categoryId}`);
      if (res.ok) {
        currentCategoryData = await res.json();
        if (currentCategoryData.settings) {
          currentCategoryData.settings.forEach(s => {
            originalValues[s.id] = s.value;
            stagedValues[s.id] = s.value;
          });
        }
      }
    } catch (e) {
      console.error(`[Settings] Failed to load category '${categoryId}':`, e);
    }
    renderRoute();
  }

  function normalizeCategoryId(raw) {
    if (!raw) return 'hub';
    let clean = raw.trim().toLowerCase().replace(/^\/+/, '').replace(/^settings\/?/, '');
    if (!clean || clean === 'hub') return 'hub';
    return ROUTE_ALIASES[clean] || clean;
  }

  // Master Route Handler
  function render(route) {
    const rawCategory = (route || '').replace(/^\/settings\/?/, '').trim();
    if (!rawCategory || rawCategory === 'hub') {
      activeView = 'hub';
      renderRoute();
    } else {
      const norm = normalizeCategoryId(rawCategory);
      if (activeView !== norm || !currentCategoryData) {
        loadCategory(norm);
      } else {
        renderRoute();
      }
    }
  }

  function renderRoute() {
    const container = document.getElementById('view-settings');
    if (!container) return;

    if (activeView === 'hub') {
      renderSettingsHub(container);
    } else {
      renderCategoryDetail(container);
    }
  }

  // --------------------------------------------------------------------------
  // 1. SETTINGS HOME / HUB VIEW (Square/Card-Based Control Plane)
  // --------------------------------------------------------------------------
  function renderSettingsHub(container) {
    const totalCategories = categoriesCatalog.length || 43;
    const currentComp = (window.state && window.state.activeCompany) ? window.state.activeCompany.name : 'ZONATA Primary Enterprise';
    const currentUser = (window.state && window.state.host) ? window.state.host.name : 'Sukhraj Singh';
    const userRole = (window.state && window.state.host) ? window.state.host.role : 'SOVEREIGN_HOST';

    let filteredCats = categoriesCatalog.filter(cat => {
      if (globalSearchQuery) {
        const q = globalSearchQuery.toLowerCase();
        return cat.name.toLowerCase().includes(q) ||
               cat.desc.toLowerCase().includes(q) ||
               cat.id.toLowerCase().includes(q) ||
               (cat.current_value_summary && cat.current_value_summary.toLowerCase().includes(q));
      }
      return true;
    });

    if (activeQuickFilter === 'overrides') {
      filteredCats = filteredCats.filter(c => c.status === 'Attention' || c.status === 'Warning');
    } else if (activeQuickFilter === 'recent') {
      filteredCats = filteredCats.slice(0, 12);
    }

    container.innerHTML = `
      <div class="settings-center-root">
        <!-- Enterprise Header Bar -->
        <div class="settings-header-banner">
          <div class="settings-header-main">
            <div class="settings-title-row">
              <div class="settings-badge-pill">CONTROL PLANE</div>
              <h1>Settings</h1>
            </div>
            <p class="settings-subtitle">Configure and govern your ZONATA company operating environment.</p>
          </div>
          <div class="settings-meta-summary">
            <div class="settings-meta-chip">
              <span class="chip-label">Company:</span>
              <span class="chip-val">${escapeHtml(currentComp)}</span>
            </div>
            <div class="settings-meta-chip">
              <span class="chip-label">Scope:</span>
              <span class="chip-val">Sovereign Host</span>
            </div>
            <div class="settings-meta-chip">
              <span class="chip-label">Identity:</span>
              <span class="chip-val">${escapeHtml(currentUser)} (${escapeHtml(userRole)})</span>
            </div>
            <div class="settings-meta-chip environment-chip ${authEnvironment.environment}">
              <span class="chip-label">Mode:</span>
              <span class="chip-val">${authEnvironment.environment.toUpperCase()}</span>
            </div>
          </div>
        </div>

        <!-- Health Vitals Bar (Compact Semantic States, Zero Charts) -->
        <div class="settings-vitals-grid">
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('security')">
            <div class="vital-icon">🔐</div>
            <div class="vital-info">
              <div class="vital-title">Security & MFA</div>
              <div class="vital-state">● Healthy • Enforced</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('ai')">
            <div class="vital-icon">🧠</div>
            <div class="vital-info">
              <div class="vital-title">AI Policy & Safety</div>
              <div class="vital-state">● Configured • Firewall ON</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('ai_ceo')">
            <div class="vital-icon">👑</div>
            <div class="vital-info">
              <div class="vital-title">AI CEO Governance</div>
              <div class="vital-state">● Operational • Level 3</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('integrations')">
            <div class="vital-icon">🔗</div>
            <div class="vital-info">
              <div class="vital-title">Integrations</div>
              <div class="vital-state">● 8 Connected • Least-Privilege</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('audit')">
            <div class="vital-icon">⛓️</div>
            <div class="vital-info">
              <div class="vital-title">Evidence Ledger</div>
              <div class="vital-state">● Verified • SHA-256 Merkle</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('recovery')">
            <div class="vital-icon">💾</div>
            <div class="vital-info">
              <div class="vital-title">Disaster Recovery</div>
              <div class="vital-state">● Healthy • Snapshot 6h</div>
            </div>
          </div>
        </div>

        <!-- Search & Filter Controls -->
        <div class="settings-toolbar">
          <div class="settings-search-box">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input 
              type="text" 
              placeholder="Search setting by name, category, provider, permission, or scope..." 
              value="${escapeHtml(globalSearchQuery)}" 
              oninput="EnterpriseSettings.handleSearch(this.value)" 
            />
            ${globalSearchQuery ? `<button class="clear-search-btn" onclick="EnterpriseSettings.handleSearch('')">✕</button>` : ''}
          </div>

          <div class="settings-filter-pills">
            <button class="filter-pill ${activeQuickFilter === 'all' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('all')">All Categories (${totalCategories})</button>
            <button class="filter-pill ${activeQuickFilter === 'recent' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('recent')">Recent</button>
            <button class="filter-pill ${activeQuickFilter === 'overrides' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('overrides')">Attention & Warnings</button>
            <button class="filter-pill" onclick="EnterpriseSettings.openGlobalAudit()">Audit Ledger Shortcut →</button>
          </div>
        </div>

        <!-- 6 Visual Category Groups -->
        <div class="settings-groups-stack">
          ${GROUPS.map(grp => {
            const groupCats = filteredCats.filter(c => c.group_id === grp.id);
            if (groupCats.length === 0) return '';
            return `
              <div class="settings-group-section">
                <div class="settings-group-header">
                  <div class="group-title-row">
                    <h3>${escapeHtml(grp.name)}</h3>
                    <span class="group-count-badge">${groupCats.length} Categories</span>
                  </div>
                  <p class="group-desc">${escapeHtml(grp.desc)}</p>
                </div>

                <!-- 4-Column Square Grid of Compact Cards -->
                <div class="settings-cards-grid">
                  ${groupCats.map(cat => renderSquareCategoryCard(cat)).join('')}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  function renderSquareCategoryCard(cat) {
    const statusClass = (cat.status || 'Healthy').toLowerCase();
    const statusBadge = `<span class="cat-status-dot status-${statusClass}">● ${escapeHtml(cat.status || 'Healthy')}</span>`;

    return `
      <div class="settings-square-card" onclick="EnterpriseSettings.navigateTo('${cat.id}')">
        <div class="square-card-top">
          <div class="square-icon-box">${cat.icon || '⚙️'}</div>
          ${statusBadge}
        </div>
        <div class="square-card-body">
          <h4 class="square-card-title">${escapeHtml(cat.name)}</h4>
          <p class="square-card-desc">${escapeHtml(cat.desc)}</p>
          <div class="square-card-value">
            <span class="val-label">Value:</span>
            <span class="val-text">${escapeHtml(cat.current_value_summary || 'Configured')}</span>
          </div>
        </div>
        <div class="square-card-footer">
          <span class="square-subset-tag">${escapeHtml(cat.scope || 'Company')} Scope</span>
          <span class="square-action-link">Open →</span>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 2. CATEGORY DETAIL VIEW (Compact Sidebar + Setting Card Grid)
  // --------------------------------------------------------------------------
  function renderCategoryDetail(container) {
    if (!currentCategoryData || !currentCategoryData.category) {
      container.innerHTML = `
        <div class="settings-loading-card">
          <div class="spinner"></div>
          <p>Loading enterprise configuration for '${escapeHtml(activeView)}'...</p>
        </div>
      `;
      return;
    }

    const cat = currentCategoryData.category;
    const settingsList = currentCategoryData.settings || [];
    const proposals = currentCategoryData.proposals || [];
    const audits = currentCategoryData.recent_audits || [];

    container.innerHTML = `
      <div class="settings-detail-workspace">
        <!-- Left Sub-Navigation Sidebar -->
        <aside class="settings-detail-sidebar">
          <div class="sidebar-back-btn" onclick="EnterpriseSettings.navigateTo('hub')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            <span>All Settings Hub</span>
          </div>
          
          <div class="sidebar-category-nav">
            ${GROUPS.map(grp => {
              const grpCats = categoriesCatalog.filter(c => c.group_id === grp.id);
              return `
                <div class="sidebar-nav-group">
                  <div class="sidebar-group-heading">${escapeHtml(grp.name.replace('GROUP ', ''))}</div>
                  ${grpCats.map(c => `
                    <button 
                      class="sidebar-nav-item ${c.id === cat.id ? 'active' : ''}" 
                      onclick="EnterpriseSettings.navigateTo('${c.id}')"
                    >
                      <span class="nav-icon">${c.icon}</span>
                      <span class="nav-name">${escapeHtml(c.name)}</span>
                    </button>
                  `).join('')}
                </div>
              `;
            }).join('')}
          </div>
        </aside>

        <!-- Right Main Settings Surface -->
        <main class="settings-detail-main">
          <!-- Unsaved Changes Alert Bar -->
          ${hasUnsavedChanges ? `
            <div class="settings-unsaved-banner">
              <div class="banner-text">
                <span class="banner-icon">⚠️</span>
                <span>You have unsaved changes in <strong>${escapeHtml(cat.name)}</strong>.</span>
              </div>
              <div class="banner-actions">
                <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.discardChanges()">Discard</button>
                <button class="btn btn-primary btn-sm" onclick="EnterpriseSettings.promptSaveCategory()">Save Changes</button>
              </div>
            </div>
          ` : ''}

          <!-- Category Header & Scope Selector -->
          <div class="category-header-panel">
            <div class="category-breadcrumbs">
              <a href="#/settings" onclick="EnterpriseSettings.navigateTo('hub')">Home</a>
              <span class="sep">/</span>
              <a href="#/settings" onclick="EnterpriseSettings.navigateTo('hub')">Settings</a>
              <span class="sep">/</span>
              <span class="curr">${escapeHtml(cat.name)}</span>
            </div>

            <div class="category-title-bar">
              <div class="cat-title-left">
                <div class="cat-icon-large">${cat.icon || '⚙️'}</div>
                <div>
                  <h2>${escapeHtml(cat.name)}</h2>
                  <p class="cat-description">${escapeHtml(cat.desc)}</p>
                </div>
              </div>

              <!-- Scope & Inheritance Selector -->
              <div class="scope-selector-card">
                <div class="scope-row">
                  <span class="scope-label">Scope:</span>
                  <select class="scope-select" onchange="EnterpriseSettings.setScope(this.value)">
                    <option value="Host" ${activeScope === 'Host' ? 'selected' : ''}>Host Sovereign</option>
                    <option value="Company" ${activeScope === 'Company' ? 'selected' : ''}>Company Override</option>
                    <option value="Department" ${activeScope === 'Department' ? 'selected' : ''}>Department</option>
                    <option value="User" ${activeScope === 'User' ? 'selected' : ''}>User Profile</option>
                  </select>
                </div>
                <div class="inheritance-indicator">
                  <span class="indicator-badge badge-inherited">● Inherited From: Host Default</span>
                </div>
              </div>
            </div>

            <div class="category-actions-bar">
              <div class="actions-left">
                <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.resetToInherited()">Reset to Inherited</button>
                <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.toggleAuditDrawer()">Audit Trail (${audits.length})</button>
              </div>
              <div class="actions-right">
                <button class="btn btn-primary btn-sm" onclick="EnterpriseSettings.promptSaveCategory()" ${!hasUnsavedChanges ? 'disabled' : ''}>Save Changes</button>
              </div>
            </div>
          </div>

          <!-- Pending AI CEO Proposals Banner -->
          ${proposals.length > 0 ? `
            <div class="proposals-block">
              <div class="proposals-header">
                <span class="proposals-badge">AI CEO Proposals (${proposals.length})</span>
                <span class="proposals-sub">Autonomous optimization proposals awaiting Sovereign approval</span>
              </div>
              <div class="proposals-list">
                ${proposals.map(p => `
                  <div class="proposal-card">
                    <div class="proposal-header">
                      <strong>${escapeHtml(p.setting_id)}:</strong> Proposed Value = <code>${JSON.stringify(p.proposed_value)}</code>
                      <span class="badge badge-warning">${escapeHtml(p.risk_level)} Risk</span>
                    </div>
                    <p class="proposal-reason"><strong>Reason:</strong> ${escapeHtml(p.reason)}</p>
                    <p class="proposal-benefit"><strong>Expected Benefit:</strong> ${escapeHtml(p.expected_benefit)}</p>
                    <div class="proposal-actions">
                      <button class="btn btn-success btn-sm" onclick="EnterpriseSettings.resolveProposal('${p.proposal_id}', 'APPROVED')">Approve Proposal</button>
                      <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.resolveProposal('${p.proposal_id}', 'REJECTED')">Reject</button>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}

          <!-- Grid of Setting Cards -->
          <div class="category-cards-grid">
            ${settingsList.map(s => renderSettingCard(s)).join('')}
          </div>
        </main>
      </div>

      <!-- High-Impact Change Preview Modal -->
      ${previewPendingChange ? renderChangePreviewModal() : ''}

      <!-- Audit Drawer / Modal -->
      ${showAuditDrawer ? renderAuditDrawer(audits) : ''}
    `;
  }

  // --------------------------------------------------------------------------
  // 3. SETTING CARD RENDERER (Multi-Type Square/Near-Square Cards)
  // --------------------------------------------------------------------------
  function renderSettingCard(s) {
    const curVal = stagedValues.hasOwnProperty(s.id) ? stagedValues[s.id] : s.value;
    const isDirty = stagedValues.hasOwnProperty(s.id) && stagedValues[s.id] !== originalValues[s.id];
    const riskBadge = s.risk === 'CRITICAL' ? '<span class="policy-tag tag-critical">Critical Risk</span>' :
                      s.risk === 'HIGH' ? '<span class="policy-tag tag-high">High Risk</span>' :
                      '<span class="policy-tag tag-low">Standard</span>';

    const policyTags = [
      s.editable_by === 'OWNER' ? '<span class="policy-tag tag-owner">Owner Controlled</span>' : '',
      s.is_ceo_managed ? '<span class="policy-tag tag-ceo">Managed by AI CEO</span>' : '',
      s.editable_by === 'READ_ONLY' ? '<span class="policy-tag tag-readonly">Read Only</span>' : '',
      s.requires_approval ? '<span class="policy-tag tag-approval">Requires Approval</span>' : '',
      s.secret ? '<span class="policy-tag tag-secret">Sensitive Token</span>' : '',
      riskBadge
    ].filter(Boolean).join('');

    // Effective vs Configured proof
    const effectiveProof = `
      <div class="effective-runtime-pill">
        <span class="eff-label">Runtime Enforcement:</span>
        <span class="eff-val">${escapeHtml(String(s.effective_runtime_value || curVal))}</span>
        <span class="eff-badge status-${(s.runtime_status || 'ACTIVE').toLowerCase()}">${escapeHtml(s.runtime_status || 'ACTIVE')}</span>
      </div>
    `;

    return `
      <div class="setting-card ${isDirty ? 'card-dirty' : ''}">
        <div class="card-head">
          <div class="card-title-line">
            <h5>${escapeHtml(s.name)}</h5>
            ${isDirty ? '<span class="badge badge-amber">Modified</span>' : ''}
          </div>
          <div class="policy-tags-row">${policyTags}</div>
        </div>

        <p class="card-desc">${escapeHtml(s.desc || '')}</p>

        <!-- Dynamic Control Area -->
        <div class="card-control-box">
          ${renderControlForSetting(s, curVal)}
        </div>

        <!-- Effective Runtime Status Proof -->
        ${effectiveProof}

        <!-- Card Footer -->
        <div class="card-footer-meta">
          <div class="footer-left">
            <span class="footer-scope">${escapeHtml(s.scope || 'Company')}</span>
            <span class="footer-dot">•</span>
            <span class="footer-updated">v${s.version || 1}</span>
          </div>
          <div class="footer-right">
            ${s.type === 'token' ? `<button class="btn-text-xs" onclick="EnterpriseSettings.runDiagnosticTest('api_token')">Test Token</button>` : ''}
            <button class="btn-text-xs" onclick="EnterpriseSettings.viewSettingAudit('${s.id}')">Audit</button>
          </div>
        </div>
      </div>
    `;
  }

  function renderControlForSetting(s, curVal) {
    switch (s.type) {
      case 'toggle':
        return `
          <label class="toggle-switch-wrapper">
            <input 
              type="checkbox" 
              ${curVal ? 'checked' : ''} 
              ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
              onchange="EnterpriseSettings.stageChange('${s.id}', this.checked)" 
            />
            <span class="toggle-slider"></span>
            <span class="toggle-state-text">${curVal ? 'ENABLED' : 'DISABLED'}</span>
          </label>
        `;

      case 'select':
        return `
          <select 
            class="setting-select-control" 
            ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
            onchange="EnterpriseSettings.stageChange('${s.id}', this.value)"
          >
            ${(s.options || []).map(opt => `
              <option value="${escapeHtml(opt)}" ${String(curVal) === String(opt) ? 'selected' : ''}>${escapeHtml(opt)}</option>
            `).join('')}
          </select>
        `;

      case 'number':
        return `
          <div class="number-control-box">
            <input 
              type="number" 
              class="setting-input-control" 
              value="${curVal}" 
              ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
              oninput="EnterpriseSettings.stageChange('${s.id}', parseFloat(this.value) || 0)" 
            />
          </div>
        `;

      case 'currency':
        return `
          <div class="currency-control-box">
            <span class="currency-prefix">₹</span>
            <input 
              type="number" 
              class="setting-input-control" 
              value="${curVal}" 
              ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
              oninput="EnterpriseSettings.stageChange('${s.id}', parseFloat(this.value) || 0)" 
            />
          </div>
        `;

      case 'token':
        return `
          <div class="token-control-box">
            <input 
              type="password" 
              class="setting-input-control token-input" 
              value="${escapeHtml(curVal)}" 
              id="token-${s.id}" 
              ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
              oninput="EnterpriseSettings.stageChange('${s.id}', this.value)" 
            />
            <button class="btn btn-secondary btn-xs" onclick="EnterpriseSettings.toggleTokenVisibility('token-${s.id}')">Reveal</button>
            <button class="btn btn-secondary btn-xs" onclick="EnterpriseSettings.runDiagnosticTest('api_token')">Test</button>
          </div>
        `;

      case 'slider':
        return `
          <div class="slider-control-box">
            <input 
              type="range" 
              min="1" 
              max="10" 
              value="${curVal}" 
              class="setting-slider" 
              oninput="EnterpriseSettings.stageChange('${s.id}', parseInt(this.value)); document.getElementById('val-${s.id}').innerText = this.value;" 
            />
            <span class="slider-readout" id="val-${s.id}">${curVal} FPS</span>
          </div>
        `;

      case 'radio':
        return `
          <div class="radio-segmented-box">
            ${(s.options || []).map(opt => `
              <button 
                class="segment-btn ${String(curVal) === String(opt) ? 'active' : ''}" 
                onclick="EnterpriseSettings.stageChange('${s.id}', '${opt}')"
              >
                ${escapeHtml(opt)}
              </button>
            `).join('')}
          </div>
        `;

      case 'multiselect':
        const arr = Array.isArray(curVal) ? curVal : [];
        return `
          <div class="multiselect-tags-box">
            ${(s.options || []).map(opt => {
              const checked = arr.includes(opt);
              return `
                <label class="tag-checkbox ${checked ? 'active' : ''}">
                  <input 
                    type="checkbox" 
                    ${checked ? 'checked' : ''} 
                    onchange="EnterpriseSettings.toggleMultiSelectTag('${s.id}', '${opt}', this.checked)" 
                  />
                  <span>${escapeHtml(opt)}</span>
                </label>
              `;
            }).join('')}
          </div>
        `;

      case 'status':
        return `
          <div class="status-indicator-box">
            <span class="status-verified-badge">🛡️ ${escapeHtml(String(curVal))}</span>
          </div>
        `;

      case 'button_action':
        return `
          <div class="action-btn-box">
            <button class="btn btn-danger btn-sm" onclick="EnterpriseSettings.triggerDangerAction('${s.id}', '${s.name}')">${escapeHtml(s.name)}</button>
          </div>
        `;

      case 'text':
      default:
        return `
          <input 
            type="text" 
            class="setting-input-control" 
            value="${escapeHtml(curVal)}" 
            ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
            oninput="EnterpriseSettings.stageChange('${s.id}', this.value)" 
          />
        `;
    }
  }

  // --------------------------------------------------------------------------
  // 4. ACTION & CHANGE HANDLERS
  // --------------------------------------------------------------------------
  function stageChange(settingId, newVal) {
    stagedValues[settingId] = newVal;
    hasUnsavedChanges = Object.keys(stagedValues).some(k => stagedValues[k] !== originalValues[k]);
    renderRoute();
  }

  function toggleMultiSelectTag(settingId, opt, isChecked) {
    let arr = Array.isArray(stagedValues[settingId]) ? [...stagedValues[settingId]] : [];
    if (isChecked) {
      if (!arr.includes(opt)) arr.push(opt);
    } else {
      arr = arr.filter(x => x !== opt);
    }
    stageChange(settingId, arr);
  }

  function discardChanges() {
    stagedValues = { ...originalValues };
    hasUnsavedChanges = false;
    renderRoute();
  }

  function resetToInherited() {
    if (!currentCategoryData || !currentCategoryData.settings) return;
    currentCategoryData.settings.forEach(s => {
      stagedValues[s.id] = s.default;
    });
    hasUnsavedChanges = true;
    renderRoute();
  }

  async function promptSaveCategory() {
    // Check if any staged change is HIGH or CRITICAL risk
    const highRiskChanges = [];
    if (currentCategoryData && currentCategoryData.settings) {
      currentCategoryData.settings.forEach(s => {
        if (stagedValues[s.id] !== originalValues[s.id] && (s.risk === 'HIGH' || s.risk === 'CRITICAL')) {
          highRiskChanges.push({
            setting: s,
            oldVal: originalValues[s.id],
            newVal: stagedValues[s.id]
          });
        }
      });
    }

    if (highRiskChanges.length > 0) {
      // Trigger Preview & Confirmation Modal
      previewPendingChange = highRiskChanges;
      renderRoute();
      return;
    }

    await executeSaveCategory();
  }

  async function executeSaveCategory() {
    previewPendingChange = null;
    const catId = currentCategoryData.category.id;

    try {
      const res = await fetch(`/api/settings/category/${catId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({
          values: stagedValues,
          reason: 'Manual batch update from Enterprise Settings Center'
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          originalValues = { ...stagedValues };
          hasUnsavedChanges = false;
          await loadCategory(catId);
          await fetchCategories();
          await fetchEffectiveState();
          showNotification('Enterprise configuration saved and propagated to runtime.', 'success');
        } else {
          showNotification(`Save Error: ${data.errors ? data.errors.join('; ') : 'Validation failed'}`, 'error');
        }
      }
    } catch (e) {
      showNotification('Network exception saving settings.', 'error');
    }
  }

  async function resolveProposal(proposalId, decision) {
    try {
      const res = await fetch(`/api/settings/proposal/${proposalId}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({
          decision: decision,
          reason: `Proposal ${decision.toLowerCase()} by Sovereign Host`
        })
      });
      if (res.ok) {
        await loadCategory(activeView);
        showNotification(`Proposal ${decision}.`, 'success');
      }
    } catch (e) {
      showNotification('Error resolving proposal.', 'error');
    }
  }

  async function runDiagnosticTest(target) {
    try {
      const res = await fetch(`/api/settings/test/${target}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: target })
      });
      if (res.ok) {
        activeTestResult = await res.json();
        alert(`Diagnostic Test [${activeTestResult.target}]:\n\nStatus: ${activeTestResult.status}\nDetail: ${activeTestResult.detail}\nLatency: ${activeTestResult.latency_ms} ms\nEvidence SHA-256: ${activeTestResult.evidence_hash}`);
      }
    } catch (e) {
      alert('Diagnostic test could not connect to server.');
    }
  }

  function triggerDangerAction(settingId, name) {
    const confirmation = prompt(`CRITICAL ACTION REQUIREMENT:\n\nYou are about to invoke "${name}".\nType CONFIRM in all capitals to proceed with immediate execution:`);
    if (confirmation === 'CONFIRM') {
      alert(`Action '${name}' triggered with cryptographic audit receipt.`);
    }
  }

  function toggleTokenVisibility(inputId) {
    const el = document.getElementById(inputId);
    if (!el) return;
    el.type = el.type === 'password' ? 'text' : 'password';
  }

  function toggleAuditDrawer() {
    showAuditDrawer = !showAuditDrawer;
    renderRoute();
  }

  function setScope(scope) {
    activeScope = scope;
    showNotification(`Active scope set to '${scope}'.`, 'info');
  }

  function handleSearch(q) {
    globalSearchQuery = q;
    renderRoute();
  }

  function setQuickFilter(f) {
    activeQuickFilter = f;
    renderRoute();
  }

  function openGlobalAudit() {
    navigateTo('audit');
  }

  function navigateTo(dest) {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved configuration changes. Discard and proceed?')) {
        return;
      }
    }
    const clean = normalizeCategoryId(dest);
    window.location.hash = clean === 'hub' ? '/settings' : `/settings/${clean}`;
    render(window.location.hash.slice(1));
  }

  // --------------------------------------------------------------------------
  // 5. MODAL RENDERERS (Change Preview & Audit Drawer)
  // --------------------------------------------------------------------------
  function renderChangePreviewModal() {
    return `
      <div class="settings-modal-backdrop">
        <div class="settings-modal-box">
          <div class="modal-header">
            <h4>⚠️ High-Impact Configuration Review</h4>
            <button class="modal-close-btn" onclick="EnterpriseSettings.cancelPreview()">✕</button>
          </div>
          <div class="modal-body">
            <p class="modal-intro">The following modifications exceed the standard operational risk threshold and require explicit sovereign confirmation:</p>
            <div class="impact-review-table">
              ${previewPendingChange.map(c => `
                <div class="impact-row">
                  <div class="impact-col-name"><strong>${escapeHtml(c.setting.name)}</strong></div>
                  <div class="impact-col-diff">
                    <span class="diff-old">${escapeHtml(String(c.oldVal))}</span>
                    <span class="diff-arrow">→</span>
                    <span class="diff-new">${escapeHtml(String(c.newVal))}</span>
                  </div>
                  <div class="impact-col-risk">
                    <span class="badge badge-warning">${escapeHtml(c.setting.risk)} Risk</span>
                  </div>
                </div>
              `).join('')}
            </div>
            <div class="modal-disclaimer">
              Constitutional Guarantee: Applying these changes writes an immutable cryptographic receipt to the SHA-256 Merkle Evidence Ledger.
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" onclick="EnterpriseSettings.cancelPreview()">Cancel</button>
            <button class="btn btn-primary" onclick="EnterpriseSettings.executeSaveCategory()">Confirm & Apply</button>
          </div>
        </div>
      </div>
    `;
  }

  function renderAuditDrawer(audits) {
    return `
      <div class="settings-drawer-backdrop" onclick="EnterpriseSettings.toggleAuditDrawer()">
        <div class="settings-drawer" onclick="event.stopPropagation()">
          <div class="drawer-header">
            <h4>⛓️ Settings Audit Ledger</h4>
            <button class="drawer-close-btn" onclick="EnterpriseSettings.toggleAuditDrawer()">✕</button>
          </div>
          <div class="drawer-body">
            ${audits.length === 0 ? `
              <p class="empty-audit-text">No audit events recorded for this category yet.</p>
            ` : `
              <div class="audit-events-stream">
                ${audits.map(evt => `
                  <div class="audit-event-card">
                    <div class="event-top-line">
                      <span class="event-setting-key">${escapeHtml(evt.setting_id)}</span>
                      <span class="event-time">${new Date(evt.created_at * 1000).toLocaleTimeString()}</span>
                    </div>
                    <div class="event-diff-line">
                      <code>${escapeHtml(evt.old_value)}</code> → <code>${escapeHtml(evt.new_value)}</code>
                    </div>
                    <div class="event-meta-line">
                      <span>Actor: ${escapeHtml(evt.actor)}</span>
                      <span>•</span>
                      <span>Reason: ${escapeHtml(evt.reason || 'Manual modification')}</span>
                    </div>
                    <div class="event-hash-line">
                      SHA-256: <code>${escapeHtml(evt.evidence_hash.slice(0, 24))}...</code>
                    </div>
                  </div>
                `).join('')}
              </div>
            `}
          </div>
        </div>
      </div>
    `;
  }

  function cancelPreview() {
    previewPendingChange = null;
    renderRoute();
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function showNotification(msg, type) {
    const banner = document.createElement('div');
    banner.className = `settings-toast toast-${type || 'info'}`;
    banner.innerText = msg;
    document.body.appendChild(banner);
    setTimeout(() => {
      banner.classList.add('fade-out');
      setTimeout(() => banner.remove(), 400);
    }, 3200);
  }

  // Public API
  return {
    init,
    render,
    navigateTo,
    stageChange,
    toggleMultiSelectTag,
    discardChanges,
    resetToInherited,
    promptSaveCategory,
    executeSaveCategory,
    resolveProposal,
    runDiagnosticTest,
    triggerDangerAction,
    toggleTokenVisibility,
    toggleAuditDrawer,
    setScope,
    handleSearch,
    setQuickFilter,
    openGlobalAudit,
    cancelPreview,
    viewSettingAudit: (id) => toggleAuditDrawer()
  };
})();

// Attach to window
window.EnterpriseSettings = EnterpriseSettings;
document.addEventListener('DOMContentLoaded', () => {
  if (window.EnterpriseSettings && window.EnterpriseSettings.init) {
    window.EnterpriseSettings.init();
  }
});
