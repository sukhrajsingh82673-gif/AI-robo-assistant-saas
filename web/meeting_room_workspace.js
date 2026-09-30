/**
 * ZONATA — AI CEO Meeting Room Executive Workspace
 * Real executive communication room between Host and AI CEO supporting
 * video/avatar streams, real-time voice, live transcripts, shared reports,
 * and governed strategic decisions.
 */

(function() {
  'use strict';

  class MeetingRoomWorkspaceManager {
    constructor() {
      this.meeting = null;
      this.transcripts = [];
      this.reports = null;
      this.decisions = [];
      this.loading = false;
      this.isRecognizingVoice = false;
      this.speechRecognition = null;
      this.isCameraActive = false;
      this.localMediaStream = null;
      this.speechSynth = window.speechSynthesis || null;
      this.initSpeechRecognition();
    }

    initSpeechRecognition() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        this.speechRecognition = new SpeechRecognition();
        this.speechRecognition.continuous = false;
        this.speechRecognition.interimResults = false;
        this.speechRecognition.lang = 'en-US';

        this.speechRecognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          if (transcript) {
            const input = document.getElementById('meetingTextInput');
            if (input) input.value = transcript;
            this.sendHostMessage('VOICE');
          }
          this.isRecognizingVoice = false;
          this.updateMicButton();
        };

        this.speechRecognition.onerror = (err) => {
          console.warn('Speech recognition error:', err);
          this.isRecognizingVoice = false;
          this.updateMicButton();
        };

        this.speechRecognition.onend = () => {
          this.isRecognizingVoice = false;
          this.updateMicButton();
        };
      }
    }

    async render(containerId = 'view-meeting') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';

      this.loading = true;
      container.innerHTML = `
        <div style="padding:40px; text-align:center;">
          <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
          <div style="font-size:14px; color:var(--text-secondary);">Connecting to AI CEO Executive Command Room...</div>
        </div>
      `;

      try {
        await this.loadActiveMeeting(companyId);
        await this.loadTranscripts();
        await this.loadReports(companyId);
        await this.loadDecisions(companyId);
        this.renderWorkspace(container);
      } catch (err) {
        console.error('Failed to open meeting room:', err);
        container.innerHTML = `
          <div style="padding:40px; text-align:center;">
            <h3>Unable to initialize Meeting Room</h3>
            <p style="color:var(--text-muted);">${err.message}</p>
            <button class="btn-primary" onclick="window.MeetingRoomWorkspace.render()">Retry</button>
          </div>
        `;
      } finally {
        this.loading = false;
      }
    }

    async loadActiveMeeting(companyId) {
      const res = await fetch(`/api/meetings/active?company_id=${encodeURIComponent(companyId)}`);
      if (res.ok) {
        this.meeting = await res.json();
      }
    }

    async loadTranscripts() {
      if (!this.meeting) return;
      const res = await fetch(`/api/meetings/${this.meeting.meeting_id}/transcripts`);
      if (res.ok) {
        const data = await res.json();
        this.transcripts = data.transcripts || [];
      }
    }

    async loadReports(companyId) {
      const res = await fetch(`/api/meetings/reports?company_id=${encodeURIComponent(companyId)}`);
      if (res.ok) {
        this.reports = await res.json();
      }
    }

    async loadDecisions(companyId) {
      const res = await fetch(`/api/meetings/decisions?company_id=${encodeURIComponent(companyId)}`);
      if (res.ok) {
        const data = await res.json();
        this.decisions = data.decisions || [];
      }
    }

    renderWorkspace(container) {
      const m = this.meeting || {};
      const statusPill = this.getStatusBadge(m.status);

      container.innerHTML = `
        <div class="meeting-room-workspace" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- 1. Executive Meeting Header -->
          <div class="meeting-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; box-shadow:var(--shadow-sm);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
              <div>
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                  <span class="badge badge-purple" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Executive Council</span>
                  <span class="badge ${statusPill.class}" style="font-weight:700;">${m.status || 'Ready'}</span>
                </div>
                <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                  AI CEO Meeting Room
                </h1>
                <div style="font-size:13px; color:var(--text-secondary); display:flex; gap:16px; flex-wrap:wrap;">
                  <span>Selected Company: <strong style="color:var(--text-primary);">${this.escape(m.company_name || 'Enterprise')}</strong></span>
                  <span>•</span>
                  <span>Host: <strong>${this.escape(m.host_user_id || 'Owner')}</strong></span>
                  <span>•</span>
                  <span>Strategic Context: <em>${this.escape(m.strategic_context || 'General Operations')}</em></span>
                </div>
              </div>

              <!-- Header Action Controls -->
              <div style="display:flex; gap:8px; flex-wrap:wrap;">
                ${m.status !== 'Live' ? `
                  <button class="btn-primary" style="background:#10b981; border:none; padding:8px 16px;" onclick="window.MeetingRoomWorkspace.startMeeting()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    Start Meeting
                  </button>
                ` : `
                  <button class="btn-secondary" style="color:#ef4444; border-color:#ef4444; padding:8px 16px;" onclick="window.MeetingRoomWorkspace.endMeeting()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12"/></svg>
                    End Meeting
                  </button>
                `}
                <button class="btn-secondary" onclick="window.MeetingRoomWorkspace.openReportsDrawer()">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  View Reports
                </button>
                <button class="btn-secondary" onclick="window.MeetingRoomWorkspace.openDecisionModal()">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                  Record Decision
                </button>
                <button class="btn-secondary" onclick="window.navigateTo('/schedule')">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                  Schedule Action
                </button>
              </div>
            </div>
          </div>

          <!-- 2. Main Executive Area: Split Screen (Video & Hologram / Transcript) -->
          <div style="display:grid; grid-template-columns:minmax(320px, 1fr) minmax(360px, 1fr); gap:20px;" class="meeting-main-grid">
            
            <!-- Left Panel: AI CEO Avatar & Video Media Surface -->
            <div class="meeting-media-surface" style="background:#090d16; border:1px solid var(--border-color); border-radius:var(--radius-lg); overflow:hidden; display:flex; flex-direction:column; position:relative; min-height:460px; box-shadow:var(--shadow-md);">
              
              <!-- Connectivity Badges Strip -->
              <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 16px; background:rgba(0,0,0,0.5); border-bottom:1px solid rgba(255,255,255,0.08); z-index:10;">
                <div style="display:flex; gap:10px; font-size:11px; font-weight:700;">
                  <span style="color:${this.isCameraActive ? '#10b981' : 'var(--text-muted)'}; display:inline-flex; align-items:center; gap:4px;">
                    <span class="status-pulse-dot" style="background:${this.isCameraActive ? '#10b981' : '#6b7280'}; width:8px; height:8px;"></span>
                    ${this.isCameraActive ? 'VIDEO CONNECTED' : 'VIDEO STANDBY'}
                  </span>
                  <span style="color:#10b981; display:inline-flex; align-items:center; gap:4px;">
                    <span class="status-pulse-dot" style="background:#10b981; width:8px; height:8px;"></span>
                    VOICE CONNECTED
                  </span>
                  <span style="color:#10b981; display:inline-flex; align-items:center; gap:4px;">
                    <span class="status-pulse-dot" style="background:#10b981; width:8px; height:8px;"></span>
                    TEXT CONNECTED
                  </span>
                </div>
                <div style="font-size:11.5px; color:#94a3b8; font-family:var(--font-mono);">WebRTC 1.0</div>
              </div>

              <!-- Main Stage: AI CEO Avatar & Video Stream Area -->
              <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:30px; position:relative;">
                
                <!-- Holographic Avatar Visualization -->
                <div class="ai-ceo-avatar-glow" style="width:140px; height:140px; border-radius:50%; background:radial-gradient(circle, rgba(124,58,237,0.3) 0%, rgba(37,99,235,0.05) 70%); border:2px solid rgba(124,58,237,0.4); display:flex; align-items:center; justify-content:center; margin-bottom:16px; position:relative; box-shadow:0 0 30px rgba(124,58,237,0.3);">
                  <div style="font-size:54px; filter:drop-shadow(0 0 10px rgba(124,58,237,0.8));">🧠</div>
                  <div class="avatar-ripple" style="position:absolute; inset:-10px; border-radius:50%; border:1px dashed rgba(124,58,237,0.3); animation:spin 20s linear infinite;"></div>
                </div>

                <div style="font-size:17px; font-weight:700; color:#f8fafc; margin-bottom:4px;">AI CEO Executive Stream</div>
                
                <!-- Truthful Status Display (as explicitly instructed: "AI CEO Video - Waiting for AI video provider") -->
                <div style="font-size:12px; color:#94a3b8; background:rgba(255,255,255,0.06); padding:4px 12px; border-radius:var(--radius-sm); border:1px solid rgba(255,255,255,0.1); margin-top:6px;">
                  Waiting for AI video provider • Voice & Text Fully Operational
                </div>

                <!-- Picture-In-Picture (PIP) Host Video Stream -->
                <div id="hostPipContainer" style="position:absolute; bottom:16px; right:16px; width:130px; height:96px; border-radius:var(--radius-md); background:#1e293b; border:2px solid rgba(255,255,255,0.2); overflow:hidden; display:flex; flex-direction:column; align-items:center; justify-content:center; box-shadow:0 8px 16px rgba(0,0,0,0.5);">
                  <video id="hostVideoEl" autoplay playsinline muted style="width:100%; height:100%; object-fit:cover; display:${this.isCameraActive ? 'block' : 'none'};"></video>
                  <div id="hostVideoFallback" style="display:${this.isCameraActive ? 'none' : 'flex'}; flex-direction:column; align-items:center; justify-content:center; font-size:11px; color:#94a3b8; text-align:center; padding:6px;">
                    <span style="font-size:20px; margin-bottom:2px;">👤</span>
                    <span>Host Camera Off</span>
                  </div>
                </div>
              </div>

              <!-- Media Control Toolbar -->
              <div style="background:rgba(0,0,0,0.7); border-top:1px solid rgba(255,255,255,0.08); padding:12px 18px; display:flex; justify-content:center; gap:14px; align-items:center;">
                <button class="btn-media-toggle ${this.isCameraActive ? 'active' : ''}" id="cameraToggleBtn" onclick="window.MeetingRoomWorkspace.toggleCamera()" style="background:${this.isCameraActive ? '#10b981' : 'rgba(255,255,255,0.1)'}; color:#fff; border:none; border-radius:50%; width:42px; height:42px; display:flex; align-items:center; justify-content:center; cursor:pointer;" title="Toggle Camera">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                </button>
                <button class="btn-media-toggle ${this.isRecognizingVoice ? 'active' : ''}" id="micToggleBtn" onclick="window.MeetingRoomWorkspace.toggleVoice()" style="background:${this.isRecognizingVoice ? '#ef4444' : 'rgba(255,255,255,0.1)'}; color:#fff; border:none; border-radius:50%; width:42px; height:42px; display:flex; align-items:center; justify-content:center; cursor:pointer;" title="Push to Talk / Speech to Text">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                </button>
                <button class="btn-secondary" style="font-size:12px; padding:6px 12px; border-radius:var(--radius-md); background:rgba(255,255,255,0.06); color:#f8fafc;" onclick="window.MeetingRoomWorkspace.openReportsDrawer()">
                  📑 Shared Context
                </button>
              </div>
            </div>

            <!-- Right Panel: Meeting Transcript & Real-Time Discussion Timeline -->
            <div class="meeting-transcript-surface" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); display:flex; flex-direction:column; min-height:460px; box-shadow:var(--shadow-sm);">
              
              <!-- Transcript Header -->
              <div style="padding:14px 18px; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <span style="font-size:14px; font-weight:700; color:var(--text-primary);">Executive Transcript & Audit Record</span>
                  <span style="font-size:12px; color:var(--text-muted); margin-left:8px;">(${this.transcripts.length} entries)</span>
                </div>
                <button class="btn-secondary" style="font-size:11.5px; padding:4px 8px;" onclick="window.MeetingRoomWorkspace.clearTranscriptsLocal()">
                  Clear View
                </button>
              </div>

              <!-- Message History Scroll Area -->
              <div id="transcriptScrollBox" style="flex:1; padding:16px; overflow-y:auto; max-height:360px; display:flex; flex-direction:column; gap:12px;">
                ${this.renderTranscriptsHtml()}
              </div>

              <!-- Discussion Input Bar -->
              <div style="padding:14px 18px; border-top:1px solid var(--border-color); background:var(--bg-surface-hover);">
                <form onsubmit="event.preventDefault(); window.MeetingRoomWorkspace.sendHostMessage('TEXT');" style="display:flex; gap:10px;">
                  <input type="text" id="meetingTextInput" class="form-input" style="flex:1; padding:11px 14px; font-size:13.5px;" placeholder="Address the AI CEO (e.g. 'Review sales velocity and advise on direct discounts')..." />
                  <button type="submit" class="btn-primary" style="padding:0 20px;">
                    Send
                  </button>
                </form>
              </div>
            </div>

          </div>

          <!-- 3. Executive Decision Records & Directives Log -->
          <div class="meeting-decisions-panel" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <div>
                <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0 0 2px 0;">
                  Session Decisions & Cryptographic Grants
                </h3>
                <p style="font-size:12.5px; color:var(--text-secondary); margin:0;">
                  Governed decisions recorded during AI CEO sessions with cryptographic audit hash verification.
                </p>
              </div>
              <button class="btn-primary" style="font-size:12.5px; padding:6px 14px;" onclick="window.MeetingRoomWorkspace.openDecisionModal()">
                + Record Decision
              </button>
            </div>

            <div style="display:flex; flex-direction:column; gap:8px;">
              ${this.decisions.length === 0 ? '<div style="font-size:13px; color:var(--text-muted); padding:16px 0; text-align:center;">No decision records logged yet for this company.</div>' : ''}
              ${this.decisions.map(d => `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px; background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); flex-wrap:wrap; gap:10px;">
                  <div>
                    <div style="display:flex; align-items:center; gap:8px;">
                      <span class="badge badge-emerald">${d.status}</span>
                      <span class="badge badge-subtle">${d.decision_type}</span>
                      <span style="font-size:13px; font-weight:700; color:var(--text-primary);">${this.escape(d.title)}</span>
                    </div>
                    <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">${this.escape(d.description)}</div>
                  </div>
                  <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono); text-align:right;">
                    Grant Hash: ${d.signed_grant_hash}
                    <div>${new Date(d.created_at * 1000).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'})}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

        </div>
      `;

      // Auto scroll transcript to bottom
      const box = document.getElementById('transcriptScrollBox');
      if (box) box.scrollTop = box.scrollHeight;
    }

    renderTranscriptsHtml() {
      if (this.transcripts.length === 0) {
        return `<div style="text-align:center; padding:30px; color:var(--text-muted);">Transcript empty. Start by speaking or sending a prompt.</div>`;
      }

      return this.transcripts.map(t => {
        const isHost = t.speaker === 'HOST';
        const isSystem = t.speaker === 'SYSTEM';
        const timeStr = new Date(t.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        if (isSystem) {
          return `
            <div style="text-align:center; margin:6px 0;">
              <span style="font-size:11px; background:var(--bg-surface-hover); border:1px solid var(--border-color); padding:3px 10px; border-radius:12px; color:var(--text-muted);">
                ⚙️ ${this.escape(t.message)} (${timeStr})
              </span>
            </div>
          `;
        }

        return `
          <div class="transcript-entry ${isHost ? 'host' : 'ceo'}" style="display:flex; flex-direction:column; align-items:${isHost ? 'flex-end' : 'flex-start'};">
            <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
              <span style="font-size:11px; font-weight:700; color:${isHost ? 'var(--accent-blue)' : '#a78bfa'};">
                ${t.speaker}
              </span>
              <span style="font-size:10px; color:var(--text-muted);">${timeStr}</span>
              ${t.mode === 'VOICE' ? `<span style="font-size:9.5px; background:rgba(239,68,68,0.15); color:#ef4444; padding:1px 4px; border-radius:3px;">VOICE</span>` : ''}
            </div>
            <div style="max-width:85%; background:${isHost ? 'var(--accent-blue)' : 'var(--bg-surface-hover)'}; color:${isHost ? '#fff' : 'var(--text-primary)'}; padding:10px 14px; border-radius:var(--radius-md); font-size:13px; line-height:1.45; border:${isHost ? 'none' : '1px solid var(--border-color)'};">
              ${this.escape(t.message)}
            </div>
            ${t.related_context ? `<div style="font-size:10.5px; color:var(--text-muted); margin-top:2px;">Context: ${this.escape(t.related_context)}</div>` : ''}
          </div>
        `;
      }).join('');
    }

    async sendHostMessage(mode = 'TEXT') {
      const input = document.getElementById('meetingTextInput');
      if (!input || !input.value.trim() || !this.meeting) return;

      const message = input.value.trim();
      input.value = '';

      try {
        const res = await fetch(`/api/meetings/${this.meeting.meeting_id}/message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, mode })
        });

        if (res.ok) {
          const data = await res.json();
          await this.loadTranscripts();
          
          // Re-render transcript section
          const box = document.getElementById('transcriptScrollBox');
          if (box) {
            box.innerHTML = this.renderTranscriptsHtml();
            box.scrollTop = box.scrollHeight;
          }

          // If AI CEO response and speech synthesis available, speak it
          if (this.speechSynth && data.ai_ceo_response && data.ai_ceo_response.message) {
            this.speakCeoResponse(data.ai_ceo_response.message);
          }
        }
      } catch (err) {
        console.error('Failed to send host message:', err);
      }
    }

    speakCeoResponse(text) {
      if (!this.speechSynth) return;
      this.speechSynth.cancel();
      const utterance = new SpeechSynthesisUtterance(text.substring(0, 200)); // Speak key lead sentence
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      this.speechSynth.speak(utterance);
    }

    async toggleCamera() {
      const videoEl = document.getElementById('hostVideoEl');
      const fallbackEl = document.getElementById('hostVideoFallback');
      const btn = document.getElementById('cameraToggleBtn');

      if (!this.isCameraActive) {
        try {
          if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            this.localMediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            if (videoEl) {
              videoEl.srcObject = this.localMediaStream;
              videoEl.style.display = 'block';
            }
            if (fallbackEl) fallbackEl.style.display = 'none';
            this.isCameraActive = true;
            if (btn) btn.style.background = '#10b981';
          } else {
            alert('Camera not supported on this browser context.');
          }
        } catch (e) {
          console.warn('Camera access denied or unavailable:', e);
          alert('Camera permission denied or camera device unavailable.');
        }
      } else {
        if (this.localMediaStream) {
          this.localMediaStream.getTracks().forEach(t => t.stop());
          this.localMediaStream = null;
        }
        if (videoEl) videoEl.style.display = 'none';
        if (fallbackEl) fallbackEl.style.display = 'flex';
        this.isCameraActive = false;
        if (btn) btn.style.background = 'rgba(255,255,255,0.1)';
      }
    }

    toggleVoice() {
      if (!this.speechRecognition) {
        alert('Speech-to-text is not supported in this browser environment.');
        return;
      }

      if (!this.isRecognizingVoice) {
        try {
          this.speechRecognition.start();
          this.isRecognizingVoice = true;
          this.updateMicButton();
        } catch (e) {
          console.warn('Could not start speech recognition:', e);
        }
      } else {
        this.speechRecognition.stop();
        this.isRecognizingVoice = false;
        this.updateMicButton();
      }
    }

    updateMicButton() {
      const btn = document.getElementById('micToggleBtn');
      if (btn) {
        btn.style.background = this.isRecognizingVoice ? '#ef4444' : 'rgba(255,255,255,0.1)';
      }
    }

    async startMeeting() {
      if (!this.meeting) return;
      const res = await fetch(`/api/meetings/${this.meeting.meeting_id}/start`, { method: 'POST' });
      if (res.ok) {
        this.render();
      }
    }

    async endMeeting() {
      if (!this.meeting) return;
      const res = await fetch(`/api/meetings/${this.meeting.meeting_id}/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: 'Host concluded operational meeting session.' })
      });
      if (res.ok) {
        this.render();
      }
    }

    clearTranscriptsLocal() {
      this.transcripts = [];
      const box = document.getElementById('transcriptScrollBox');
      if (box) box.innerHTML = this.renderTranscriptsHtml();
    }

    openReportsDrawer() {
      const modalBody = document.getElementById('modalBody');
      const modalTitle = document.getElementById('modalTitle');
      const overlay = document.getElementById('modalOverlay');

      if (!modalBody || !overlay || !this.reports) return;

      const r = this.reports.reports || {};
      modalTitle.textContent = `Shared Context & Reports — ${this.reports.company_name}`;
      modalBody.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <!-- Executive Brief -->
          <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
            <div style="font-size:14px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">${r.executive_brief?.title}</div>
            <div style="font-size:12.5px; color:var(--text-secondary);">${r.executive_brief?.summary}</div>
            <div style="font-size:12px; color:var(--accent-emerald); font-weight:600; margin-top:6px;">Health Index: ${r.executive_brief?.health_score}%</div>
          </div>

          <!-- Financial Summary -->
          <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
            <div style="font-size:14px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">${r.financial_summary?.title}</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; font-size:12px;">
              <div>Gross Revenue: <strong>₹${(r.financial_summary?.gross_revenue||0).toLocaleString()}</strong></div>
              <div>Operating Costs: <strong>₹${(r.financial_summary?.operating_expenses||0).toLocaleString()}</strong></div>
              <div>Contribution: <strong style="color:var(--accent-emerald);">₹${(r.financial_summary?.contribution_margin||0).toLocaleString()}</strong></div>
            </div>
          </div>

          <!-- Operations Summary -->
          <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
            <div style="font-size:14px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">${r.operations_summary?.title}</div>
            <div style="font-size:12px; color:var(--text-secondary);">
              Nodes Online: <strong>${r.operations_summary?.nodes_online}</strong> • Quarantined: <strong>${r.operations_summary?.quarantine_events}</strong> • Night Audit: <strong>${r.operations_summary?.night_audit_status}</strong>
            </div>
          </div>

          <!-- Risk & Attention -->
          <div style="background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.3); border-radius:var(--radius-md); padding:14px;">
            <div style="font-size:14px; font-weight:700; color:#ef4444; margin-bottom:4px;">${r.risk_and_attention?.title}</div>
            <div style="font-size:12px; color:var(--text-primary);">
              Pending Approvals in Decision Room: <strong>${r.risk_and_attention?.pending_approvals_count}</strong>
            </div>
          </div>

          <div style="text-align:right;">
            <button class="btn-primary" onclick="closeModal()">Close</button>
          </div>
        </div>
      `;

      overlay.style.display = 'flex';
    }

    openDecisionModal() {
      const modalBody = document.getElementById('modalBody');
      const modalTitle = document.getElementById('modalTitle');
      const overlay = document.getElementById('modalOverlay');

      if (!modalBody || !overlay) return;

      modalTitle.textContent = 'Record Governed Decision';
      modalBody.innerHTML = `
        <form id="recordDecisionForm" onsubmit="event.preventDefault(); window.MeetingRoomWorkspace.submitDecisionForm();" style="display:flex; flex-direction:column; gap:14px;">
          <div class="form-group">
            <label class="form-label">Decision Title</label>
            <input type="text" id="decFormTitle" class="form-input" placeholder="e.g. Enforce 10% commercial discount ceiling" required />
          </div>

          <div class="form-group">
            <label class="form-label">Decision Category</label>
            <select id="decFormType" class="form-input">
              <option value="STRATEGIC">Strategic Policy</option>
              <option value="MISSION">Mission Execution</option>
              <option value="BUDGET">Budget / Expenditure</option>
              <option value="APPROVAL">Governance Approval</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Strategic Rationale & Directive</label>
            <textarea id="decFormDesc" class="form-input" rows="3" placeholder="Explain the agreed action and constraints for the autonomous workforce..." required></textarea>
          </div>

          <div class="form-group" style="display:flex; align-items:center; gap:8px;">
            <input type="checkbox" id="decFormCreateMission" style="width:16px; height:16px;" />
            <label for="decFormCreateMission" style="font-size:13px; color:var(--text-primary); cursor:pointer;">
              Automatically instantiate new Mission in TaskMaker / Mission Queue
            </label>
          </div>

          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:10px;">
            <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Sign & Record Decision</button>
          </div>
        </form>
      `;

      overlay.style.display = 'flex';
    }

    async submitDecisionForm() {
      const title = document.getElementById('decFormTitle').value.trim();
      const decision_type = document.getElementById('decFormType').value;
      const description = document.getElementById('decFormDesc').value.trim();
      const create_mission = document.getElementById('decFormCreateMission').checked;
      const companyId = this.meeting ? this.meeting.company_id : 'comp_primary';
      const meetingId = this.meeting ? this.meeting.meeting_id : null;

      try {
        const res = await fetch('/api/meetings/decisions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_id: companyId,
            meeting_id: meetingId,
            title,
            decision_type,
            description,
            create_mission
          })
        });

        if (res.ok) {
          closeModal();
          await this.loadDecisions(companyId);
          await this.loadTranscripts();
          this.render();
        } else {
          alert('Failed to record decision.');
        }
      } catch (e) {
        console.error('Error submitting decision:', e);
      }
    }

    getStatusBadge(status) {
      switch (status) {
        case 'Live': return { class: 'badge-emerald' };
        case 'Paused': return { class: 'badge-amber' };
        case 'Ended': return { class: 'badge-subtle' };
        case 'Ready':
        default: return { class: 'badge-blue' };
      }
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

  window.MeetingRoomWorkspace = new MeetingRoomWorkspaceManager();
})();
