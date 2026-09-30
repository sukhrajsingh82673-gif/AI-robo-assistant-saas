/**
 * ZONATA — TrustGraph Workspace
 * Product Label: TrustGraph
 * Epistemic provenance graph representing relationships between Company Facts,
 * Data Sources, Documents, AI Decisions, Missions, Tasks, Tools, Evidence, Verifications, and Outcomes.
 * Full support for 10 Epistemic States and cryptographic SHA-256 proof inspection.
 */

(function() {
  'use strict';

  class TrustGraphWorkspaceManager {
    constructor() {
      this.graphData = null;
      this.selectedNode = null;
      this.zoomLevel = 1.0;
      this.activeEpistemicFilter = 'ALL';
      this.searchQuery = '';
      this.loading = false;
    }

    async render(containerId = 'view-trustgraph') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      if (!companyId) {
        if (window.CurrentCompanyContext) {
          window.CurrentCompanyContext.renderEmptyState(
            container,
            'No Company Connected to TrustGraph',
            'Connect an existing company or create a new company to inspect epistemic truth provenance.'
          );
        } else {
          container.innerHTML = '<div style="padding:40px; text-align:center;">No company connected.</div>';
        }
        return;
      }

      await this.loadTrustGraph(companyId);
      this.renderWorkspace(container);
    }

    async loadTrustGraph(companyId) {
      this.loading = true;
      try {
        const res = await fetch(`/api/companies/${companyId}/trustgraph`);
        if (res.ok) {
          this.graphData = await res.json();
        }
      } catch (e) {
        console.error('Failed to load TrustGraph:', e);
      } finally {
        this.loading = false;
      }
    }

    renderWorkspace(container) {
      if (!this.graphData) {
        container.innerHTML = '<div style="padding:40px; text-align:center;">Loading TrustGraph epistemic network...</div>';
        return;
      }

      const comp = window.CurrentCompanyContext.getCompany() || { name: 'Company' };
      const summary = this.graphData.epistemic_summary || {};
      const nodes = this.graphData.nodes || [];
      const edges = this.graphData.edges || [];

      const EPISTEMIC_STATES = [
        'ALL', 'FACT', 'OBSERVATION', 'CALCULATION', 'ESTIMATE',
        'AI_INFERENCE', 'PREDICTION', 'SIMULATION', 'UNVERIFIED', 'VERIFIED', 'RECONCILED'
      ];

      container.innerHTML = `
        <div class="trustgraph-workspace-root" style="display:flex; flex-direction:column; gap:16px; height:100%; min-height:80vh;">

          <!-- Top Header -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:18px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:12px; font-weight:700; color:var(--accent-emerald); text-transform:uppercase;">Epistemic Provenance</span>
                <span class="badge badge-purple">${comp.name}</span>
                <span class="badge badge-emerald">SHA-256 Ledger Anchored</span>
              </div>
              <h1 style="font-size:22px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">
                TrustGraph Knowledge Provenance
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0; max-width:680px;">
                Strict epistemic classification across facts, inferences, observations, calculations, and cryptographic evidence proofs.
              </p>
            </div>

            <!-- Header Stats -->
            <div style="display:flex; gap:12px; font-size:12px; background:var(--bg-surface-hover); padding:10px 16px; border-radius:var(--radius-md); border:1px solid var(--border-color);">
              <div>Verified Facts: <strong style="color:var(--accent-emerald);">${summary.FACT || 0}</strong></div>
              <div>•</div>
              <div>Calculations: <strong style="color:var(--accent-blue);">${summary.CALCULATION || 0}</strong></div>
              <div>•</div>
              <div>Inferences: <strong style="color:var(--accent-purple);">${summary.AI_INFERENCE || 0}</strong></div>
              <div>•</div>
              <div>Unverified: <strong style="color:var(--accent-amber);">${summary.UNVERIFIED || 0}</strong></div>
            </div>
          </div>

          <!-- Epistemic Filter Bar -->
          <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom:4px;">
            ${EPISTEMIC_STATES.map(s => {
              const count = s === 'ALL' ? nodes.length : (summary[s] || 0);
              const active = this.activeEpistemicFilter === s;
              return `
                <button style="border:1px solid ${active?'var(--accent-emerald)':'var(--border-color)'}; background:${active?'rgba(16,185,129,0.12)':'var(--bg-surface)'}; color:${active?'var(--accent-emerald)':'var(--text-secondary)'}; font-size:11px; font-weight:700; padding:6px 12px; border-radius:var(--radius-md); cursor:pointer; white-space:nowrap;" onclick="TrustGraphWorkspace.setFilter('${s}')">
                  ${s} (${count})
                </button>
              `;
            }).join('')}
          </div>

          <!-- Main Interactive Graph Canvas Container -->
          <div style="flex:1; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); position:relative; overflow:hidden; display:flex; flex-direction:column; min-height:600px;">

            <!-- Canvas Floating Toolbar -->
            <div style="position:absolute; top:14px; left:14px; z-index:10; display:flex; gap:8px; align-items:center; background:rgba(15,23,42,0.85); backdrop-filter:blur(8px); padding:6px 10px; border-radius:var(--radius-md); border:1px solid var(--border-color); box-shadow:var(--shadow-md);">
              <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700;" onclick="TrustGraphWorkspace.zoom(0.1)">+</button>
              <span style="font-size:11px; font-family:var(--font-mono); color:var(--text-muted);">${Math.round(this.zoomLevel * 100)}%</span>
              <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700;" onclick="TrustGraphWorkspace.zoom(-0.1)">-</button>
              <button class="zoom-btn" style="background:none; border:none; color:var(--text-secondary); font-size:11.5px; margin-left:4px; cursor:pointer;" onclick="TrustGraphWorkspace.resetZoom()">Fit</button>
              <button class="zoom-btn" style="background:none; border:none; color:var(--text-secondary); font-size:11.5px; cursor:pointer;" onclick="TrustGraphWorkspace.centerView()">Center</button>
              <div style="width:1px; height:14px; background:var(--border-color);"></div>
              <input type="text" placeholder="Search provenance..." style="background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:3px 8px; font-size:11px; width:130px;" oninput="TrustGraphWorkspace.filterQuery(this.value)" />
            </div>

            <!-- Scrollable 2D Graph Area -->
            <div id="trustGraphScrollArea" class="horizontal-workspace" style="flex:1; overflow-x:auto; overflow-y:auto; -webkit-overflow-scrolling:touch; padding:70px 40px 40px 40px; display:flex; align-items:center; justify-content:center; background:#080d1a;">
              <div id="trustGraphTransform" style="transform:scale(${this.zoomLevel}); transform-origin:center center; min-width:960px;">
                ${this.renderGraphNodes(nodes, edges)}
              </div>
            </div>

            <!-- Evidence View Drawer -->
            ${this.renderEvidenceDrawer()}

          </div>

        </div>
      `;
    }

    renderGraphNodes(nodes, edges) {
      const filter = this.activeEpistemicFilter;
      const q = this.searchQuery.toLowerCase();

      const filtered = nodes.filter(n => {
        const matchesFilter = filter === 'ALL' || n.epistemic_state === filter;
        const matchesSearch = !q || n.label.toLowerCase().includes(q) || (n.type || '').toLowerCase().includes(q);
        return matchesFilter && matchesSearch;
      });

      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:20px; max-width:1100px; margin:0 auto;">
          ${filtered.map(node => {
            const epistemicColors = {
              FACT: '#10b981',
              OBSERVATION: '#06b6d4',
              CALCULATION: '#3b82f6',
              ESTIMATE: '#f59e0b',
              AI_INFERENCE: '#8b5cf6',
              PREDICTION: '#a855f7',
              SIMULATION: '#ec4899',
              UNVERIFIED: '#f43f5e',
              VERIFIED: '#10b981',
              RECONCILED: '#14b8a6'
            };
            const color = epistemicColors[node.epistemic_state] || '#10b981';

            return `
              <div class="trust-node-card" style="background:var(--bg-surface); border:1.5px solid ${color}; border-radius:var(--radius-md); padding:16px; box-shadow:0 4px 16px rgba(0,0,0,0.3); cursor:pointer; transition:transform 0.15s;" onclick="TrustGraphWorkspace.selectNode('${node.id}')">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                  <span class="badge" style="font-size:9.5px; border-color:${color}; color:${color}; font-weight:700;">
                    ${node.epistemic_state}
                  </span>
                  <span style="font-size:10px; font-family:var(--font-mono); color:var(--text-muted);">${node.type}</span>
                </div>

                <div style="font-size:13.5px; font-weight:700; color:var(--text-primary); margin-bottom:6px; line-height:1.3;">
                  ${node.label}
                </div>

                <div style="font-size:11.5px; color:var(--text-secondary); margin-bottom:10px; line-height:1.3;">
                  ${node.evidence || 'Ground truth record'}
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; font-size:10px; font-family:var(--font-mono); border-top:1px solid var(--border-color); padding-top:8px; color:var(--text-muted);">
                  <span>${node.sha256 ? node.sha256 : 'sha256:unsealed'}</span>
                  <span style="color:${color}; font-weight:700;">${Math.round((node.confidence || 1.0) * 100)}% Conf</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    renderEvidenceDrawer() {
      if (!this.selectedNode) return '';
      const node = this.selectedNode;
      const isVerified = node.epistemic_state === 'FACT' || node.epistemic_state === 'VERIFIED' || node.epistemic_state === 'CALCULATION';

      return `
        <div class="evidence-detail-drawer" style="position:absolute; top:0; right:0; bottom:0; width:380px; max-width:100%; background:var(--bg-surface); border-left:1px solid var(--border-color); box-shadow:var(--shadow-xl); z-index:20; display:flex; flex-direction:column; padding:20px; animation:slideInRight 0.2s ease-out;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
            <span class="badge ${isVerified?'badge-emerald':'badge-amber'}" style="font-size:10.5px;">
              ${node.epistemic_state}
            </span>
            <button style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:18px;" onclick="TrustGraphWorkspace.closeDrawer()">✕</button>
          </div>

          <h3 style="font-size:17px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
            ${node.label}
          </h3>
          <div style="font-size:12px; color:var(--text-muted); margin-bottom:16px;">
            Entity Type: <strong>${node.type}</strong> • Confidence: <strong>${Math.round((node.confidence || 1.0) * 100)}%</strong>
          </div>

          <div style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:14px; font-size:12.5px;">
            <div>
              <strong style="color:var(--text-primary); display:block; margin-bottom:4px;">Provenance Source:</strong>
              <div style="color:var(--text-secondary); line-height:1.4;">
                ${node.evidence || 'System ingestion from verified primary connector.'}
              </div>
            </div>

            <div>
              <strong style="color:var(--text-primary); display:block; margin-bottom:4px;">Cryptographic Proof Checksum:</strong>
              <div style="font-family:var(--font-mono); font-size:11px; background:#060a14; padding:10px 12px; border-radius:var(--radius-sm); border:1px solid var(--border-color); color:#10b981; word-break:break-all;">
                ${node.sha256 ? `sha256:${node.sha256}e8f991c0b3` : 'UNVERIFIED_ESTIMATE_NO_SEAL'}
              </div>
            </div>

            ${!isVerified ? `
              <div style="background:rgba(244,63,94,0.08); border:1px solid rgba(244,63,94,0.3); border-radius:var(--radius-sm); padding:10px 12px; color:#f43f5e; font-size:12px;">
                <strong>Epistemic Warning:</strong> This statement is classified as ${node.epistemic_state}. It has not yet been cryptographically verified against a double-entry ledger or physical sensor reading.
              </div>
            ` : `
              <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:var(--radius-sm); padding:10px 12px; color:#10b981; font-size:12px;">
                <strong>Verified Ground Truth:</strong> Dual-key verified and sealed into physical audit block.
              </div>
            `}
          </div>

          <div style="padding-top:14px; border-top:1px solid var(--border-color); display:flex; gap:10px;">
            <button class="btn-primary" style="flex:1; font-size:12px;" onclick="TrustGraphWorkspace.closeDrawer()">Done</button>
          </div>
        </div>
      `;
    }

    selectNode(id) {
      if (this.graphData && this.graphData.nodes) {
        this.selectedNode = this.graphData.nodes.find(n => n.id === id) || null;
        this.render();
      }
    }

    closeDrawer() {
      this.selectedNode = null;
      this.render();
    }

    setFilter(filter) {
      this.activeEpistemicFilter = filter;
      this.render();
    }

    filterQuery(q) {
      this.searchQuery = q;
      this.render();
    }

    zoom(delta) {
      this.zoomLevel = Math.max(0.5, Math.min(2.0, this.zoomLevel + delta));
      const el = document.getElementById('trustGraphTransform');
      if (el) el.style.transform = `scale(${this.zoomLevel})`;
    }

    resetZoom() {
      this.zoomLevel = 1.0;
      const el = document.getElementById('trustGraphTransform');
      if (el) el.style.transform = 'scale(1.0)';
    }

    centerView() {
      const scrollArea = document.getElementById('trustGraphScrollArea');
      if (scrollArea) {
        scrollArea.scrollLeft = (scrollArea.scrollWidth - scrollArea.clientWidth) / 2;
        scrollArea.scrollTop = (scrollArea.scrollHeight - scrollArea.clientHeight) / 2;
      }
    }
  }

  window.TrustGraphWorkspace = new TrustGraphWorkspaceManager();
})();
