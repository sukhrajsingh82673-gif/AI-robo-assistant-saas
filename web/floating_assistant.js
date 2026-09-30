/**
 * ZONATA — Floating Live Assistant & Universal Coworker
 * Draggable, collapsible, persistent floating assistant supporting
 * AI Chat (with clear internal/external citations) and Coworker (10-stage desktop executor).
 */

(function() {
  'use strict';

  class FloatingAssistantManager {
    constructor() {
      this.isOpen = false;
      this.activeTab = 'chat'; // 'chat' | 'coworker'
      this.workspaceMode = 'PERSONAL'; // 'PERSONAL' | 'COMPANY'
      this.chatMessages = [
        {
          sender: 'assistant',
          text: 'Hello, Host. I am your floating live assistant. Ask me questions with verified citations, or switch to Coworker for desktop automation.',
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
                <div style="font-size:11px; color:var(--text-muted);">Companion & Desktop Executor</div>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:4px;">
              <button class="assistant-btn-icon" onclick="window.FloatingAssistant.toggleOpen(event)" title="Collapse">
                ✕
              </button>
            </div>
          </div>

          <!-- Mode Tab Navigation -->
          <div class="assistant-nav-tabs">
            <button class="assistant-tab-btn ${this.activeTab === 'chat' ? 'active' : ''}" onclick="window.FloatingAssistant.switchTab('chat')">
              💬 AI Chat
            </button>
            <button class="assistant-tab-btn ${this.activeTab === 'coworker' ? 'active' : ''}" onclick="window.FloatingAssistant.switchTab('coworker')">
              🤖 Coworker Executor
            </button>
          </div>

          <!-- Tab 1: AI Chat Surface -->
          <div class="assistant-tab-content ${this.activeTab === 'chat' ? 'active' : ''}" id="assistantChatTab">
            <div class="assistant-chat-scroll" id="assistantChatScroll">
              ${this.renderChatMessagesHtml()}
            </div>
            <div class="assistant-chat-input-bar">
              <input type="text" id="assistantChatInput" class="assistant-input" placeholder="Ask anything about SaaS or company data..." onkeydown="if(event.key==='Enter') window.FloatingAssistant.sendChat()" />
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
                <input type="text" id="coworkerTaskInput" class="assistant-input" placeholder="e.g. 'Organize downloads' or 'Verify Tally backup'..." onkeydown="if(event.key==='Enter') window.FloatingAssistant.dispatchCoworkerTask()" />
                <button class="assistant-send-btn" onclick="window.FloatingAssistant.dispatchCoworkerTask()">Dispatch</button>
              </div>
            </div>

            <!-- 10-Stage Task Lifecycle Feed -->
            <div class="assistant-coworker-feed" id="coworkerFeed">
              ${this.renderCoworkerTasksHtml()}
            </div>
          </div>
        </div>
      `;

      this.bindDragEvents(container);
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
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          dragged = true;
          container.style.right = 'auto';
          container.style.bottom = 'auto';
          const newLeft = Math.min(window.innerWidth - 80, Math.max(10, initialLeft + dx));
          const newTop = Math.min(window.innerHeight - 80, Math.max(10, initialTop + dy));
          container.style.left = `${newLeft}px`;
          container.style.top = `${newTop}px`;
        }
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
        flyout.classList.toggle('open', this.isOpen);
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

    escape(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
  }

  window.FloatingAssistant = new FloatingAssistantManager();
})();
