/**
 * ZONATA AI — Universal Owner Assistant & Floating Interface
 * 
 * Persistent, draggable floating assistant acting as the personal and organizational
 * communication gateway between the Owner (Host) and the sovereign AI CEO.
 * 
 * Features:
 * 1. Omnipresent Draggable Floating Action Button with 4-Corner Magnetic Snapping
 * 2. Responsive viewport boundary containment (mobile touch + desktop mouse)
 * 3. Position persistence across navigation in localStorage
 * 4. Clean, compact Apple-grade flyout window (preserves compact dimensions)
 * 5. Single unified conversational & multimodal surface (no fragmented navigation tabs)
 * 6. Dual context support: Private Personal Workspace vs Governed Company Workspace
 * 7. Deliverable cards for authentic document downloads (PDF, DOCX, XLSX, PPTX, CSV)
 * 8. Autonomous Meeting scheduling cards with Google Meet links & statutory disclosure
 * 9. One-click Host authorization gate banners & emergency killswitch containment
 */

(function() {
  'use strict';

  class UniversalFloatingAssistant {
    constructor() {
      this.isOpen = false;
      this.workspaceMode = 'AUTO'; // 'AUTO' | 'PERSONAL' | 'COMPANY'
      this.currentCorner = 'bottom-left'; // 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right'
      this.isListening = false;
      this.isSpeaking = false;
      this.currentExecutionState = 'IDLE';
      this.sessionId = 'asst_' + Date.now().toString(36);
      this.messages = [
        {
          id: 'welcome',
          sender: 'assistant',
          text: 'Hello, Host. I am ZONATA AI, your universal assistant and direct gateway to the AI CEO. Ask anything personal, delegate company objectives, request documents, or schedule meetings.',
          citations: [{ source_type: 'INTERNAL', label: 'ZONATA Operational Core', verified: true }],
          deliverable: null,
          actionCard: null,
          timestamp: Date.now() / 1000
        }
      ];
      this.pendingAttachments = [];
      this.lastPrompt = '';
      this.isDragging = false;
      this.dragStartedAt = 0;
      this.dragThreshold = 5;
    }

    init() {
      let container = document.getElementById('floatingAssistantContainer');
      if (!container) {
        container = document.createElement('div');
        container.id = 'floatingAssistantContainer';
        container.className = 'floating-assistant-container';
        document.body.appendChild(container);
      }
      this.render(container);
      this.applySavedCornerPosition(container);
      this.bindDragPhysics(container);
      window.addEventListener('resize', () => {
        const current = document.getElementById('floatingAssistantContainer');
        if (current) this.snapToCorner(current, this.currentCorner, false);
      });
      this.startStateSync();
    }

    // =========================================================================
    // 4-CORNER MAGNETIC SNAPPING & DRAG PHYSICS
    // =========================================================================

    applySavedCornerPosition(container) {
      const savedCorner = localStorage.getItem('zonata_assistant_corner') || 'bottom-left';
      this.snapToCorner(container, savedCorner, false);
    }

    snapToCorner(container, cornerName, animate = true) {
      this.currentCorner = cornerName;
      localStorage.setItem('zonata_assistant_corner', cornerName);

      const isMobile = window.innerWidth <= 768;
      const sidePadding = isMobile ? 12 : 20;
      const topPadding = isMobile ? 12 : 20;
      // Keep the FAB clear of the mobile bottom navigation bar.
      const bottomPadding = isMobile ? 76 : 20;
      const flyout = document.getElementById('assistantFlyout');
      const wasMinimized = !!(flyout && flyout.classList.contains('minimized'));
      const extraClasses = (this.isOpen ? ' open' : '') + (wasMinimized ? ' minimized' : '');
      container.style.transition = animate ? 'all 0.35s cubic-bezier(0.16, 1, 0.3, 1)' : 'none';

      container.style.top = 'auto';
      container.style.bottom = 'auto';
      container.style.left = 'auto';
      container.style.right = 'auto';

      if (cornerName === 'bottom-left') {
        container.style.bottom = `${bottomPadding}px`;
        container.style.left = `${sidePadding}px`;
        if (flyout) flyout.className = 'assistant-flyout-window anchor-bottom-left' + extraClasses;
      } else if (cornerName === 'bottom-right') {
        container.style.bottom = `${bottomPadding}px`;
        container.style.right = `${sidePadding}px`;
        if (flyout) flyout.className = 'assistant-flyout-window anchor-bottom-right' + extraClasses;
      } else if (cornerName === 'top-left') {
        container.style.top = `${topPadding}px`;
        container.style.left = `${sidePadding}px`;
        if (flyout) flyout.className = 'assistant-flyout-window anchor-top-left' + extraClasses;
      } else if (cornerName === 'top-right') {
        container.style.top = `${topPadding}px`;
        container.style.right = `${sidePadding}px`;
        if (flyout) flyout.className = 'assistant-flyout-window anchor-top-right' + extraClasses;
      }
    }

    calculateNearestCorner(clientX, clientY) {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const isLeft = clientX < w / 2;
      const isTop = clientY < h / 2;

      if (isTop && isLeft) return 'top-left';
      if (isTop && !isLeft) return 'top-right';
      if (!isTop && isLeft) return 'bottom-left';
      return 'bottom-right';
    }

    bindDragPhysics(container) {
      const handle = document.getElementById('assistantFloatingFab');
      if (!handle) return;

      let startX = 0, startY = 0;
      let initialLeft = 0, initialTop = 0;
      let hasMoved = false;

      const onStart = (cx, cy) => {
        const rect = container.getBoundingClientRect();
        startX = cx;
        startY = cy;
        initialLeft = rect.left;
        initialTop = rect.top;
        hasMoved = false;
        this.dragStartedAt = Date.now();

        container.style.transition = 'none';
        container.style.transform = 'scale(1.06)';
      };

      const onMove = (cx, cy) => {
        const dx = cx - startX;
        const dy = cy - startY;
        if (Math.hypot(dx, dy) > this.dragThreshold) {
          hasMoved = true;
          this.isDragging = true;
        }

        if (hasMoved) {
          const btnW = 56;
          const btnH = 56;
          const maxLeft = window.innerWidth - btnW - 10;
          const maxTop = window.innerHeight - btnH - 10;

          const newLeft = Math.min(maxLeft, Math.max(10, initialLeft + dx));
          const newTop = Math.min(maxTop, Math.max(10, initialTop + dy));

          container.style.left = `${newLeft}px`;
          container.style.top = `${newTop}px`;
          container.style.right = 'auto';
          container.style.bottom = 'auto';
        }
      };

      const onEnd = (cx, cy) => {
        container.style.transform = 'scale(1)';
        if (hasMoved) {
          const nearest = this.calculateNearestCorner(cx, cy);
          this.snapToCorner(container, nearest, true);
        }
        setTimeout(() => {
          this.isDragging = false;
        }, 50);
      };

      // Mouse Listeners
      const handleMouseDown = (e) => {
        if (e.target.closest('#assistantFlyout')) return;
        onStart(e.clientX, e.clientY);

        const handleMouseMove = (ev) => onMove(ev.clientX, ev.clientY);
        const handleMouseUp = (ev) => {
          document.removeEventListener('mousemove', handleMouseMove);
          document.removeEventListener('mouseup', handleMouseUp);
          onEnd(ev.clientX, ev.clientY);
        };
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
      };

      // Touch Listeners (Mobile Handheld UX)
      const handleTouchStart = (e) => {
        if (e.target.closest('#assistantFlyout')) return;
        if (!e.touches || e.touches.length === 0) return;
        const t = e.touches[0];
        onStart(t.clientX, t.clientY);

        const handleTouchMove = (ev) => {
          if (!ev.touches || ev.touches.length === 0) return;
          onMove(ev.touches[0].clientX, ev.touches[0].clientY);
        };
        const handleTouchEnd = (ev) => {
          document.removeEventListener('touchmove', handleTouchMove);
          document.removeEventListener('touchend', handleTouchEnd);
          const tEnd = ev.changedTouches && ev.changedTouches.length ? ev.changedTouches[0] : t;
          onEnd(tEnd.clientX, tEnd.clientY);
        };
        document.addEventListener('touchmove', handleTouchMove, { passive: true });
        document.addEventListener('touchend', handleTouchEnd);
      };

      handle.addEventListener('mousedown', handleMouseDown);
      handle.addEventListener('touchstart', handleTouchStart, { passive: true });
    }

    // =========================================================================
    // UI RENDERING (Apple-Grade Compact Glassmorphism)
    // =========================================================================

    render(container) {
      container.innerHTML = `
        <!-- Floating Draggable Action Button (FAB) -->
        <div class="assistant-floating-fab" id="assistantFloatingFab" title="ZONATA AI Universal Assistant" onclick="window.FloatingAssistant.handleFabClick(event)">
          <div class="assistant-fab-inner">
            <span class="assistant-fab-icon">✨</span>
            <span class="assistant-pulse-ring" id="assistantPulseRing"></span>
          </div>
          <span class="assistant-fab-pill-label">ZONATA AI</span>
        </div>

        <!-- Compact Flyout Window -->
        <div class="assistant-flyout-window anchor-${this.currentCorner} ${this.isOpen ? 'open' : ''}" id="assistantFlyout">
          <!-- Window Header -->
          <div class="assistant-flyout-header" id="assistantFlyoutHeader">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="assistant-header-sparkle">✨</span>
              <div>
                <div class="assistant-header-title">ZONATA AI</div>
                <div class="assistant-header-subtitle">Universal Owner Assistant & AI CEO Gateway</div>
              </div>
            </div>

            <div style="display:flex; align-items:center; gap:6px;">
              <!-- Workspace Context Pill -->
              <div class="workspace-pill-badge" id="assistantWorkspacePill" onclick="window.FloatingAssistant.cycleWorkspaceMode()" title="Click to toggle Personal / Company mode">
                <span id="workspacePillIcon">${this.workspaceMode === 'PERSONAL' ? '👤' : this.workspaceMode === 'COMPANY' ? '🏢' : '⚡'}</span>
                <span id="workspacePillText">${this.workspaceMode}</span>
              </div>

              <!-- Minimize Button -->
              <button class="assistant-icon-btn" onclick="window.FloatingAssistant.toggleMinimize(event)" title="Minimize Assistant">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              </button>

              <!-- Close Button -->
              <button class="assistant-icon-btn" onclick="window.FloatingAssistant.toggleOpen(event)" title="Close Assistant">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>
          </div>

          <!-- Conversation Stream Area -->
          <div class="assistant-messages-container" id="assistantMessagesContainer">
            ${this.renderMessagesHtml()}
          </div>

          <!-- Pending Attachment Tray -->
          <div id="assistantAttachmentTray" class="assistant-attachment-tray" style="display:${this.pendingAttachments.length ? 'flex' : 'none'};">
            ${this.renderAttachmentTrayHtml()}
          </div>

          <!-- Audio Waveform Live Bar -->
          <div id="assistantWaveformBar" class="assistant-waveform-container" style="display:${this.isListening || this.isSpeaking ? 'flex' : 'none'};">
            ${this.renderWaveformHtml()}
          </div>

          <!-- Unified Input Surface -->
          <div class="assistant-input-tray">
            <div class="assistant-input-row">
              <textarea 
                id="assistantMainInput" 
                class="assistant-prompt-textarea" 
                rows="1" 
                placeholder="Ask ZONATA AI or assign any personal/company task..."
                onkeydown="window.FloatingAssistant.handleInputKeydown(event)"
                oninput="window.FloatingAssistant.autoResizeTextarea(this)"
              ></textarea>

              <button class="assistant-send-trigger" onclick="window.FloatingAssistant.submitPrompt()" title="Transmit Directive">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
              </button>
            </div>

            <!-- Multimodal & Action Toolbelt -->
            <div class="assistant-toolbelt">
              <div style="display:flex; align-items:center; gap:6px;">
                <!-- Voice / Mic Toggle -->
                <button class="toolbelt-btn ${this.isListening ? 'active-red' : ''}" id="btnToolbeltMic" onclick="window.FloatingAssistant.toggleMic()" title="Voice Directive">
                  🎙️ <span class="toolbelt-label">Voice</span>
                </button>

                <!-- Screen Observe Button -->
                <button class="toolbelt-btn" onclick="window.FloatingAssistant.observeScreen()" title="Observe Screen Telemetry">
                  🖥️ <span class="toolbelt-label">Screen</span>
                </button>

                <!-- Document / File Upload Trigger -->
                <button class="toolbelt-btn" onclick="document.getElementById('asstFileInput').click()" title="Attach Document / File">
                  📎 <span class="toolbelt-label">Attach</span>
                </button>
                <input type="file" id="asstFileInput" style="display:none;" onchange="window.FloatingAssistant.handleFileSelected(event)" multiple />
              </div>

              <!-- Emergency Killswitch Direct Access -->
              <button class="toolbelt-btn btn-killswitch" onclick="window.FloatingAssistant.triggerEmergencyStop()" title="Emergency Freeze All Missions">
                🛑 <span class="toolbelt-label">STOP</span>
              </button>
            </div>
          </div>
        </div>
      `;
    }

    renderMessagesHtml() {
      return this.messages.map(m => {
        const isUser = m.sender === 'user';
        return `
          <div class="assistant-msg-row ${isUser ? 'user-row' : 'assistant-row'}">
            <div class="assistant-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}">
              <div class="bubble-text">${this.formatMarkdown(m.text)}</div>

              <!-- Deliverable Artifact Card -->
              ${m.deliverable ? this.renderDeliverableCardHtml(m.deliverable) : ''}

              <!-- Action Card (Mission / Meeting Invite / Approval) -->
              ${m.actionCard ? this.renderActionCardHtml(m.actionCard) : ''}

              <!-- Clarification Choice Buttons -->
              ${m.choices ? this.renderChoicesHtml(m.choices) : ''}

              <!-- Citations Bar -->
              ${m.citations && m.citations.length ? `
                <div class="bubble-citations">
                  ${m.citations.map(c => `
                    <span class="citation-badge ${c.source_type === 'INTERNAL' ? 'cit-internal' : 'cit-external'}">
                      ${c.source_type === 'INTERNAL'
                        ? '🏢 [INTERNAL]'
                        : c.source_type === 'MODEL'
                          ? '🤖 [MODEL]'
                          : (c.status === 'UNAVAILABLE' ? '⚠️ [NO EXTERNAL SOURCE]' : '🌐 [EXTERNAL]')} ${this.escape(c.label)}
                    </span>
                  `).join('')}
                </div>
              ` : ''}

              <div class="bubble-timestamp">${new Date(m.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
          </div>
        `;
      }).join('');
    }

    renderDeliverableCardHtml(deliv) {
      const isDoc = deliv.type === 'DOCUMENT' || deliv.doc_id;
      const fmt = (deliv.format || 'PDF').toUpperCase();
      const fmtColor = {
        PDF: '#ef4444',
        DOCX: '#2563eb',
        XLSX: '#10b981',
        PPTX: '#f59e0b',
        CSV: '#059669',
        TXT: '#64748b'
      }[fmt] || '#3b82f6';

      return `
        <div class="deliverable-card">
          <div style="display:flex; align-items:center; gap:8px;">
            <div class="file-format-badge" style="background:${fmtColor};">${fmt}</div>
            <div style="flex:1; min-width:0;">
              <div class="deliverable-title">${this.escape(deliv.title || 'Deliverable Artifact')}</div>
              <div class="deliverable-meta">
                <span>Boundary: <b>${this.escape(deliv.storage_boundary || 'PERSONAL')}</b></span>
                ${deliv.size_bytes ? `<span>• ${(deliv.size_bytes / 1024).toFixed(1)} KB</span>` : ''}
              </div>
            </div>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.08);">
            <span class="hash-tag">${deliv.sha256 ? `SHA-256: ${this.escape(deliv.sha256.substring(0, 12))}...` : 'No checksum issued'}</span>
            ${deliv.download_url ? `
              <a href="${this.escape(deliv.download_url)}" target="_blank" rel="noopener noreferrer" class="btn-deliverable-download" download>
                ⬇️ Download File
              </a>
            ` : `<span style="font-size:11px; color:var(--text-muted);">No download available</span>`}
          </div>
        </div>
      `;
    }

    renderActionCardHtml(action) {
      if (action.type === 'MEETING_INVITE') {
        const isScheduled = action.status === 'SCHEDULED' && action.provider_status === 'CONFIRMED';
        const badgeColor = isScheduled ? '#10b981' : '#ef4444';
        return `
          <div class="meeting-invite-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
              <span style="font-weight:700; color:${isScheduled ? '#3b82f6' : '#ef4444'};">
                📅 ${isScheduled ? 'Calendar Event Confirmed' : 'Meeting Not Scheduled'}
              </span>
              <span style="font-size:10px; padding:2px 6px; border-radius:4px; background:${badgeColor}; color:#fff;">
                ${this.escape(action.provider_status || 'UNKNOWN')}
              </span>
            </div>
            <div style="font-size:12px; font-weight:600; margin-bottom:4px;">${this.escape(action.title || 'Meeting request')}</div>
            ${action.scheduled_time ? `<div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">Time: <b>${this.escape(action.scheduled_time)}</b></div>` : ''}
            ${action.reason && !isScheduled ? `<div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">Reason: ${this.escape(action.reason)}</div>` : ''}

            <div style="display:flex; gap:6px; flex-wrap:wrap;">
              ${action.google_meet_url ? `
                <a href="${this.escape(action.google_meet_url)}" target="_blank" rel="noopener noreferrer" class="btn-meet-join">
                  📹 Join Google Meet
                </a>
              ` : ''}
              ${action.briefing_dossier_url ? `
                <a href="${this.escape(action.briefing_dossier_url)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="font-size:11px; padding:5px 8px;">
                  📄 Briefing Dossier
                </a>
              ` : ''}
            </div>
          </div>
        `;
      }

      if (action.type === 'WORKFORCE_MISSION') {
        const verified = action.verification_status === 'VERIFIED';
        return `
          <div class="action-status-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span style="font-weight:700; color:#8b5cf6;">🏢 Workforce Delegation</span>
              <span class="badge-blue" style="font-size:10px;">${this.escape(action.status || 'DELEGATED')}</span>
            </div>
            <div style="font-size:11.5px; margin-bottom:4px;">Department: <b>${this.escape(action.department || 'Operations')}</b></div>
            <div style="font-size:10.5px; color:var(--text-muted);">Mission ID: <code>${this.escape(action.mission_id || '')}</code></div>
            <div style="font-size:10.5px; margin-top:4px; color:${verified ? '#10b981' : '#f59e0b'};">
              Verification: <b>${this.escape(action.verification_status || 'UNVERIFIED')}</b>
            </div>

            ${action.requires_approval ? `
              <div class="approval-banner" style="margin-top:8px;">
                <div style="font-size:11px; font-weight:700; color:#ef4444; margin-bottom:4px;">⚠️ DoA Authorization Required</div>
                <div style="display:flex; gap:6px;">
                  <button class="btn-primary" style="font-size:11px; padding:3px 8px; background:#10b981;" onclick="window.FloatingAssistant.authorizeApproval('${this.escape(action.approval_id)}', true)">Authorize</button>
                  <button class="btn-secondary" style="font-size:11px; padding:3px 8px; color:#ef4444;" onclick="window.FloatingAssistant.authorizeApproval('${this.escape(action.approval_id)}', false)">Deny</button>
                </div>
              </div>
            ` : ''}
          </div>
        `;
      }

      return '';
    }

    renderChoicesHtml(choices) {
      return `
        <div style="display:flex; gap:6px; margin-top:8px; flex-wrap:wrap;">
          ${choices.map(c => `
            <button class="btn-choice-pill" onclick="window.FloatingAssistant.selectClarification('${c.mode}')">
              ${this.escape(c.label)}
            </button>
          `).join('')}
        </div>
      `;
    }

    renderAttachmentTrayHtml() {
      return this.pendingAttachments.map((f, i) => `
        <div class="attachment-chip">
          <span>📎 ${this.escape(f.name)}</span>
          <button class="chip-remove" onclick="window.FloatingAssistant.removeAttachment(${i})">✕</button>
        </div>
      `).join('');
    }

    renderWaveformHtml() {
      const bars = [];
      for (let i = 0; i < 24; i++) {
        bars.push(`<div class="waveform-anim-bar active" style="animation-delay:${(i * 0.04).toFixed(2)}s"></div>`);
      }
      return bars.join('');
    }

    // =========================================================================
    // USER ACTIONS & COMM CHANNELS
    // =========================================================================

    handleFabClick(e) {
      if (this.isDragging) return;
      this.toggleOpen(e);
    }

    toggleOpen(e) {
      if (e) e.stopPropagation();
      this.isOpen = !this.isOpen;
      const flyout = document.getElementById('assistantFlyout');
      if (flyout) {
        if (this.isOpen) {
          flyout.classList.remove('minimized');
          flyout.classList.add('open');
          setTimeout(() => {
            const inp = document.getElementById('assistantMainInput');
            if (inp) inp.focus();
            this.scrollToBottom();
          }, 100);
        } else {
          flyout.classList.remove('open');
        }
      }
    }

    toggleMinimize(e) {
      if (e) e.stopPropagation();
      const flyout = document.getElementById('assistantFlyout');
      if (!flyout) return;
      flyout.classList.toggle('minimized');
    }

    cycleWorkspaceMode() {
      const modes = ['AUTO', 'PERSONAL', 'COMPANY'];
      const idx = modes.indexOf(this.workspaceMode);
      this.workspaceMode = modes[(idx + 1) % modes.length];

      const pillText = document.getElementById('workspacePillText');
      const pillIcon = document.getElementById('workspacePillIcon');
      if (pillText) pillText.textContent = this.workspaceMode;
      if (pillIcon) {
        pillIcon.textContent = this.workspaceMode === 'PERSONAL' ? '👤' : this.workspaceMode === 'COMPANY' ? '🏢' : '⚡';
      }
    }

    handleInputKeydown(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.submitPrompt();
      }
    }

    autoResizeTextarea(el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(100, el.scrollHeight)}px`;
    }

    async submitPrompt(customText = null, modeOverride = null) {
      const inp = document.getElementById('assistantMainInput');
      const text = customText !== null ? customText : (inp ? inp.value.trim() : '');
      if (!text && this.pendingAttachments.length === 0) return;

      if (inp && customText === null) {
        inp.value = '';
        inp.style.height = 'auto';
      }

      const attachmentsToSend = [...this.pendingAttachments];
      this.pendingAttachments = [];
      const tray = document.getElementById('assistantAttachmentTray');
      if (tray) tray.style.display = 'none';

      this.lastPrompt = text;
      const requestMode = modeOverride || this.workspaceMode;

      // Append user message to UI immediately
      this.messages.push({
        id: 'msg_' + Date.now(),
        sender: 'user',
        text: text,
        timestamp: Date.now() / 1000
      });
      this.refreshMessages();

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;

      try {
        const res = await fetch('/api/assistant/interact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: text,
            workspace_mode: requestMode,
            company_id: companyId,
            session_id: this.sessionId,
            attachments: attachmentsToSend
          })
        });

        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          this.messages.push({
            id: 'err_' + Date.now(),
            sender: 'assistant',
            text: data.error || `The assistant request failed (HTTP ${res.status}). Nothing was executed.`,
            citations: [],
            timestamp: Date.now() / 1000
          });
          this.refreshMessages();
          return;
        }

        this.messages.push({
          id: 'msg_' + Date.now(),
          sender: 'assistant',
          text: data.reply,
          deliverable: data.deliverable_card,
          actionCard: data.action_card,
          choices: data.choices,
          citations: data.citations || [],
          executionState: data.execution_state,
          timestamp: data.timestamp || (Date.now() / 1000)
        });
        this.refreshMessages();

        // If speech synthesis supported and user prompted via voice
        if (this.isListening) {
          this.speakText(data.reply);
        }
      } catch (err) {
        console.error('Interaction error:', err);
        this.messages.push({
          id: 'err_' + Date.now(),
          sender: 'assistant',
          text: 'I could not reach the ZONATA AI backend, so nothing was executed.',
          citations: [],
          timestamp: Date.now() / 1000
        });
        this.refreshMessages();
      }
    }

    selectClarification(selectedMode) {
      if (!this.lastPrompt) return;
      this.workspaceMode = selectedMode;
      const pillText = document.getElementById('workspacePillText');
      const pillIcon = document.getElementById('workspacePillIcon');
      if (pillText) pillText.textContent = this.workspaceMode;
      if (pillIcon) {
        pillIcon.textContent = this.workspaceMode === 'PERSONAL' ? '👤' : this.workspaceMode === 'COMPANY' ? '🏢' : '⚡';
      }
      this.submitPrompt(this.lastPrompt, selectedMode);
    }

    async handleFileSelected(e) {
      const files = e.target.files;
      if (!files || files.length === 0) return;
      const boundary = this.workspaceMode === 'COMPANY' ? 'COMPANY' : 'PERSONAL';

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        try {
          const dataUrl = await this.readFileAsDataUrl(file);
          const res = await fetch('/api/assistant/documents/upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              filename: file.name,
              content_base64: dataUrl,
              storage_boundary: boundary
            })
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || !data.document) {
            throw new Error(data.error || `upload failed (HTTP ${res.status})`);
          }
          this.pendingAttachments.push({
            doc_id: data.document.doc_id,
            name: data.document.name || file.name,
            size: data.document.size_bytes || file.size,
            type: file.type,
            storage_boundary: data.document.storage_boundary,
            sha256: data.document.sha256
          });
        } catch (err) {
          console.error('Attachment upload failed:', err);
          this.messages.push({
            id: 'att_' + Date.now(),
            sender: 'assistant',
            text: `Attachment **${file.name}** was not uploaded, so it is not attached. Nothing was stored.`,
            citations: [],
            timestamp: Date.now() / 1000
          });
          this.refreshMessages();
        }
      }

      const tray = document.getElementById('assistantAttachmentTray');
      if (tray) {
        tray.style.display = this.pendingAttachments.length ? 'flex' : 'none';
        tray.innerHTML = this.renderAttachmentTrayHtml();
      }
      e.target.value = '';
    }

    readFileAsDataUrl(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ''));
        reader.onerror = () => reject(reader.error || new Error('read failed'));
        reader.readAsDataURL(file);
      });
    }

    removeAttachment(idx) {
      this.pendingAttachments.splice(idx, 1);
      const tray = document.getElementById('assistantAttachmentTray');
      if (tray) {
        tray.style.display = this.pendingAttachments.length ? 'flex' : 'none';
        tray.innerHTML = this.renderAttachmentTrayHtml();
      }
    }

    // =========================================================================
    // MULTIMODAL CAPABILITIES (Voice, Vision, Screen, Killswitch)
    // =========================================================================

    toggleMic() {
      this.isListening = !this.isListening;
      const wf = document.getElementById('assistantWaveformBar');
      const btn = document.getElementById('btnToolbeltMic');

      if (btn) btn.className = 'toolbelt-btn ' + (this.isListening ? 'active-red' : '');
      if (wf) wf.style.display = this.isListening ? 'flex' : 'none';

      if (this.isListening) {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
          const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
          const rec = new SpeechRec();
          rec.onresult = (evt) => {
            const transcript = evt.results[0][0].transcript;
            const inp = document.getElementById('assistantMainInput');
            if (inp) inp.value = transcript;
            this.toggleMic();
            this.submitPrompt();
          };
          rec.onerror = () => this.toggleMic();
          rec.start();
        } else {
          this.toggleMic();
          alert('Speech recognition is not natively available in this browser. Please type your directive.');
        }
      }
    }

    async observeScreen() {
      // Browser pages cannot silently capture other applications.  Rather than
      // recording a fabricated observation, state the real capability boundary.
      this.messages.push({
        id: 'obs_' + Date.now(),
        sender: 'assistant',
        text: '🖥️ **Screen observation is not connected in this build.** No screenshot was taken, nothing was sealed, and no company system was contacted. Connecting a host screen agent requires explicit device permission.',
        citations: [{ source_type: 'INTERNAL', label: 'Multimodal capability boundary', verified: true }],
        timestamp: Date.now() / 1000
      });
      this.refreshMessages();
    }

    async triggerEmergencyStop() {
      if (!confirm('🛑 Engage Sovereign EMERGENCY STOP (KillSwitch)? This will immediately freeze company missions at the configured level.')) return;

      try {
        const res = await fetch('/api/assistant/emergency-stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'Emergency KillSwitch engaged by Host' })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
          this.messages.push({
            id: 'stop_' + Date.now(),
            sender: 'assistant',
            text: `🛑 **Emergency stop was not engaged.** ${data.error || `HTTP ${res.status}`}. No containment state was changed.`,
            citations: [],
            timestamp: Date.now() / 1000
          });
          this.refreshMessages();
          return;
        }
        this.messages.push({
          id: 'stop_' + Date.now(),
          sender: 'assistant',
          text: `🛑 **KillSwitch engaged.**\n\nLevel: **${data.level}**\nTarget: \`${data.target_id}\`\nSwitch: \`${data.switch_id}\`\nReason: ${data.reason}\n\nThis is a real containment record from the KillSwitch Matrix. Release it from governance when the situation is contained.`,
          citations: [{ source_type: 'INTERNAL', label: 'ZONATA KillSwitch Matrix', verified: true }],
          timestamp: Date.now() / 1000
        });
        this.refreshMessages();
      } catch (e) {
        this.messages.push({
          id: 'stop_' + Date.now(),
          sender: 'assistant',
          text: 'The emergency-stop request could not reach the backend. Containment was NOT engaged.',
          citations: [],
          timestamp: Date.now() / 1000
        });
        this.refreshMessages();
      }
    }

    async authorizeApproval(approvalId, approved) {
      try {
        const res = await fetch(`/api/approvals/${approvalId}/decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved })
        });
        const data = await res.json().catch(() => ({}));
        this.messages.push({
          id: 'apr_' + Date.now(),
          sender: 'assistant',
          text: res.ok
            ? (approved
              ? `Approval \`${approvalId}\` recorded as **approved**. Execution continues under the approval workflow; completion still requires a verified result.`
              : `Approval \`${approvalId}\` recorded as **denied**. The gated action will not run.`)
            : `Approval decision failed: ${data.error || `HTTP ${res.status}`}. Nothing changed.`,
          citations: [{ source_type: 'INTERNAL', label: 'Sovereign Approval Ledger', verified: res.ok }],
          timestamp: Date.now() / 1000
        });
        this.refreshMessages();
      } catch (e) {
        this.messages.push({
          id: 'apr_' + Date.now(),
          sender: 'assistant',
          text: 'The approval decision could not be submitted. Nothing changed.',
          citations: [],
          timestamp: Date.now() / 1000
        });
        this.refreshMessages();
      }
    }

    speakText(text) {
      if ('speechSynthesis' in window) {
        const cleanText = text.replace(/[*#_`>]/g, '');
        const u = new SpeechSynthesisUtterance(cleanText);
        u.rate = 1.0;
        window.speechSynthesis.speak(u);
      }
    }

    // =========================================================================
    // UTILITIES & STATE SYNC
    // =========================================================================

    refreshMessages() {
      const container = document.getElementById('assistantMessagesContainer');
      if (container) {
        container.innerHTML = this.renderMessagesHtml();
        this.scrollToBottom();
      }
    }

    scrollToBottom() {
      const container = document.getElementById('assistantMessagesContainer');
      if (container) container.scrollTop = container.scrollHeight;
    }

    formatMarkdown(text) {
      if (!text) return '';
      let escaped = this.escape(text);
      // Bold
      escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
      // Italic
      escaped = escaped.replace(/\*(.*?)\*/g, '<i>$1</i>');
      // Inline code
      escaped = escaped.replace(/`(.*?)`/g, '<code>$1</code>');
      // Markdown links: safe http(s) or absolute internal urls only
      escaped = escaped.replace(/\[(.*?)\]\(((?:https?:\/\/|\/)[^\s"'>]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="chat-inline-link">$1</a>');
      // Line breaks
      escaped = escaped.replace(/\n/g, '<br/>');
      return escaped;
    }

    startStateSync() {
      // Sync coworker lifecycle state to pulse ring
      setInterval(async () => {
        try {
          const res = await fetch('/api/v2/coworker/status');
          if (res.ok) {
            const data = await res.json();
            const ring = document.getElementById('assistantPulseRing');
            if (ring && data.lifecycle_state) {
              ring.style.background = data.lifecycle_state === 'IDLE' ? '#10b981' : '#3b82f6';
            }
          }
        } catch (e) {}
      }, 5000);
    }

    escape(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }
  }

  // Export singleton to window
  window.FloatingAssistant = new UniversalFloatingAssistant();
  // Auto-init on DOMContentLoaded or immediate if already loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.FloatingAssistant.init());
  } else {
    window.FloatingAssistant.init();
  }
})();
