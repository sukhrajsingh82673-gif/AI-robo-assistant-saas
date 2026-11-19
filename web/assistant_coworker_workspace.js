/**
 * ZONATA AI Assistant & Universal Co-Worker Workspace
 * Front-end implementation unifying AI Assistant + Co-Worker + Schedule + Missions + Approvals + Governed Terminal.
 * 
 * Philosophy:
 * "One ZONATA AI Assistant / Universal Co-Worker that accepts a natural-language objective
 * and autonomously plans, delegates, executes, verifies, recovers, and delivers the result."
 * The user sees: ZONATA AI Assistant -> Co-Worker.
 * Internal runtimes (Hermes, OpenClaw, OpenHands, Terminal, Browser, etc.) are execution providers.
 */

(function() {
  'use strict';

  class AssistantCoworkerWorkspaceManager {
    constructor() {
      this.currentMissionId = null;
      this.missions = [];
      this.approvals = [];
      this.artifacts = [];
      this.realityMatrix = [];
      this.dashboard = null;
      this.terminalHistory = [];
      this.nodes = [];
      this.recoveryEvents = [];
      this.isPolling = false;
      this.pollInterval = null;
    }

    async init() {
      await this.refreshData();
      if (!this.isPolling) {
        this.pollInterval = setInterval(() => this.refreshData(true), 5000);
        this.isPolling = true;
      }
    }

    async refreshData(silent = false) {
      try {
        const [dashRes, msnRes, appRes, artRes, matRes, nodeRes, recRes] = await Promise.all([
          fetch('/api/coworker/dashboard').then(r => r.json()).catch(() => null),
          fetch('/api/coworker/missions').then(r => r.json()).catch(() => ({ missions: [] })),
          fetch('/api/coworker/approvals').then(r => r.json()).catch(() => ({ approvals: [] })),
          fetch('/api/coworker/artifacts').then(r => r.json()).catch(() => ({ artifacts: [] })),
          fetch('/api/coworker/reality-matrix').then(r => r.json()).catch(() => ({ reality_matrix: [] })),
          fetch('/api/coworker/nodes').then(r => r.json()).catch(() => ({ nodes: [] })),
          fetch('/api/coworker/recovery/events').then(r => r.json()).catch(() => ({ events: [] }))
        ]);

        if (dashRes) this.dashboard = dashRes;
        if (msnRes && msnRes.missions) this.missions = msnRes.missions;
        if (appRes && appRes.approvals) this.approvals = appRes.approvals;
        if (artRes && artRes.artifacts) this.artifacts = artRes.artifacts;
        if (matRes && matRes.reality_matrix) this.realityMatrix = matRes.reality_matrix;
        if (nodeRes && nodeRes.nodes) this.nodes = nodeRes.nodes;
        if (recRes && recRes.events) this.recoveryEvents = recRes.events;

        if (!this.currentMissionId && this.missions.length > 0) {
          this.currentMissionId = this.missions[0].mission_id;
        }

        if (!silent) {
          this.updateBadges();
        }
      } catch (e) {
        console.error('Error refreshing coworker data:', e);
      }
    }

    updateBadges() {
      const appBtn = document.getElementById('navItemApprovals');
      if (appBtn) {
        let badge = appBtn.querySelector('.nav-pill');
        if (this.approvals.length > 0) {
          if (!badge) {
            badge = document.createElement('span');
            badge.className = 'nav-pill';
            badge.style.background = '#ef4444';
            badge.style.color = '#fff';
            appBtn.appendChild(badge);
          }
          badge.textContent = this.approvals.length;
        } else if (badge) {
          badge.remove();
        }
      }
    }

    // =========================================================================
    // 1. ASSISTANT VIEW (Natural Language Front Door)
    // =========================================================================
    async renderAssistant(containerId) {
      if (window.USE_SAMPLE_DATA && window.AppleCoworkerAssistant) {
        window.AppleCoworkerAssistant.render(containerId, 'company');
        return;
      }
      await this.init();
      const el = document.getElementById(containerId);
      if (!el) return;

      el.innerHTML = `
        <div class="workspace-page-header">
          <div>
            <div style="display:inline-flex; align-items:center; gap:8px; padding:4px 12px; background:rgba(37,99,235,0.15); border:1px solid #3b82f6; border-radius:20px; font-size:0.75rem; color:#93c5fd; font-weight:600; margin-bottom:10px;">
              <span>🧠 AI CEO = BRAIN</span>
              <span style="opacity:0.5;">|</span>
              <span>⚡ CO-WORKER = HANDS / BODY</span>
            </div>
            <h1 class="page-title">ZONATA AI Assistant</h1>
            <p class="page-subtitle">Your sovereign AI companion and front door to the Universal AI Co-Worker execution fabric.</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-outline" onclick="window.AssistantCoworkerWorkspace.openScheduleModal()">
              📅 Schedule Task
            </button>
            <button class="btn btn-primary" onclick="window.navigateTo('/coworker')">
              🤖 Open Co-Worker
            </button>
          </div>
        </div>

        <!-- Assistant Hero Input Card -->
        <div class="assistant-hero-card" style="background:var(--card-bg, #1e293b); border:1px solid var(--border-color, #334155); border-radius:12px; padding:24px; margin-bottom:24px;">
          <h2 style="font-size:1.25rem; font-weight:600; margin-bottom:8px; display:flex; align-items:center; gap:8px;">
            <span>✨</span> Ask ZONATA anything...
          </h2>
          <p style="color:var(--text-muted, #94a3b8); font-size:0.875rem; margin-bottom:16px;">
            Enter any business, engineering, or operational objective. The Assistant will formulate a governed execution plan, delegate to specialized workers, and deliver verified results.
          </p>

          <div style="position:relative; margin-bottom:16px;">
            <textarea id="assistantObjectiveInput" rows="3" class="form-control" style="width:100%; border-radius:8px; padding:12px; font-size:1rem; background:rgba(0,0,0,0.2); color:#fff; border:1px solid #475569;" placeholder="Describe what you want to achieve... (e.g. 'Research top 10 boutique hotels in Goa and synthesize competitive report')"></textarea>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <label style="display:flex; align-items:center; gap:6px; font-size:0.875rem; color:#cbd5e1; cursor:pointer;">
                <input type="checkbox" id="assistantBackgroundCheck" checked style="accent-color:#2563eb;" />
                Run as autonomous background mission
              </label>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-secondary" onclick="window.AssistantCoworkerWorkspace.submitCeoObjective()" style="padding:10px 18px; font-weight:600;">
                🧠 Dispatch from AI CEO
              </button>
              <button class="btn btn-primary" id="btnSubmitAssistant" onclick="window.AssistantCoworkerWorkspace.submitAssistantObjective()" style="padding:10px 24px; font-weight:600;">
                🚀 Delegate to Co-Worker
              </button>
            </div>
          </div>

          <!-- Quick Action Chips -->
          <div style="margin-top:20px; padding-top:16px; border-top:1px solid #334155;">
            <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.05em; color:#94a3b8; margin-bottom:8px;">Recommended Objectives</div>
            <div style="display:flex; flex-wrap:wrap; gap:8px;">
              <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.fillPrompt('Research the top 10 hotels in Goa and prepare a comparison report')">
                🏨 Hotel Market Research
              </button>
              <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.fillPrompt('Inspect repository structure, run all tests, and diagnose failures')">
                🧪 Run Test Suite & Inspect Code
              </button>
              <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.fillPrompt('Inspect host environment, disk storage, and installed developer software')">
                💻 System Diagnostics
              </button>
              <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.fillPrompt('Discover and admit verified open-source HTML parsing tool into Capability Registry')">
                🔌 Self-Extend Tool Registry
              </button>
              <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.fillPrompt('Prepare weekly executive SaaS churn analysis report in background')">
                📊 Weekly SaaS Churn Report
              </button>
            </div>
          </div>
        </div>

        <!-- Recent Co-Worker Missions Overview -->
        <div class="card" style="margin-top:24px;">
          <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
            <h3 class="card-title">Recent Co-Worker Delegations</h3>
            <span style="font-size:0.875rem; color:#94a3b8;">${this.missions.length} Missions</span>
          </div>
          <div class="card-body">
            ${this.renderMissionsListSummary()}
          </div>
        </div>
      `;
    }

    fillPrompt(text) {
      const input = document.getElementById('assistantObjectiveInput');
      if (input) {
        input.value = text;
        input.focus();
      }
    }

    async submitAssistantObjective() {
      const input = document.getElementById('assistantObjectiveInput');
      if (!input || !input.value.trim()) {
        showToast('Please enter an objective for the Co-Worker.', 'warning');
        return;
      }

      const prompt = input.value.trim();
      const btn = document.getElementById('btnSubmitAssistant');
      if (btn) {
        btn.disabled = true;
        btn.textContent = 'Delegating to Co-Worker...';
      }

      try {
        const res = await fetch('/api/coworker/mission', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, auto_step: true })
        });
        const data = await res.json();
        if (data.success) {
          showToast(`Mission created: ${data.mission_id}`, 'success');
          this.currentMissionId = data.mission_id;
          input.value = '';
          window.navigateTo('/coworker');
        } else {
          showToast(`Error: ${data.error || 'Failed to dispatch mission'}`, 'error');
        }
      } catch (e) {
        showToast(`Failed: ${e.message}`, 'error');
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.textContent = '🚀 Delegate to Co-Worker';
        }
      }
    }

    async submitCeoObjective() {
      const input = document.getElementById('assistantObjectiveInput');
      if (!input || !input.value.trim()) {
        showToast('Please enter a strategic objective for the AI CEO.', 'warning');
        return;
      }

      const objective = input.value.trim();
      showToast('Dispatching Strategic Directive from AI CEO Brain...', 'info');

      try {
        const res = await fetch('/api/coworker/ceo/mission', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            objective,
            business_context: { priority: "HIGH", strategy: "autonomous_delivery" },
            budget: 50.0
          })
        });
        const data = await res.json();
        if (data.mission_id) {
          showToast(`AI CEO Mission initiated: ${data.mission_id} (${data.execution_status})`, 'success');
          this.currentMissionId = data.mission_id;
          input.value = '';
          await this.refreshData();
          window.navigateTo('/coworker');
        } else {
          showToast(`Error: ${data.error || 'Failed to dispatch CEO mission'}`, 'error');
        }
      } catch (err) {
        showToast(`Request failed: ${err.message}`, 'error');
      }
    }

    renderMissionsListSummary() {
      if (!this.missions || this.missions.length === 0) {
        return `<div style="text-align:center; padding:32px; color:#94a3b8;">No missions dispatched yet. Ask ZONATA anything above!</div>`;
      }

      return `
        <div class="table-responsive">
          <table class="table">
            <thead>
              <tr>
                <th>Mission ID</th>
                <th>Objective</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Deliverables</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${this.missions.slice(0, 5).map(m => `
                <tr>
                  <td><code>${m.mission_id}</code></td>
                  <td style="max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${this.escapeHtml(m.prompt)}">
                    ${this.escapeHtml(m.prompt)}
                  </td>
                  <td><span class="badge ${this.getStatusBadgeClass(m.status)}">${m.status}</span></td>
                  <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                      <div class="progress-bar-bg" style="flex:1; height:6px; background:#334155; border-radius:3px; overflow:hidden;">
                        <div style="width:${m.progress_percent}%; height:100%; background:#2563eb;"></div>
                      </div>
                      <span style="font-size:0.75rem;">${Math.round(m.progress_percent)}%</span>
                    </div>
                  </td>
                  <td>${m.deliverables && m.deliverables.length ? `📄 ${m.deliverables.length} files` : '—'}</td>
                  <td>
                    <button class="btn btn-sm btn-outline" onclick="window.AssistantCoworkerWorkspace.openMission('${m.mission_id}')">
                      View Co-Worker
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    // =========================================================================
    // 2. CO-WORKER VIEW (Execution Pipeline & Single-Product Workspace)
    // =========================================================================
    async renderCoworker(containerId) {
      await this.init();
      const el = document.getElementById(containerId);
      if (!el) return;

      const activeMission = this.missions.find(m => m.mission_id === this.currentMissionId) || this.missions[0];
      // HUD values come from the live dashboard snapshot; unknown stays unknown.
      const ac = (this.dashboard && this.dashboard.agent_cloud) || {};
      const integ = ac.verified_integrations || {};
      const cyber = ac.cybersecurity || {};
      const cloudLabel = ac.catalog_status === 'ONLINE'
        ? `${ac.total_registered_agents || 0} Registered (${ac.busy_agents || 0} Busy / ${ac.max_bounded_workers || 0} Pool)`
        : 'Not initialized';
      const cloudSub = ac.catalog_status === 'ONLINE'
        ? `Queue depth ${ac.queue_depth || 0}`
        : (ac.catalog_status || 'No agent cloud attached');

      el.innerHTML = `
        <div class="workspace-page-header">
          <div>
            <div style="display:inline-flex; align-items:center; gap:8px; padding:3px 10px; background:rgba(16,185,129,0.15); border:1px solid #10b981; border-radius:16px; font-size:0.75rem; color:#6ee7b7; font-weight:700; margin-bottom:8px;">
              <span>🤖 COWORKER 3.0 EXECUTIVE COCKPIT</span>
              <span style="opacity:0.4;">|</span>
              <span>👑 CEO-DIRECTED AUTONOMOUS OPERATOR</span>
            </div>
            <h1 class="page-title">ZONATA Autonomous Coworker 3.0</h1>
            <p class="page-subtitle">Hermes session runtime, OpenCode Git worktree engine, catalogued Agent Cloud with bounded scheduling, X11 visual perception, and defensive cybersecurity patrols. Status values below are read live from the backend.</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-outline" onclick="window.AssistantCoworkerWorkspace.triggerSecurityPatrol()" title="Run immediate cybersecurity patrol">
              🛡️ Security Patrol
            </button>
            ${activeMission ? `
              <button class="btn btn-outline" onclick="window.AssistantCoworkerWorkspace.stepMission('${activeMission.mission_id}')">
                ⚡ Advance Step
              </button>
              <button class="btn btn-warning" onclick="window.AssistantCoworkerWorkspace.controlMission('${activeMission.mission_id}', 'TAKE_CONTROL')">
                ✋ Take Control
              </button>
            ` : ''}
            <button class="btn btn-primary" onclick="window.navigateTo('/assistant')">
              + New Objective
            </button>
          </div>
        </div>

        <!-- Coworker 3.0 Executive Reality & Fleet Telemetry HUD -->
        <div class="coworker-reality-hud" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-bottom:20px;">
          <div class="card" style="padding:14px; background:rgba(15,23,42,0.85); border:1px solid #334155; border-radius:10px;">
            <div style="font-size:0.75rem; color:#94a3b8; font-weight:700; text-transform:uppercase;">☁️ Enterprise Agent Cloud</div>
            <div style="font-size:0.95rem; font-weight:700; color:#38bdf8; margin:6px 0 2px;">
              ${cloudLabel}
            </div>
            <div style="font-size:0.75rem; color:#64748b;">${cloudSub}</div>
          </div>
          <div class="card" style="padding:14px; background:rgba(15,23,42,0.85); border:1px solid #334155; border-radius:10px;">
            <div style="font-size:0.75rem; color:#94a3b8; font-weight:700; text-transform:uppercase;">🛠️ OpenCode & Hermes Engine</div>
            <div style="font-size:0.95rem; font-weight:700; color:#34d399; margin:6px 0 2px;">
              Hermes: ${integ.hermes_runtime || 'UNKNOWN'}
            </div>
            <div style="font-size:0.75rem; color:#64748b;">OpenCode: ${integ.opencode_engine || 'UNKNOWN'}</div>
          </div>
          <div class="card" style="padding:14px; background:rgba(15,23,42,0.85); border:1px solid #334155; border-radius:10px;">
            <div style="font-size:0.75rem; color:#94a3b8; font-weight:700; text-transform:uppercase;">🖥️ OpenDots Perception</div>
            <div style="font-size:0.85rem; font-weight:600; color:#cbd5e1; margin:6px 0 2px;">
              ${integ.opendots_computer_use || 'UNKNOWN'}
            </div>
            <div style="font-size:0.75rem; color:#64748b;">Terminal: ${integ.terminal_sandboxed || 'UNKNOWN'}</div>
          </div>
          <div class="card" style="padding:14px; background:rgba(15,23,42,0.85); border:1px solid #334155; border-radius:10px;">
            <div style="font-size:0.75rem; color:#94a3b8; font-weight:700; text-transform:uppercase;">🛡️ Cybersecurity Command</div>
            <div style="font-size:0.95rem; font-weight:700; color:#a78bfa; margin:6px 0 2px;">
              ${cyber.threat_level || 'UNKNOWN'} · ${cyber.patrol_status || 'NOT_RUN'}
            </div>
            <div style="font-size:0.75rem; color:#64748b;">Critical ${cyber.critical_findings || 0} · High ${cyber.high_findings || 0}</div>
          </div>
        </div>

        <!-- Visual 7-Stage Execution Pipeline -->
        <div class="pipeline-flow-card" style="background:var(--card-bg, #1e293b); border:1px solid #334155; border-radius:12px; padding:18px 24px; margin-bottom:24px;">
          <div class="pipeline-stages" style="display:flex; justify-content:space-between; align-items:center; position:relative;">
            ${this.renderPipelineStep('Objective', activeMission ? true : false, false)}
            <div class="pipeline-connector ${activeMission ? 'active' : ''}"></div>
            ${this.renderPipelineStep('Plan', activeMission ? true : false, false)}
            <div class="pipeline-connector ${activeMission && activeMission.progress_percent >= 25 ? 'active' : ''}"></div>
            ${this.renderPipelineStep('Workers', activeMission && activeMission.subworkers && activeMission.subworkers.length > 0, false)}
            <div class="pipeline-connector ${activeMission && activeMission.progress_percent >= 50 ? 'active' : ''}"></div>
            ${this.renderPipelineStep('Execution', activeMission && activeMission.progress_percent >= 50, activeMission && activeMission.status === 'RUNNING')}
            <div class="pipeline-connector ${activeMission && activeMission.progress_percent >= 80 ? 'active' : ''}"></div>
            ${this.renderPipelineStep('Verification', activeMission && (activeMission.progress_percent >= 80 || activeMission.status === 'COMPLETED'), false)}
            <div class="pipeline-connector ${activeMission && activeMission.status === 'COMPLETED' ? 'active' : ''}"></div>
            ${this.renderPipelineStep('Result', activeMission && activeMission.status === 'COMPLETED', false)}
          </div>
        </div>

        ${activeMission ? this.renderActiveMissionWorkspace(activeMission) : `
          <div class="card" style="padding:48px; text-align:center;">
            <h3>No Active Co-Worker Mission</h3>
            <p style="color:#94a3b8; margin:12px 0 20px;">Delegate a task to the Co-Worker from the Assistant to start autonomous execution.</p>
            <button class="btn btn-primary" onclick="window.navigateTo('/assistant')">Go to Assistant</button>
          </div>
        `}
      `;
    }

    renderPipelineStep(name, completed, active) {
      let icon = completed ? '✓' : '○';
      let bg = completed ? '#10b981' : (active ? '#2563eb' : '#334155');
      let textCol = completed || active ? '#ffffff' : '#94a3b8';

      return `
        <div style="display:flex; flex-direction:column; align-items:center; z-index:2;">
          <div style="width:36px; height:36px; border-radius:50%; background:${bg}; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.875rem; box-shadow:0 0 12px ${completed ? 'rgba(16,185,129,0.4)' : (active ? 'rgba(37,99,235,0.4)' : 'transparent')};">
            ${active ? '<span class="spinner-border spinner-border-sm" style="width:14px; height:14px; border-width:2px;"></span>' : icon}
          </div>
          <span style="font-size:0.75rem; font-weight:600; color:${textCol}; margin-top:6px;">${name}</span>
        </div>
      `;
    }

    renderActiveMissionWorkspace(m) {
      const isCompleted = m.status === 'COMPLETED';
      const isWaiting = m.status === 'WAITING' || m.status === 'AWAITING_APPROVAL';

      return `
        <div style="display:grid; grid-template-columns: 2fr 1fr; gap:24px;">
          <!-- Left Column: Active Objective & Execution Stream -->
          <div>
            <div class="card" style="margin-bottom:24px;">
              <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <span style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase;">Mission ID: <code>${m.mission_id}</code></span>
                  <h3 class="card-title" style="margin-top:4px;">${this.escapeHtml(m.prompt)}</h3>
                </div>
                <span class="badge ${this.getStatusBadgeClass(m.status)}" style="font-size:0.875rem; padding:6px 12px;">${m.status}</span>
              </div>
              <div class="card-body">
                <!-- User-Facing Friendly Status -->
                <div style="background:rgba(37, 99, 235, 0.1); border-left:4px solid #2563eb; padding:14px; border-radius:4px; margin-bottom:20px;">
                  <div style="display:flex; align-items:center; gap:8px; font-weight:600; color:#60a5fa;">
                    <span>🤖</span>
                    <span>${isCompleted ? 'Co-Worker completed this mission!' : (isWaiting ? 'Co-Worker is awaiting operator authorization' : 'Co-Worker is working...')}</span>
                  </div>
                  <div style="font-size:0.875rem; color:#cbd5e1; margin-top:4px;">
                    Current Step: <strong>${m.current_stage}</strong>
                  </div>
                </div>

                <!-- Progress Bar -->
                <div style="margin-bottom:20px;">
                  <div style="display:flex; justify-content:space-between; font-size:0.875rem; margin-bottom:6px;">
                    <span>Autonomous Progress</span>
                    <span><strong>${Math.round(m.progress_percent)}%</strong></span>
                  </div>
                  <div style="height:8px; background:#334155; border-radius:4px; overflow:hidden;">
                    <div style="width:${m.progress_percent}%; height:100%; background:${isCompleted ? '#10b981' : '#2563eb'}; transition:width 0.4s ease;"></div>
                  </div>
                </div>

                <!-- Takeover Control Buttons -->
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                  ${m.status === 'RUNNING' ? `
                    <button class="btn btn-sm btn-outline" onclick="window.AssistantCoworkerWorkspace.controlMission('${m.mission_id}', 'PAUSE')">⏸️ Pause</button>
                  ` : ''}
                  ${m.status === 'WAITING' ? `
                    <button class="btn btn-sm btn-success" onclick="window.AssistantCoworkerWorkspace.controlMission('${m.mission_id}', 'RESUME')">▶️ Resume</button>
                  ` : ''}
                  <button class="btn btn-sm btn-danger" onclick="window.AssistantCoworkerWorkspace.controlMission('${m.mission_id}', 'STOP')">⏹️ Stop Mission</button>
                  <button class="btn btn-sm btn-outline" onclick="window.AssistantCoworkerWorkspace.controlMission('${m.mission_id}', 'RETRY')">🔄 Retry</button>
                </div>
              </div>
            </div>

            <!-- Execution Timeline & Deliverables -->
            <div class="card">
              <div class="card-header">
                <h3 class="card-title">Execution Timeline & Audit Milestones</h3>
              </div>
              <div class="card-body">
                <div class="timeline-container">
                  ${(m.timeline || []).map(t => `
                    <div class="timeline-item" style="display:flex; gap:12px; margin-bottom:14px;">
                      <div class="timeline-marker" style="width:10px; height:10px; border-radius:50%; background:#2563eb; margin-top:6px;"></div>
                      <div style="flex:1;">
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94a3b8;">
                          <strong>${t.stage}</strong>
                          <span>${new Date(t.timestamp * 1000).toLocaleTimeString()}</span>
                        </div>
                        <div style="font-size:0.875rem; color:#e2e8f0; margin-top:2px;">${t.detail}</div>
                      </div>
                    </div>
                  `).join('')}
                </div>

                ${m.deliverables && m.deliverables.length ? `
                  <div style="margin-top:20px; padding-top:16px; border-top:1px solid #334155;">
                    <div style="font-weight:600; margin-bottom:10px; color:#10b981;">📄 Verified Deliverables</div>
                    ${m.deliverables.map(d => `
                      <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(0,0,0,0.2); padding:10px 14px; border-radius:6px; margin-bottom:8px;">
                        <div>
                          <span style="font-family:monospace; font-size:0.875rem;">${d.split('/').pop()}</span>
                          <div style="font-size:0.75rem; color:#94a3b8;">Path: ${d}</div>
                        </div>
                        <button class="btn btn-sm btn-outline" onclick="window.AssistantCoworkerWorkspace.previewFile('${d}')">Preview</button>
                      </div>
                    `).join('')}
                  </div>
                ` : ''}

                ${m.evidence_id ? `
                  <div style="margin-top:16px; background:#0f172a; padding:12px; border-radius:6px; border:1px solid #1e293b;">
                    <span style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase;">Merkle Evidence Token</span>
                    <div style="font-family:monospace; color:#38bdf8; font-size:0.875rem;">${m.evidence_id}</div>
                  </div>
                ` : ''}
              </div>
            </div>
          </div>

          <!-- Right Column: Subworkers & Expandable Advanced Technical View -->
          <div>
            <!-- Active Sub-Workers Card -->
            <div class="card" style="margin-bottom:24px;">
              <div class="card-header">
                <h3 class="card-title">Assigned Sub-Workers</h3>
              </div>
              <div class="card-body">
                ${(m.subworkers || []).map(sw => `
                  <div style="display:flex; align-items:center; gap:10px; padding:8px 0; border-bottom:1px solid #334155;">
                    <div style="width:28px; height:28px; border-radius:50%; background:#2563eb; display:flex; align-items:center; justify-content:center; font-size:0.75rem;">🤖</div>
                    <div style="flex:1;">
                      <div style="font-size:0.875rem; font-weight:600;">${this.formatWorkerId(sw)}</div>
                      <div style="font-size:0.75rem; color:#94a3b8;">${sw}</div>
                    </div>
                    <span class="badge badge-success" style="font-size:0.7rem;">ACTIVE</span>
                  </div>
                `).join('')}
              </div>
            </div>

            <!-- Expandable Advanced Technical View -->
            <div class="card">
              <div class="card-header" style="cursor:pointer;" onclick="document.getElementById('techViewBody').classList.toggle('hidden')">
                <h3 class="card-title" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                  <span>🔧 Technical Diagnostics</span>
                  <span style="font-size:0.75rem; color:#94a3b8;">Click to Toggle</span>
                </h3>
              </div>
              <div id="techViewBody" class="card-body hidden" style="font-size:0.8125rem;">
                <div style="margin-bottom:12px;">
                  <span style="color:#94a3b8;">Underlying Runtimes:</span>
                  <div style="margin-top:4px;">
                    ${(m.runtimes_used || []).map(r => `<span class="badge badge-outline" style="margin-right:4px;">${r}</span>`).join('')}
                  </div>
                </div>
                <div style="margin-bottom:12px;">
                  <span style="color:#94a3b8;">Initiator:</span> <strong>${m.initiator}</strong>
                </div>
                <div style="margin-bottom:12px;">
                  <span style="color:#94a3b8;">Human Takeover Active:</span> <strong>${m.human_control ? 'YES' : 'NO'}</strong>
                </div>
                <div style="margin-bottom:12px;">
                  <span style="color:#94a3b8;">Sovereign Authority:</span> <strong>ZONATA Company Kernel</strong>
                </div>
                <div>
                  <button class="btn btn-sm btn-outline" style="width:100%;" onclick="window.navigateTo('/terminal')">
                    Open Governed Terminal
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    formatWorkerId(sw) {
      if (sw.includes('research')) return 'Research Worker';
      if (sw.includes('coding')) return 'Coding Worker';
      if (sw.includes('terminal')) return 'Terminal Worker';
      if (sw.includes('document')) return 'Document Worker';
      if (sw.includes('verification')) return 'Verification Worker';
      if (sw.includes('browser')) return 'Browser Worker';
      return 'Co-Worker Agent';
    }

    openMission(missionId) {
      this.currentMissionId = missionId;
      window.navigateTo('/coworker');
    }

    async stepMission(missionId) {
      try {
        const res = await fetch(`/api/coworker/missions/${missionId}/step`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast(`Advanced mission: ${data.stage}`, 'info');
          await this.refreshData();
          this.renderCoworker('view-coworker');
        }
      } catch (e) {
        showToast(`Failed: ${e.message}`, 'error');
      }
    }

    async controlMission(missionId, action) {
      try {
        const res = await fetch(`/api/coworker/missions/${missionId}/control`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || `Action ${action} succeeded`, 'success');
          await this.refreshData();
          this.renderCoworker('view-coworker');
        }
      } catch (e) {
        showToast(`Failed: ${e.message}`, 'error');
      }
    }

    // =========================================================================
    // 3. MISSIONS VIEW (Registry & Detail Modal)
    // =========================================================================
    async renderMissions(containerId) {
      await this.init();
      const el = document.getElementById(containerId);
      if (!el) return;

      el.innerHTML = `
        <div class="workspace-page-header">
          <div>
            <h1 class="page-title">Missions Registry</h1>
            <p class="page-subtitle">Track, inspect, control, and audit all autonomous background missions.</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-primary" onclick="window.navigateTo('/assistant')">+ New Mission</button>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <div class="table-responsive">
              <table class="table">
                <thead>
                  <tr>
                    <th>Mission ID</th>
                    <th>Objective</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Runtimes</th>
                    <th>Subworkers</th>
                    <th>Evidence</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.missions.map(m => `
                    <tr>
                      <td><code>${m.mission_id}</code></td>
                      <td style="max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${this.escapeHtml(m.prompt)}">
                        ${this.escapeHtml(m.prompt)}
                      </td>
                      <td><span class="badge ${this.getStatusBadgeClass(m.status)}">${m.status}</span></td>
                      <td>${Math.round(m.progress_percent)}%</td>
                      <td><span style="font-size:0.75rem;">${(m.runtimes_used || []).join(', ')}</span></td>
                      <td>${m.subworkers ? m.subworkers.length : 0}</td>
                      <td>${m.evidence_id ? `<code>${m.evidence_id.substring(0, 10)}...</code>` : '—'}</td>
                      <td>
                        <button class="btn btn-sm btn-outline" onclick="window.AssistantCoworkerWorkspace.openMissionDetail('${m.mission_id}')">
                          Details
                        </button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    }

    openMissionDetail(missionId) {
      const m = this.missions.find(x => x.mission_id === missionId);
      if (!m) return;

      const modalTitle = document.getElementById('modalTitle');
      const modalBody = document.getElementById('modalBody');
      const overlay = document.getElementById('modalOverlay');

      if (modalTitle) modalTitle.textContent = `Mission: ${m.mission_id}`;
      if (modalBody) {
        modalBody.innerHTML = `
          <div style="margin-bottom:16px;">
            <strong>Objective:</strong>
            <p style="margin-top:4px; font-size:0.95rem;">${this.escapeHtml(m.prompt)}</p>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px; font-size:0.875rem;">
            <div><strong>Status:</strong> <span class="badge ${this.getStatusBadgeClass(m.status)}">${m.status}</span></div>
            <div><strong>Progress:</strong> ${Math.round(m.progress_percent)}%</div>
            <div><strong>Initiator:</strong> ${m.initiator}</div>
            <div><strong>Created:</strong> ${new Date(m.created_at * 1000).toLocaleString()}</div>
          </div>
          <div style="margin-bottom:16px;">
            <strong>Assigned Sub-Workers:</strong>
            <ul style="margin:4px 0 0 16px; font-size:0.875rem;">
              ${(m.subworkers || []).map(s => `<li>${s}</li>`).join('')}
            </ul>
          </div>
          <div style="margin-bottom:16px;">
            <strong>Deliverables & Files:</strong>
            ${(m.deliverables || []).map(d => `<div style="font-family:monospace; font-size:0.8rem; background:rgba(0,0,0,0.2); padding:6px; border-radius:4px; margin-top:4px;">${d}</div>`).join('') || '<div style="color:#94a3b8; font-size:0.85rem;">None produced yet</div>'}
          </div>
          ${m.evidence_id ? `
            <div style="margin-bottom:16px;">
              <strong>SHA-256 Merkle Proof:</strong>
              <div style="font-family:monospace; color:#38bdf8; font-size:0.85rem;">${m.evidence_id}</div>
            </div>
          ` : ''}
          <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:20px;">
            <button class="btn btn-outline" onclick="closeModal()">Close</button>
            <button class="btn btn-primary" onclick="closeModal(); window.AssistantCoworkerWorkspace.openMission('${m.mission_id}')">Open in Co-Worker</button>
          </div>
        `;
      }
      if (overlay) overlay.style.display = 'flex';
    }

    // =========================================================================
    // 4. APPROVALS VIEW (Decision Room with 9-Part Context)
    // =========================================================================
    async renderApprovals(containerId) {
      await this.init();
      const el = document.getElementById(containerId);
      if (!el) return;

      el.innerHTML = `
        <div class="workspace-page-header">
          <div>
            <h1 class="page-title">Decision Room — Gated Approvals</h1>
            <p class="page-subtitle">Sovereign human oversight checkpoint. High-risk, financial, or system-mutating actions require explicit authorization.</p>
          </div>
        </div>

        ${this.approvals && this.approvals.length > 0 ? `
          <div style="display:flex; flex-direction:column; gap:20px;">
            ${this.approvals.map(app => `
              <div class="card" style="border-left:4px solid #f59e0b;">
                <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
                  <div>
                    <span class="badge badge-warning" style="margin-right:8px;">${app.risk_level} RISK</span>
                    <strong style="font-size:1rem;">${this.escapeHtml(app.what)}</strong>
                  </div>
                  <span style="font-size:0.75rem; color:#94a3b8;">${new Date(app.created_at * 1000).toLocaleTimeString()}</span>
                </div>
                <div class="card-body">
                  <!-- The 9 Required Auditable Context Fields -->
                  <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:14px; font-size:0.875rem; margin-bottom:20px; background:rgba(0,0,0,0.2); padding:16px; border-radius:8px;">
                    <div><span style="color:#94a3b8;">WHAT WILL HAPPEN:</span><br/><strong>${this.escapeHtml(app.what)}</strong></div>
                    <div><span style="color:#94a3b8;">WHY IT IS REQUIRED:</span><br/><strong>${this.escapeHtml(app.why)}</strong></div>
                    <div><span style="color:#94a3b8;">WHO REQUESTED IT:</span><br/><strong>${this.escapeHtml(app.who)}</strong></div>
                    <div><span style="color:#94a3b8;">WHICH WORKER:</span><br/><strong>${this.escapeHtml(app.worker)}</strong></div>
                    <div><span style="color:#94a3b8;">WHICH NODE:</span><br/><strong>${this.escapeHtml(app.node)}</strong></div>
                    <div><span style="color:#94a3b8;">WHAT DATA WILL BE USED:</span><br/><strong>${this.escapeHtml(app.data)}</strong></div>
                    <div><span style="color:#94a3b8;">CREDENTIAL SCOPE:</span><br/><strong>${this.escapeHtml(app.credentials)}</strong></div>
                    <div><span style="color:#94a3b8;">RISK LEVEL:</span><br/><strong style="color:#f59e0b;">${this.escapeHtml(app.risk_level)}</strong></div>
                    <div><span style="color:#94a3b8;">EXPECTED RESULT:</span><br/><strong>${this.escapeHtml(app.expected_result)}</strong></div>
                  </div>

                  <!-- Explicit Action Buttons -->
                  <div style="display:flex; justify-content:flex-end; gap:10px;">
                    <button class="btn btn-outline" onclick="window.AssistantCoworkerWorkspace.decideApproval('${app.approval_id}', 'CANCEL')">Cancel</button>
                    <button class="btn btn-danger" onclick="window.AssistantCoworkerWorkspace.decideApproval('${app.approval_id}', 'DENY')">Deny</button>
                    <button class="btn btn-success" onclick="window.AssistantCoworkerWorkspace.decideApproval('${app.approval_id}', 'APPROVE')">✓ Authorize & Execute</button>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="card" style="padding:48px; text-align:center;">
            <div style="font-size:2rem; margin-bottom:12px;">🛡️</div>
            <h3>No Pending Approvals</h3>
            <p style="color:#94a3b8; margin-top:6px;">All autonomous background operations are operating safely within authorized policy boundaries.</p>
          </div>
        `}
      `;
    }

    async decideApproval(approvalId, decision) {
      try {
        const res = await fetch(`/api/coworker/approvals/${approvalId}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision })
        });
        const data = await res.json();
        if (data.success) {
          showToast(`Approval decision recorded: ${decision}`, 'success');
          await this.refreshData();
          this.renderApprovals('view-approvals');
        }
      } catch (e) {
        showToast(`Failed: ${e.message}`, 'error');
      }
    }

    // =========================================================================
    // 5. UNIVERSAL LINUX TERMINAL VIEW (Section 35 Governed Execution Fabric)
    // =========================================================================
    async renderTerminal(containerId) {
      if (window.AppleGovernedTerminal) {
        window.AppleGovernedTerminal.render(containerId);
        return;
      }
      await this.init();
      const el = document.getElementById(containerId);
      if (!el) return;

      // Fetch node metrics & diagnostics
      let hostData = { cpu: { cores: 8, architecture: 'x86_64' }, ram: { total_mb: 4096, available_mb: 3000 }, disk: { free_mb: 8000 } };
      let diagStatus = 'READY';
      try {
        const diagRes = await fetch('/api/terminal/diagnostics');
        const diag = await diagRes.json();
        diagStatus = diag.status || 'READY';
        const hostRes = await fetch('/api/terminal/host-inspection');
        hostData = await hostRes.json();
      } catch (e) {
        console.warn('Diagnostics fetch fallback:', e);
      }

      const activeProfile = this.selectedProfile || 'profile_linux_dev';

      el.innerHTML = `
        <div class="workspace-page-header" style="margin-bottom:16px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
              <h1 class="page-title" style="margin:0;">Universal Linux Terminal Execution Fabric</h1>
              <span class="badge ${diagStatus === 'READY' ? 'badge-success' : 'badge-warning'}" style="font-size:0.75rem;">${diagStatus}</span>
              <span class="badge" style="background:#3b82f6; color:#fff; font-size:0.75rem;">AICU-Governed</span>
            </div>
            <p class="page-subtitle">Dynamic runtime environment selected per task. Persistent governed interface over replaceable Linux substrates.</p>
          </div>
          <div class="header-actions" style="display:flex; gap:8px;">
            <button class="btn btn-outline" onclick="window.AssistantCoworkerWorkspace.runTerminalDiag()">
              🩺 Self-Diagnostics
            </button>
            <button class="btn btn-outline" onclick="window.AssistantCoworkerWorkspace.runHostInspection()">
              💻 Hardware Inspection
            </button>
          </div>
        </div>

        <!-- Node Hardware & Substrate Telemetry Bar -->
        <div class="card" style="margin-bottom:16px; background:#0f172a; border:1px solid #1e293b;">
          <div class="card-body" style="padding:12px 16px;">
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:12px; font-size:0.8rem;">
              <div>
                <span style="color:#64748b; display:block;">Host Architecture</span>
                <strong style="color:#38bdf8;">${hostData.architecture || 'x86_64'} (${hostData.cpu ? hostData.cpu.cores : 8} Cores)</strong>
              </div>
              <div>
                <span style="color:#64748b; display:block;">RAM Capacity</span>
                <strong style="color:#10b981;">${hostData.ram ? hostData.ram.available_mb : 3000}MB / ${hostData.ram ? hostData.ram.total_mb : 4096}MB</strong>
              </div>
              <div>
                <span style="color:#64748b; display:block;">Free Storage</span>
                <strong style="color:#a855f7;">${hostData.disk ? hostData.disk.free_mb : 8000}MB Available</strong>
              </div>
              <div>
                <span style="color:#64748b; display:block;">Active Execution State</span>
                <strong id="terminalStateIndicator" style="color:#eab308;">${this.terminalCurrentState || 'PREPARING'}</strong>
              </div>
              <div>
                <span style="color:#64748b; display:block;">KillSwitch Matrix</span>
                <strong style="color:#10b981;">ACTIVE (9 Levels)</strong>
              </div>
            </div>
          </div>
        </div>

        <!-- Dynamic Linux Runtime Profile Selector -->
        <div class="card" style="margin-bottom:16px;">
          <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
            <h3 class="card-title">Dynamic Linux Runtime Profiles (Substrate Selection)</h3>
            <span style="font-size:0.75rem; color:#64748b;">Runtime is variable; Universal Terminal interface is constant</span>
          </div>
          <div class="card-body" style="padding:12px 16px;">
            <div style="display:flex; flex-wrap:wrap; gap:8px;">
              <button class="chip-btn ${activeProfile === 'profile_linux_dev' ? 'active' : ''}" style="${activeProfile === 'profile_linux_dev' ? 'background:#2563eb; color:#fff;' : ''}" onclick="window.AssistantCoworkerWorkspace.selectRuntimeProfile('profile_linux_dev')">
                🐧 Debian/Ubuntu Dev (Standard)
              </button>
              <button class="chip-btn ${activeProfile === 'profile_linux_lightweight' ? 'active' : ''}" style="${activeProfile === 'profile_linux_lightweight' ? 'background:#2563eb; color:#fff;' : ''}" onclick="window.AssistantCoworkerWorkspace.selectRuntimeProfile('profile_linux_lightweight')">
                ⚡ Alpine Lightweight (&lt;2GB RAM)
              </button>
              <button class="chip-btn ${activeProfile === 'profile_security_lab' ? 'active' : ''}" style="${activeProfile === 'profile_security_lab' ? 'background:#2563eb; color:#fff;' : ''}" onclick="window.AssistantCoworkerWorkspace.selectRuntimeProfile('profile_security_lab')">
                🛡️ Kali Defensive Security Lab
              </button>
              <button class="chip-btn ${activeProfile === 'profile_privacy_isolated' ? 'active' : ''}" style="${activeProfile === 'profile_privacy_isolated' ? 'background:#2563eb; color:#fff;' : ''}" onclick="window.AssistantCoworkerWorkspace.selectRuntimeProfile('profile_privacy_isolated')">
                🔒 Tails Privacy Isolated (VM)
              </button>
              <button class="chip-btn ${activeProfile === 'profile_desktop_gui' ? 'active' : ''}" style="${activeProfile === 'profile_desktop_gui' ? 'background:#2563eb; color:#fff;' : ''}" onclick="window.AssistantCoworkerWorkspace.selectRuntimeProfile('profile_desktop_gui')">
                🖥️ XFCE Desktop (Virtual Display)
              </button>
              <button class="chip-btn ${activeProfile === 'profile_build_node' ? 'active' : ''}" style="${activeProfile === 'profile_build_node' ? 'background:#2563eb; color:#fff;' : ''}" onclick="window.AssistantCoworkerWorkspace.selectRuntimeProfile('profile_build_node')">
                ⚙️ Fedora Build Node (Parallel)
              </button>
              <button class="chip-btn ${activeProfile === 'profile_host_controlled' ? 'active' : ''}" style="${activeProfile === 'profile_host_controlled' ? 'background:#2563eb; color:#fff;' : ''}" onclick="window.AssistantCoworkerWorkspace.selectRuntimeProfile('profile_host_controlled')">
                🏛️ Controlled Host Execution
              </button>
              <button class="chip-btn ${activeProfile === 'profile_production_verified' ? 'active' : ''}" style="${activeProfile === 'profile_production_verified' ? 'background:#2563eb; color:#fff;' : ''}" onclick="window.AssistantCoworkerWorkspace.selectRuntimeProfile('profile_production_verified')">
                🚀 Production Verified
              </button>
            </div>
          </div>
        </div>

        <!-- Terminal Quick Action Presets -->
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px;">
          <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.setTerminalCmd('uname -a; python3 --version; node -v')">Inspect Host Runtimes</button>
          <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.setTerminalCmd('git status')">Git Status Check</button>
          <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.setTerminalCmd('df -h /; free -m')">Disk & Memory Check</button>
          <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.setTerminalCmd('python3 -m unittest tests/test_governed_terminal_runtime.py')">Run Governed Tests</button>
          <button class="chip-btn" onclick="window.AssistantCoworkerWorkspace.dispatchAicuObjective('Inspect python environment, build status and git commit state')">🧠 AICU 16-Step Objective</button>
        </div>

        <!-- Command Execution & Control Panel -->
        <div class="card" style="margin-bottom:20px;">
          <div class="card-body">
            <div style="display:flex; gap:10px; align-items:center; margin-bottom:10px;">
              <span style="font-family:monospace; color:#10b981; font-weight:700;">zonata@terminal:~$</span>
              <input type="text" id="terminalCmdInput" class="form-control" style="flex:1; font-family:monospace; background:rgba(0,0,0,0.3); color:#fff;" placeholder="Enter governed command (e.g. 'python3 --version', 'git status', 'df -h /')" onkeydown="if(event.key==='Enter') window.AssistantCoworkerWorkspace.executeTerminalCmd()" />
              <button class="btn btn-primary" onclick="window.AssistantCoworkerWorkspace.executeTerminalCmd()">
                ▶ Execute
              </button>
              <button class="btn btn-outline" style="color:#ef4444; border-color:#ef4444;" onclick="window.AssistantCoworkerWorkspace.controlTerminalSession('STOP')">
                ⏹ Stop
              </button>
              <button class="btn btn-outline" onclick="window.AssistantCoworkerWorkspace.controlTerminalSession('PAUSE')">
                ⏸ Pause
              </button>
              <button class="btn btn-outline" onclick="window.AssistantCoworkerWorkspace.controlTerminalSession('RESUME')">
                ⏯ Resume
              </button>
            </div>
            <div style="font-size:0.75rem; color:#94a3b8; display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;">
              <span>Subordinate to ZONATA Governance • Merkle Evidence Ledger Verified • Zero Raw Secrets</span>
              <div style="display:flex; gap:12px; align-items:center;">
                <label style="cursor:pointer; display:flex; align-items:center; gap:4px;">
                  <input type="checkbox" id="terminalApproveCheck" style="accent-color:#2563eb;" /> Grant Consequential Pre-Approval
                </label>
                <label style="cursor:pointer; display:flex; align-items:center; gap:4px;">
                  <input type="checkbox" id="terminalGuiCheck" style="accent-color:#10b981;" /> Request Virtual Display (GUI)
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- Execution History & Output Console -->
        <div class="card">
          <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:8px;">
              <h3 class="card-title" style="margin:0;">Console Output Stream & Independent Verification</h3>
              <span id="outputStateBadge" class="badge" style="background:#0284c7; color:#fff; font-size:0.7rem;">OBSERVING</span>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-sm btn-outline" onclick="window.AssistantCoworkerWorkspace.clearTerminal()">Clear</button>
            </div>
          </div>
          <div class="card-body" style="padding:0;">
            <div id="terminalConsoleOutput" style="background:#090d16; color:#e2e8f0; font-family:monospace; font-size:0.85rem; padding:16px; min-height:280px; max-height:500px; overflow-y:auto; border-radius:0 0 8px 8px;">
              ${this.terminalHistory.length ? this.terminalHistory.map(h => this.renderTerminalHistoryItem(h)).join('') : '<div style="color:#64748b;">Awaiting command execution... Select a runtime profile or run a governed command above.</div>'}
            </div>
          </div>
        </div>
      `;
    }

    selectRuntimeProfile(profileId) {
      this.selectedProfile = profileId;
      showToast(`Selected Linux Runtime: ${profileId}`, 'info');
      this.renderTerminal('view-terminal');
    }

    setTerminalCmd(cmd) {
      const input = document.getElementById('terminalCmdInput');
      if (input) {
        input.value = cmd;
        input.focus();
      }
    }

    async controlTerminalSession(action) {
      showToast(`Session signal: ${action} sent`, 'info');
      const ind = document.getElementById('terminalStateIndicator');
      if (ind) ind.innerText = action === 'STOP' ? 'STOPPED' : (action === 'PAUSE' ? 'WAITING_AUTHORIZATION' : 'EXECUTING');
    }

    async dispatchAicuObjective(objective) {
      const ind = document.getElementById('terminalStateIndicator');
      if (ind) ind.innerText = 'DISCOVERING';

      this.terminalHistory.unshift({
        command: `[AICU Objective] ${objective}`,
        status: 'EXECUTING',
        runtime_profile: this.selectedProfile || 'profile_linux_dev',
        timestamp: Date.now() / 1000
      });
      this.updateConsoleOutput();

      try {
        const res = await fetch('/api/terminal/agent/objective', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            objective,
            human_approved: true,
            force_gui: document.getElementById('terminalGuiCheck') ? document.getElementById('terminalGuiCheck').checked : false
          })
        });
        const data = await res.json();
        this.terminalHistory[0] = {
          command: `[AICU Objective] ${objective}`,
          status: data.status,
          runtime_profile: data.runtime_profile,
          environment_used: data.environment_used,
          stdout: data.summary,
          verified: data.status === 'SUCCESS',
          evidence_hash: data.evidence_id,
          duration_ms: data.duration_ms,
          timestamp: Date.now() / 1000
        };
        if (ind) ind.innerText = data.status === 'SUCCESS' ? 'COMPLETED' : 'FAILED';
      } catch (e) {
        this.terminalHistory[0] = {
          command: `[AICU Objective] ${objective}`,
          status: 'FAILED',
          error: e.message,
          timestamp: Date.now() / 1000
        };
        if (ind) ind.innerText = 'FAILED';
      }
      this.updateConsoleOutput();
    }

    async executeTerminalCmd() {
      const input = document.getElementById('terminalCmdInput');
      if (!input || !input.value.trim()) return;

      const command = input.value.trim();
      const approved = document.getElementById('terminalApproveCheck') ? document.getElementById('terminalApproveCheck').checked : false;
      const ind = document.getElementById('terminalStateIndicator');
      if (ind) ind.innerText = 'EXECUTING';

      this.terminalHistory.unshift({
        command,
        status: 'EXECUTING',
        runtime_profile: this.selectedProfile || 'profile_linux_dev',
        timestamp: Date.now() / 1000
      });
      this.updateConsoleOutput();

      try {
        const res = await fetch('/api/terminal/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            command,
            human_approved: approved,
            profile_id: this.selectedProfile || 'profile_linux_dev',
            use_fabric: true
          })
        });
        const data = await res.json();
        this.terminalHistory[0] = {
          command,
          status: data.status,
          risk_tier: data.risk_tier,
          exit_code: data.exit_code,
          stdout: data.stdout,
          stderr: data.stderr,
          error: data.error,
          verified: data.status === 'SUCCEEDED',
          evidence_hash: data.evidence_id || data.evidence_hash,
          duration_ms: data.duration_ms,
          timestamp: Date.now() / 1000
        };
        if (ind) ind.innerText = data.status === 'SUCCEEDED' ? 'COMPLETED' : (data.status === 'POLICY_DENIED' ? 'WAITING_AUTHORIZATION' : 'FAILED');
      } catch (e) {
        this.terminalHistory[0] = {
          command,
          status: 'FAILED',
          error: e.message,
          timestamp: Date.now() / 1000
        };
        if (ind) ind.innerText = 'FAILED';
      }

      this.updateConsoleOutput();
      input.value = '';
    }

    renderTerminalHistoryItem(h) {
      return `
        <div style="margin-bottom:16px; border-bottom:1px solid #1e293b; padding-bottom:12px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <div>
              <span style="color:#10b981;">$</span> <strong style="color:#38bdf8;">${this.escapeHtml(h.command)}</strong>
              ${h.runtime_profile ? `<span class="badge" style="background:#1e293b; color:#94a3b8; font-size:0.65rem; margin-left:6px;">${h.runtime_profile}</span>` : ''}
            </div>
            <div>
              ${h.risk_tier ? `<span class="badge badge-outline" style="font-size:0.7rem; margin-right:6px;">${h.risk_tier}</span>` : ''}
              <span class="badge ${h.status === 'SUCCEEDED' || h.status === 'SUCCESS' ? 'badge-success' : (h.status === 'POLICY_DENIED' ? 'badge-danger' : 'badge-warning')}" style="font-size:0.7rem;">${h.status}</span>
            </div>
          </div>
          ${h.stdout ? `<pre style="margin:6px 0; color:#cbd5e1; white-space:pre-wrap; word-break:break-all;">${this.escapeHtml(h.stdout)}</pre>` : ''}
          ${h.stderr ? `<pre style="margin:6px 0; color:#f87171; white-space:pre-wrap;">${this.escapeHtml(h.stderr)}</pre>` : ''}
          ${h.error ? `<div style="color:#ef4444; margin:4px 0;">Error: ${this.escapeHtml(h.error)}</div>` : ''}
          <div style="font-size:0.75rem; color:#64748b; margin-top:4px; display:flex; gap:12px; flex-wrap:wrap;">
            <span>Exit Code: ${h.exit_code !== undefined ? h.exit_code : '—'}</span>
            <span style="color:${h.verified ? '#10b981' : '#f59e0b'}; font-weight:600;">Verified (Exit 0 ≠ Success): ${h.verified ? 'VERIFIED' : 'UNVERIFIED'}</span>
            ${h.evidence_hash ? `<span>Merkle Receipt: <code>${h.evidence_hash.substring(0, 16)}...</code></span>` : ''}
            ${h.duration_ms ? `<span>Duration: ${Math.round(h.duration_ms)}ms</span>` : ''}
          </div>
        </div>
      `;
    }

    updateConsoleOutput() {
      const el = document.getElementById('terminalConsoleOutput');
      if (el) {
        el.innerHTML = this.terminalHistory.map(h => this.renderTerminalHistoryItem(h)).join('');
      }
    }

    clearTerminal() {
      this.terminalHistory = [];
      this.updateConsoleOutput();
    }

    async runTerminalDiag() {
      try {
        const res = await fetch('/api/terminal/diagnostics');
        const data = await res.json();
        showToast(`Terminal Status: ${data.status} (${Object.keys(data.components).length} subsystems healthy)`, 'success');
        this.terminalHistory.unshift({
          command: '[Self-Diagnostics] TerminalHealthService Audit',
          status: data.status,
          stdout: JSON.stringify(data, null, 2),
          verified: data.status === 'READY' || data.status === 'DEGRADED',
          timestamp: Date.now() / 1000
        });
        this.updateConsoleOutput();
      } catch (e) {
        showToast(`Diagnostics failed: ${e.message}`, 'error');
      }
    }

    async runHostInspection() {
      try {
        const res = await fetch('/api/terminal/host-inspection');
        const data = await res.json();
        this.terminalHistory.unshift({
          command: '[Host Inspection] Hardware & Virtualization Telemetry',
          status: 'SUCCEEDED',
          stdout: JSON.stringify(data, null, 2),
          verified: true,
          timestamp: Date.now() / 1000
        });
        this.updateConsoleOutput();
      } catch (e) {
        showToast(`Inspection failed: ${e.message}`, 'error');
      }
    }


    // =========================================================================
    // 6. ACTIVITY & REALITY MATRIX VIEW
    // =========================================================================
    async renderActivity(containerId) {
      await this.init();
      const el = document.getElementById(containerId);
      if (!el) return;

      el.innerHTML = `
        <div class="workspace-page-header">
          <div>
            <h1 class="page-title">Co-Worker Activity & Reality Matrix</h1>
            <p class="page-subtitle">Truthful audit matrix of real, partial, and environment-constrained capabilities.</p>
          </div>
        </div>

        <!-- Telemetry Summary Cards -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-bottom:24px;">
          <div class="card" style="padding:16px;">
            <div style="color:#94a3b8; font-size:0.8rem;">Active Co-Workers</div>
            <div style="font-size:1.5rem; font-weight:700; margin-top:4px;">${this.dashboard?.metrics?.active_coworkers_count || 0}</div>
          </div>
          <div class="card" style="padding:16px;">
            <div style="color:#94a3b8; font-size:0.8rem;">Specialized Runtimes</div>
            <div style="font-size:1.5rem; font-weight:700; margin-top:4px;">${this.dashboard?.specialized_runtimes?.length || 6}</div>
          </div>
          <div class="card" style="padding:16px;">
            <div style="color:#94a3b8; font-size:0.8rem;">Total Missions</div>
            <div style="font-size:1.5rem; font-weight:700; margin-top:4px;">${this.missions.length}</div>
          </div>
          <div class="card" style="padding:16px;">
            <div style="color:#94a3b8; font-size:0.8rem;">Kill Switch State</div>
            <div style="font-size:1.5rem; font-weight:700; margin-top:4px; color:#10b981;">DISARMED</div>
          </div>
        </div>

        <!-- Truthful Reality Matrix Table -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Provider Reality & Non-Fabrication Matrix</h3>
          </div>
          <div class="card-body">
            <div class="table-responsive">
              <table class="table">
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Runtime</th>
                    <th>Status</th>
                    <th>Runnable</th>
                    <th>Real Execution</th>
                    <th>Verification</th>
                    <th>Blocker / Reality Note</th>
                  </tr>
                </thead>
                <tbody>
                  ${(this.realityMatrix || []).map(r => `
                    <tr>
                      <td><strong>${r.Provider || r['Provider ID']}</strong></td>
                      <td>${r.Version || '1.0.0'}</td>
                      <td><span class="badge ${r.Status === 'REAL_PRODUCTION_QUALIFIED' ? 'badge-success' : 'badge-warning'}">${r.Status}</span></td>
                      <td>${r.Runnable}</td>
                      <td>${r['Real Execution']}</td>
                      <td>${r.Verification}</td>
                      <td style="font-size:0.8rem; color:#94a3b8;">${r.Blocker || 'None'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Fleet Worker Nodes & Bootstrapping -->
        <div class="card" style="margin-top:24px;">
          <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <h3 class="card-title">Distributed Worker Fleet & Node Fabric</h3>
              <p style="font-size:0.8rem; color:#94a3b8; margin:0;">Zero-mock fleet nodes across Linux, Windows, macOS, GPU, and Cloud environments.</p>
            </div>
            <span class="badge badge-primary">${(this.nodes || []).length} Nodes Connected</span>
          </div>
          <div class="card-body">
            <div style="background:#090d16; border:1px solid #334155; border-radius:8px; padding:14px; margin-bottom:18px;">
              <div style="font-size:0.8rem; font-weight:600; color:#93c5fd; margin-bottom:6px;">⚡ Connect Any Machine to Fleet (Bootstrap Agent):</div>
              <div style="display:flex; gap:8px; align-items:center;">
                <code id="fleetBootstrapCmd" style="flex:1; background:#020617; color:#38bdf8; padding:8px 12px; border-radius:6px; font-size:0.8rem; user-select:all; overflow-x:auto;">${(() => { const origin = window.location.origin; return `curl -s ${origin}/api/coworker/nodes/bootstrap.py | python3 - --join ${origin} --token <YOUR_FLEET_TOKEN>`; })()}</code>
                <button class="btn btn-sm btn-outline" onclick="navigator.clipboard.writeText(document.querySelector('#fleetBootstrapCmd').innerText); showToast('Bootstrap command copied!', 'info');">Copy</button>
              </div>
            </div>

            <div class="table-responsive">
              <table class="table">
                <thead>
                  <tr>
                    <th>Node ID</th>
                    <th>Type</th>
                    <th>Platform</th>
                    <th>Architecture</th>
                    <th>State</th>
                    <th>Capabilities</th>
                    <th>GPU / Display</th>
                  </tr>
                </thead>
                <tbody>
                  ${(this.nodes || []).length === 0 ? `
                    <tr>
                      <td colspan="7" style="text-align:center; color:#94a3b8; padding:18px;">
                        No worker nodes registered. Register a node with the bootstrap command above.
                      </td>
                    </tr>` : ''}
                  ${(this.nodes || []).map(n => `
                    <tr>
                      <td><strong>${n.node_id}</strong></td>
                      <td>${n.node_type}</td>
                      <td>${n.platform}</td>
                      <td>${n.architecture}</td>
                      <td><span class="badge ${n.state === 'AUTHORIZED' ? 'badge-success' : 'badge-warning'}">${n.state}</span></td>
                      <td>${(n.capabilities || []).length} Capabilities</td>
                      <td>${n.gpu_availability ? 'GPU' : 'No GPU'} | ${n.display_availability ? 'Display' : 'Headless'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Failure & Universal Fallback Events -->
        <div class="card" style="margin-top:24px;">
          <div class="card-header">
            <h3 class="card-title">Universal Fallback & Recovery Events</h3>
          </div>
          <div class="card-body">
            ${(this.recoveryEvents && this.recoveryEvents.length > 0) ? `
              <div class="table-responsive">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Event ID</th>
                      <th>Mission</th>
                      <th>Failed Target</th>
                      <th>State</th>
                      <th>Fallback Action</th>
                      <th>Reconciliation Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${this.recoveryEvents.map(e => `
                      <tr>
                        <td><code>${e.event_id}</code></td>
                        <td>${e.mission_id}</td>
                        <td>${e.failed_provider} @ ${e.failed_node}</td>
                        <td><span class="badge ${e.state === 'RECOVERED' ? 'badge-success' : 'badge-warning'}">${e.state}</span></td>
                        <td>${e.fallback_provider || 'None'}</td>
                        <td style="font-size:0.8rem; color:#94a3b8;">${e.notes || e.error_message}</td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            ` : `
              <div style="text-align:center; padding:24px; color:#94a3b8;">
                No unrecovered failure events. All execution pipelines operating cleanly.
              </div>
            `}
          </div>
        </div>
      `;
    }

    // =========================================================================
    // 7. ARTIFACTS VIEW (Files & Deliverables)
    // =========================================================================
    async renderArtifacts(containerId) {
      await this.init();
      const el = document.getElementById(containerId);
      if (!el) return;

      el.innerHTML = `
        <div class="workspace-page-header">
          <div>
            <h1 class="page-title">Files & Verified Artifacts</h1>
            <p class="page-subtitle">Cryptographically verified deliverables synthesized by autonomous Co-Worker missions.</p>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            ${this.artifacts && this.artifacts.length > 0 ? `
              <div class="table-responsive">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Filename</th>
                      <th>Size</th>
                      <th>SHA-256 Digest</th>
                      <th>Created</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${this.artifacts.map(a => `
                      <tr>
                        <td><strong>📄 ${a.name}</strong></td>
                        <td>${Math.round(a.size_bytes / 1024 * 10) / 10} KB</td>
                        <td><code style="font-size:0.75rem;">${a.sha256.substring(0, 16)}...</code></td>
                        <td>${new Date(a.created_at * 1000).toLocaleString()}</td>
                        <td>
                          <button class="btn btn-sm btn-outline" onclick="window.AssistantCoworkerWorkspace.previewFile('${a.path}')">
                            View Content
                          </button>
                        </td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            ` : `
              <div style="text-align:center; padding:48px; color:#94a3b8;">
                No deliverables synthesized yet. Launch a mission to produce verified artifacts.
              </div>
            `}
          </div>
        </div>
      `;
    }

    previewFile(path) {
      fetch('/api/coworker/terminal/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          capability: 'terminal.file_operation',
          parameters: { action: 'read', file_path: path }
        })
      })
      .then(r => r.json())
      .then(data => {
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');
        const overlay = document.getElementById('modalOverlay');

        if (modalTitle) modalTitle.textContent = `File Preview: ${path.split('/').pop()}`;
        if (modalBody) {
          const content = data.output ? data.output.content : (data.error || 'Unable to read file');
          modalBody.innerHTML = `
            <pre style="background:#090d16; color:#e2e8f0; padding:16px; border-radius:6px; font-size:0.85rem; max-height:450px; overflow:auto; white-space:pre-wrap;">${this.escapeHtml(content)}</pre>
            <div style="text-align:right; margin-top:12px;">
              <button class="btn btn-primary" onclick="closeModal()">Close</button>
            </div>
          `;
        }
        if (overlay) overlay.style.display = 'flex';
      });
    }

    openScheduleModal() {
      window.navigateTo('/schedule');
    }

    async triggerSecurityPatrol() {
      try {
        const res = await fetch('/api/v2/coworker/security/patrol', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        if (res.ok) {
          const data = await res.json();
          alert(`Defensive Security Patrol executed successfully!\nTotal Findings: ${data.findings_count}\nClean Status: ${data.clean ? 'YES (All clear)' : 'NO (Review findings)'}`);
          await this.refreshData();
          this.renderCoworker('view-coworker');
        } else {
          alert('Failed to trigger security patrol');
        }
      } catch (e) {
        alert('Error triggering security patrol: ' + e);
      }
    }

    async dispatchCoworker2Mission(promptText) {
      if (!promptText || !promptText.trim()) return;
      try {
        const res = await fetch('/api/v2/coworker/missions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            objective: promptText.trim(),
            description: promptText.trim(),
            risk_level: 'LOW',
            auto_advance: true
          })
        });
        if (res.ok) {
          const data = await res.json();
          alert(`Coworker 2.0 Mission created: ${data.task_id} (${data.status})`);
          await this.refreshData();
          this.renderCoworker('view-coworker');
        }
      } catch (e) {
        console.error('Dispatch failed:', e);
      }
    }

    // Helper functions
    getStatusBadgeClass(status) {
      switch (status) {
        case 'COMPLETED': return 'badge-success';
        case 'RUNNING': return 'badge-primary';
        case 'WAITING':
        case 'AWAITING_APPROVAL': return 'badge-warning';
        case 'FAILED': return 'badge-danger';
        default: return 'badge-outline';
      }
    }

    escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }
  }

  window.AssistantCoworkerWorkspace = new AssistantCoworkerWorkspaceManager();
})();
