/**
 * ZONATA — Tools & Universal Capability Layer + Real Tool Factory
 * Production implementation: Real capability registry • 10-step resolution sequence • Governed tool builder & testing
 */

const ToolsFactory = (function() {
  let toolsList = [];
  let filterCategory = 'all';
  let searchQuery = '';
  let activeView = 'registry'; // 'registry' | 'factory' | 'detail' | 'discovery'
  let selectedToolId = null;

  // Active builder state
  let builderState = {
    step: 1, // 1: Requirement, 2: Strategy, 3: Build Plan, 4: Builder Code, 5: Sandbox Testing, 6: Registration
    requirement: '',
    purpose: '',
    inputs: '',
    outputs: '',
    constraints: 'Sandboxed read/write only. Zero unencrypted secret exposure.',
    runtime: 'Python 3 Sandboxed',
    category: 'Custom Automation',
    permissions: ['Filesystem read', 'Network access'],
    specText: '',
    strategyEval: null,
    discovery: null,
    discoveryError: null,
    sourceCode: '',
    testResults: [],
    buildError: null,
    builtTool: null
  };

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Discovery state
  let discoveryQuery = '';
  let discoveryResult = null;
  let isSearching = false;

  async function init() {
    await fetchTools();
  }

  async function fetchTools() {
    try {
      const res = await fetch('/api/tools');
      if (res.ok) {
        const data = await res.json();
        toolsList = data.tools || [];
      }
    } catch(e) {
      console.log('Error fetching live tools:', e);
      toolsList = [];
    }
  }

  // ------------------------------------------------------------------------
  // ROUTE RENDERER
  // ------------------------------------------------------------------------
  async function render(route, containerOrId) {
    const container = typeof containerOrId === 'string'
      ? document.getElementById(containerOrId)
      : (containerOrId || document.getElementById('view-tools'));
    if (!container) return;

    if (toolsList.length === 0) {
      await fetchTools();
    }

    if (route === '/tools/factory') {
      renderFactoryWorkspace(container);
    } else if (route.startsWith('/tools/') && route.split('/').length === 3) {
      const toolId = route.split('/')[2];
      renderToolDetail(container, toolId);
    } else {
      renderToolsRegistry(container);
    }
  }

  // ------------------------------------------------------------------------
  // 1. TOOL REGISTRY VIEW (Real Data from CapabilityRegistry & Host Fabric)
  // ------------------------------------------------------------------------
  function renderToolsRegistry(container) {
    let filtered = toolsList.filter(t => {
      const matchesCat = filterCategory === 'all' || 
        t.category.toLowerCase().includes(filterCategory.toLowerCase()) ||
        t.source.toLowerCase().includes(filterCategory.toLowerCase());
      const matchesSearch = !searchQuery || 
        t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.description && t.description.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesCat && matchesSearch;
    });

    container.innerHTML = `
      <div class="tool-fabric-header">
        <div>
          <h2 style="font-size:24px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">
            Tools & Capabilities
          </h2>
          <p style="font-size:13px; color:var(--text-secondary);">
            Capabilities available to ZONATA and tools it can create, connect and operate.
          </p>
        </div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn-secondary" onclick="ToolsFactory.openDiscoveryPrompt()" style="font-size:12.5px; padding:8px 14px;">
            🔍 Find a Capability
          </button>
          <button class="btn-primary" onclick="window.navigateTo('/tools/factory')" style="font-size:12.5px; padding:8px 16px;">
            + Build a Tool
          </button>
        </div>
      </div>

      <!-- Capability Discovery Prompt Box -->
      <div class="tool-search-discovery-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <div>
            <h4 style="font-size:14px; font-weight:700; color:var(--text-primary);">Autonomous Capability Resolution</h4>
            <p style="font-size:12px; color:var(--text-secondary);">Describe a business requirement. ZONATA searches registered capabilities, connected software, browser automation, and desktop fabric before offering to build a new tool.</p>
          </div>
        </div>
        <div style="display:flex; gap:10px;">
          <input type="text" id="quickCapabilityQuery" class="form-input" style="flex:1;" placeholder="What do you need ZONATA to do? (e.g. 'Create and send invoices through my accounting system')" onkeydown="if(event.key==='Enter') ToolsFactory.resolveCapability(this.value)" />
          <button class="btn-primary" onclick="ToolsFactory.resolveCapability(document.getElementById('quickCapabilityQuery').value)" style="padding:8px 18px; font-size:12.5px;">
            Evaluate Capability
          </button>
        </div>

        <div id="capabilityResolutionResult" style="margin-top:14px; display:none;">
          <!-- Injected dynamically by resolveCapability -->
        </div>
      </div>

      <!-- Controls & Filter Bar -->
      <div class="company-controls-bar">
        <div class="company-search-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" placeholder="Search registered tools..." value="${searchQuery}" oninput="ToolsFactory.handleSearch(this.value)" />
        </div>

        <select class="company-filter-select" onchange="ToolsFactory.handleCategoryFilter(this.value)">
          <option value="all" ${filterCategory==='all'?'selected':''}>All Categories (${toolsList.length})</option>
          <option value="Desktop" ${filterCategory==='Desktop'?'selected':''}>Desktop & Robot Fabric</option>
          <option value="Operating System" ${filterCategory==='Operating System'?'selected':''}>Operating System</option>
          <option value="Browser" ${filterCategory==='Browser'?'selected':''}>Browser Automation</option>
          <option value="Connected Service" ${filterCategory==='Connected Service'?'selected':''}>Connected Integrations</option>
          <option value="Development" ${filterCategory==='Development'?'selected':''}>Development & CLI</option>
          <option value="User Created" ${filterCategory==='User Created'?'selected':''}>User Created / Factory</option>
        </select>
      </div>

      <!-- Tool Registry Table -->
      <div class="company-table-container">
        <table class="enterprise-data-table">
          <thead>
            <tr>
              <th>Tool Name</th>
              <th>Category</th>
              <th>Source</th>
              <th>Availability</th>
              <th>Permission Required</th>
              <th>Health</th>
              <th>Last Verified</th>
              <th style="text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${filtered.map(t => `
              <tr onclick="window.navigateTo('/tools/${t.id}')" style="cursor:pointer;">
                <td>
                  <div style="font-weight:600; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                    ${t.name}
                  </div>
                  <div style="font-size:11.5px; color:var(--text-muted);">${t.description || 'System capability'}</div>
                </td>
                <td><span class="badge badge-blue">${t.category}</span></td>
                <td><span class="badge ${t.source==='Host Fabric'?'badge-emerald':t.source==='User Created'?'badge-purple':'badge-blue'}">${t.source}</span></td>
                <td>
                  <span style="font-size:12px; font-weight:600; color:${t.availability==='Available'?'var(--accent-emerald)':'var(--accent-amber)'};">
                    ● ${t.availability}
                  </span>
                </td>
                <td><code style="font-size:11px; background:var(--bg-input); padding:2px 6px; border-radius:4px; border:1px solid var(--border-color);">${t.permission}</code></td>
                <td><span style="color:var(--accent-emerald); font-size:12px;">● ${t.health || 'Healthy'}</span></td>
                <td><span style="font-size:12px; color:var(--text-muted);">${t.last_verified || 'Realtime'}</span></td>
                <td style="text-align:right;">
                  <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px;" onclick="event.stopPropagation(); window.navigateTo('/tools/${t.id}')">
                    Inspect
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  // ------------------------------------------------------------------------
  // 2. CAPABILITY RESOLUTION ENGINE ("Find a Capability")
  // ------------------------------------------------------------------------
  async function resolveCapability(query) {
    if (!query || !query.trim()) return;
    const resBox = document.getElementById('capabilityResolutionResult');
    if (!resBox) return;

    resBox.style.display = 'block';
    resBox.innerHTML = `
      <div style="padding:16px; background:var(--bg-card); border-radius:var(--radius-sm); border:1px solid var(--border-color); font-size:12.5px;">
        <span class="status-pulse-dot" style="background:var(--accent-blue);"></span> Evaluating capability resolution sequence...
      </div>
    `;

    try {
      const res = await fetch('/api/tools/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requirement: query.trim() })
      });

      if (res.ok) {
        const data = await res.json();
        renderResolutionResult(resBox, data, query);
      } else {
        resBox.innerHTML = `<div style="color:var(--accent-rose); font-size:12.5px;">Failed to evaluate capability.</div>`;
      }
    } catch(e) {
      resBox.innerHTML = `<div style="color:var(--accent-rose); font-size:12.5px;">Network error: ${e.message}</div>`;
    }
  }

  function renderResolutionResult(container, data, origQuery) {
    const steps = data.evaluation_steps || [];
    const candidates = data.candidates || [];
    const blocked = data.blocked_candidates || [];
    const stepColor = (st) => {
      if (st === 'AVAILABLE' || st === 'MATCHED' || st === 'COMPLETED') return 'var(--accent-emerald)';
      if (st === 'NO_MATCH' || st === 'SKIPPED') return 'var(--text-muted)';
      return 'var(--accent-amber)';
    };
    const statusColor = (st) => st === 'AVAILABLE' ? 'var(--accent-emerald)' : 'var(--accent-amber)';

    container.innerHTML = `
      <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:16px;">
        <div style="font-size:12px; text-transform:uppercase; color:var(--accent-blue); font-weight:700; margin-bottom:10px;">
          Resolution Sequence Results
        </div>

        <div style="display:flex; flex-direction:column; gap:6px; margin-bottom:16px;">
          ${steps.map(st => `
            <div class="resolution-step-box">
              <span>${st.step}</span>
              <span class="resolution-step-status" style="color:${stepColor(st.status)};">${st.status}</span>
            </div>
            <div style="font-size:11.5px; color:var(--text-muted); padding:0 10px 4px;">${st.detail || ''}</div>
          `).join('')}
        </div>

        ${data.found && data.capability ? `
          <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25); border-radius:var(--radius-sm); padding:14px; margin-bottom:14px;">
            <div style="font-size:13px; font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
              <span>✓ Usable Capability Found</span>
              <span class="badge badge-emerald">${data.capability.status}</span>
            </div>
            <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
              <strong>${data.capability.name}</strong> • ${data.capability.capability}
            </div>
            <div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">
              Source: ${data.capability.source} • Permission: ${data.capability.permission}
            </div>
            <div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">
              ${data.capability.detail || ''}
            </div>
          </div>
        ` : ''}

        ${blocked.length > 0 ? `
          <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); border-radius:var(--radius-sm); padding:14px; margin-bottom:14px;">
            <div style="font-size:13px; font-weight:700; color:var(--text-primary);">
              ${data.found ? 'Other matching capabilities are not ready' : 'Matching capabilities exist but are not usable'}
            </div>
            <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
              ${data.reason || ''}
            </div>
            <div style="display:flex; flex-direction:column; gap:8px; margin-top:12px;">
              ${blocked.map(c => `
                <div style="background:var(--bg-input); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px 12px;">
                  <div style="display:flex; justify-content:space-between; gap:8px;">
                    <strong style="font-size:12.5px;">${c.name}</strong>
                    <span style="font-size:11px; font-weight:700; color:${statusColor(c.status)};">${c.status}</span>
                  </div>
                  <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">${c.detail || ''}</div>
                  ${(c.required_prerequisites && c.required_prerequisites.length) ? `
                    <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;">
                      Required: <code style="font-family:var(--font-mono);">${c.required_prerequisites.join(', ')}</code>
                    </div>
                  ` : ''}
                  <div style="font-size:11.5px; color:var(--accent-blue); margin-top:4px;">${c.action || ''}</div>
                </div>
              `).join('')}
            </div>
            <div style="margin-top:12px;">
              <button class="btn-secondary" style="font-size:12px; padding:6px 14px;" onclick="window.navigateTo('/settings')">
                Open Integration Settings →
              </button>
            </div>
          </div>
        ` : ''}

        ${!data.found && blocked.length === 0 ? `
          <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); border-radius:var(--radius-sm); padding:14px; margin-bottom:14px;">
            <div style="font-size:13px; font-weight:700; color:var(--text-primary);">
              No Registered Capability Satisfies This Request
            </div>
            <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
              ${data.reason || 'Nothing in the local registry, connector registry, or installed runtimes matched.'}
            </div>
            <div style="margin-top:12px;">
              <button class="btn-primary" style="font-size:12px; padding:7px 16px;" onclick="ToolsFactory.startToolBuilderFromQuery('${encodeURIComponent(origQuery)}')">
                Launch Tool Factory to Build Capability →
              </button>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  // ------------------------------------------------------------------------
  // 3. REAL TOOL FACTORY WORKSPACE (/tools/factory)
  // ------------------------------------------------------------------------
  function renderFactoryWorkspace(container) {
    container.innerHTML = `
      <div style="margin-bottom:20px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
        <div>
          <div style="font-size:11.5px; font-weight:700; text-transform:uppercase; color:var(--accent-blue); letter-spacing:0.05em; margin-bottom:4px;">
            ZONATA Autonomous Execution Engine
          </div>
          <h2 style="font-size:24px; font-weight:700; color:var(--text-primary); margin-bottom:2px;">
            The Tool Factory
          </h2>
          <p style="font-size:13px; color:var(--text-secondary);">
            Meta-capability resolution: When an autonomous mission requires a tool that does not yet exist, synthesize, sandbox-test, and verify it here.
          </p>
        </div>
        <button class="btn-secondary" onclick="window.navigateTo('/tools')" style="font-size:12.5px; padding:7px 14px;">
          ← Back to Registry
        </button>
      </div>

      <!-- Factory Step Tabs -->
      <div class="factory-step-tabs">
        <button class="factory-step-tab ${builderState.step===1?'active':''}" onclick="ToolsFactory.setBuilderStep(1)">1. Requirement</button>
        <button class="factory-step-tab ${builderState.step===2?'active':''}" onclick="ToolsFactory.setBuilderStep(2)">2. Source Strategy</button>
        <button class="factory-step-tab ${builderState.step===3?'active':''}" onclick="ToolsFactory.setBuilderStep(3)">3. Build Plan</button>
        <button class="factory-step-tab ${builderState.step===4?'active':''}" onclick="ToolsFactory.setBuilderStep(4)">4. Specification</button>
        <button class="factory-step-tab ${builderState.step===5?'active':''}" onclick="ToolsFactory.setBuilderStep(5)">5. Sandboxed Verification</button>
        <button class="factory-step-tab ${builderState.step===6?'active':''}" onclick="ToolsFactory.setBuilderStep(6)">6. Registration</button>
      </div>

      <!-- Step Content Card -->
      <div class="onboarding-form-card">
        ${renderFactoryStepContent()}
      </div>
    `;
  }

  function renderFactoryStepContent() {
    switch(builderState.step) {
      case 1:
        return `
          <div class="onboarding-section-header">
            <h3 class="onboarding-section-title">Step 1 — Define Capability Requirement</h3>
            <p class="onboarding-section-subtitle">Specify what functional gap must be solved for enterprise operations.</p>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
            <div class="form-group">
              <label class="form-label">Tool Name *</label>
              <input type="text" class="form-input" id="bfName" value="${builderState.builtTool ? builderState.builtTool.name : (builderState.purpose ? builderState.purpose.split(' ')[0] + ' Tool' : 'Invoice Reconciliation Bot')}" placeholder="e.g. PDF Contract Clause Parser" />
            </div>
            <div class="form-group">
              <label class="form-label">Target Capability Category</label>
              <select class="form-input" id="bfCat">
                <option value="Financial & Accounting">Financial & Accounting</option>
                <option value="Document Intelligence">Document Intelligence</option>
                <option value="Browser Automation">Browser Automation</option>
                <option value="System & CLI">System & CLI</option>
                <option value="Customer Messaging">Customer Messaging</option>
              </select>
            </div>
          </div>
          <div class="form-group" style="margin-top:14px;">
            <label class="form-label">Exact Functional Requirement & Expected Outcome *</label>
            <textarea class="form-input" rows="3" id="bfReq" placeholder="Describe the operational inputs, required transformations, and physical output...">Create and send invoices through my accounting system and reconcile bank transaction logs.</textarea>
          </div>
          <div style="display:flex; justify-content:flex-end; margin-top:20px;">
            <button class="btn-primary" onclick="ToolsFactory.advanceToStrategy()">
              Evaluate Strategy →
            </button>
          </div>
        `;

      case 2:
        const disc = builderState.discovery;
        const discCandidates = disc ? (disc.candidates || []) : [];
        const discBlocked = disc ? (disc.blocked_candidates || []) : [];
        return `
          <div class="onboarding-section-header">
            <h3 class="onboarding-section-title">Step 2 — Tool Source Strategy Evaluation</h3>
            <p class="onboarding-section-subtitle">Live discovery against this deployment's registry, connectors, and installed runtimes.</p>
          </div>

          ${builderState.discoveryError ? `
            <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:var(--radius-sm); padding:12px 16px; margin-bottom:16px; font-size:12.5px; color:var(--text-secondary);">
              ${escapeHtml(builderState.discoveryError)} Re-run discovery before building a new tool.
            </div>
          ` : ''}

          ${!disc ? `
            <div style="background:var(--bg-card); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--border-color); font-size:12.5px; color:var(--text-secondary);">
              Running discovery…
            </div>
          ` : `
            <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:20px;">
              ${discCandidates.length === 0 && discBlocked.length === 0 ? `
                <div style="background:var(--bg-card); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
                  <strong>No existing capability matched</strong>
                  <div style="font-size:11.5px; color:var(--text-secondary);">
                    ${escapeHtml(disc.reason || 'Nothing in the local registry, connector registry, or installed runtimes matched.')}
                  </div>
                </div>
              ` : ''}
              ${discCandidates.map(c => `
                <div style="background:var(--bg-card); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center; gap:10px;">
                  <div>
                    <strong>${escapeHtml(c.name)}</strong>
                    <div style="font-size:11.5px; color:var(--text-secondary);">${escapeHtml(c.detail || c.capability || '')}</div>
                  </div>
                  <span class="badge ${c.status === 'AVAILABLE' ? 'badge-emerald' : 'badge-amber'}">${escapeHtml(c.status)}</span>
                </div>
              `).join('')}
              ${discBlocked.map(c => `
                <div style="background:var(--bg-card); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center; gap:10px;">
                  <div>
                    <strong>${escapeHtml(c.name)}</strong>
                    <div style="font-size:11.5px; color:var(--text-secondary);">${escapeHtml(c.detail || '')}</div>
                    ${(c.required_prerequisites && c.required_prerequisites.length) ? `<div style="font-size:11.5px; color:var(--text-muted);">Requires: ${escapeHtml(c.required_prerequisites.join(', '))}</div>` : ''}
                  </div>
                  <span class="badge badge-amber">${escapeHtml(c.status)}</span>
                </div>
              `).join('')}
              <div style="background:var(--bg-card); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <strong>Platform recommendation</strong>
                  <div style="font-size:11.5px; color:var(--text-secondary);">
                    ${disc.recommendation === 'USE_EXISTING' ? 'Use the existing capability rather than duplicating it.' :
                      disc.recommendation === 'CONFIGURE_EXISTING' ? 'Configure the matching connector before building anything new.' :
                      'No usable capability exists; a new governed tool is the only path forward.'}
                  </div>
                </div>
                <span class="badge badge-blue">${escapeHtml(disc.recommendation || 'UNKNOWN')}</span>
              </div>
            </div>
          `}

          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary" onclick="ToolsFactory.setBuilderStep(1)">← Back</button>
            <button class="btn-primary" onclick="ToolsFactory.advanceToBuildPlan()">Continue to Build Plan →</button>
          </div>
        `;

      case 3:
        return `
          <div class="onboarding-section-header">
            <h3 class="onboarding-section-title">Step 3 — Tool Build Plan & Governance Matrix</h3>
            <p class="onboarding-section-subtitle">Security boundaries, dependencies, and testing assertions.</p>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:20px;">
            <div style="background:var(--bg-input); padding:14px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Target Runtime</div>
              <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin-top:2px;">Python 3 (Sandboxed Process)</div>
            </div>
            <div style="background:var(--bg-input); padding:14px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Declared Permissions</div>
              <div style="font-size:13px; font-weight:600; color:var(--accent-blue); margin-top:2px;">${escapeHtml((builderState.permissions || []).join(', ') || 'None declared')}</div>
            </div>
            <div style="background:var(--bg-input); padding:14px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Rollback Procedure</div>
              <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin-top:2px;">Not defined until the tool has real side effects</div>
            </div>
            <div style="background:var(--bg-input); padding:14px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Authority Ceiling</div>
              <div style="font-size:13px; font-weight:600; color:var(--accent-emerald); margin-top:2px;">AUDITED_TRANSACTIONAL</div>
            </div>
          </div>

          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary" onclick="ToolsFactory.setBuilderStep(2)">← Back</button>
            <button class="btn-primary" onclick="ToolsFactory.setBuilderStep(5)">Review Spec &amp; Execute Verification →</button>
          </div>
        `;

      case 4:
      case 5:
        return `
          <div class="onboarding-section-header">
            <h3 class="onboarding-section-title">Step 5 — Sandboxed Verification Pipeline</h3>
            <p class="onboarding-section-subtitle">The Tool Factory runs a real AST security scan and registers the package. Nothing is marked verified until those checks actually run.</p>
          </div>

          <div class="form-group" style="margin-bottom:16px;">
            <label class="form-label">Tool implementation (Python source) *</label>
            <textarea class="form-input" rows="10" id="bfSource" placeholder="def run(inputs):&#10;    # Return a JSON-serialisable result.&#10;    return {&quot;ok&quot;: True}"
              style="font-family:var(--font-mono); font-size:12px;">${escapeHtml(builderState.sourceCode || '')}</textarea>
            <div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">
              Disallowed imports (os, subprocess, socket, ctypes, pty) and dynamic calls (eval, exec, __import__, compile, open) are rejected by the AST scanner.
            </div>
          </div>

          <div style="display:flex; gap:10px; margin-bottom:16px;">
            <button class="btn-primary" onclick="ToolsFactory.runVerification()">
              Run Security Scan & Register
            </button>
          </div>

          ${builderState.buildError ? `
            <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:var(--radius-sm); padding:12px 16px; margin-bottom:16px; font-size:12.5px; color:var(--text-secondary);">
              <strong style="color:var(--accent-rose);">${escapeHtml(builderState.buildError.code || 'BUILD_FAILED')}</strong> —
              ${escapeHtml(builderState.buildError.detail || builderState.buildError.error || '')}
            </div>
          ` : ''}

          <div class="testing-pipeline-grid">
            ${(builderState.testResults.length > 0 ? builderState.testResults : [
              { stage: 'Static security scan', status: 'NOT_RUN', detail: 'Provide source code and run verification.' },
              { stage: 'Sandbox policy', status: 'NOT_RUN', detail: 'Applied only after the scan passes.' },
              { stage: 'Code signature', status: 'NOT_RUN', detail: 'Generated on registration.' },
              { stage: 'Registry write', status: 'NOT_RUN', detail: 'No package registered yet.' }
            ]).map(r => `
              <div class="pipeline-stage-card">
                <div class="pipeline-stage-title">
                  <span>${escapeHtml(r.stage)}</span>
                  <span class="badge ${r.status === 'Passed' ? 'badge-emerald' : 'badge-amber'}">${escapeHtml(r.status)}</span>
                </div>
                <div style="font-size:11.5px; color:var(--text-secondary);">${escapeHtml(r.detail || '')}</div>
              </div>
            `).join('')}
          </div>

          <div style="display:flex; justify-content:space-between; margin-top:20px;">
            <button class="btn-secondary" onclick="ToolsFactory.setBuilderStep(3)">← Back</button>
            <button class="btn-primary" onclick="ToolsFactory.executeRegistration()" ${builderState.builtTool ? '' : 'disabled'}>
              Continue to Registration →
            </button>
          </div>
        `;

      case 6:
        const t = builderState.builtTool || {};
        return `
          <div class="onboarding-section-header">
            <h3 class="onboarding-section-title">Step 6 — Tool Registered</h3>
            <p class="onboarding-section-subtitle">The package passed the static security scan and is now in this tenant's tool registry.</p>
          </div>

          <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:20px; margin-bottom:20px;">
            <div style="font-size:16px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">
              ${escapeHtml(t.name || 'Unnamed tool')}
            </div>
            <div style="font-size:12.5px; color:var(--accent-emerald); font-weight:600; margin-bottom:12px;">
              ● Registered — not yet executed
            </div>
            <div style="font-size:12px; color:var(--text-secondary); line-height:1.6;">
              Tool ID: <code style="font-family:var(--font-mono);">${escapeHtml(t.id || '—')}</code><br>
              Version: ${escapeHtml(t.version || '—')} • Risk class: ${escapeHtml(t.risk_class || '—')}<br>
              Signature: <code style="font-family:var(--font-mono);">${escapeHtml(t.signature || '—')}</code>
            </div>
            <p style="font-size:12.5px; color:var(--text-muted); line-height:1.5; margin-top:12px;">
              Registration proves the package passed static inspection. It does not prove runtime behaviour:
              run the tool under a governed ActionContract to produce execution evidence.
            </p>
          </div>

          <button class="btn-primary" onclick="window.navigateTo('/tools')" style="padding:9px 20px;">
            Return to Tools Registry
          </button>
        `;

    }
  }

  // ------------------------------------------------------------------------
  // 4. TOOL DETAIL PAGE (/tools/:toolId)
  // ------------------------------------------------------------------------
  function renderToolDetail(container, toolId) {
    const tool = toolsList.find(t => t.id === toolId);
    if (!tool) {
      container.innerHTML = `
        <div class="company-empty-state-pro">
          <h3>Tool Not Found</h3>
          <p>No registered capability with ID '${toolId}' exists.</p>
          <button class="btn-primary" onclick="window.navigateTo('/tools')">Return to Registry</button>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="margin-bottom:20px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
        <div>
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span class="badge badge-blue">${tool.category}</span>
            <span class="badge ${tool.source==='Host Fabric'?'badge-emerald':'badge-purple'}">${tool.source}</span>
            <span style="font-size:12px; font-weight:600; color:${tool.availability==='Available'?'var(--accent-emerald)':'var(--accent-amber)'};">● ${tool.availability}</span>
          </div>
          <h2 style="font-size:24px; font-weight:700; color:var(--text-primary); margin-bottom:2px;">${tool.name}</h2>
          <div style="font-size:12.5px; color:var(--text-muted); font-family:var(--font-mono);">${tool.id}</div>
        </div>
        <div style="display:flex; gap:10px;">
          <button class="btn-secondary" onclick="ToolsFactory.testToolProbe('${tool.id}')" style="font-size:12.5px; padding:7px 14px;">
            Test Run Probe
          </button>
          <button class="btn-secondary" onclick="window.navigateTo('/tools')" style="font-size:12.5px; padding:7px 14px;">
            ← Back to Registry
          </button>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:24px;">
        <div class="card">
          <div class="card-title-bar">
            <h3 class="card-title">Capability Specification</h3>
          </div>
          <div style="font-size:13px; color:var(--text-secondary); line-height:1.5;">
            ${tool.description || 'Native capability contract executed via Universal Control Kernel.'}
          </div>
          <div style="margin-top:14px; font-size:12px; color:var(--text-muted);">
            Binary / Interface Path: <code style="font-family:var(--font-mono);">${tool.path || 'Kernel Internal Hook'}</code>
          </div>
        </div>

        <div class="card">
          <div class="card-title-bar">
            <h3 class="card-title">Permission & Authority Boundary</h3>
          </div>
          <div style="display:flex; flex-direction:column; gap:8px;">
            <div style="display:flex; justify-content:space-between; font-size:12.5px;">
              <span>Authority Required:</span>
              <strong style="color:var(--accent-blue);">${tool.permission}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12.5px;">
              <span>Health Status:</span>
              <strong style="color:${['Healthy','Registered'].includes(tool.health) ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">${escapeHtml(tool.health || 'Unknown')}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12.5px;">
              <span>Last Cryptographic Check:</span>
              <span>${tool.last_verified || 'Active'}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Danger Zone -->
      <div class="settings-danger-box">
        <h4 style="font-size:14px; font-weight:700; color:var(--accent-rose); margin-bottom:4px;">Disable Capability</h4>
        <p style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">
          Disabling this capability will prevent all AI workforce members from invoking it during automated mission executions.
        </p>
        <button class="btn-secondary" style="color:var(--accent-rose); border-color:var(--accent-rose); font-size:12px;" onclick="ToolsFactory.disableTool('${tool.id}')">
          Disable Tool
        </button>
      </div>
    `;
  }

  // ------------------------------------------------------------------------
  // ACTIONS & HANDLERS
  // ------------------------------------------------------------------------
  function setBuilderStep(step) {
    builderState.step = step;
    render('/tools/factory');
  }

  async function advanceToStrategy() {
    const req = (document.getElementById('bfReq')?.value || '').trim();
    const name = (document.getElementById('bfName')?.value || '').trim();
    const cat = document.getElementById('bfCat')?.value || 'Custom Automation';
    if (!req) {
      showToast('Describe the functional requirement first.', 'warning');
      return;
    }
    builderState.requirement = req;
    builderState.purpose = req;
    builderState.category = cat;
    builderState.builtTool = { name: name || 'Custom Tool' };
    builderState.discovery = null;
    builderState.discoveryError = null;
    builderState.step = 2;
    render('/tools/factory');

    try {
      const res = await fetch('/api/tools/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requirement: req })
      });
      if (res.ok) {
        builderState.discovery = await res.json();
      } else {
        builderState.discoveryError = `Discovery failed with HTTP ${res.status}.`;
      }
    } catch (e) {
      builderState.discoveryError = `Discovery request failed: ${e.message}`;
    }
    render('/tools/factory');
  }

  function advanceToBuildPlan() {
    builderState.step = 3;
    render('/tools/factory');
  }

  async function runVerification() {
    const source = (document.getElementById('bfSource')?.value || '').trim();
    builderState.sourceCode = source;
    builderState.buildError = null;

    if (!source) {
      builderState.buildError = {
        code: 'MISSING_SOURCE_CODE',
        detail: 'Enter the Python implementation before running verification.'
      };
      builderState.testResults = [{
        stage: 'Static security scan',
        status: 'NOT_RUN',
        detail: 'No source code was supplied.'
      }];
      render('/tools/factory');
      return;
    }

    builderState.testResults = [{
      stage: 'Static security scan',
      status: 'Running',
      detail: 'Submitting source code to the Tool Factory AST scanner…'
    }];
    render('/tools/factory');

    try {
      const res = await fetch('/api/tools/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: (builderState.builtTool && builderState.builtTool.name) || 'Custom Tool',
          purpose: builderState.requirement,
          category: builderState.category,
          risk_class: 'LOW_RISK',
          permissions: builderState.permissions,
          source_code: source
        })
      });
      const json = await res.json();
      builderState.testResults = json.test_results || [];
      if (res.ok) {
        builderState.builtTool = json.tool;
        builderState.buildError = null;
        showToast('Tool registered in the tenant tool registry.', 'success');
        await fetchTools();
      } else {
        builderState.buildError = {
          code: json.code || ('HTTP_' + res.status),
          detail: json.detail || json.error || 'The tool was rejected.'
        };
        if (!builderState.testResults.length) {
          builderState.testResults = [{
            stage: 'Static security scan',
            status: 'Failed',
            detail: (json.violations || []).join('; ') || 'Rejected.'
          }];
        }
      }
    } catch (e) {
      builderState.buildError = { code: 'NETWORK_ERROR', detail: e.message };
      builderState.testResults = [{
        stage: 'Static security scan',
        status: 'Failed',
        detail: 'The build request could not be completed: ' + e.message
      }];
    }
    render('/tools/factory');
  }

  function executeRegistration() {
    if (!builderState.builtTool || !builderState.builtTool.id) {
      showToast('Run verification first — nothing has been registered yet.', 'warning');
      return;
    }
    builderState.step = 6;
    render('/tools/factory');
  }

  function startToolBuilderFromQuery(encodedQuery) {
    const q = decodeURIComponent(encodedQuery || '');
    builderState.step = 1;
    builderState.requirement = q;
    builderState.purpose = q;
    window.navigateTo('/tools/factory');
  }

  function openDiscoveryPrompt() {
    const el = document.getElementById('quickCapabilityQuery');
    if (el) {
      el.focus();
      el.scrollIntoView({ behavior: 'smooth' });
    }
  }

  async function disableTool(toolId) {
    try {
      const res = await fetch(`/api/tools/${encodeURIComponent(toolId)}/disable`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const json = await res.json();
      if (res.ok) {
        showToast(`${toolId} revoked from the tenant registry.`, 'success');
        await fetchTools();
        render('/tools');
      } else {
        showToast(json.detail || json.error || 'Disable failed.', 'warning');
      }
    } catch (e) {
      showToast(`Disable request failed: ${e.message}`, 'error');
    }
  }

  async function testToolProbe(toolId) {
    try {
      const res = await fetch(`/api/tools/${encodeURIComponent(toolId)}/probe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const json = await res.json();
      if (res.ok && json.status === 'PASSED') {
        showToast(`${toolId}: ${json.detail}`, 'success');
      } else if (res.ok) {
        showToast(`${toolId}: ${json.detail || json.status}`, 'warning');
      } else {
        showToast(`${toolId}: ${json.detail || json.error || 'probe failed'}`, 'error');
      }
    } catch (e) {
      showToast(`Probe request failed: ${e.message}`, 'error');
    }
  }

  function handleSearch(val) {
    searchQuery = val;
    render('/tools');
  }
  function handleCategoryFilter(cat) {
    filterCategory = cat;
    render('/tools');
  }

  return {
    init,
    render,
    resolveCapability,
    openDiscoveryPrompt,
    startToolBuilderFromQuery,
    setBuilderStep,
    advanceToStrategy,
    advanceToBuildPlan,
    runVerification,
    executeRegistration,
    testToolProbe,
    disableTool,
    handleSearch,
    handleCategoryFilter
  };
})();

window.ToolsFactory = ToolsFactory;
