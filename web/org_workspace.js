/**
 * ZONATA — Company Organization Workspace
 * Generative organization design, interactive visual org graph, zoom canvas,
 * node inspection drawer, tree view mode, and proposed structure approval.
 */

(function() {
  'use strict';

  class OrgWorkspaceManager {
    constructor() {
      this.viewMode = 'graph'; // 'graph' | 'tree'
      this.zoomLevel = 1.0;
      this.orgData = null;
      this.selectedNode = null;
      this.searchQuery = '';
      this.proposedData = null;
      this.showDiffModal = false;
    }

    async render(containerId = 'view-organization') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      if (!companyId) {
        if (window.CurrentCompanyContext) {
          window.CurrentCompanyContext.renderEmptyState(
            container,
            'No Company Connected to Organization',
            'Connect an existing company or create a new company to view or design its organization.'
          );
        } else {
          container.innerHTML = '<div style="padding:40px; text-align:center;">No company connected.</div>';
        }
        return;
      }

      await this.loadOrgData(companyId);
      this.renderWorkspace(container);
    }

    async loadOrgData(companyId) {
      try {
        const res = await fetch(`/api/companies/${companyId}/organization`);
        if (res.ok) {
          this.orgData = await res.json();
        }
      } catch (e) {
        console.error('Failed to load organization blueprint:', e);
      }
    }

    renderWorkspace(container) {
      if (!this.orgData) {
        container.innerHTML = '<div style="padding:40px; text-align:center;">Loading organization architecture...</div>';
        return;
      }

      const org = this.orgData;
      const comp = window.CurrentCompanyContext.getCompany() || { name: 'Company' };
      const statusBadge = org.status === 'ACTIVE' ? 'badge-emerald' : org.status === 'PROPOSED' ? 'badge-amber' : 'badge-blue';

      container.innerHTML = `
        <div class="org-workspace-root" style="display:flex; flex-direction:column; gap:16px; height:100%; min-height:80vh;">

          <!-- Top Org Header -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:18px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:12px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Company Organization</span>
                <span class="badge ${statusBadge}">${org.status}</span>
                <span class="badge badge-purple">${org.industry || 'Enterprise'}</span>
              </div>
              <h1 style="font-size:22px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">
                ${comp.name} Organizational Architecture
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0; max-width:680px;">
                ${org.rationale || 'Synthesized dynamic hierarchy tailored to operational reality.'}
              </p>
            </div>

            <!-- Header Actions -->
            <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
              <!-- View Mode Toggle -->
              <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:3px; display:flex; gap:2px;">
                <button style="border:none; background:${this.viewMode==='graph'?'var(--bg-surface)':'none'}; color:${this.viewMode==='graph'?'var(--accent-blue)':'var(--text-secondary)'}; font-size:12px; font-weight:600; padding:5px 12px; border-radius:var(--radius-sm); cursor:pointer;" onclick="OrgWorkspace.setViewMode('graph')">
                  Visual Graph
                </button>
                <button style="border:none; background:${this.viewMode==='tree'?'var(--bg-surface)':'none'}; color:${this.viewMode==='tree'?'var(--accent-blue)':'var(--text-secondary)'}; font-size:12px; font-weight:600; padding:5px 12px; border-radius:var(--radius-sm); cursor:pointer;" onclick="OrgWorkspace.setViewMode('tree')">
                  Tree View
                </button>
              </div>

              <button class="btn-secondary" style="font-size:12.5px; padding:7px 12px;" onclick="OrgWorkspace.proposeNewStructure()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                Propose Structure
              </button>

              ${org.status === 'PROPOSED' ? `
                <button class="btn-primary" style="font-size:12.5px; padding:7px 14px; background:var(--accent-emerald);" onclick="OrgWorkspace.approveStructure('${org.blueprint_id}')">
                  Approve Structure
                </button>
              ` : ''}
            </div>
          </div>

          <!-- Main Canvas Container with Zoom Controls & Search -->
          <div style="flex:1; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); position:relative; overflow:hidden; display:flex; flex-direction:column; min-height:600px;">

            <!-- Canvas Floating Toolbar -->
            <div style="position:absolute; top:14px; left:14px; z-index:10; display:flex; gap:8px; align-items:center; background:rgba(15,23,42,0.85); backdrop-filter:blur(8px); padding:6px 10px; border-radius:var(--radius-md); border:1px solid var(--border-color); box-shadow:var(--shadow-md);">
              <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700; padding:2px 8px;" onclick="OrgWorkspace.zoom(0.1)" title="Zoom In">+</button>
              <span style="font-size:11px; font-family:var(--font-mono); color:var(--text-muted); min-width:36px; text-align:center;">${Math.round(this.zoomLevel * 100)}%</span>
              <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700; padding:2px 8px;" onclick="OrgWorkspace.zoom(-0.1)" title="Zoom Out">-</button>
              <div style="width:1px; height:14px; background:var(--border-color);"></div>
              <button class="zoom-btn" style="background:none; border:none; color:var(--text-secondary); cursor:pointer; font-size:11.5px; padding:2px 6px;" onclick="OrgWorkspace.resetZoom()" title="Fit Screen">Fit</button>
              <button class="zoom-btn" style="background:none; border:none; color:var(--text-secondary); cursor:pointer; font-size:11.5px; padding:2px 6px;" onclick="OrgWorkspace.centerView()" title="Center">Center</button>
              <div style="width:1px; height:14px; background:var(--border-color);"></div>
              <input type="text" placeholder="Search roles or nodes..." style="background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:3px 8px; font-size:11px; width:130px;" oninput="OrgWorkspace.filterNodes(this.value)" />
            </div>

            <!-- Scrollable 2D Canvas Area -->
            <div id="orgCanvasScrollArea" class="horizontal-workspace" style="flex:1; overflow-x:auto; overflow-y:auto; -webkit-overflow-scrolling:touch; padding:70px 40px 40px 40px; display:flex; align-items:flex-start; justify-content:center;">
              <div id="orgCanvasTransform" style="transform: scale(${this.zoomLevel}); transform-origin: top center; transition: transform 0.15s ease-out; min-width:960px;">
                ${this.viewMode === 'graph' ? this.renderVisualGraph(org) : this.renderTreeView(org)}
              </div>
            </div>

            <!-- Node Detail Drawer (Slide-Over or Bottom Sheet on mobile) -->
            ${this.renderNodeDetailDrawer()}

          </div>

        </div>
      `;
    }

    renderVisualGraph(org) {
      const execs = org.executives || [];
      const depts = org.departments || [];
      const workforce = org.workforce || [];
      const query = this.searchQuery.toLowerCase();

      return `
        <div class="org-tree-graph" style="display:flex; flex-direction:column; align-items:center; gap:40px;">

          <!-- Level 1: Root Node -->
          <div class="org-node root-node" style="background:#1e293b; border:2px solid var(--accent-blue); border-radius:var(--radius-md); padding:14px 24px; text-align:center; min-width:220px; box-shadow:0 0 20px rgba(37,99,235,0.2); cursor:pointer;" onclick="OrgWorkspace.selectNode({ type:'COMPANY', title:'Host Governance', details:{} })">
            <div style="font-size:11px; text-transform:uppercase; color:var(--accent-blue); font-weight:700;">Executive Authority</div>
            <div style="font-size:15px; font-weight:700; color:white; margin-top:2px;">AI CEO & Host Governance</div>
            <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">${execs.length} Direct Executive Reports</div>
          </div>

          <!-- Connector Line -->
          <div style="width:2px; height:24px; background:var(--border-color); margin:-16px 0;"></div>

          <!-- Level 2: Executive Officers Grid -->
          <div class="org-level" style="display:flex; gap:24px; justify-content:center; flex-wrap:nowrap;">
            ${execs.map(ex => {
              const matches = !query || (ex.name || '').toLowerCase().includes(query) || (ex.role || '').toLowerCase().includes(query);
              return `
                <div class="org-node exec-node" style="background:var(--bg-surface); border:1px solid ${matches?'var(--accent-purple)':'var(--border-color)'}; border-radius:var(--radius-md); padding:14px 18px; min-width:200px; box-shadow:var(--shadow-sm); cursor:pointer; opacity:${matches?1:0.35}; transition:transform 0.2s;" onclick="OrgWorkspace.selectNode({ type:'EXECUTIVE', title:'${ex.role}', details:${JSON.stringify(ex).replace(/"/g, '&quot;')} })">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span class="badge badge-purple" style="font-size:9.5px;">EXECUTIVE</span>
                    <span style="font-size:10.5px; color:var(--accent-emerald);">● ACTIVE</span>
                  </div>
                  <div style="font-size:13.5px; font-weight:700; color:var(--text-primary);">${ex.role}</div>
                  <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">${ex.name || 'Executive AI'}</div>
                  <div style="font-size:11px; color:var(--text-muted); margin-top:8px; border-top:1px solid var(--border-color); padding-top:6px;">
                    Dept: ${ex.department || 'Corporate'}
                  </div>
                </div>
              `;
            }).join('')}
          </div>

          <!-- Connector Line -->
          <div style="width:2px; height:24px; background:var(--border-color); margin:-16px 0;"></div>

          <!-- Level 3: Operational Departments Grid -->
          <div class="org-level" style="display:flex; gap:20px; justify-content:center; flex-wrap:nowrap;">
            ${depts.map(dept => {
              const deptAgents = workforce.filter(w => w.department_id === dept.id);
              const matches = !query || dept.name.toLowerCase().includes(query) || dept.code.toLowerCase().includes(query);
              return `
                <div class="org-node dept-node" style="background:var(--bg-surface); border:1px solid ${matches?'var(--accent-blue)':'var(--border-color)'}; border-radius:var(--radius-md); padding:14px 16px; min-width:220px; box-shadow:var(--shadow-sm); cursor:pointer; opacity:${matches?1:0.35};" onclick="OrgWorkspace.selectNode({ type:'DEPARTMENT', title:'${dept.name}', details:${JSON.stringify(dept).replace(/"/g, '&quot;')} })">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span class="badge badge-blue" style="font-size:9.5px;">${dept.code}</span>
                    <span style="font-size:11px; color:var(--text-muted);">${deptAgents.length} Agents</span>
                  </div>
                  <div style="font-size:14px; font-weight:700; color:var(--text-primary);">${dept.name}</div>
                  <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px; line-height:1.3; max-width:200px;">
                    ${dept.justification || 'Operational department'}
                  </div>

                  <!-- Sub-agents in this Department -->
                  <div style="margin-top:12px; border-top:1px solid var(--border-color); padding-top:8px; display:flex; flex-direction:column; gap:6px;">
                    ${deptAgents.slice(0, 3).map(ag => `
                      <div style="font-size:11.5px; color:var(--text-secondary); display:flex; align-items:center; gap:5px;" onclick="event.stopPropagation(); OrgWorkspace.selectNode({ type:'AGENT', title:'${ag.role}', details:${JSON.stringify(ag).replace(/"/g, '&quot;')} })">
                        <span style="color:var(--accent-emerald);">●</span>
                        <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${ag.role}</span>
                      </div>
                    `).join('')}
                    ${deptAgents.length > 3 ? `<div style="font-size:10.5px; color:var(--accent-blue);">+${deptAgents.length - 3} more specialists</div>` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>

        </div>
      `;
    }

    renderTreeView(org) {
      const execs = org.executives || [];
      const depts = org.departments || [];
      const workforce = org.workforce || [];

      return `
        <div style="max-width:800px; margin:0 auto; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:24px;">
          <div style="font-size:16px; font-weight:700; color:var(--text-primary); margin-bottom:16px;">
            Hierarchical Reporting Tree
          </div>
          <div style="font-family:var(--font-mono); font-size:12.5px; line-height:1.8; color:var(--text-primary);">
            <div>🏢 <strong>Company Root</strong> (Host & AI CEO)</div>
            ${execs.map(ex => `
              <div style="padding-left:24px; color:var(--accent-purple);">
                ├── 👑 <strong>${ex.role}</strong> (${ex.name})
              </div>
            `).join('')}
            ${depts.map(d => {
              const deptAgents = workforce.filter(w => w.department_id === d.id);
              return `
                <div style="padding-left:24px; color:var(--accent-blue); margin-top:8px;">
                  ├── 📂 <strong>${d.name}</strong> [${d.code}]
                </div>
                ${deptAgents.map(ag => `
                  <div style="padding-left:48px; color:var(--text-secondary);">
                    ├── 🤖 ${ag.role} (<span style="color:var(--accent-emerald);">${ag.status || 'ACTIVE'}</span>)
                  </div>
                `).join('')}
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    renderNodeDetailDrawer() {
      if (!this.selectedNode) return '';
      const node = this.selectedNode;
      const details = node.details || {};

      return `
        <div class="org-node-drawer" style="position:absolute; top:0; right:0; bottom:0; width:360px; max-width:100%; background:var(--bg-surface); border-left:1px solid var(--border-color); box-shadow:var(--shadow-xl); z-index:20; display:flex; flex-direction:column; padding:20px; animation:slideInRight 0.2s ease-out;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <span class="badge badge-purple" style="font-size:10px;">${node.type}</span>
            <button style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:18px;" onclick="OrgWorkspace.closeDrawer()">✕</button>
          </div>

          <h3 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
            ${node.title}
          </h3>
          <div style="font-size:12.5px; color:var(--text-secondary); margin-bottom:18px;">
            ${details.name || details.justification || 'Operational node registered in company blueprint.'}
          </div>

          <div style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:14px; font-size:12.5px;">
            ${details.responsibilities ? `
              <div>
                <strong style="color:var(--text-primary); display:block; margin-bottom:4px;">Responsibilities:</strong>
                <ul style="margin:0 0 0 16px; padding:0; color:var(--text-secondary);">
                  ${(details.responsibilities || []).map(r => `<li>${r}</li>`).join('')}
                </ul>
              </div>
            ` : ''}

            ${details.tools ? `
              <div>
                <strong style="color:var(--text-primary); display:block; margin-bottom:4px;">Allowed Capabilities & Tools:</strong>
                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                  ${(details.tools || []).map(t => `<span class="badge badge-blue" style="font-size:10px;">${t}</span>`).join('')}
                </div>
              </div>
            ` : ''}

            ${details.budget ? `
              <div>
                <strong style="color:var(--text-primary);">Budget Ceiling:</strong>
                <span style="color:var(--accent-amber); font-weight:700;">₹${details.budget.toLocaleString()}</span>
              </div>
            ` : ''}
          </div>

          <div style="padding-top:14px; border-top:1px solid var(--border-color); display:flex; gap:10px;">
            <button class="btn-secondary" style="flex:1; font-size:12px;" onclick="window.navigateTo('/workforce')">Open in Workforce</button>
            <button class="btn-primary" style="flex:1; font-size:12px;" onclick="OrgWorkspace.closeDrawer()">Close</button>
          </div>
        </div>
      `;
    }

    selectNode(node) {
      this.selectedNode = node;
      const drawerContainer = document.querySelector('.org-node-drawer');
      if (drawerContainer) drawerContainer.remove();
      const parent = document.getElementById('orgCanvasScrollArea').parentElement;
      if (parent) {
        parent.insertAdjacentHTML('beforeend', this.renderNodeDetailDrawer());
      }
    }

    closeDrawer() {
      this.selectedNode = null;
      const d = document.querySelector('.org-node-drawer');
      if (d) d.remove();
    }

    setViewMode(mode) {
      this.viewMode = mode;
      this.render();
    }

    zoom(delta) {
      this.zoomLevel = Math.max(0.4, Math.min(2.0, this.zoomLevel + delta));
      const el = document.getElementById('orgCanvasTransform');
      if (el) el.style.transform = `scale(${this.zoomLevel})`;
      const label = document.querySelector('.zoom-btn + span');
      if (label) label.textContent = `${Math.round(this.zoomLevel * 100)}%`;
    }

    resetZoom() {
      this.zoomLevel = 1.0;
      const el = document.getElementById('orgCanvasTransform');
      if (el) el.style.transform = 'scale(1.0)';
      const label = document.querySelector('.zoom-btn + span');
      if (label) label.textContent = '100%';
    }

    centerView() {
      const scrollArea = document.getElementById('orgCanvasScrollArea');
      if (scrollArea) {
        scrollArea.scrollLeft = (scrollArea.scrollWidth - scrollArea.clientWidth) / 2;
        scrollArea.scrollTop = 0;
      }
    }

    filterNodes(q) {
      this.searchQuery = q;
      this.render();
    }

    async proposeNewStructure() {
      const compId = window.CurrentCompanyContext.getCompanyId();
      if (!compId) return;

      showToast('Synthesizing dynamic organizational proposal...', 'info');
      try {
        const res = await fetch(`/api/companies/${compId}/organization/propose`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        if (res.ok) {
          const data = await res.json();
          this.orgData = Object.assign(this.orgData, data);
          showToast('New organizational structure proposed!', 'success');
          this.render();
        }
      } catch (e) {
        showToast('Failed to propose structure', 'error');
      }
    }

    async approveStructure(blueprintId) {
      const compId = window.CurrentCompanyContext.getCompanyId();
      if (!compId) return;

      showToast('Committing organization blueprint to corporate registry...', 'info');
      try {
        const res = await fetch(`/api/companies/${compId}/organization/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ blueprint_id: blueprintId })
        });
        if (res.ok) {
          showToast('Organizational structure approved & active!', 'success');
          await this.loadOrgData(compId);
          this.render();
        }
      } catch (e) {
        showToast('Approval failed', 'error');
      }
    }
  }

  window.OrgWorkspace = new OrgWorkspaceManager();
})();
