/**
 * ZONATA — Floating Live Assistant & Universal Multimodal HUD (HAL AI Integration)
 * Draggable, collapsible, persistent floating assistant supporting:
 * 1. 💬 AI Chat (with clear internal/external citations)
 * 2. 🤖 Coworker (10-stage desktop executor)
 * 3. 👁️ Multimodal HUD (Live Waveform, Mic/Camera toggles, Screen Observation, Host Takeover, KillSwitch)
 * 4. 👑 AI CEO (Voice-to-CEO, Executive speech directives & TTS playback)
 */

(function() {
  'use strict';

  class FloatingAssistantManager {
    constructor() {
      this.isOpen = false;
      this.activeTab = 'chat'; // 'chat' | 'coworker' | 'multimodal' | 'ceo'
      this.workspaceMode = 'PERSONAL'; // 'PERSONAL' | 'COMPANY'
      this.isListening = false;
      this.isSpeaking = false;
      this.cameraActive = false;
      this.hostTakeoverActive = false;
      this.currentExecutionState = 'IDLE';
      this.activeSessionId = null;
      this.multimodalObservations = [];
      this.chatMessages = [
        {
          sender: 'assistant',
          text: 'Hello, Host. I am your ZONATA Live Assistant powered by the governed HAL Multimodal Layer. Talk to me, observe screens, or delegate desktop automation.',
          citations: [{ source_type: 'INTERNAL', label: 'ZONATA Operational Core', verified: true }]
        }
      ];
      this.coworkerTasks = [];
      this.isDragging = false;
      this.dragOffset = { x: 0, y: 0 };
    }

    init() {
      let container = document.getElementById('floatingAssistantContainer');
      if (!container) {
        container = document.createElement('div');
        container.id = 'floatingAssistantContainer';
        container.className = 'floating-assistant-container';
        document.body.appendChild(container);
      }
      this.renderWidget(container);
      this.loadSavedPosition(container);
      this.loadCoworkerTasks();
      this.loadMultimodalStatus();
    }

    loadSavedPosition(container) {
      const saved = localStorage.getItem('zonata_assistant_pos');
      if (saved) {
        try {
          const pos = JSON.parse(saved);
          container.style.right = 'auto';
          container.style.bottom = 'auto';
          container.style.left = `${Math.min(window.innerWidth - 70, Math.max(10, pos.x))}px`;
          container.style.top = `${Math.min(window.innerHeight - 70, Math.max(10, pos.y))}px`;
        } catch (e) {}
      }
    }

    savePosition(x, y) {
      localStorage.setItem('zonata_assistant_pos', JSON.stringify({ x, y }));
    }

    renderWidget(container) {
      container.innerHTML = `
        <!-- Floating Launcher Pill/Button -->
        <div class="assistant-floating-badge" id="assistantBadge" title="Open ZONATA Live Assistant" onclick="window.FloatingAssistant.toggleOpen(event)">
          <div class="assistant-pill-icon">✨</div>
          <span class="assistant-pill-label">ZONATA Assistant</span>
          <span class="pulse-indicator" style="background:#10b981;"></span>
        </div>

        <!-- Flyout Window -->
        <div class="assistant-flyout-window ${this.isOpen ? 'open' : ''}" id="assistantFlyout">
          <!-- Window Header (Draggable Handle) -->
          <div class="assistant-window-header" id="assistantHeaderHandle">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:16px;">✨</span>
              <div>
                <div style="font-size:13px; font-weight:700; color:var(--text-primary);">Live Assistant</div>
                <div style="font-size:11px; color:var(--text-muted);">Multimodal Companion & Executive HUD</div>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:4px;">
              <button class="assistant-btn-icon" onclick="window.FloatingAssistant.toggleOpen(event)" title="Collapse">
                ✕
              </button>
            </div>
          </div>

          <!-- Mode Tab Navigation (4 Modes) -->
          <div class="assistant-nav-tabs">
            <button class="assistant-tab-btn ${this.activeTab === 'chat' ? 'active' : ''}" onclick="window.FloatingAssistant.switchTab('chat')">
              💬 Chat
            </button>
            <button class="assistant-tab-btn ${this.activeTab === 'coworker' ? 'active' : ''}" onclick="window.FloatingAssistant.switchTab('coworker')">
              🤖 Coworker
            </button>
            <button class="assistant-tab-btn ${this.activeTab === 'multimodal' ? 'active' : ''}" onclick="window.FloatingAssistant.switchTab('multimodal')">
              👁️ Multimodal
            </button>
            <button class="assistant-tab-btn ${this.activeTab === 'ceo' ? 'active' : ''}" onclick="window.FloatingAssistant.switchTab('ceo')">
              👑 AI CEO
            </button>
          </div>

          <!-- Tab 1: AI Chat Surface -->
          <div class="assistant-tab-content ${this.activeTab === 'chat' ? 'active' : ''}" id="assistantChatTab">
            <div class="assistant-chat-scroll" id="assistantChatScroll">
              ${this.renderChatMessagesHtml()}
            </div>
            <div class="assistant-chat-input-bar">
              <input type="text" id="assistantChatInput" class="assistant-input" placeholder="Ask anything about company truth or metrics..." onkeydown="if(event.key==='Enter') window.FloatingAssistant.sendChat()" />
              <button class="assistant-send-btn" onclick="window.FloatingAssistant.sendChat()">Send</button>
            </div>
          </div>

          <!-- Tab 2: Coworker Surface -->
          <div class="assistant-tab-content ${this.activeTab === 'coworker' ? 'active' : ''}" id="assistantCoworkerTab">
            <!-- Workspace Mode Switcher -->
            <div class="assistant-workspace-bar">
              <span style="font-size:11px; color:var(--text-muted); font-weight:600;">Workspace:</span>
              <div class="btn-group" style="display:flex; gap:4px;">
                <button class="btn-workspace-pill ${this.workspaceMode === 'PERSONAL' ? 'active' : ''}" onclick="window.FloatingAssistant.setWorkspaceMode('PERSONAL')">
                  👤 Personal
                </button>
                <button class="btn-workspace-pill ${this.workspaceMode === 'COMPANY' ? 'active' : ''}" onclick="window.FloatingAssistant.setWorkspaceMode('COMPANY')">
                  🏢 Company
                </button>
              </div>
            </div>

            <!-- Task Trigger Input -->
            <div style="padding:10px 14px; border-bottom:1px solid var(--border-color); background:var(--bg-surface-hover);">
              <div style="font-size:11.5px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">Assign Desktop / Robot Task:</div>
              <div style="display:flex; gap:6px;">
                <input type="text" id="coworkerTaskInput" class="assistant-input" placeholder="e.g. 'Read executive summary' or 'Verify filesystem report'..." onkeydown="if(event.key==='Enter') window.FloatingAssistant.dispatchCoworkerTask()" />
                <button class="assistant-send-btn" onclick="window.FloatingAssistant.dispatchCoworkerTask()">Dispatch</button>
              </div>
            </div>

            <!-- 10-Stage Task Lifecycle Feed -->
            <div class="assistant-coworker-feed" id="coworkerFeed">
              ${this.renderCoworkerTasksHtml()}
            </div>
          </div>

          <!-- Tab 3: Multimodal HUD Surface -->
          <div class="assistant-tab-content ${this.activeTab === 'multimodal' ? 'active' : ''}" id="assistantMultimodalTab">
            <div class="multimodal-hud-container" id="multimodalHudScroll">
              <!-- Live Status Banner -->
              <div class="multimodal-status-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                  <span style="font-weight:700; color:var(--text-primary);">HAL9000 Multimodal Runtime</span>
                  <span class="hud-state-badge hud-state-${this.currentExecutionState}">${this.currentExecutionState}</span>
                </div>
                <div style="font-size:11px; color:var(--text-secondary);">
                  Governed Vision, Speech, Desktop Robot & MCP Gateway
                </div>
              </div>

              <!-- Live Waveform Audio Visualizer -->
              <div class="multimodal-waveform-canvas" id="hudWaveform">
                ${this.renderWaveformBarsHtml()}
              </div>

              <!-- Action & Control Grid -->
              <div class="multimodal-controls-grid">
                <button class="btn-hud-action" id="btnHudMic" onclick="window.FloatingAssistant.toggleMic()">
                  ${this.isListening ? '🔴 Stop Mic' : '🎙️ Mic Input'}
                </button>
                <button class="btn-hud-action" onclick="window.FloatingAssistant.captureScreenObservation()">
                  🖥️ Observe Screen
                </button>
                <button class="btn-hud-action" onclick="window.FloatingAssistant.toggleCamera()">
                  📷 ${this.cameraActive ? 'Stop Camera' : 'Face Track Cam'}
                </button>
                <button class="btn-hud-action btn-hud-takeover" onclick="window.FloatingAssistant.triggerHostTakeover()">
                  ✋ Take Control
                </button>
              </div>

              <!-- Emergency KillSwitch Button -->
              <button class="btn-hud-action btn-hud-stop" style="width:100%;" onclick="window.FloatingAssistant.triggerEmergencyStop()">
                🛑 Emergency STOP (KillSwitch)
              </button>

              <!-- Observations & Evidence Stream -->
              <div style="margin-top:4px;">
                <div style="font-size:11px; font-weight:700; color:var(--text-secondary); margin-bottom:6px;">Recent Multimodal Observations:</div>
                <div id="multimodalObservationsFeed" style="display:flex; flex-direction:column; gap:6px;">
                  ${this.renderObservationsHtml()}
                </div>
              </div>
            </div>
          </div>

          <!-- Tab 4: AI CEO Direct Multimodal Meeting Surface -->
          <div class="assistant-tab-content ${this.activeTab === 'ceo' ? 'active' : ''}" id="assistantCeoTab">
            <div style="padding:14px; display:flex; flex-direction:column; gap:10px; overflow-y:auto; flex:1;">
              <div class="multimodal-status-card">
                <div style="font-weight:700; color:var(--text-primary); margin-bottom:2px;">👑 Executive Voice-to-CEO</div>
                <div style="font-size:11px; color:var(--text-secondary);">
                  Deliver verbal directives directly to the AI CEO with verified synthesis.
                </div>
              </div>

              <div style="display:flex; flex-direction:column; gap:8px;">
                <textarea id="ceoDirectiveInput" class="assistant-input" rows="3" placeholder="Speak or type executive directive, e.g. 'Analyze our Q3 gross margins and draft an executive directive.'"></textarea>
                <div style="display:flex; gap:8px;">
                  <button class="assistant-send-btn" style="flex:1;" onclick="window.FloatingAssistant.dispatchVoiceToCeo()">Transmit Directive</button>
                  <button class="btn-secondary" style="font-size:11px; padding:6px 12px;" onclick="window.FloatingAssistant.quickCeoPrompt()">Example</button>
                </div>
              </div>

              <div id="ceoResponseBox" style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px; font-size:12px; display:none;">
                <div style="font-weight:700; color:#3b82f6; margin-bottom:4px;">AI CEO Response:</div>
                <div id="ceoResponseText" style="color:var(--text-primary); margin-bottom:8px; line-height:1.4;"></div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:10.5px; color:var(--text-muted);">
                  <span id="ceoEvidenceHash">Hash: Verified</span>
                  <button class="btn-secondary" style="font-size:10px; padding:2px 8px;" onclick="window.FloatingAssistant.playCeoAudio()">🔊 Play Speech</button>
                </div>
              </div>
            </div>
          </div>

        </div>
      `;

      this.bindDragEvents(container);
    }

    renderWaveformBarsHtml() {
      const bars = [];
      const count = 28;
      for (let i = 0; i < count; i++) {
        bars.push(`<div class="waveform-bar ${this.isListening || this.isSpeaking ? 'active' : ''}" style="animation-delay:${(i * 0.05).toFixed(2)}s"></div>`);
      }
      return bars.join('');
    }

    renderObservationsHtml() {
      if (this.multimodalObservations.length === 0) {
        return `<div style="text-align:center; padding:12px; font-size:11px; color:var(--text-muted);">No observations captured yet. Click 'Observe Screen' or 'Mic Input'.</div>`;
      }
      return this.multimodalObservations.slice(0, 5).map(o => `
        <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:8px 10px; font-size:11px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
            <span style="font-weight:700; color:#3b82f6;">[${this.escape(o.source)}]</span>
            <span style="color:var(--text-muted); font-size:9.5px;">${new Date(o.timestamp * 1000).toLocaleTimeString()}</span>
          </div>
          <div style="color:var(--text-primary); margin-bottom:3px;">${this.escape(o.redacted_content || o.details || 'Observation recorded')}</div>
          <div style="font-size:9.5px; color:var(--text-muted); font-family:monospace;">SHA256: ${this.escape((o.raw_hash || '').substring(0, 16))}...</div>
        </div>
      `).join('');
    }

    bindDragEvents(container) {
      const handle = document.getElementById('assistantBadge');
      if (!handle) return;

      let startX = 0, startY = 0;
      let initialLeft = 0, initialTop = 0;
      let dragged = false;

      const onMouseDown = (e) => {
        if (e.target.closest('#assistantFlyout')) return;
        dragged = false;
        startX = e.clientX;
        startY = e.clientY;
        const rect = container.getBoundingClientRect();
        initialLeft = rect.left;
        initialTop = rect.top;

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
      };

      const onMouseMove = (e) => {
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragged = true;

        const newLeft = Math.min(window.innerWidth - 70, Math.max(10, initialLeft + dx));
        const newTop = Math.min(window.innerHeight - 70, Math.max(10, initialTop + dy));

        container.style.right = 'auto';
        container.style.bottom = 'auto';
        container.style.left = `${newLeft}px`;
        container.style.top = `${newTop}px`;
      };

      const onMouseUp = (e) => {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        if (dragged) {
          const rect = container.getBoundingClientRect();
          this.savePosition(rect.left, rect.top);
        }
      };

      handle.addEventListener('mousedown', onMouseDown);
    }

    toggleOpen(e) {
      if (e) e.stopPropagation();
      this.isOpen = !this.isOpen;
      const flyout = document.getElementById('assistantFlyout');
      if (flyout) {
        if (this.isOpen) {
          flyout.classList.add('open');
        } else {
          flyout.classList.remove('open');
        }
      }
    }

    switchTab(tab) {
      this.activeTab = tab;
      const container = document.getElementById('floatingAssistantContainer');
      if (container) this.renderWidget(container);
    }

    setWorkspaceMode(mode) {
      this.workspaceMode = mode;
      const container = document.getElementById('floatingAssistantContainer');
      if (container) this.renderWidget(container);
    }

    renderChatMessagesHtml() {
      return this.chatMessages.map(m => {
        const isUser = m.sender === 'user';
        return `
          <div class="assistant-msg-bubble ${isUser ? 'user' : 'assistant'}">
            <div class="msg-text">${this.escape(m.text)}</div>
            ${m.citations && m.citations.length > 0 ? `
              <div class="msg-citations">
                <span class="citation-label">Citations:</span>
                ${m.citations.map(c => `
                  <span class="citation-tag ${c.source_type === 'INTERNAL' ? 'internal' : 'external'}">
                    ${c.source_type === 'INTERNAL' ? '🏢 [INTERNAL]' : '🌐 [WEB RESEARCH]'} ${this.escape(c.label)}
                  </span>
                `).join('')}
              </div>
            ` : ''}
          </div>
        `;
      }).join('');
    }

    async sendChat() {
      const input = document.getElementById('assistantChatInput');
      if (!input || !input.value.trim()) return;

      const prompt = input.value.trim();
      input.value = '';

      this.chatMessages.push({ sender: 'user', text: prompt });
      const scrollEl = document.getElementById('assistantChatScroll');
      if (scrollEl) {
        scrollEl.innerHTML = this.renderChatMessagesHtml();
        scrollEl.scrollTop = scrollEl.scrollHeight;
      }

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;

      try {
        const res = await fetch('/api/assistant/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, company_id: companyId })
        });

        if (res.ok) {
          const data = await res.json();
          this.chatMessages.push({
            sender: 'assistant',
            text: data.reply,
            citations: data.citations || []
          });
          if (scrollEl) {
            scrollEl.innerHTML = this.renderChatMessagesHtml();
            scrollEl.scrollTop = scrollEl.scrollHeight;
          }
        }
      } catch (err) {
        console.error('Chat error:', err);
      }
    }

    renderCoworkerTasksHtml() {
      if (this.coworkerTasks.length === 0) {
        return `<div style="text-align:center; padding:30px; font-size:12px; color:var(--text-muted);">No active tasks in ${this.workspaceMode} workspace.</div>`;
      }

      return this.coworkerTasks.map(t => {
        const isAwaiting = t.status === 'AWAITING_APPROVAL';
        const isCompleted = t.status === 'COMPLETED';

        return `
          <div class="coworker-task-card ${isAwaiting ? 'awaiting-approval' : ''}">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
              <span style="font-size:12.5px; font-weight:700; color:var(--text-primary);">${this.escape(t.prompt)}</span>
              <span class="badge ${isCompleted ? 'badge-emerald' : isAwaiting ? 'badge-amber' : 'badge-blue'}">${t.status}</span>
            </div>
            <div style="font-size:11.5px; color:var(--text-secondary); margin-bottom:8px;">
              Tier: <code>${t.permission_tier}</code> • Target: ${this.escape(t.target_outcome)}
            </div>

            ${isAwaiting ? `
              <div class="approval-gate-banner">
                <div style="font-size:11.5px; font-weight:700; color:#ef4444; margin-bottom:4px;">⚠️ Host Authorization Required</div>
                <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
                  This action involves sensitive permissions (${t.permission_tier}). Grant authorization to proceed.
                </div>
                <div style="display:flex; gap:8px;">
                  <button class="btn-primary" style="font-size:11.5px; padding:4px 10px; background:#10b981;" onclick="window.FloatingAssistant.approveTask('${t.task_id}', true)">Authorize</button>
                  <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px; color:#ef4444;" onclick="window.FloatingAssistant.approveTask('${t.task_id}', false)">Deny</button>
                </div>
              </div>
            ` : ''}

            <!-- 10-Stage Lifecycle Trace -->
            <div class="task-stage-trace">
              ${(t.execution_log || []).map(st => `
                <div class="trace-step">
                  <span class="trace-stage">${st.stage}</span>
                  <span class="trace-detail">${this.escape(st.detail)}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }).join('');
    }

    async loadCoworkerTasks() {
      try {
        const res = await fetch(`/api/assistant/coworker/tasks?workspace_mode=${this.workspaceMode}`);
        if (res.ok) {
          const data = await res.json();
          this.coworkerTasks = data.tasks || [];
        }
      } catch (e) {}
    }

    async dispatchCoworkerTask() {
      const input = document.getElementById('coworkerTaskInput');
      if (!input || !input.value.trim()) return;

      const prompt = input.value.trim();
      input.value = '';

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;

      try {
        const res = await fetch('/api/assistant/coworker/task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt,
            workspace_mode: this.workspaceMode,
            company_id: companyId
          })
        });

        if (res.ok) {
          await this.loadCoworkerTasks();
          const feed = document.getElementById('coworkerFeed');
          if (feed) feed.innerHTML = this.renderCoworkerTasksHtml();
        }
      } catch (err) {
        console.error('Dispatch error:', err);
      }
    }

    async approveTask(taskId, approved) {
      try {
        const res = await fetch(`/api/assistant/coworker/tasks/${taskId}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved })
        });
        if (res.ok) {
          await this.loadCoworkerTasks();
          const feed = document.getElementById('coworkerFeed');
          if (feed) feed.innerHTML = this.renderCoworkerTasksHtml();
        }
      } catch (err) {
        console.error('Approval failed:', err);
      }
    }

    // =========================================================================
    // MULTIMODAL HUD ACTIONS
    // =========================================================================

    async loadMultimodalStatus() {
      try {
        const res = await fetch('/api/multimodal/status');
        if (res.ok) {
          const data = await res.json();
          this.multimodalStatus = data;
        }
      } catch (e) {}
    }

    toggleMic() {
      this.isListening = !this.isListening;
      const wf = document.getElementById('hudWaveform');
      const btn = document.getElementById('btnHudMic');
      if (btn) btn.innerText = this.isListening ? '🔴 Stop Mic' : '🎙️ Mic Input';
      if (wf) wf.innerHTML = this.renderWaveformBarsHtml();

      if (this.isListening) {
        this.currentExecutionState = 'LISTENING';
        // Auto-transcribe mock or Web Speech
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
          const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
          const rec = new SpeechRec();
          rec.onresult = async (evt) => {
            const transcript = evt.results[0][0].transcript;
            await this.processTranscript(transcript);
          };
          rec.start();
        } else {
          setTimeout(async () => {
            if (this.isListening) {
              await this.processTranscript("Analyze recent system performance and desktop tasks");
              this.isListening = false;
              if (btn) btn.innerText = '🎙️ Mic Input';
              if (wf) wf.innerHTML = this.renderWaveformBarsHtml();
            }
          }, 2500);
        }
      } else {
        this.currentExecutionState = 'IDLE';
      }
    }

    async processTranscript(transcript) {
      try {
        const res = await fetch('/api/multimodal/transcribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audio_text: transcript })
        });
        if (res.ok) {
          const data = await res.json();
          if (data.is_valid) {
            this.multimodalObservations.unshift({
              source: 'AUDIO_MIC',
              redacted_content: `Heard: "${data.filtered}"`,
              timestamp: Date.now() / 1000,
              raw_hash: 'vad_' + Date.now().toString(16)
            });
            const feed = document.getElementById('multimodalObservationsFeed');
            if (feed) feed.innerHTML = this.renderObservationsHtml();
          }
        }
      } catch (e) {}
    }

    async captureScreenObservation() {
      this.currentExecutionState = 'OBSERVING';
      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      try {
        const res = await fetch('/api/multimodal/observe/screen', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_id: companyId,
            window_title: document.title || 'ZONATA Enterprise Workspace',
            content_preview: 'Interactive screen capture showing metrics and navigation panels'
          })
        });
        if (res.ok) {
          const data = await res.json();
          this.currentExecutionState = 'COMPLETED';
          this.multimodalObservations.unshift(data.observation);
          const feed = document.getElementById('multimodalObservationsFeed');
          if (feed) feed.innerHTML = this.renderObservationsHtml();
        }
      } catch (e) {
        this.currentExecutionState = 'FAILED';
      }
    }

    async toggleCamera() {
      this.cameraActive = !this.cameraActive;
      if (this.cameraActive) {
        this.currentExecutionState = 'OBSERVING';
        try {
          const res = await fetch('/api/multimodal/observe/webcam', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blur_background: true })
          });
          if (res.ok) {
            const data = await res.json();
            this.multimodalObservations.unshift({
              source: 'WEBCAM_HUD',
              redacted_content: `Face Tracking: ${data.faces_detected} targets identified. Privacy blur enabled.`,
              timestamp: data.timestamp,
              raw_hash: data.frame_hash
            });
            const feed = document.getElementById('multimodalObservationsFeed');
            if (feed) feed.innerHTML = this.renderObservationsHtml();
          }
        } catch (e) {}
      } else {
        this.currentExecutionState = 'IDLE';
      }
    }

    async triggerHostTakeover() {
      this.hostTakeoverActive = true;
      this.currentExecutionState = 'HOST_TAKEOVER';
      try {
        await fetch('/api/multimodal/task/takeover', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: 'mms_live', user_id: 'usr_owner' })
        });
        alert('✋ Host Takeover Engaged. Autonomous AI execution halted. Control is manual.');
        this.switchTab('multimodal');
      } catch (e) {}
    }

    async triggerEmergencyStop() {
      this.currentExecutionState = 'CANCELLED';
      this.isListening = false;
      this.isSpeaking = false;
      try {
        await fetch('/api/multimodal/task/interrupt', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: 'mms_live', reason: 'Emergency KillSwitch triggered by Host' })
        });
        alert('🛑 Emergency STOP (KillSwitch) engaged. All operations terminated.');
        this.switchTab('multimodal');
      } catch (e) {}
    }

    // =========================================================================
    // AI CEO VOICE DIRECTIVES
    // =========================================================================

    quickCeoPrompt() {
      const el = document.getElementById('ceoDirectiveInput');
      if (el) el.value = "Analyze our Q3 gross margins and prepare an executive directive.";
    }

    async dispatchVoiceToCeo() {
      const el = document.getElementById('ceoDirectiveInput');
      if (!el || !el.value.trim()) return;

      const transcript = el.value.trim();
      el.value = '';

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;

      try {
        const res = await fetch('/api/multimodal/voice-to-ceo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcript, company_id: companyId })
        });

        if (res.ok) {
          const data = await res.json();
          this.lastCeoData = data;
          const box = document.getElementById('ceoResponseBox');
          const txt = document.getElementById('ceoResponseText');
          const hashEl = document.getElementById('ceoEvidenceHash');

          if (box && txt) {
            box.style.display = 'block';
            txt.innerText = data.ceo_response;
            if (hashEl) hashEl.innerText = `Evidence: ${data.evidence_hash.substring(0, 16)}...`;
          }

          // Automatically speak if Web Speech is available
          this.playCeoAudio();
        }
      } catch (e) {
        console.error('Voice-to-CEO failed:', e);
      }
    }

    playCeoAudio() {
      if (!this.lastCeoData || !this.lastCeoData.ceo_response) return;
      if ('speechSynthesis' in window) {
        const u = new SpeechSynthesisUtterance(this.lastCeoData.ceo_response);
        u.rate = 1.0;
        window.speechSynthesis.speak(u);
      }
    }

    escape(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
  }

  window.FloatingAssistant = new FloatingAssistantManager();
})();
