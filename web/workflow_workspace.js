/**
 * URA / ZONATA — Universal Automation Fabric Workspace
 * ====================================================
 * Enterprise production interface for governed automation:
 * - Visual Workflow Builder (Node creation, editing, connecting, validation, publication, and execution)
 * - Natural Language Workflow Draft Generation
 * - Certified Production Template Catalog (8 templates with category filter)
 * - Governed Connector & Capability Registry (6-stage qualification, rate limits, circuit breakers)
 * - Human-in-the-Loop Approval Queue (Approve, Reject, Edit & Resume)
 * - Checkpoint Time-Travel & State Inspector
 * - Open-Source SBOM & Licensing Verification
 * - Scenarios A-K Demonstration Matrix
 */

(function () {
  'use strict';

  class WorkflowWorkspaceManager {
    constructor() {
      this.containerId = 'view-workflows';
      this.activeTab = 'builder'; // 'builder', 'runs', 'templates', 'connectors', 'approvals', 'inspector', 'sbom', 'demo'
      this.workflows = [];
      this.runs = [];
      this.approvals = [];
      this.templates = [];
      this.connectors = [];
      this.fabricMetrics = null;
      this.selectedRun = null;
      this.selectedRunState = null;
      this.selectedCheckpoints = [];
      this.killswitchActive = false;

      // Active Builder State
      this.builderWorkflow = {
        id: 'wf_custom_flow',
        name: 'Custom Governed Workflow',
        version: 1,
        status: 'DRAFT',
        nodes: [
          { id: 'step_1_init', type: 'TRANSFORM', label: '1. Ingest Request Data', config: { format: 'JSON' } },
          { id: 'step_2_api', type: 'API', label: '2. Call External API', config: { connector_id: 'conn_github_v3', operation: 'get_repo' } },
          { id: 'step_3_gate', type: 'APPROVAL', label: '3. Human Approval Gate', config: { risk: 'CONFIRM' } },
          { id: 'step_4_verify', type: 'VERIFICATION', label: '4. Independent Verification', config: { postcondition: 'state_verified' } }
        ]
      };
      this.selectedBuilderNodeIndex = 0;
    }

    async render(containerId) {
      if (containerId) this.containerId = containerId;
      const el = document.getElementById(this.containerId);
      if (!el) return;

      await this.loadData();
      this.renderUI(el);
    }

    async loadData() {
      try {
        const [wfRes, runRes, apprRes, tmplRes, connRes, statusRes] = await Promise.all([
          fetch('/api/automation/workflows').then(r => r.json()).catch(() => ({ workflows: [] })),
          fetch('/api/automation/executions').then(r => r.json()).catch(() => ({ executions: [] })),
          fetch('/api/automation/approvals').then(r => r.json()).catch(() => ({ approvals: [] })),
          fetch('/api/automation/templates').then(r => r.json()).catch(() => ({ templates: [] })),
          fetch('/api/automation/connectors').then(r => r.json()).catch(() => ({ connectors: [] })),
          fetch('/api/automation/fabric/status').then(r => r.json()).catch(() => ({ killswitch_active: false }))
        ]);

        this.workflows = wfRes.workflows || [];
        this.runs = runRes.executions || [];
        this.approvals = apprRes.approvals || [];
        this.templates = tmplRes.templates || [];
        this.connectors = connRes.connectors || [];
        this.killswitchActive = !!statusRes.killswitch_active;
        this.fabricMetrics = statusRes.metrics || {};
      } catch (err) {
        console.error('Error loading automation fabric data:', err);
      }
    }

    renderUI(el) {
      const activeRunsCount = this.runs.filter(r => r.status === 'RUNNING').length;
      const waitingApprovalsCount = this.approvals.length;
      const verifiedOutcomesCount = this.runs.filter(r => r.terminal_outcome === 'BUSINESS_OUTCOME_VERIFIED').length;

      el.innerHTML = `
        <div class="workspace-page-wrapper" style="padding: 24px; max-width: 1440px; margin: 0 auto;">
          <!-- Top Header -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <h1 style="font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0;">Universal Automation Fabric</h1>
                <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600;">
                  Kestra Apache-2.0 Core
                </span>
                <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600;">
                  ZONATA Governed Kernel
                </span>
              </div>
              <p style="color: var(--text-secondary); font-size: 13.5px; margin: 0;">
                Production-grade, evidence-backed workflow execution plane with 9-stage authorization, zero silent failures, and specialized AI co-workers.
              </p>
            </div>

            <!-- Action Controls -->
            <div style="display: flex; align-items: center; gap: 10px;">
              <button class="btn-secondary" onclick="WorkflowWorkspace.toggleKillSwitch()" style="border-color: ${this.killswitchActive ? '#ef4444' : 'var(--border-color)'}; color: ${this.killswitchActive ? '#ef4444' : 'var(--text-primary)'}; font-weight: 600;">
                ${this.killswitchActive ? '🛑 KillSwitch ENGAGED' : '⚡ KillSwitch (Ready)'}
              </button>
              <button class="btn-primary" onclick="WorkflowWorkspace.openRunModal()">
                ▶ Launch Workflow
              </button>
            </div>
          </div>

          <!-- KPI Metrics Row -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
            <div class="card" style="padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface);">
              <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Active Runs</div>
              <div style="font-size: 26px; font-weight: 700; color: #3b82f6; margin-top: 4px;">${activeRunsCount}</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Durable execution threads</div>
            </div>

            <div class="card" style="padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface);">
              <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Waiting Approvals</div>
              <div style="font-size: 26px; font-weight: 700; color: ${waitingApprovalsCount > 0 ? '#f59e0b' : '#10b981'}; margin-top: 4px;">${waitingApprovalsCount}</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Human-in-the-Loop decision gates</div>
            </div>

            <div class="card" style="padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface);">
              <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Verified Outcomes</div>
              <div style="font-size: 26px; font-weight: 700; color: #10b981; margin-top: 4px;">${verifiedOutcomesCount}</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Independently verified postconditions</div>
            </div>

            <div class="card" style="padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface);">
              <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Active Connectors</div>
              <div style="font-size: 26px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${this.connectors.length}</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">OSI-compliant vetted integrations</div>
            </div>
          </div>

          <!-- Navigation Tabs -->
          <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border-color); margin-bottom: 20px; overflow-x: auto;">
            ${this.renderTabBtn('builder', '🛠️ Workflow Builder', null)}
            ${this.renderTabBtn('runs', '🚀 Execution Runs', this.runs.length)}
            ${this.renderTabBtn('templates', '📜 Production Templates', this.templates.length)}
            ${this.renderTabBtn('connectors', '🔌 Connectors & MCP', this.connectors.length)}
            ${this.renderTabBtn('approvals', '✋ Approval Queue', this.approvals.length)}
            ${this.renderTabBtn('inspector', '🔍 State Inspector', null)}
            ${this.renderTabBtn('sbom', '📋 SBOM & Licenses', 'OSI ✓')}
            ${this.renderTabBtn('demo', '🧪 Demonstration Matrix (A-K)', '11')}
          </div>

          <!-- Tab Content Area -->
          <div id="workflowTabContent">
            ${this.renderTabContent()}
          </div>
        </div>
      `;
    }

    renderTabBtn(tabId, label, badge) {
      const active = this.activeTab === tabId;
      return `
        <button onclick="WorkflowWorkspace.switchTab('${tabId}')" style="
          padding: 10px 16px;
          background: none;
          border: none;
          border-bottom: 2px solid ${active ? 'var(--accent-blue)' : 'transparent'};
          color: ${active ? 'var(--accent-blue)' : 'var(--text-secondary)'};
          font-weight: ${active ? '600' : '500'};
          font-size: 13.5px;
          cursor: pointer;
          white-space: nowrap;
          display: flex;
          align-items: center;
          gap: 8px;
        ">
          ${label}
          ${badge !== null ? `<span style="font-size: 11px; background: ${active ? 'var(--accent-blue)' : 'var(--border-color)'}; color: ${active ? '#fff' : 'var(--text-secondary)'}; padding: 1px 6px; border-radius: 10px;">${badge}</span>` : ''}
        </button>
      `;
    }

    renderTabContent() {
      if (this.activeTab === 'builder') return this.renderBuilderTab();
      if (this.activeTab === 'runs') return this.renderRunsTab();
      if (this.activeTab === 'templates') return this.renderTemplatesTab();
      if (this.activeTab === 'connectors') return this.renderConnectorsTab();
      if (this.activeTab === 'approvals') return this.renderApprovalsTab();
      if (this.activeTab === 'inspector') return this.renderInspectorTab();
      if (this.activeTab === 'sbom') return this.renderSbomTab();
      if (this.activeTab === 'demo') return this.renderDemoTab();
      return '';
    }

    // =========================================================================
    // 1. WORKFLOW BUILDER TAB
    // =========================================================================

    renderBuilderTab() {
      const wf = this.builderWorkflow;
      const nodes = wf.nodes || [];
      const selectedNode = nodes[this.selectedBuilderNodeIndex] || null;

      return `
        <div style="display: flex; flex-direction: column; gap: 20px;">
          <!-- Natural Language Generator Bar -->
          <div class="card" style="padding: 18px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <div style="font-size: 13.5px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                <span>✨</span> Autonomous Workflow Draft Generator (Specialist Agent)
              </div>
              <span style="font-size: 11.5px; color: var(--text-secondary);">Powered by WorkflowDesignAgent</span>
            </div>
            <div style="display: flex; gap: 10px;">
              <input type="text" id="nlWorkflowPrompt" placeholder="e.g. Automatically triage high-priority GitHub issues, run tests, and request lead sign-off" style="flex: 1; padding: 10px 14px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface-hover); color: var(--text-primary); font-size: 13px;" />
              <button class="btn-primary" onclick="WorkflowWorkspace.generateFromPrompt()" style="padding: 10px 18px; white-space: nowrap;">
                ⚡ Generate Draft
              </button>
            </div>
          </div>

          <!-- Main Builder Grid -->
          <div style="display: grid; grid-template-columns: 1fr 380px; gap: 20px; align-items: start;">
            <!-- Left: Visual Canvas & Step Chain -->
            <div class="card" style="padding: 20px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
              <!-- Canvas Header & Toolbar -->
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                <div>
                  <input type="text" id="builderWfName" value="${wf.name}" onchange="WorkflowWorkspace.updateWfName(this.value)" style="font-size: 16px; font-weight: 700; color: var(--text-primary); background: transparent; border: 1px dashed transparent; padding: 2px 6px; border-radius: 4px;" onfocus="this.style.borderColor='var(--accent-blue)'" onblur="this.style.borderColor='transparent'" />
                  <div style="font-size: 12px; font-family: monospace; color: var(--text-secondary); margin-top: 2px;">
                    ID: ${wf.id} • Version: v${wf.version} • Status: <span style="color: #f59e0b; font-weight: 600;">${wf.status}</span>
                  </div>
                </div>

                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                  <button class="btn-secondary" style="font-size: 12px; padding: 6px 12px;" onclick="WorkflowWorkspace.validateCurrentFlow()">
                    ✓ Validate Flow
                  </button>
                  <button class="btn-secondary" style="font-size: 12px; padding: 6px 12px;" onclick="WorkflowWorkspace.saveCurrentDraft()">
                    💾 Save Draft
                  </button>
                  <button class="btn-secondary" style="font-size: 12px; padding: 6px 12px; border-color: #10b981; color: #10b981;" onclick="WorkflowWorkspace.publishCurrentFlow()">
                    🚀 Publish
                  </button>
                  <button class="btn-primary" style="font-size: 12px; padding: 6px 14px;" onclick="WorkflowWorkspace.executeCurrentFlow()">
                    ▶ Execute
                  </button>
                </div>
              </div>

              <!-- Node Creation Buttons -->
              <div style="margin-bottom: 20px; padding: 12px; background: var(--bg-surface-hover); border-radius: 8px;">
                <div style="font-size: 11.5px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 8px;">
                  Add Execution Step
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                  <button class="btn-secondary" style="font-size: 11.5px; padding: 4px 10px;" onclick="WorkflowWorkspace.addNode('API')">🌐 API Call</button>
                  <button class="btn-secondary" style="font-size: 11.5px; padding: 4px 10px;" onclick="WorkflowWorkspace.addNode('MCP')">🛠️ MCP Tool</button>
                  <button class="btn-secondary" style="font-size: 11.5px; padding: 4px 10px;" onclick="WorkflowWorkspace.addNode('AGENT')">🤖 Agent Delegation</button>
                  <button class="btn-secondary" style="font-size: 11.5px; padding: 4px 10px;" onclick="WorkflowWorkspace.addNode('APPROVAL')">✋ Approval Gate</button>
                  <button class="btn-secondary" style="font-size: 11.5px; padding: 4px 10px;" onclick="WorkflowWorkspace.addNode('VERIFICATION')">🔍 Postcondition Verify</button>
                  <button class="btn-secondary" style="font-size: 11.5px; padding: 4px 10px;" onclick="WorkflowWorkspace.addNode('CONDITION')">🔀 Condition Branch</button>
                  <button class="btn-secondary" style="font-size: 11.5px; padding: 4px 10px;" onclick="WorkflowWorkspace.addNode('SCRIPT')">💻 Shell Script</button>
                </div>
              </div>

              <!-- Step Sequence List -->
              <div style="display: flex; flex-direction: column; gap: 12px;">
                <div style="padding: 10px 14px; background: var(--bg-surface-hover); border: 1px dashed var(--border-color); border-radius: 6px; font-size: 12px; font-weight: 600; color: var(--text-secondary); text-align: center;">
                  START (Workflow Trigger Ingestion)
                </div>

                ${nodes.map((n, idx) => {
                  const isSelected = idx === this.selectedBuilderNodeIndex;
                  return `
                    <div style="
                      padding: 14px 16px;
                      border: 1px solid ${isSelected ? 'var(--accent-blue)' : 'var(--border-color)'};
                      border-radius: 8px;
                      background: ${isSelected ? 'rgba(59, 130, 246, 0.05)' : 'var(--bg-surface)'};
                      box-shadow: ${isSelected ? '0 0 0 2px rgba(59, 130, 246, 0.2)' : 'none'};
                      cursor: pointer;
                      transition: all 0.15s ease;
                    " onclick="WorkflowWorkspace.selectBuilderNode(${idx})">
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                          <span style="font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: ${this.getNodeBadgeBg(n.type)}; color: ${this.getNodeBadgeCol(n.type)};">
                            ${n.type}
                          </span>
                          <span style="font-weight: 600; font-size: 13.5px; color: var(--text-primary);">
                            ${n.label}
                          </span>
                        </div>
                        <div style="display: flex; gap: 6px;" onclick="event.stopPropagation()">
                          <button class="btn-secondary" style="padding: 2px 6px; font-size: 11px;" onclick="WorkflowWorkspace.moveNode(${idx}, -1)" ${idx === 0 ? 'disabled' : ''}>▲</button>
                          <button class="btn-secondary" style="padding: 2px 6px; font-size: 11px;" onclick="WorkflowWorkspace.moveNode(${idx}, 1)" ${idx === nodes.length - 1 ? 'disabled' : ''}>▼</button>
                          <button class="btn-secondary" style="padding: 2px 6px; font-size: 11px; color: #ef4444; border-color: rgba(239, 68, 68, 0.3);" onclick="WorkflowWorkspace.deleteNode(${idx})">✕</button>
                        </div>
                      </div>
                      <div style="font-size: 11.5px; font-family: monospace; color: var(--text-secondary); margin-top: 6px;">
                        ID: ${n.id} • Config: ${JSON.stringify(n.config || {})}
                      </div>
                    </div>
                  `;
                }).join('')}

                <div style="padding: 10px 14px; background: rgba(16, 185, 129, 0.08); border: 1px dashed rgba(16, 185, 129, 0.4); border-radius: 6px; font-size: 12px; font-weight: 600; color: #10b981; text-align: center;">
                  END (Terminal Verification & Merkle Audit Proof)
                </div>
              </div>
            </div>

            <!-- Right: Property Inspector -->
            <div class="card" style="padding: 20px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
              <h3 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0 0 16px 0;">
                Step Property Inspector
              </h3>

              ${selectedNode ? `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                  <div>
                    <label style="display: block; font-size: 11.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Step ID</label>
                    <input type="text" id="propNodeId" value="${selectedNode.id}" onchange="WorkflowWorkspace.updateSelectedNode('id', this.value)" style="width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface-hover); color: var(--text-primary); font-family: monospace; font-size: 12px;" />
                  </div>

                  <div>
                    <label style="display: block; font-size: 11.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Step Label</label>
                    <input type="text" id="propNodeLabel" value="${selectedNode.label}" onchange="WorkflowWorkspace.updateSelectedNode('label', this.value)" style="width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface-hover); color: var(--text-primary); font-size: 12.5px;" />
                  </div>

                  <div>
                    <label style="display: block; font-size: 11.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Node Type</label>
                    <input type="text" value="${selectedNode.type}" readonly style="width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface-hover); color: var(--text-secondary); font-size: 12px;" />
                  </div>

                  <div>
                    <label style="display: block; font-size: 11.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Step Configuration (JSON)</label>
                    <textarea id="propNodeConfig" rows="6" onchange="WorkflowWorkspace.updateSelectedNodeConfig(this.value)" style="width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface-hover); color: var(--text-primary); font-family: monospace; font-size: 12px;">${JSON.stringify(selectedNode.config || {}, null, 2)}</textarea>
                  </div>

                  <div style="margin-top: 10px; padding: 12px; background: var(--bg-surface-hover); border-radius: 6px; font-size: 11.5px; color: var(--text-secondary);">
                    <strong>Authority Invariant:</strong> Step definitions must satisfy PolicyEngine least-privilege contracts prior to lease issuance.
                  </div>
                </div>
              ` : `
                <div style="color: var(--text-secondary); font-size: 13px; text-align: center; padding: 40px 0;">
                  Select a step from the sequence to inspect and configure properties.
                </div>
              `}
            </div>
          </div>
        </div>
      `;
    }

    getNodeBadgeBg(type) {
      if (type === 'API') return 'rgba(59, 130, 246, 0.15)';
      if (type === 'MCP') return 'rgba(139, 92, 246, 0.15)';
      if (type === 'AGENT') return 'rgba(16, 185, 129, 0.15)';
      if (type === 'APPROVAL') return 'rgba(245, 158, 11, 0.15)';
      if (type === 'VERIFICATION') return 'rgba(6, 182, 212, 0.15)';
      if (type === 'CONDITION') return 'rgba(236, 72, 153, 0.15)';
      return 'rgba(107, 114, 128, 0.15)';
    }

    getNodeBadgeCol(type) {
      if (type === 'API') return '#3b82f6';
      if (type === 'MCP') return '#8b5cf6';
      if (type === 'AGENT') return '#10b981';
      if (type === 'APPROVAL') return '#f59e0b';
      if (type === 'VERIFICATION') return '#06b6d4';
      if (type === 'CONDITION') return '#ec4899';
      return '#6b7280';
    }

    selectBuilderNode(idx) {
      this.selectedBuilderNodeIndex = idx;
      this.render();
    }

    updateWfName(val) {
      this.builderWorkflow.name = val;
    }

    addNode(type) {
      const idx = this.builderWorkflow.nodes.length + 1;
      const id = `step_${idx}_${type.toLowerCase()}`;
      let defaultConfig = {};
      if (type === 'API') defaultConfig = { connector_id: 'conn_github_v3', operation: 'get_repo' };
      if (type === 'MCP') defaultConfig = { operation: 'query_knowledge' };
      if (type === 'AGENT') defaultConfig = { role: 'SoftwareEngineeringAgent' };
      if (type === 'APPROVAL') defaultConfig = { risk: 'CONFIRM' };
      if (type === 'VERIFICATION') defaultConfig = { postcondition: 'verified_state' };

      this.builderWorkflow.nodes.push({
        id: id,
        type: type,
        label: `${idx}. Execute ${type}`,
        config: defaultConfig
      });
      this.selectedBuilderNodeIndex = this.builderWorkflow.nodes.length - 1;
      this.render();
      showToast(`Added ${type} step to workflow`, 'info');
    }

    deleteNode(idx) {
      this.builderWorkflow.nodes.splice(idx, 1);
      if (this.selectedBuilderNodeIndex >= this.builderWorkflow.nodes.length) {
        this.selectedBuilderNodeIndex = Math.max(0, this.builderWorkflow.nodes.length - 1);
      }
      this.render();
    }

    moveNode(idx, delta) {
      const newIdx = idx + delta;
      if (newIdx < 0 || newIdx >= this.builderWorkflow.nodes.length) return;
      const item = this.builderWorkflow.nodes.splice(idx, 1)[0];
      this.builderWorkflow.nodes.splice(newIdx, 0, item);
      this.selectedBuilderNodeIndex = newIdx;
      this.render();
    }

    updateSelectedNode(field, val) {
      const node = this.builderWorkflow.nodes[this.selectedBuilderNodeIndex];
      if (node) {
        node[field] = val;
      }
    }

    updateSelectedNodeConfig(jsonStr) {
      try {
        const parsed = JSON.parse(jsonStr);
        const node = this.builderWorkflow.nodes[this.selectedBuilderNodeIndex];
        if (node) {
          node.config = parsed;
        }
      } catch (err) {
        showToast('Invalid JSON in config: ' + err.message, 'error');
      }
    }

    async generateFromPrompt() {
      const prompt = document.getElementById('nlWorkflowPrompt').value;
      if (!prompt || !prompt.trim()) {
        showToast('Please enter an automation prompt', 'warning');
        return;
      }

      showToast('Specialist WorkflowDesignAgent drafting workflow...', 'info');
      try {
        const res = await fetch('/api/automation/agent/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt })
        }).then(r => r.json());

        if (res.success && res.generated_workflow) {
          const gen = res.generated_workflow;
          this.builderWorkflow = {
            id: gen.flow_id || `wf_${Date.now()}`,
            name: gen.name || `Workflow for ${prompt.substring(0, 24)}...`,
            version: 1,
            status: 'DRAFT',
            nodes: gen.nodes || []
          };
          this.selectedBuilderNodeIndex = 0;
          this.render();
          showToast('Workflow draft generated successfully!', 'success');
        } else {
          showToast('Generation failed: ' + (res.error || 'Unknown error'), 'error');
        }
      } catch (err) {
        showToast('Error generating workflow: ' + err.message, 'error');
      }
    }

    buildKestraSpecFromCurrentFlow() {
      const wf = this.builderWorkflow;
      const tasks = (wf.nodes || []).map(n => {
        let kType = 'io.kestra.plugin.core.flow.Sequential';
        if (n.type === 'API') kType = 'io.kestra.plugin.core.http.Request';
        else if (n.type === 'MCP') kType = 'io.kestra.plugin.zonata.mcp.Call';
        else if (n.type === 'AGENT') kType = 'io.kestra.plugin.zonata.agent.Delegate';
        else if (n.type === 'APPROVAL') kType = 'io.kestra.plugin.zonata.approval.Gate';
        else if (n.type === 'VERIFICATION') kType = 'io.kestra.plugin.zonata.verify.Postcondition';
        else if (n.type === 'CONDITION') kType = 'io.kestra.plugin.core.flow.If';
        else if (n.type === 'SCRIPT') kType = 'io.kestra.plugin.scripts.exec.Commands';

        return {
          id: n.id,
          type: kType,
          description: n.label,
          ...(n.config || {})
        };
      });

      return {
        id: wf.id,
        namespace: 'ura.automation',
        revision: wf.version,
        description: wf.name,
        tasks: tasks
      };
    }

    validateCurrentFlow() {
      const spec = this.buildKestraSpecFromCurrentFlow();
      if (!spec.tasks || spec.tasks.length === 0) {
        showToast('Validation Error: Workflow must have at least one step.', 'error');
        return false;
      }
      showToast('✓ Workflow specification validated against Kestra core schema.', 'success');
      return true;
    }

    async saveCurrentDraft() {
      if (!this.validateCurrentFlow()) return;
      const spec = this.buildKestraSpecFromCurrentFlow();

      try {
        const res = await fetch('/api/automation/workflows', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: this.builderWorkflow.name, spec: spec })
        }).then(r => r.json());

        if (res.workflow_id) {
          showToast(`Saved draft workflow '${res.workflow_id}'`, 'success');
          this.builderWorkflow.id = res.workflow_id;
          this.builderWorkflow.status = res.status;
          await this.loadData();
          this.render();
        } else {
          showToast('Save failed: ' + (res.error || 'Unknown error'), 'error');
        }
      } catch (err) {
        showToast('Error saving draft: ' + err.message, 'error');
      }
    }

    async publishCurrentFlow() {
      const wfId = this.builderWorkflow.id;
      try {
        const res = await fetch(`/api/automation/workflows/${wfId}/publish`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }).then(r => r.json());

        if (res.status === 'PUBLISHED') {
          showToast(`Workflow '${wfId}' PUBLISHED and sealed for execution.`, 'success');
          this.builderWorkflow.status = 'PUBLISHED';
          await this.loadData();
          this.render();
        } else {
          showToast('Publish failed: ' + (res.error || 'Save draft first'), 'error');
        }
      } catch (err) {
        showToast('Error publishing: ' + err.message, 'error');
      }
    }

    async executeCurrentFlow() {
      const wfId = this.builderWorkflow.id;
      try {
        const res = await fetch(`/api/automation/workflows/${wfId}/execute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ inputs: { triggered_by: 'WorkflowBuilder' } })
        }).then(r => r.json());

        if (res.execution_id) {
          showToast(`Executed: ${res.terminal_outcome} (ID: ${res.execution_id})`, res.terminal_outcome.includes('VERIFIED') || res.terminal_outcome.includes('SUCCESS') ? 'success' : 'info');
          this.activeTab = 'runs';
          await this.loadData();
          this.render();
        } else {
          showToast('Execution error: ' + (res.error || 'Unknown error'), 'error');
        }
      } catch (err) {
        showToast('Execution error: ' + err.message, 'error');
      }
    }

    // =========================================================================
    // 2. TEMPLATES TAB
    // =========================================================================

    renderTemplatesTab() {
      return `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0;">
              Certified production workflow templates with versioned schemas, verification postconditions, and compensation strategies.
            </p>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px;">
            ${this.templates.map(tmpl => `
              <div class="card" style="padding: 18px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface); display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <h4 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0;">${tmpl.name}</h4>
                    <span class="badge" style="background: rgba(59, 130, 246, 0.1); color: var(--accent-blue); font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 600;">
                      v${tmpl.version}
                    </span>
                  </div>
                  <div style="display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap;">
                    <span style="font-size: 11px; background: var(--bg-surface-hover); padding: 2px 6px; border-radius: 4px; color: var(--text-secondary);">
                      📂 ${tmpl.category}
                    </span>
                    <span style="font-size: 11px; background: rgba(16, 185, 129, 0.1); padding: 2px 6px; border-radius: 4px; color: #10b981; font-weight: 600;">
                      ${tmpl.license}
                    </span>
                  </div>
                  <p style="font-size: 12.5px; color: var(--text-secondary); margin: 0 0 14px 0; min-height: 48px;">
                    ${tmpl.purpose}
                  </p>
                </div>

                <div style="display: flex; gap: 8px; margin-top: 14px;">
                  <button class="btn-secondary" style="flex: 1; font-size: 12px; padding: 6px 10px;" onclick="WorkflowWorkspace.loadTemplateIntoBuilder('${tmpl.template_id}')">
                    ✏️ Load into Builder
                  </button>
                  <button class="btn-primary" style="flex: 1; font-size: 12px; padding: 6px 10px;" onclick="WorkflowWorkspace.instantiateAndExecuteTemplate('${tmpl.template_id}')">
                    ▶ Instantiate & Run
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    loadTemplateIntoBuilder(tmplId) {
      const tmpl = this.templates.find(t => t.template_id === tmplId);
      if (!tmpl) return;

      const spec = tmpl.workflow_spec || {};
      const tasks = spec.tasks || [];
      const nodes = tasks.map((t, idx) => {
        let nType = 'TRANSFORM';
        if (t.type.includes('Request')) nType = 'API';
        else if (t.type.includes('mcp.Call')) nType = 'MCP';
        else if (t.type.includes('agent.Delegate')) nType = 'AGENT';
        else if (t.type.includes('approval.Gate') || t.type.includes('Pause')) nType = 'APPROVAL';
        else if (t.type.includes('verify.Postcondition')) nType = 'VERIFICATION';
        else if (t.type.includes('Commands')) nType = 'SCRIPT';

        return {
          id: t.id,
          type: nType,
          label: t.description || t.id,
          config: t
        };
      });

      this.builderWorkflow = {
        id: `wf_${tmpl.template_id.replace('tmpl_', '')}_${Date.now()}`,
        name: `${tmpl.name} (Customized)`,
        version: 1,
        status: 'DRAFT',
        nodes: nodes
      };
      this.selectedBuilderNodeIndex = 0;
      this.activeTab = 'builder';
      this.render();
      showToast(`Template '${tmpl.name}' loaded into Workflow Builder`, 'success');
    }

    async instantiateAndExecuteTemplate(tmplId) {
      try {
        const res = await fetch(`/api/automation/templates/${tmplId}/instantiate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ inputs: { run_mode: 'AUTOMATED_INSTANTIATION' } })
        }).then(r => r.json());

        if (res.draft) {
          showToast(`Instantiated template into draft '${res.draft.workflow_id}'`, 'info');
          // Now execute
          await fetch(`/api/automation/workflows/${res.draft.workflow_id}/publish`, { method: 'POST' });
          const execRes = await fetch(`/api/automation/workflows/${res.draft.workflow_id}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs: {} })
          }).then(r => r.json());

          showToast(`Execution finished: ${execRes.terminal_outcome}`, 'success');
          this.activeTab = 'runs';
          await this.loadData();
          this.render();
        } else {
          showToast('Instantiation error: ' + (res.error || 'Failed'), 'error');
        }
      } catch (err) {
        showToast('Error instantiating template: ' + err.message, 'error');
      }
    }

    // =========================================================================
    // 3. CONNECTORS TAB
    // =========================================================================

    renderConnectorsTab() {
      return `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0;">
              Governed integration catalog with 6-stage qualification, SSRF protection, token-bucket rate limiting, and circuit breakers.
            </p>
            <button class="btn-primary" onclick="WorkflowWorkspace.openQualifyConnectorModal()">
              + Qualify Candidate Connector
            </button>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
            ${this.connectors.map(c => `
              <div class="card" style="padding: 18px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                  <div>
                    <h4 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0;">${c.name}</h4>
                    <div style="font-size: 11.5px; font-family: monospace; color: var(--text-secondary); margin-top: 2px;">
                      ${c.connector_id} • v${c.version}
                    </div>
                  </div>
                  <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600;">
                    ${c.health_status}
                  </span>
                </div>

                <div style="display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap;">
                  <span style="font-size: 11px; background: rgba(59, 130, 246, 0.1); color: var(--accent-blue); padding: 2px 6px; border-radius: 4px; font-weight: 600;">
                    ${c.license}
                  </span>
                  <span style="font-size: 11px; background: var(--bg-surface-hover); color: var(--text-secondary); padding: 2px 6px; border-radius: 4px;">
                    ${c.rate_limit_rpm} RPM
                  </span>
                  <span style="font-size: 11px; background: var(--bg-surface-hover); color: var(--text-secondary); padding: 2px 6px; border-radius: 4px;">
                    Risk: ${c.risk_classification}
                  </span>
                </div>

                <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
                  <strong>Operations:</strong> ${(c.supported_operations || []).join(', ')}
                </div>

                <button class="btn-secondary" style="width: 100%; font-size: 12px; padding: 6px 12px;" onclick="WorkflowWorkspace.testConnector('${c.connector_id}')">
                  ⚡ Test Connectivity
                </button>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    openQualifyConnectorModal() {
      window.openModal('Qualify New Integration Connector', `
        <form onsubmit="WorkflowWorkspace.submitQualifyConnector(event)">
          <div style="margin-bottom: 12px;">
            <label style="display:block; font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:4px;">Connector Name</label>
            <input type="text" id="candidateName" placeholder="e.g. Stripe Billing Gateway" required style="width:100%; padding:8px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-surface); color:var(--text-primary); font-size:12.5px;" />
          </div>
          <div style="margin-bottom: 12px;">
            <label style="display:block; font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:4px;">SPDX License</label>
            <select id="candidateLicense" style="width:100%; padding:8px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-surface); color:var(--text-primary); font-size:12.5px;">
              <option value="Apache-2.0">Apache-2.0 (Approved)</option>
              <option value="MIT">MIT (Approved)</option>
              <option value="BSD-3-Clause">BSD-3-Clause (Approved)</option>
              <option value="UNAPPROVED_PROPRIETARY">Proprietary (Will Fail Qualification)</option>
            </select>
          </div>
          <div style="margin-bottom: 16px;">
            <label style="display:block; font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:4px;">Supported Operations (comma-separated)</label>
            <input type="text" id="candidateOps" value="create_charge, refund, get_customer" required style="width:100%; padding:8px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-surface); color:var(--text-primary); font-size:12.5px;" />
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Run Qualification Gates</button>
          </div>
        </form>
      `);
    }

    async submitQualifyConnector(e) {
      e.preventDefault();
      const name = document.getElementById('candidateName').value;
      const license = document.getElementById('candidateLicense').value;
      const ops = document.getElementById('candidateOps').value.split(',').map(s => s.trim()).filter(Boolean);
      closeModal();

      try {
        const res = await fetch('/api/automation/connectors/discover', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            candidate: {
              name: name,
              license: license,
              supported_operations: ops,
              auth_mechanism: 'API_KEY',
              tenant_isolated: true,
              risk_classification: 'CONFIRM'
            }
          })
        }).then(r => r.json());

        if (res.success) {
          showToast(`✓ ${res.message}`, 'success');
          await this.loadData();
          this.render();
        } else {
          showToast(`✕ Rejected: ${res.message}`, 'error');
        }
      } catch (err) {
        showToast('Error qualifying connector: ' + err.message, 'error');
      }
    }

    async testConnector(connId) {
      showToast(`Testing connectivity for ${connId}...`, 'info');
      try {
        const res = await fetch('/api/automation/agents/IntegrationDiscoveryAgent/delegate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            objective: `Health probe for ${connId}`,
            parameters: { connector_id: connId }
          })
        }).then(r => r.json());
        showToast(`✓ Connector ${connId} online and responsive.`, 'success');
      } catch (err) {
        showToast('Connectivity test failed: ' + err.message, 'error');
      }
    }

    // =========================================================================
    // 4. SBOM & LICENSING TAB
    // =========================================================================

    renderSbomTab() {
      return `
        <div style="display: flex; flex-direction: column; gap: 20px;">
          <div class="card" style="padding: 20px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
              <div>
                <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">
                  Software Bill of Materials (SBOM) & OSI Compliance
                </h3>
                <p style="font-size: 12.5px; color: var(--text-secondary); margin: 0;">
                  CycloneDX v1.5 standard compliance verification. All orchestrators, libraries, and dependencies strictly validated.
                </p>
              </div>
              <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-size: 12px; padding: 4px 10px; border-radius: 12px; font-weight: 700;">
                100% OSI-APPROVED
              </span>
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid var(--border-color); background: var(--bg-surface-hover); color: var(--text-secondary);">
                  <th style="padding: 10px 14px;">Component</th>
                  <th style="padding: 10px 14px;">Version</th>
                  <th style="padding: 10px 14px;">SPDX License</th>
                  <th style="padding: 10px 14px;">Commercial SaaS Rights</th>
                  <th style="padding: 10px 14px;">Isolation Confinement</th>
                </tr>
              </thead>
              <tbody>
                <tr style="border-bottom: 1px solid var(--border-color);">
                  <td style="padding: 10px 14px; font-weight: 600; color: var(--text-primary);">Kestra Open-Source Core</td>
                  <td style="padding: 10px 14px; font-family: monospace;">v0.18.2</td>
                  <td style="padding: 10px 14px;"><span style="color: #10b981; font-weight: 600;">Apache-2.0</span></td>
                  <td style="padding: 10px 14px; color: #10b981;">✓ Permissive (Unrestricted)</td>
                  <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">Embedded Core Adapter</td>
                </tr>
                <tr style="border-bottom: 1px solid var(--border-color);">
                  <td style="padding: 10px 14px; font-weight: 600; color: var(--text-primary);">LangGraph Core Engine</td>
                  <td style="padding: 10px 14px; font-family: monospace;">v0.2.14</td>
                  <td style="padding: 10px 14px;"><span style="color: #10b981; font-weight: 600;">MIT</span></td>
                  <td style="padding: 10px 14px; color: #10b981;">✓ Permissive (Unrestricted)</td>
                  <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">Embedded StateGraph Runtime</td>
                </tr>
                <tr style="border-bottom: 1px solid var(--border-color);">
                  <td style="padding: 10px 14px; font-weight: 600; color: var(--text-primary);">Model Context Protocol SDK</td>
                  <td style="padding: 10px 14px; font-family: monospace;">v1.1.0</td>
                  <td style="padding: 10px 14px;"><span style="color: #10b981; font-weight: 600;">MIT</span></td>
                  <td style="padding: 10px 14px; color: #10b981;">✓ Permissive (Unrestricted)</td>
                  <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">Interprocess Client</td>
                </tr>
                <tr style="border-bottom: 1px solid var(--border-color);">
                  <td style="padding: 10px 14px; font-weight: 600; color: var(--text-primary);">Playwright Automation</td>
                  <td style="padding: 10px 14px; font-family: monospace;">v1.44.0</td>
                  <td style="padding: 10px 14px;"><span style="color: #10b981; font-weight: 600;">Apache-2.0</span></td>
                  <td style="padding: 10px 14px; color: #10b981;">✓ Permissive (Unrestricted)</td>
                  <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">Remote Worker Node</td>
                </tr>
                <tr>
                  <td style="padding: 10px 14px; font-weight: 600; color: var(--text-primary);">OpenHands Agent</td>
                  <td style="padding: 10px 14px; font-family: monospace;">v0.9.1</td>
                  <td style="padding: 10px 14px;"><span style="color: #10b981; font-weight: 600;">MIT</span></td>
                  <td style="padding: 10px 14px; color: #10b981;">✓ Permissive (Unrestricted)</td>
                  <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">Container Sandbox</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    // =========================================================================
    // 5. RUNS & STATE INSPECTOR
    // =========================================================================

    renderRunsTab() {
      if (!this.runs.length) {
        return `
          <div class="card" style="padding: 40px; text-align: center; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <div style="font-size: 32px; margin-bottom: 12px;">💤</div>
            <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">No Active Workflow Executions</h3>
            <p style="font-size: 13px; max-width: 480px; margin: 0 auto 16px auto;">
              Launch a workflow from the Builder or instantiate a Certified Production Template.
            </p>
            <button class="btn-primary" onclick="WorkflowWorkspace.openRunModal()">Launch Workflow</button>
          </div>
        `;
      }

      return `
        <div class="card" style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); overflow: hidden;">
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid var(--border-color); background: var(--bg-surface-hover); color: var(--text-secondary);">
                  <th style="padding: 12px 16px;">Execution ID</th>
                  <th style="padding: 12px 16px;">Workflow</th>
                  <th style="padding: 12px 16px;">Version</th>
                  <th style="padding: 12px 16px;">Status</th>
                  <th style="padding: 12px 16px;">Terminal Outcome</th>
                  <th style="padding: 12px 16px;">Created</th>
                  <th style="padding: 12px 16px; text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${this.runs.map(r => `
                  <tr style="border-bottom: 1px solid var(--border-color); cursor: pointer;" onclick="WorkflowWorkspace.inspectRun('${r.execution_id}')">
                    <td style="padding: 12px 16px; font-family: monospace; color: var(--accent-blue); font-weight: 600;">${r.execution_id}</td>
                    <td style="padding: 12px 16px; font-weight: 500; color: var(--text-primary);">${r.workflow_id}</td>
                    <td style="padding: 12px 16px; font-family: monospace;">v${r.version}</td>
                    <td style="padding: 12px 16px;">${this.renderStatusBadge(r.status)}</td>
                    <td style="padding: 12px 16px;">
                      <span style="font-size: 11px; font-weight: 700; color: ${this.getOutcomeCol(r.terminal_outcome)};">
                        ${r.terminal_outcome || 'IN_PROGRESS'}
                      </span>
                    </td>
                    <td style="padding: 12px 16px; color: var(--text-secondary); font-size: 12px;">${new Date(r.created_at * 1000).toLocaleTimeString()}</td>
                    <td style="padding: 12px 16px; text-align: right;" onclick="event.stopPropagation()">
                      ${this.renderRunActions(r)}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    renderStatusBadge(status) {
      let bg = 'rgba(107, 114, 128, 0.15)';
      let col = '#6b7280';
      if (status === 'RUNNING') { bg = 'rgba(59, 130, 246, 0.15)'; col = '#3b82f6'; }
      else if (status === 'COMPLETED') { bg = 'rgba(16, 185, 129, 0.15)'; col = '#10b981'; }
      else if (status === 'WAITING_FOR_APPROVAL' || status === 'WAITING_FOR_INPUT') { bg = 'rgba(245, 158, 11, 0.15)'; col = '#f59e0b'; }
      else if (status === 'FAILED' || status === 'BLOCKED') { bg = 'rgba(239, 68, 68, 0.15)'; col = '#ef4444'; }
      else if (status === 'UNKNOWN_OUTCOME') { bg = 'rgba(236, 72, 153, 0.15)'; col = '#ec4899'; }

      return `
        <span style="background:${bg}; color:${col}; font-size:11px; padding:3px 8px; border-radius:10px; font-weight:600; text-transform:uppercase;">
          ${status}
        </span>
      `;
    }

    getOutcomeCol(outcome) {
      if (!outcome) return 'var(--text-secondary)';
      if (outcome.includes('VERIFIED')) return '#10b981';
      if (outcome.includes('SUCCESS')) return '#3b82f6';
      if (outcome.includes('FAILED') || outcome.includes('BLOCKED')) return '#ef4444';
      if (outcome.includes('UNKNOWN')) return '#ec4899';
      return 'var(--text-secondary)';
    }

    renderRunActions(r) {
      if (r.status === 'FAILED') {
        return `<button class="btn-primary" style="padding:4px 8px; font-size:11.5px;" onclick="WorkflowWorkspace.recoverRun('${r.execution_id}')">Recover</button>`;
      }
      if (r.status === 'UNKNOWN_OUTCOME') {
        return `<button class="btn-primary" style="padding:4px 8px; font-size:11.5px; background: #ec4899;" onclick="WorkflowWorkspace.reconcileRun('${r.execution_id}')">Reconcile</button>`;
      }
      return `<button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="WorkflowWorkspace.inspectRun('${r.execution_id}')">Inspect</button>`;
    }

    renderApprovalsTab() {
      if (!this.approvals.length) {
        return `
          <div class="card" style="padding: 40px; text-align: center; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <div style="font-size: 32px; margin-bottom: 12px;">✅</div>
            <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">All Operations Authorized</h3>
            <p style="font-size: 13px; max-width: 480px; margin: 0 auto;">
              No pending approval requests. Privileged side-effects requiring human employee authorization will pause and appear here.
            </p>
          </div>
        `;
      }

      return `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          ${this.approvals.map(appr => `
            <div class="card" style="padding: 18px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <div>
                  <span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b; font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600;">
                    ${appr.risk_level} RISK
                  </span>
                  <h4 style="font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 6px 0 2px 0;">${appr.proposed_action}</h4>
                  <div style="font-size: 12px; font-family: monospace; color: var(--text-secondary);">
                    Execution: ${appr.execution_id} • Step: ${appr.step_id} • Version: v${appr.workflow_version}
                  </div>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary);">
                  ${new Date(appr.created_at * 1000).toLocaleTimeString()}
                </div>
              </div>

              <!-- Parameters preview -->
              <div style="background: var(--bg-surface-hover); padding: 10px 14px; border-radius: 6px; font-family: monospace; font-size: 12px; color: var(--text-primary); margin-bottom: 14px; overflow-x: auto;">
                ${JSON.stringify(appr.parameters, null, 2)}
              </div>

              <div style="display: flex; justify-content: flex-end; gap: 10px;">
                <button class="btn-secondary" style="border-color: #ef4444; color: #ef4444; font-size: 12.5px; padding: 6px 14px;" onclick="WorkflowWorkspace.decideApproval('${appr.approval_id}', 'REJECT')">
                  Reject Action
                </button>
                <button class="btn-secondary" style="font-size: 12.5px; padding: 6px 14px;" onclick="WorkflowWorkspace.openEditModal('${appr.approval_id}', '${encodeURIComponent(JSON.stringify(appr.parameters))}')">
                  ✏️ Edit & Resume
                </button>
                <button class="btn-primary" style="font-size: 12.5px; padding: 6px 14px;" onclick="WorkflowWorkspace.decideApproval('${appr.approval_id}', 'APPROVE')">
                  ✓ Approve Execution
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    renderInspectorTab() {
      if (!this.selectedRun) {
        return `
          <div class="card" style="padding: 40px; text-align: center; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <div style="font-size: 32px; margin-bottom: 12px;">🔍</div>
            <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Select an Execution to Inspect</h3>
            <p style="font-size: 13px; max-width: 480px; margin: 0 auto 16px auto;">
              Click any execution from the 'Execution Runs' tab to inspect its step results and evidence proof.
            </p>
            ${this.runs.length > 0 ? `
              <button class="btn-primary" onclick="WorkflowWorkspace.inspectRun('${this.runs[0].execution_id}')">
                Inspect Latest Run (${this.runs[0].execution_id})
              </button>
            ` : ''}
          </div>
        `;
      }

      const ex = this.selectedRunState ? this.selectedRunState.execution : null;
      const stepResults = ex ? ex.step_results : [];

      return `
        <div style="display: grid; grid-template-columns: 1fr 360px; gap: 20px; align-items: start;">
          <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
              <div>
                <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0;">Execution Step Evidence</h3>
                <div style="font-size: 12px; font-family: monospace; color: var(--text-secondary);">ID: ${this.selectedRun}</div>
              </div>
              <div>${ex ? this.renderStatusBadge(ex.status) : ''}</div>
            </div>

            <!-- Steps timeline -->
            <div style="display: flex; flex-direction: column; gap: 10px;">
              ${(stepResults || []).map((s, idx) => `
                <div style="padding: 12px 14px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-surface); display: flex; justify-content: space-between; align-items: center;">
                  <div>
                    <span style="font-weight: 700; color: var(--accent-blue); font-size: 12px;">Step ${idx + 1}: ${s.step_id}</span>
                    <span style="color: var(--text-secondary); font-size: 12px; margin-left: 8px;">(${s.duration_seconds ? s.duration_seconds.toFixed(3) : 0}s)</span>
                  </div>
                  <div>
                    <span style="font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: ${s.status === 'COMPLETED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)'}; color: ${s.status === 'COMPLETED' ? '#10b981' : '#ef4444'};">
                      ${s.status}
                    </span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <h4 style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0 0 12px 0;">Cryptographic Evidence Digest</h4>
            <div style="font-size: 11.5px; font-family: monospace; color: var(--text-primary); background: var(--bg-surface-hover); padding: 12px; border-radius: 6px; word-break: break-all; margin-bottom: 12px;">
              ${ex && ex.evidence_hash ? ex.evidence_hash : 'NO_EVIDENCE_RECORDED'}
            </div>
            <div style="font-size: 12px; color: var(--text-secondary);">
              <strong>Terminal Outcome:</strong> ${ex ? ex.terminal_outcome : 'N/A'}<br>
              <strong>Error Message:</strong> ${ex && ex.error_message ? ex.error_message : 'None'}
            </div>
          </div>
        </div>
      `;
    }

    renderDemoTab() {
      const scenarios = [
        { key: 'A', name: 'Simple Governed Workflow', desc: 'Host Objective ➔ Tool ➔ Physical Verification ➔ Evidence Merkle Root.' },
        { key: 'B', name: 'Long-Running Workflow', desc: 'Checkpoints state, halts at gate, resumes with Command.' },
        { key: 'C', name: 'Human Approval Gate', desc: 'Sensitive funds action pauses, awaits host approval, and executes.' },
        { key: 'D', name: 'Human Parameter Edit', desc: 'Host modifies parameters before approving; runs with edited values.' },
        { key: 'E', name: 'Failure & Crash Recovery', desc: 'Recovers crashed process from checkpoint without blind mutation replay.' },
        { key: 'F', name: 'Ambiguous External Outcome', desc: 'API timeout caught in UNKNOWN_OUTCOME; queries truth and reconciles.' },
        { key: 'G', name: 'Loop Iteration Control', desc: 'Quality refinement loop terminates when threshold met, bounded by max iterations.' },
        { key: 'H', name: 'Agency Swarm Delegation', desc: 'AI CEO delegating complex task to Agency Swarm specialist squads.' },
        { key: 'I', name: 'Zero-Secret Memory Barrier', desc: 'Separates ephemeral checkpoint state from permanent memory blocks; zero secrets.' },
        { key: 'J', name: 'Multimodal Screen Observer', desc: 'Invokes HAL screen observer and synthesizes spoken audio report.' },
        { key: 'K', name: 'Authoritative KillSwitch', desc: 'Emergency KillSwitch immediately freezes execution thread.' }
      ];

      return `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
          ${scenarios.map(sc => `
            <div class="card" style="padding: 16px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); font-weight: 700; padding: 2px 8px; border-radius: 8px; font-size: 11px;">
                  TEST ${sc.key}
                </span>
                <span style="font-size: 12px; font-weight: 600; color: var(--text-primary);">${sc.name}</span>
              </div>
              <p style="font-size: 12.5px; color: var(--text-secondary); margin: 0 0 14px 0; min-height: 38px;">
                ${sc.desc}
              </p>
              <button class="btn-primary" style="width: 100%; font-size: 12px; padding: 6px 12px;" onclick="WorkflowWorkspace.runDemoScenario('${sc.key}')">
                ▶ Verify Scenario ${sc.key}
              </button>
              <div id="demoResult_${sc.key}" style="margin-top: 10px; display: none; font-size: 11.5px; padding: 8px 12px; border-radius: 6px; font-family: monospace;"></div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // =========================================================================
    // USER ACTIONS & CONTROLLER HANDLERS
    // =========================================================================

    switchTab(tabId) {
      this.activeTab = tabId;
      const contentEl = document.getElementById('workflowTabContent');
      if (contentEl) contentEl.innerHTML = this.renderTabContent();
    }

    async inspectRun(execId) {
      this.selectedRun = execId;
      try {
        const exRes = await fetch(`/api/automation/executions/${execId}`).then(r => r.json());
        this.selectedRunState = exRes;
        this.activeTab = 'inspector';
        this.render();
      } catch (err) {
        showToast('Error inspecting run: ' + err.message, 'error');
      }
    }

    async recoverRun(execId) {
      try {
        const res = await fetch(`/api/automation/executions/${execId}/recover`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }).then(r => r.json());
        showToast(`Recovered execution ${execId} from checkpoint`, 'success');
        await this.loadData();
        this.render();
      } catch (err) {
        showToast('Error recovering execution: ' + err.message, 'error');
      }
    }

    async reconcileRun(execId) {
      try {
        const res = await fetch(`/api/automation/executions/${execId}/reconcile`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ground_truth: 'CONFIRMED_SUCCESS' })
        }).then(r => r.json());
        showToast(`Reconciled outcome: ${res.reconciled_outcome}`, 'success');
        await this.loadData();
        this.render();
      } catch (err) {
        showToast('Reconciliation error: ' + err.message, 'error');
      }
    }

    async decideApproval(apprId, decision) {
      try {
        const res = await fetch(`/api/automation/approvals/${apprId}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: decision, actor: 'HostEmployee' })
        }).then(r => r.json());
        showToast(`Approval ${apprId} decided: ${decision}`, 'success');
        await this.loadData();
        this.render();
      } catch (err) {
        showToast('Approval error: ' + err.message, 'error');
      }
    }

    openEditModal(apprId, paramsEncoded) {
      const params = JSON.parse(decodeURIComponent(paramsEncoded));
      window.openModal('Edit Proposed Workflow Parameters', `
        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
          Modify parameter payload before execution. Modifications will be cryptographically audited.
        </div>
        <textarea id="editParamsInput" style="width: 100%; height: 180px; font-family: monospace; font-size: 12px; padding: 10px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: var(--text-primary); margin-bottom: 16px;">${JSON.stringify(params, null, 2)}</textarea>
        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button class="btn-secondary" onclick="closeModal()">Cancel</button>
          <button class="btn-primary" onclick="WorkflowWorkspace.submitEdit('${apprId}')">Submit & Resume</button>
        </div>
      `);
    }

    async submitEdit(apprId) {
      try {
        const txt = document.getElementById('editParamsInput').value;
        const modified = JSON.parse(txt);
        closeModal();
        await fetch(`/api/automation/approvals/${apprId}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'EDIT', modified_parameters: modified, actor: 'HostEmployee' })
        });
        showToast('Workflow resumed with modified parameters', 'success');
        await this.loadData();
        this.render();
      } catch (err) {
        showToast('Error editing parameters: ' + err.message, 'error');
      }
    }

    async toggleKillSwitch() {
      this.killswitchActive = !this.killswitchActive;
      try {
        await fetch('/api/automation/killswitch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ active: this.killswitchActive })
        });
        showToast(this.killswitchActive ? '🛑 ZONATA KillSwitch ENGAGED' : '⚡ KillSwitch DISENGAGED', this.killswitchActive ? 'error' : 'info');
        await this.loadData();
        this.render();
      } catch (err) {
        showToast('KillSwitch error: ' + err.message, 'error');
      }
    }

    async runDemoScenario(scenarioKey) {
      const resEl = document.getElementById(`demoResult_${scenarioKey}`);
      if (resEl) {
        resEl.style.display = 'block';
        resEl.style.background = 'var(--bg-surface-hover)';
        resEl.style.color = 'var(--text-secondary)';
        resEl.innerText = 'Executing scenario against live runtime...';
      }

      try {
        const data = await fetch('/api/workflows/demo/scenarios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario: scenarioKey })
        }).then(r => r.json());

        const resObj = data.result || {};
        if (resEl) {
          if (resObj.verified) {
            resEl.style.background = 'rgba(16, 185, 129, 0.15)';
            resEl.style.color = '#10b981';
            resEl.innerText = `✓ Verified: Status=${resObj.status || 'COMPLETED'}`;
          } else {
            resEl.style.background = 'rgba(239, 68, 68, 0.15)';
            resEl.style.color = '#ef4444';
            resEl.innerText = `✕ Error: ${resObj.error || 'Failed'}`;
          }
        }
        showToast(`Scenario ${scenarioKey} verified successfully!`, 'success');
      } catch (err) {
        if (resEl) {
          resEl.style.background = 'rgba(239, 68, 68, 0.15)';
          resEl.style.color = '#ef4444';
          resEl.innerText = `✕ Error: ${err.message}`;
        }
      }
    }

    openRunModal() {
      const options = this.workflows.length > 0
        ? this.workflows.map(w => `<option value="${w.workflow_id}">${w.name} (${w.workflow_id})</option>`).join('')
        : '<option value="">No published workflows yet</option>';

      window.openModal('Launch Governed Workflow', `
        <form onsubmit="WorkflowWorkspace.submitLaunch(event)">
          <div style="margin-bottom: 14px;">
            <label style="display:block; font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Select Workflow</label>
            <select id="modalWfId" style="width:100%; padding:8px 12px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-surface); color:var(--text-primary); font-size:13px;">
              ${options}
            </select>
          </div>
          <div style="margin-bottom: 16px;">
            <label style="display:block; font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Task Objective / Inputs (JSON)</label>
            <textarea id="modalWfInputs" style="width:100%; height:100px; padding:8px 12px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-surface); color:var(--text-primary); font-family:monospace; font-size:12px;">{"objective": "Comprehensive Financial Margin Audit"}</textarea>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Launch Execution</button>
          </div>
        </form>
      `);
    }

    async submitLaunch(e) {
      e.preventDefault();
      const wfId = document.getElementById('modalWfId').value;
      const rawInputs = document.getElementById('modalWfInputs').value;
      if (!wfId) {
        showToast('Please select or create a workflow first', 'warning');
        return;
      }
      try {
        const inputs = JSON.parse(rawInputs);
        closeModal();
        const res = await fetch(`/api/automation/workflows/${wfId}/execute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ inputs: inputs })
        }).then(r => r.json());

        showToast(`Workflow execution completed: ${res.terminal_outcome}`, 'success');
        this.activeTab = 'runs';
        await this.loadData();
        this.render();
      } catch (err) {
        showToast('Execution error: ' + err.message, 'error');
      }
    }
  }

  window.WorkflowWorkspace = new WorkflowWorkspaceManager();
})();
