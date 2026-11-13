/**
 * URA Assistant — the single assistant surface.
 *
 * One launcher, one non-modal window, one conversation. The Co-worker screen is
 * NOT an assistant and is not touched here; it remains the agent/employee
 * execution workspace and the assistant links to it.
 *
 * The backend is the existing FloatingAssistantService pipeline:
 *   POST /api/assistant/interact
 *   POST /api/assistant/documents/upload
 *   POST /api/assistant/emergency-stop
 *   POST /api/approvals
 *
 * No API keys and no fabricated data live in this file.
 */
(function () {
  'use strict';

  const STORAGE = 'ura.assistant.v1';
  const MAX_ATTACHMENTS = 4;

  const PAGE_LABELS = {
    overview: 'Overview',
    coworker: 'Co-worker',
    missions: 'Work & Missions',
    work: 'Work & Missions',
    approvals: 'Approvals',
    terminal: 'Terminal',
    activity: 'Activity',
    artifacts: 'Artifacts',
    schedule: 'Schedule',
    operations: 'Operations',
    customers: 'Customers',
    finance: 'Finance',
    people: 'People',
    records: 'Records',
    files: 'Files',
    reports: 'Reports',
    'agent-factory': 'Agent Factory',
    integrations: 'Integrations',
    governance: 'Governance',
    company: 'Company',
    organization: 'Organization',
    'ceo-records': 'AI CEO Records',
    workforce: 'Workforce',
    tasks: 'TaskMaker',
    workflows: 'Workflows',
    'agent-network': 'Agent Network',
    'mcp-network': 'MCP Network',
    settings: 'Settings',
    plugins: 'Plugins',
    design: 'Design'
  };

  const PAGE_SUGGESTIONS = {
    overview: ['What needs my attention?', 'Summarize this week', 'Open approvals'],
    approvals: ['Which approvals are waiting?', 'Explain the riskiest one', 'Open Finance'],
    finance: ['Where are we losing money?', 'Summarize this month', 'Open reports'],
    customers: ['Which leads are hottest?', 'Summarize this pipeline', 'Draft a follow-up'],
    missions: ['What is running now?', 'Show blocked work', 'Delegate a task'],
    coworker: ['What is the Co-worker doing?', 'Open mission control', 'Pause the current mission'],
    people: ['Who is overloaded?', 'Summarize the team', 'Open workforce'],
    meetings: ['Prepare my next meeting', 'Show past decisions', 'Open the meeting library'],
    reports: ['Generate a weekly report', 'What changed since last week?', 'Open evidence'],
    default: ['What can you do?', 'Open the Co-worker', 'What needs my attention?']
  };

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatText(text) {
    let out = escapeHtml(text);
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
    out = out.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    return out;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function userKey() {
    try {
      const host = (window.state && window.state.host) || null;
      return (host && (host.email || host.name)) || localStorage.getItem('zonata_user_id') || 'owner';
    } catch (err) {
      return 'owner';
    }
  }

  class URAAssistantController {
    constructor() {
      this.root = null;
      this.launcher = null;
      this.win = null;
      this.isOpen = false;
      this.phone = false;
      this.mode = 'window';
      this.scope = 'PERSONAL';
      this.anchor = 'bottom-right';
      this.winPos = null;
      this.showButton = 'always';
      this.companyGranted = false;
      this.companyPermissionPending = false;
      this.messages = [];
      this.pendingAttachments = [];
      this.busy = false;
      this.sessionId = null;
      this.lastPrompt = '';
      this.agentRole = null;
      this.streamState = null;
      this.pendingConfirmations = [];
      this.jobs = [];
      this.jobsOpen = false;
      this.webOpen = false;
      this.watchingJobId = null;
      this.jobPollTimer = null;
      this.drag = null;
      this.storageKey = `${STORAGE}:${userKey()}`;
      this.initialized = false;
    }

    // ------------------------------------------------------------- lifecycle
    init() {
      if (this.initialized) return;
      const mount = document.getElementById('uraAssistantRoot');
      if (!mount) return;
      this.initialized = true;
      this.root = mount;
      this.phone = this.isPhone();
      this.load();
      this.render();
      this.launcher = document.getElementById('uraLauncher');
      this.win = document.getElementById('uraWindow');
      this.bind();
      this.refreshContext();
      this.checkCompanyPermission();
      this.startJobsPolling();
      if (this.showButton === 'hidden' && this.launcher) this.launcher.hidden = true;
      this.applyAnchor();
      this.applyMode();
      this.renderMessages();
      window.addEventListener('resize', () => {
        this.phone = this.isPhone();
        this.applyMode();
        this.clampWindow();
      });
      window.addEventListener('hashchange', () => this.refreshContext());
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') this.refreshContext();
      });
    }

    isPhone() {
      return window.matchMedia('(max-width: 768px)').matches;
    }

    load() {
      let saved = null;
      try { saved = JSON.parse(localStorage.getItem(this.storageKey) || 'null'); } catch (err) { saved = null; }
      const data = saved && typeof saved === 'object' ? saved : {};
      this.anchor = data.anchor || 'bottom-right';
      this.mode = data.mode || 'window';
      if (!['window', 'docked', 'expanded'].includes(this.mode)) this.mode = 'window';
      this.scope = data.scope === 'COMPANY' ? 'COMPANY' : 'PERSONAL';
      this.winPos = data.winPos || null;
      this.showButton = data.showButton || 'always';
      this.sessionId = data.sessionId || `ura_${Math.random().toString(36).slice(2, 10)}`;
      if (Array.isArray(data.messages)) this.messages = data.messages.slice(-80);
    }

    save() {
      try {
        localStorage.setItem(this.storageKey, JSON.stringify({
          anchor: this.anchor,
          mode: this.mode,
          scope: this.scope,
          winPos: this.winPos,
          showButton: this.showButton,
          sessionId: this.sessionId,
          messages: this.messages.slice(-80)
        }));
      } catch (err) { /* storage may be unavailable; the assistant still works */ }
    }

    // ------------------------------------------------------------------ DOM
    render() {
      this.root.innerHTML = `
        <button class="ura-launcher" id="uraLauncher" data-anchor="bottom-right" data-state="idle"
                type="button" aria-label="Open URA Assistant" title="URA Assistant (Ctrl/Cmd+J)">
          <span class="ura-ring" aria-hidden="true"></span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true">
            <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"/>
            <path d="M19 15l.9 2.6L22.5 18.5l-2.6.9L19 22l-.9-2.6L15.5 18.5l2.6-.9L19 15z"/>
          </svg>
          <span class="ura-badge" id="uraBadge" hidden>0</span>
          <span class="ura-dot" id="uraDot" hidden></span>
        </button>

        <section class="ura-window" id="uraWindow" data-mode="window" data-anchor="bottom-right"
                 role="dialog" aria-modal="false" aria-label="URA Assistant" hidden>
          <div class="ura-sheet-grabber" aria-hidden="true"></div>
          <header class="ura-header" id="uraHeader">
            <div class="ura-title">URA Assistant<small id="uraScopeLabel">Personal</small></div>
            <div class="ura-scope" role="group" aria-label="Assistant scope">
              <button type="button" data-scope="PERSONAL" aria-pressed="true">Personal</button>
              <button type="button" data-scope="COMPANY" aria-pressed="false">Company <span class="ura-lock" id="uraCompanyLock" hidden>🔒</span></button>
            </div>
            <div class="ura-actions">
              <button class="ura-icon-btn ura-jobs-btn" type="button" data-action="jobs" title="Background jobs" aria-label="Background jobs">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                <span class="ura-badge ura-badge-corner" id="uraJobsBadge" hidden>0</span>
              </button>
              <button class="ura-icon-btn" type="button" data-action="dock" title="Dock to side panel" aria-label="Dock to side panel">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="15" y1="4" x2="15" y2="20"/></svg>
              </button>
              <button class="ura-icon-btn" type="button" data-action="expand" title="Expand" aria-label="Expand assistant">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
              </button>
              <button class="ura-icon-btn" type="button" data-action="minimise" title="Minimise (Esc)" aria-label="Minimise assistant">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
              </button>
              <button class="ura-icon-btn" type="button" data-action="close" title="Close" aria-label="Close assistant">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>
              </button>
            </div>
          </header>

          <div class="ura-context">
            <span class="ura-chip" id="uraContextChip">Looking at Overview</span>
            <span class="ura-chip" id="uraCompanyChip" hidden></span>
            <span class="ura-chip ura-agent-chip" id="uraAgentChip" hidden></span>
          </div>

          <div class="ura-panel" id="uraJobsPanel" hidden aria-label="Background jobs">
            <div class="ura-panel-head">
              <strong>Jobs</strong>
              <span class="ura-panel-meta" id="uraJobsLimit"></span>
              <button class="ura-memory-link" type="button" data-jobs-close>Done</button>
            </div>
            <div class="ura-jobs-list" id="uraJobsList"></div>
          </div>

          <div class="ura-panel" id="uraWebPanel" hidden aria-label="Web access settings">
            <div class="ura-panel-head">
              <strong>Web access</strong>
              <button class="ura-memory-link" type="button" data-web-close>Done</button>
            </div>
            <div class="ura-web-body" id="uraWebBody">Loading…</div>
          </div>

          <div class="ura-banner" id="uraPermissionBanner" hidden>
            <span>Company scope needs the AI CEO's permission.</span>
            <button type="button" id="uraAskPermission">Ask the CEO</button>
          </div>

          <div class="ura-messages" id="uraMessages" role="log" aria-live="polite" aria-relevant="additions text"></div>

          <div class="ura-suggestions" id="uraSuggestions" aria-label="Suggestions"></div>

          <div class="ura-composer-wrap" style="position:relative;">
            <div class="ura-plus-menu" id="uraPlusMenu" hidden>
              <button type="button" data-plus="upload">📎 Upload a document</button>
              <button type="button" data-plus="coworker">🤖 Open the Co-worker</button>
              <button type="button" data-plus="screen">🖥️ Observe my screen</button>
              <button type="button" data-plus="stop">🛑 Emergency stop</button>
              <div class="ura-menu-note">The Co-worker is an agent/employee workspace.</div>
              <button type="button" data-plus="research">🔎 Research the web</button>
              <button type="button" data-plus="background">⏳ Run in background</button>
              <button type="button" data-plus="jobs">🗂️ Jobs <span class="ura-plus-count" id="uraPlusJobsCount"></span></button>
              <button type="button" data-plus="web">🌐 Web access…</button>
              <button type="button" data-plus="remember">🧠 Remember this</button>
              <button type="button" data-plus="memory">🧠 Saved memory</button>
              <button type="button" data-plus="clear">🗑️ Clear history</button>
            </div>
            <div class="ura-composer">
              <button class="ura-round" type="button" data-action="plus" title="Add" aria-label="Add attachment or action" aria-expanded="false">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              </button>
              <textarea id="uraInput" rows="1" placeholder="Ask URA anything…" aria-label="Message URA Assistant"></textarea>
              <button class="ura-round" type="button" data-action="mic" title="Dictate" aria-label="Dictate a message">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 19v3"/></svg>
              </button>
              <button class="ura-round ura-send" type="button" data-action="send" title="Send" aria-label="Send message">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
              </button>
            </div>
            <input type="file" id="uraFileInput" hidden accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.pptx,image/*" />
          </div>
          <div class="ura-window-resize" id="uraResize" aria-hidden="true"></div>
        </section>
      `;
    }

    bind() {
      const root = this.root;
      root.addEventListener('click', (event) => {
        const scopeBtn = event.target.closest('[data-scope]');
        if (scopeBtn) { this.setScope(scopeBtn.dataset.scope); return; }
        const actionBtn = event.target.closest('[data-action]');
        if (actionBtn) { this.action(actionBtn.dataset.action); return; }
        const plusBtn = event.target.closest('[data-plus]');
        if (plusBtn) { this.plusAction(plusBtn.dataset.plus); return; }
        const confirmBtn = event.target.closest('[data-confirm-index]');
        if (confirmBtn) { this.confirmTool(Number(confirmBtn.dataset.confirmIndex)); return; }
        const forgetBtn = event.target.closest('[data-forget-memory]');
        if (forgetBtn) { this.forgetMemory(forgetBtn.dataset.forgetMemory); return; }
        const jobBtn = event.target.closest('[data-job-action]');
        if (jobBtn) { this.jobRequest(jobBtn.dataset.jobId, jobBtn.dataset.jobAction); return; }
        const watchBtn = event.target.closest('[data-watch-job]');
        if (watchBtn) { this.watchJob(watchBtn.dataset.watchJob); return; }
        const openJobBtn = event.target.closest('[data-open-job]');
        if (openJobBtn) { this.showJobResult(openJobBtn.dataset.openJob); return; }
        if (event.target.closest('[data-jobs-panel]')) { this.openJobs(); return; }
        if (event.target.closest('[data-jobs-close]')) { this.closeJobs(); return; }
        if (event.target.closest('[data-web-close]')) { this.closeWebAccess(); return; }
        if (event.target.closest('[data-web-save]')) { this.saveWebAccess(); return; }
        if (event.target.closest('[data-jobs-seen]')) { this.markJobsSeen(); return; }
        if (event.target.closest('[data-open-memory]')) { this.openMemory(); return; }
        if (event.target.closest('[data-forget-all]')) { this.forgetAllMemories(); return; }
        if (event.target.closest('#uraAskPermission')) { this.askCompanyPermission(); }
      });

      this.launcher.addEventListener('pointerdown', (event) => this.startLauncherDrag(event));
      const header = document.getElementById('uraHeader');
      header.addEventListener('pointerdown', (event) => {
        if (this.phone) this.startSheetSwipe(event);
        else this.startWindowDrag(event);
      });
      const resize = document.getElementById('uraResize');
      if (resize) resize.addEventListener('pointerdown', (event) => this.startResize(event));

      const input = document.getElementById('uraInput');
      input.addEventListener('keydown', (event) => this.onComposerKey(event));
      input.addEventListener('input', () => this.autoResize(input));
      document.getElementById('uraFileInput').addEventListener('change', (event) => this.uploadFiles(event));

      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && this.isOpen && !document.getElementById('modalOverlay')?.classList.contains('active')) {
          event.preventDefault();
          this.minimise();
        }
      });
    }

    // -------------------------------------------------------------- context
    refreshContext() {
      const nav = (window.state && window.state.activeNav) || 'overview';
      const label = PAGE_LABELS[nav] || 'Overview';
      const chip = document.getElementById('uraContextChip');
      if (chip) chip.innerHTML = `Looking at <b>${escapeHtml(label)}</b>`;
      const company = this.getCompany();
      const companyChip = document.getElementById('uraCompanyChip');
      if (companyChip) {
        if (company && company.name) {
          companyChip.hidden = false;
          companyChip.textContent = company.name;
        } else {
          companyChip.hidden = true;
        }
      }
      this.renderSuggestions(nav);
      this.applyScopeUi();
    }

    getCompany() {
      try {
        if (window.CurrentCompanyContext && window.CurrentCompanyContext.getCompany) {
          return window.CurrentCompanyContext.getCompany();
        }
      } catch (err) { /* fall through */ }
      const companies = (window.state && window.state.companies) || [];
      const id = window.state && window.state.activeCompanyId;
      return companies.find((c) => (c.company_id || c.id) === id) || companies[0] || null;
    }

    getCompanyId() {
      try {
        if (window.CurrentCompanyContext && window.CurrentCompanyContext.getCompanyId) {
          return window.CurrentCompanyContext.getCompanyId();
        }
      } catch (err) { /* fall through */ }
      const company = this.getCompany();
      return company ? (company.company_id || company.id) : (window.state && window.state.activeCompanyId) || null;
    }

    currentPage() {
      const nav = (window.state && window.state.activeNav) || 'overview';
      if (nav === 'overview' && /\/meeting/.test(window.location.hash)) return 'meetings';
      return nav;
    }

    renderSuggestions(nav) {
      const el = document.getElementById('uraSuggestions');
      if (!el) return;
      const list = PAGE_SUGGESTIONS[this.currentPage()] || PAGE_SUGGESTIONS.default;
      el.innerHTML = list.map((text) => `<button type="button" data-suggest="${escapeHtml(text)}">${escapeHtml(text)}</button>`).join('');
      el.querySelectorAll('[data-suggest]').forEach((btn) => {
        btn.addEventListener('click', () => this.send(btn.dataset.suggest));
      });
    }

    // ---------------------------------------------------------------- scope
    setScope(scope) {
      if (scope === 'COMPANY' && !this.companyGranted) {
        this.scope = 'COMPANY';
        this.applyScopeUi();
        this.renderPermissionBanner();
        this.save();
        return;
      }
      this.scope = scope === 'COMPANY' ? 'COMPANY' : 'PERSONAL';
      this.applyScopeUi();
      this.save();
    }

    applyScopeUi() {
      const label = document.getElementById('uraScopeLabel');
      if (label) label.textContent = this.scope === 'COMPANY' ? 'Company' : 'Personal';
      this.root.querySelectorAll('[data-scope]').forEach((btn) => {
        btn.setAttribute('aria-pressed', String(btn.dataset.scope === this.scope));
      });
      const lock = document.getElementById('uraCompanyLock');
      if (lock) lock.hidden = this.companyGranted || this.scope !== 'COMPANY';
      this.renderPermissionBanner();
    }

    renderPermissionBanner() {
      const banner = document.getElementById('uraPermissionBanner');
      if (!banner) return;
      const show = this.scope === 'COMPANY' && !this.companyGranted;
      banner.hidden = !show;
      const btn = document.getElementById('uraAskPermission');
      if (btn) {
        btn.disabled = this.companyPermissionPending;
        btn.textContent = this.companyPermissionPending ? 'Request sent' : 'Ask the CEO';
      }
    }

    async checkCompanyPermission() {
      try {
        const res = await fetch('/api/approvals');
        if (!res.ok) return;
        const data = await res.json();
        const list = Array.isArray(data.approvals) ? data.approvals : [];
        const granted = list.some((item) => {
          const desc = String(item.action_desc || item.action || item.title || '');
          const status = String(item.status || item.state || '').toUpperCase();
          return /ura assistant/i.test(desc) && /(approved|granted|executed|complete)/.test(status);
        });
        this.companyGranted = granted;
        this.applyScopeUi();
      } catch (err) { /* leave locked; server still enforces */ }
    }

    async askCompanyPermission() {
      if (this.companyPermissionPending) return;
      const companyId = this.getCompanyId();
      if (!companyId) {
        this.addMessage('assistant', 'No company is onboarded yet, so there is nothing to grant access to. Onboard a company first.');
        return;
      }
      this.companyPermissionPending = true;
      this.renderPermissionBanner();
      try {
        const res = await fetch('/api/approvals', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_id: companyId,
            action_desc: 'URA Assistant access to company data (kind: cowork)',
            reason: 'The owner asked the assistant to read and act on company data in Company scope.',
            risk_level: 'LOW',
            consequence: 'Assistant can read company context and propose governed actions.'
          })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `Approval request failed (HTTP ${res.status})`);
        this.addToolStep('Asked the AI CEO for permission');
        this.addMessage('assistant', 'I sent the permission request to the AI CEO. Until it is approved, Company scope stays locked. You can check again from this banner after it is approved.');
      } catch (err) {
        this.addMessage('assistant', `I could not send the permission request: ${err.message}. Nothing was granted.`);
      } finally {
        this.companyPermissionPending = false;
        this.renderPermissionBanner();
      }
    }

    // -------------------------------------------------------------- open/ui
    open(options = {}) {
      if (!this.initialized) this.init();
      this.phone = this.isPhone();
      if (options.focus === 'company') {
        this.scope = 'COMPANY';
        this.applyScopeUi();
      }
      if (options.focus === 'meetings') {
        this.renderSuggestions('meetings');
      }
      if (this.phone) {
        this.mode = this.mode === 'sheet-full' ? 'sheet-full' : 'sheet';
      } else if (!['window', 'docked', 'expanded'].includes(this.mode)) {
        this.mode = 'window';
      }
      this.isOpen = true;
      this.win.hidden = false;
      this.applyMode();
      this.applyAnchor();
      this.renderMessages();
      this.save();
      setTimeout(() => {
        const input = document.getElementById('uraInput');
        if (input) input.focus();
      }, 120);
    }

    minimise() {
      if (this.phone) {
        this.mode = 'sheet';
        this.isOpen = false;
        this.win.hidden = true;
      } else {
        this.mode = 'minimized';
        this.isOpen = false;
        this.win.hidden = true;
      }
      this.save();
    }

    close() {
      this.mode = 'closed';
      this.isOpen = false;
      this.win.hidden = true;
      this.save();
    }

    toggle() {
      if (!this.initialized) this.init();
      if (this.isOpen) this.minimise();
      else this.open();
    }

    toggleSheet() {
      this.phone = this.isPhone();
      if (!this.phone) { this.toggle(); return; }
      if (!this.isOpen) {
        this.mode = 'sheet';
        this.open();
      } else if (this.mode === 'sheet-full') {
        this.minimise();
      } else {
        this.mode = 'sheet-full';
        this.applyMode();
        this.save();
      }
    }

    applyMode() {
      if (!this.win) this.win = document.getElementById('uraWindow');
      if (!this.win) return;
      this.win.dataset.mode = this.phone
        ? (this.mode === 'sheet-full' ? 'sheet-full' : 'sheet')
        : this.mode;
      this.win.hidden = !this.isOpen || ['minimized', 'closed'].includes(this.mode);
      if (this.phone) return;
      if (this.mode === 'window' && this.winPos) {
        this.win.style.left = `${this.winPos.left}px`;
        this.win.style.top = `${this.winPos.top}px`;
        this.win.style.width = `${this.winPos.width}px`;
        this.win.style.height = `${this.winPos.height}px`;
        this.win.style.right = 'auto';
        this.win.style.bottom = 'auto';
        this.win.dataset.anchor = 'free';
      } else if (this.mode === 'window') {
        this.win.style.left = '';
        this.win.style.top = '';
        this.win.style.width = '';
        this.win.style.height = '';
        this.win.style.right = '';
        this.win.style.bottom = '';
        this.win.dataset.anchor = this.anchor;
      } else {
        this.win.style.left = '';
        this.win.style.top = '';
        this.win.style.width = '';
        this.win.style.height = '';
      }
    }

    action(action) {
      if (action === 'send') this.send();
      else if (action === 'plus') this.togglePlusMenu();
      else if (action === 'mic') this.dictate();
      else if (action === 'dock') this.setMode(this.mode === 'docked' ? 'window' : 'docked');
      else if (action === 'expand') this.setMode(this.mode === 'expanded' ? 'window' : 'expanded');
      else if (action === 'jobs') this.openJobs();
      else if (action === 'minimise') this.minimise();
      else if (action === 'close') this.close();
    }

    setMode(mode) {
      this.mode = mode;
      this.isOpen = true;
      this.applyMode();
      this.save();
    }

    togglePlusMenu() {
      const menu = document.getElementById('uraPlusMenu');
      const plus = this.root.querySelector('[data-action="plus"]');
      if (!menu) return;
      menu.hidden = !menu.hidden;
      if (plus) plus.setAttribute('aria-expanded', String(!menu.hidden));
    }

    plusAction(action) {
      const menu = document.getElementById('uraPlusMenu');
      if (menu) menu.hidden = true;
      const plus = this.root.querySelector('[data-action="plus"]');
      if (plus) plus.setAttribute('aria-expanded', 'false');
      if (action === 'upload') document.getElementById('uraFileInput').click();
      if (action === 'coworker') {
        this.minimise();
        if (window.navigateTo) window.navigateTo('/coworker');
      }
      if (action === 'screen') this.observeScreen();
      if (action === 'stop') this.emergencyStop();
      if (action === 'research') this.researchLast();
      if (action === 'background') this.startBackground();
      if (action === 'jobs') this.openJobs();
      if (action === 'web') this.openWebAccess();
      if (action === 'remember') this.rememberLast();
      if (action === 'memory') this.openMemory();
      if (action === 'clear') this.clearConversation();
    }

    // --------------------------------------------------------------- anchors
    applyAnchor() {
      if (!this.launcher) this.launcher = document.getElementById('uraLauncher');
      if (!this.launcher) return;
      this.launcher.dataset.anchor = this.anchor;
      this.launcher.style.left = '';
      this.launcher.style.top = '';
      this.launcher.style.right = '';
      this.launcher.style.bottom = '';
      if (this.mode === 'window' && !this.winPos && this.win) {
        this.win.dataset.anchor = this.anchor;
      }
    }

    computeAnchor(x, y) {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const anchors = [
        ['top-left', 46, 46], ['top', w / 2, 46], ['top-right', w - 46, 46],
        ['left', 46, h / 2], ['right', w - 46, h / 2],
        ['bottom-left', 46, h - 46], ['bottom', w / 2, h - 46], ['bottom-right', w - 46, h - 46]
      ];
      let best = anchors[0];
      let bestDist = Infinity;
      for (const item of anchors) {
        const dist = Math.hypot(item[1] - x, item[2] - y);
        if (dist < bestDist) { bestDist = dist; best = item; }
      }
      return best[0];
    }

    startLauncherDrag(event) {
      if (event.button !== undefined && event.button !== 0) return;
      const startX = event.clientX;
      const startY = event.clientY;
      let moved = false;
      let left = 0;
      let top = 0;
      const rect = this.launcher.getBoundingClientRect();
      this.launcher.classList.add('is-dragging');
      this.launcher.style.left = `${rect.left}px`;
      this.launcher.style.top = `${rect.top}px`;
      this.launcher.style.right = 'auto';
      this.launcher.style.bottom = 'auto';
      this.launcher.setPointerCapture(event.pointerId);

      const onMove = (moveEvent) => {
        const dx = moveEvent.clientX - startX;
        const dy = moveEvent.clientY - startY;
        if (!moved && Math.hypot(dx, dy) > 5) moved = true;
        if (!moved) return;
        left = clamp(rect.left + dx, 8, window.innerWidth - 60);
        top = clamp(rect.top + dy, 8, window.innerHeight - 60);
        this.launcher.style.left = `${left}px`;
        this.launcher.style.top = `${top}px`;
      };
      const onUp = () => {
        this.launcher.removeEventListener('pointermove', onMove);
        this.launcher.removeEventListener('pointerup', onUp);
        this.launcher.removeEventListener('pointercancel', onUp);
        this.launcher.classList.remove('is-dragging');
        if (!moved) { this.open(); return; }
        this.anchor = this.computeAnchor(left + 26, top + 26);
        this.applyAnchor();
        if (this.win && this.mode === 'window' && !this.winPos) this.win.dataset.anchor = this.anchor;
        this.save();
      };
      this.launcher.addEventListener('pointermove', onMove);
      this.launcher.addEventListener('pointerup', onUp);
      this.launcher.addEventListener('pointercancel', onUp);
    }

    startWindowDrag(event) {
      if (event.button !== undefined && event.button !== 0) return;
      if (event.target.closest('button, input, textarea, a')) return;
      if (!this.win || this.phone) return;
      if (this.mode === 'docked' || this.mode === 'expanded') return;
      const rect = this.win.getBoundingClientRect();
      const startX = event.clientX;
      const startY = event.clientY;
      let moved = false;
      this.win.classList.add('is-dragging');
      document.getElementById('uraHeader').setPointerCapture(event.pointerId);

      const onMove = (moveEvent) => {
        const dx = moveEvent.clientX - startX;
        const dy = moveEvent.clientY - startY;
        if (!moved && Math.hypot(dx, dy) > 4) moved = true;
        if (!moved) return;
        this.win.style.left = `${clamp(rect.left + dx, 8, window.innerWidth - rect.width - 8)}px`;
        this.win.style.top = `${clamp(rect.top + dy, 8, window.innerHeight - rect.height - 8)}px`;
        this.win.style.right = 'auto';
        this.win.style.bottom = 'auto';
        this.win.dataset.anchor = 'free';
      };
      const onUp = () => {
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerup', onUp);
        document.removeEventListener('pointercancel', onUp);
        this.win.classList.remove('is-dragging');
        if (!moved) return;
        const next = this.win.getBoundingClientRect();
        this.winPos = {
          left: Math.round(next.left),
          top: Math.round(next.top),
          width: Math.round(next.width),
          height: Math.round(next.height)
        };
        this.save();
      };
      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', onUp);
      document.addEventListener('pointercancel', onUp);
    }

    startSheetSwipe(event) {
      if (event.button !== undefined && event.button !== 0) return;
      if (event.target.closest('button, input, textarea, a')) return;
      const startY = event.clientY;
      let delta = 0;
      const onMove = (moveEvent) => {
        delta = moveEvent.clientY - startY;
        this.win.style.transform = `translateY(${Math.max(-40, delta)}px)`;
      };
      const onUp = () => {
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerup', onUp);
        this.win.style.transform = '';
        if (delta > 60) {
          if (this.mode === 'sheet-full') { this.mode = 'sheet'; this.applyMode(); this.save(); }
          else this.minimise();
        } else if (delta < -50 && this.mode !== 'sheet-full') {
          this.mode = 'sheet-full';
          this.applyMode();
          this.save();
        }
      };
      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', onUp);
    }

    startResize(event) {
      if (!this.win || this.phone || this.mode !== 'window') return;
      event.preventDefault();
      const rect = this.win.getBoundingClientRect();
      const startX = event.clientX;
      const startY = event.clientY;
      const onMove = (moveEvent) => {
        const width = clamp(rect.width + (moveEvent.clientX - startX), 320, window.innerWidth - rect.left - 12);
        const height = clamp(rect.height + (moveEvent.clientY - startY), 420, window.innerHeight - rect.top - 12);
        this.win.style.width = `${width}px`;
        this.win.style.height = `${height}px`;
      };
      const onUp = () => {
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerup', onUp);
        const next = this.win.getBoundingClientRect();
        this.winPos = {
          left: Math.round(next.left),
          top: Math.round(next.top),
          width: Math.round(next.width),
          height: Math.round(next.height)
        };
        this.save();
      };
      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', onUp);
    }

    clampWindow() {
      if (!this.win || this.phone || !this.winPos || this.mode !== 'window') return;
      const maxLeft = Math.max(8, window.innerWidth - 120);
      const maxTop = Math.max(8, window.innerHeight - 120);
      this.winPos.left = clamp(this.winPos.left, 8, maxLeft);
      this.winPos.top = clamp(this.winPos.top, 8, maxTop);
      this.winPos.width = clamp(this.winPos.width, 320, window.innerWidth - 24);
      this.winPos.height = clamp(this.winPos.height, 420, window.innerHeight - 24);
      this.applyMode();
    }

    // -------------------------------------------------------------- messages
    addMessage(sender, text, extra = {}) {
      this.messages.push({
        id: `ura_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        sender,
        text,
        timestamp: Date.now() / 1000,
        ...extra
      });
      this.save();
      this.renderMessages();
      return this.messages[this.messages.length - 1];
    }

    addToolStep(label, working = false) {
      this.messages.push({
        id: `tool_${Date.now()}_${Math.random().toString(36).slice(2, 5)}`,
        sender: 'tool',
        text: label,
        working,
        timestamp: Date.now() / 1000
      });
      this.renderMessages();
    }

    renderMessages() {
      const box = document.getElementById('uraMessages');
      if (!box) return;
      if (!this.messages.length) {
        const company = this.getCompany();
        const where = company && company.name ? ` for ${company.name}` : '';
        box.innerHTML = `<div class="ura-empty">Ask about the page you are on${escapeHtml(where)}, open a screen, or hand deeper work to the Co-worker.<br><span style="font-size:11px;color:var(--label-3);">I use live app data. I never invent numbers.</span></div>`;
      } else {
        box.innerHTML = this.messages.map((message) => this.renderMessage(message)).join('');
      }
      box.scrollTop = box.scrollHeight;
    }

    renderMessage(message) {
      if (message.sender === 'tool') {
        return `<div class="ura-tool-row ${message.working ? 'working' : ''}"><span class="ura-check">${message.working ? '•' : '✓'}</span><span>${escapeHtml(message.text)}</span></div>`;
      }
      const mine = message.sender === 'user';
      const time = new Date((message.timestamp || Date.now() / 1000) * 1000)
        .toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const citations = Array.isArray(message.citations) && message.citations.length
        ? `<div class="ura-citations">${message.citations.map((c) => {
          const label = escapeHtml(c.label || c.source_type || 'Source');
          const inner = c.url
            ? `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener noreferrer">${label}</a>`
            : label;
          const sample = c.sample ? ' <em>sample</em>' : '';
          return `<span>${inner}${sample}</span>`;
        }).join('')}</div>`
        : '';
      const metaName = mine ? 'You' : 'URA';
      return `
        <div class="ura-msg ${mine ? 'user' : 'assistant'}">
          <div class="ura-body">${mine ? escapeHtml(message.text) : formatText(message.text || '')}${message.streaming && !message.text ? '<span class="ura-typing" aria-label="Working"><i></i><i></i><i></i></span>' : ''}${this.renderExtra(message)}</div>
          ${citations}
          <div class="ura-meta">${metaName}${message.agent ? ` · ${escapeHtml(message.agent)}` : ''} · ${time}${message.streaming ? ' · streaming' : ''}</div>
        </div>
      `;
    }

    renderExtra(message) {
      let html = '';
      if (message.streaming && message.text) {
        html += '<span class="ura-typing" aria-hidden="true"><i></i><i></i><i></i></span>';
      }
      if (message.card) {
        html += this.renderToolCard(message.card);
      }
      if (message.confirmationIndex != null) {
        html += `<div class="ura-confirm" role="group" aria-label="Confirm action">
          <button class="ura-confirm-yes" type="button" data-confirm-index="${message.confirmationIndex}">Confirm</button>
          <span class="ura-confirm-risk">${escapeHtml(message.risk || 'MEDIUM')} risk</span>
        </div>`;
      }
      if (Array.isArray(message.memoryList)) {
        const items = message.memoryList;
        html += `<div class="ura-memory-list">
          ${items.length ? items.map((m) => `
            <div class="ura-memory-row">
              <span>${escapeHtml(m.content)}</span>
              <button type="button" data-forget-memory="${escapeHtml(m.memory_id)}" title="Forget this" aria-label="Forget this memory">✕</button>
            </div>`).join('') : '<div class="ura-card-meta">No saved memory.</div>'}
          <button class="ura-memory-link" type="button" data-open-memory>Refresh saved memory</button>
          ${items.length ? '<button class="ura-memory-link ura-memory-danger" type="button" data-forget-all>Forget all</button>' : ''}
        </div>`;
      }
      const deliverable = message.deliverable;
      if (deliverable) {
        html += `<div class="ura-card">
          <div class="ura-card-title">${escapeHtml(deliverable.title || 'Document')}</div>
          <div class="ura-card-meta">${escapeHtml((deliverable.format || 'file').toUpperCase())}${deliverable.size_bytes ? ` · ${(deliverable.size_bytes / 1024).toFixed(1)} KB` : ''}${deliverable.sha256 ? ` · SHA-256 ${escapeHtml(String(deliverable.sha256).slice(0, 12))}…` : ''}</div>
          ${deliverable.download_url ? `<div style="margin-top:6px;"><a href="${escapeHtml(deliverable.download_url)}" target="_blank" rel="noopener noreferrer" download>Download</a></div>` : ''}
        </div>`;
      }
      const action = message.actionCard;
      if (action) {
        if (action.type === 'MEETING_INVITE') {
          const confirmed = action.status === 'SCHEDULED' && action.provider_status === 'CONFIRMED';
          html += `<div class="ura-card">
            <div class="ura-card-title">${confirmed ? 'Meeting confirmed' : 'Meeting not scheduled'}</div>
            <div class="ura-card-meta">${escapeHtml(action.title || 'Meeting request')} · ${escapeHtml(action.provider_status || 'UNKNOWN')}</div>
            ${action.reason && !confirmed ? `<div class="ura-card-meta" style="margin-top:4px;">${escapeHtml(action.reason)}</div>` : ''}
            ${action.google_meet_url ? `<div style="margin-top:6px;"><a href="${escapeHtml(action.google_meet_url)}" target="_blank" rel="noopener noreferrer">Join</a></div>` : ''}
          </div>`;
        } else if (action.type === 'WORKFORCE_MISSION') {
          html += `<div class="ura-card">
            <div class="ura-card-title">Workforce delegation</div>
            <div class="ura-card-meta">${escapeHtml(action.department || 'Operations')} · ${escapeHtml(action.status || 'DELEGATED')} · ${escapeHtml(action.verification_status || 'UNVERIFIED')}</div>
            ${action.requires_approval && action.approval_id ? `<div style="margin-top:6px;display:flex;gap:6px;"><button class="ura-round ura-send" type="button" onclick="window.URAAssistant.decideApproval('${escapeHtml(action.approval_id)}', true)">Approve</button><button class="ura-round" type="button" onclick="window.URAAssistant.decideApproval('${escapeHtml(action.approval_id)}', false)">Decline</button></div>` : ''}
          </div>`;
        } else if (action.type === 'PERMISSION_REQUIRED') {
          html += `<div class="ura-card">
            <div class="ura-card-title">Company access is locked</div>
            <div class="ura-card-meta">An approved request with “URA Assistant” and “(kind: cowork)” is required.</div>
            <div class="ura-card-actions">
              <button class="ura-confirm-yes" type="button" id="uraAskPermission">Ask the AI CEO</button>
              <button class="ura-memory-link" type="button" onclick="window.navigateTo('/approvals')">Open approvals</button>
            </div>
          </div>`;
        }
      }
      if (Array.isArray(message.choices) && message.choices.length) {
        html += `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">${message.choices.map((c) => `<button class="ura-choice" type="button" onclick="window.URAAssistant.chooseScope('${escapeHtml(c.mode)}','${escapeHtml(c.label)}')"><span class="ura-chip">${escapeHtml(c.label)}</span></button>`).join('')}</div>`;
      }
      return html;
    }

    renderToolCard(card) {
      if (!card || !card.type) return '';
      const title = escapeHtml(card.title || card.label || 'Action');
      let body = '';
      if (card.type === 'NAVIGATE') {
        body = `<div class="ura-card-meta">${escapeHtml(card.label || card.path || '')}</div>
          <div class="ura-card-actions"><button class="ura-confirm-yes" type="button" onclick="window.navigateTo('${escapeHtml(card.path || '/overview')}')">Open</button></div>`;
      } else if (card.type === 'SEARCH_RESULTS') {
        body = `<div class="ura-card-meta">${(card.items || []).length} record(s)</div>
          <div class="ura-memory-list">${(card.items || []).map((item) => `
            <div class="ura-memory-row"><span>${escapeHtml(item.title || 'Record')}</span><span class="ura-card-meta">${escapeHtml(item.category || '')}</span></div>
          `).join('')}</div>`;
      } else if (card.type === 'COWORKER_TASK') {
        body = `<div class="ura-card-meta">${escapeHtml(card.status || 'DELEGATED')}${card.task_id ? ` · ${escapeHtml(card.task_id)}` : ''}</div>
          <div class="ura-card-actions"><button class="ura-confirm-yes" type="button" onclick="window.navigateTo('/coworker')">Open the Co-worker</button></div>`;
      } else if (card.type === 'APPROVAL_DECISION') {
        body = `<div class="ura-card-meta">${escapeHtml(card.request_id || '')} · ${escapeHtml(card.status || '')}</div>
          <div class="ura-card-actions"><button class="ura-memory-link" type="button" onclick="window.navigateTo('/approvals')">Open approvals</button></div>`;
      } else if (card.type === 'SETTING_CHANGED') {
        body = `<div class="ura-card-meta">${escapeHtml(card.key || '')} = ${escapeHtml(JSON.stringify(card.value))}</div>`;
      } else if (card.type === 'SECURITY_SCAN') {
        body = `<div class="ura-card-meta">${card.finding_count == null ? 'Findings were not reported.' : `${card.finding_count} finding(s)`}</div>
          <div class="ura-card-actions"><button class="ura-memory-link" type="button" onclick="window.navigateTo('/governance')">Open governance</button></div>`;
      } else if (card.type === 'REPORT_LIST') {
        body = `<div class="ura-card-meta">${card.count || 0} report(s)</div>
          <div class="ura-card-actions"><button class="ura-confirm-yes" type="button" onclick="window.navigateTo('/reports')">Open reports</button></div>`;
      } else if (card.type === 'REPORT_CREATED') {
        body = `<div class="ura-card-meta">${escapeHtml(card.report_id || '')} · ${escapeHtml(card.title || '')}</div>
          <div class="ura-card-actions"><button class="ura-confirm-yes" type="button" onclick="window.navigateTo('/reports')">Open reports</button></div>`;
      } else if (card.type === 'AGENT_BLUEPRINT') {
        body = `<div class="ura-card-meta">${escapeHtml(card.name || 'Blueprint prepared')} · not activated</div>
          <div class="ura-card-actions"><button class="ura-confirm-yes" type="button" onclick="window.navigateTo('/agent-factory')">Review in Agent Factory</button></div>`;
      } else if (card.type === 'INTEGRATION_HANDOFF' || card.type === 'TERMINAL_HANDOFF') {
        body = `<div class="ura-card-meta">${escapeHtml(card.provider || card.command || '')} · nothing connected automatically</div>
          <div class="ura-card-actions"><button class="ura-confirm-yes" type="button" onclick="window.navigateTo('${escapeHtml(card.path || '/integrations')}')">Open</button></div>`;
      } else if (card.type === 'WEB_SOURCES') {
        const sources = Array.isArray(card.sources) ? card.sources : [];
        const blocked = Array.isArray(card.blocked) ? card.blocked : [];
        body = `<div class="ura-card-meta">${sources.length} allowed source(s)${card.sample ? ' · sample data, not real pages' : ''}</div>
          <div class="ura-memory-list">${sources.map((source, index) => `
            <div class="ura-memory-row">
              <span>${index + 1}. <a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.label || source.url)}</a></span>
              <span class="ura-card-meta">${escapeHtml(source.sample ? 'sample' : (source.provider || 'web'))}</span>
            </div>
          `).join('')}</div>
          ${blocked.length ? `<div class="ura-card-meta">${blocked.length} source(s) excluded by the access policy.</div>` : ''}
          ${card.sample ? '<div class="ura-sample-note">Sample data. These are not pages fetched from the internet.</div>' : ''}`;
      } else if (card.type === 'WEB_ACCESS_OFF' || card.type === 'WEB_NOT_CONFIGURED' || card.type === 'WEB_SEARCH_FAILED' || card.type === 'WEB_NO_SOURCES') {
        body = `<div class="ura-card-meta">${escapeHtml((card.blocked || []).map((b) => b.reason).join(' ') || 'No source was read.')}</div>
          <div class="ura-card-actions"><button class="ura-memory-link" type="button" data-plus="web">Open web access</button></div>`;
      } else if (card.type === 'JOB_RESULT') {
        const result = (card.job && card.job.result) || {};
        body = `<div class="ura-card-meta">${escapeHtml(card.job ? this.jobStatusLabel(card.job.status) : '')}${result.summary ? ' · see the answer above' : ''}</div>
          <div class="ura-card-actions"><button class="ura-memory-link" type="button" data-jobs-panel>Job details</button></div>`;
      } else if (card.type === 'HANDOFF') {
        body = `<div class="ura-card-meta">${escapeHtml(card.label || 'Take over there')}</div>
          <div class="ura-card-actions"><button class="ura-confirm-yes" type="button" onclick="window.navigateTo('${escapeHtml(card.path || '/coworker')}')">Open</button></div>`;
      } else {
        body = `<div class="ura-card-meta">${escapeHtml(card.path || '')}</div>`;
      }
      return `<div class="ura-card ura-card-tool">
        <div class="ura-card-title">${title}</div>
        ${body}
      </div>`;
    }

    chooseScope(mode, label) {
      this.setScope(mode === 'COMPANY' ? 'COMPANY' : 'PERSONAL');
      if (this.lastPrompt) this.send(this.lastPrompt);
      else if (label) this.send(label);
    }

    async forgetAllMemories() {
      try {
        const res = await fetch(`/api/assistant/memory?scope=${encodeURIComponent(this.scope)}`, { method: 'DELETE' });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        this.messages = this.messages.map((m) => (m.memoryList ? { ...m, memoryList: [] } : m));
        this.save();
        this.renderMessages();
        this.addToolStep(`Forgot ${data.removed || 0} memory item(s)`);
      } catch (err) {
        this.addMessage('assistant', `I could not clear saved memory: ${err.message}.`);
      }
    }

    async decideApproval(approvalId, approved) {
      try {
        const res = await fetch(`/api/approvals/${encodeURIComponent(approvalId)}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved: Boolean(approved) })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        this.addToolStep(approved ? 'Approved the request' : 'Declined the request');
        this.addMessage('assistant', `The approval decision was recorded: ${approved ? 'approved' : 'declined'}.`);
      } catch (err) {
        this.addMessage('assistant', `I could not record that decision: ${err.message}. Nothing changed.`);
      }
    }

    // ------------------------------------------------------------------ jobs
    jobsBadgeCount() {
      const terminal = ['SUCCEEDED', 'FAILED'];
      return this.jobs.filter((job) => {
        const status = String(job.status || '').toUpperCase();
        if (['QUEUED', 'RUNNING', 'PAUSED'].includes(status)) return true;
        return terminal.includes(status) && !job.notification_seen;
      }).length;
    }

    startJobsPolling() {
      if (window.__URA_NO_POLL__ || this.jobPollTimer) return;
      this.refreshJobs();
      this.jobPollTimer = window.setInterval(() => this.refreshJobs(), 6000);
    }

    stopJobsPolling() {
      if (this.jobPollTimer) {
        clearInterval(this.jobPollTimer);
        this.jobPollTimer = null;
      }
    }

    async refreshJobs() {
      try {
        const res = await fetch('/api/assistant/jobs?status=all');
        if (!res.ok) return;
        const data = await res.json();
        this.jobs = Array.isArray(data.jobs) ? data.jobs : [];
        this.jobLimit = data.limit || 3;
        this.jobActive = data.active || 0;
        this.updateJobsBadge();
        if (this.jobsOpen) this.renderJobs();
      } catch (err) { /* offline: keep the last known list */ }
    }

    updateJobsBadge() {
      const count = this.jobsBadgeCount();
      ['uraJobsBadge', 'uraBadge'].forEach((id) => {
        const badge = document.getElementById(id);
        if (!badge) return;
        badge.hidden = !count;
        badge.textContent = String(count);
      });
      const plusCount = document.getElementById('uraPlusJobsCount');
      if (plusCount) plusCount.textContent = count ? `(${count})` : '';
    }

    openJobs() {
      this.jobsOpen = true;
      this.webOpen = false;
      const jobsPanel = document.getElementById('uraJobsPanel');
      const webPanel = document.getElementById('uraWebPanel');
      if (jobsPanel) jobsPanel.hidden = false;
      if (webPanel) webPanel.hidden = true;
      this.renderJobs();
      this.refreshJobs();
    }

    closeJobs() {
      this.jobsOpen = false;
      const panel = document.getElementById('uraJobsPanel');
      if (panel) panel.hidden = true;
    }

    jobStatusLabel(status) {
      const map = {
        QUEUED: 'Queued', RUNNING: 'Running', PAUSED: 'Paused',
        SUCCEEDED: 'Done', FAILED: 'Failed', CANCELLED: 'Stopped'
      };
      return map[String(status || '').toUpperCase()] || String(status || 'Unknown');
    }

    renderJobs() {
      const box = document.getElementById('uraJobsList');
      if (!box) return;
      const limit = this.jobLimit || 3;
      const limitEl = document.getElementById('uraJobsLimit');
      if (limitEl) limitEl.textContent = `${this.jobActive || 0} of ${limit} active`;
      if (!this.jobs.length) {
        box.innerHTML = '<div class="ura-card-meta">No jobs yet. Ask something, then choose “Run in background”. Up to three jobs run at once and they survive a reload.</div>';
        return;
      }
      box.innerHTML = this.jobs.map((job) => this.renderJob(job)).join('');
    }

    renderJob(job) {
      const status = String(job.status || '').toUpperCase();
      const terminal = ['SUCCEEDED', 'FAILED', 'CANCELLED'].includes(status);
      const progress = Math.max(0, Math.min(100, Number(job.progress) || 0));
      const steps = Array.isArray(job.steps) ? job.steps.slice(-4) : [];
      const busy = ['QUEUED', 'RUNNING', 'PAUSED'].includes(status);
      const id = escapeHtml(job.job_id);
      const actions = [];
      if (this.watchingJobId === job.job_id) actions.push('<span class="ura-card-meta">Watching…</span>');
      if (status === 'RUNNING') actions.push(`<button class="ura-memory-link" type="button" data-job-action="pause" data-job-id="${id}">Pause</button>`);
      if (status === 'PAUSED') actions.push(`<button class="ura-memory-link" type="button" data-job-action="resume" data-job-id="${id}">Resume</button>`);
      if (busy) {
        actions.push(`<button class="ura-memory-link" type="button" data-watch-job="${id}">Watch me</button>`);
        actions.push(`<button class="ura-memory-link" type="button" data-job-action="takeover" data-job-id="${id}">Take over</button>`);
        actions.push(`<button class="ura-memory-link ura-memory-danger" type="button" data-job-action="cancel" data-job-id="${id}">Stop</button>`);
      }
      if (terminal) {
        if (job.result || job.error) actions.push(`<button class="ura-memory-link" type="button" data-open-job="${id}">Open result</button>`);
        if (status !== 'SUCCEEDED') actions.push(`<button class="ura-memory-link" type="button" data-job-action="retry" data-job-id="${id}">Retry</button>`);
      }
      return `<div class="ura-job" data-status="${escapeHtml(status)}">
        <div class="ura-job-head">
          <span class="ura-job-title">${escapeHtml(job.title || job.prompt || 'Job')}</span>
          <span class="ura-job-status" data-status="${escapeHtml(status)}">${escapeHtml(this.jobStatusLabel(status))}</span>
        </div>
        <div class="ura-job-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress}"><span style="width:${progress}%"></span></div>
        <div class="ura-card-meta">${escapeHtml(job.step || '')}${job.kind ? ` · ${escapeHtml(job.kind)}` : ''}</div>
        ${steps.length ? `<div class="ura-job-steps">${steps.map((s) => `<div>${escapeHtml(s.label || '')}</div>`).join('')}</div>` : ''}
        ${job.error ? `<div class="ura-card-meta ura-job-error">${escapeHtml(job.error)}</div>` : ''}
        <div class="ura-card-actions">${actions.join('')}</div>
      </div>`;
    }

    async jobRequest(jobId, action) {
      if (!jobId || !action) return;
      try {
        const res = await fetch(`/api/assistant/jobs/${encodeURIComponent(jobId)}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.success === false) throw new Error(data.error || `HTTP ${res.status}`);
        if (data.handoff) {
          this.addMessage('assistant', data.handoff.message || 'The job is paused. Take over there.', {
            card: { type: 'HANDOFF', path: data.handoff.path, label: data.handoff.label }
          });
          if (data.handoff.path && window.navigateTo) window.navigateTo(data.handoff.path);
        } else {
          this.addToolStep(`Job ${action}`);
        }
        await this.refreshJobs();
      } catch (err) {
        this.addMessage('assistant', `That job action failed: ${err.message}. Nothing changed.`);
      }
    }

    async startBackground(prompt) {
      const input = document.getElementById('uraInput');
      let text = (prompt != null ? prompt : (input ? input.value : '')).trim();
      if (input) { input.value = ''; input.style.height = 'auto'; }
      if (!text) {
        const lastUser = [...this.messages].reverse().find((m) => m.sender === 'user');
        if (lastUser) text = lastUser.text;
      }
      if (!text) {
        this.addMessage('assistant', 'Tell me what to work on first — type it, then choose “Run in background”.');
        return;
      }
      if (this.scope === 'COMPANY' && !this.companyGranted) {
        this.renderPermissionBanner();
        this.addMessage('assistant', 'Company scope is locked until the AI CEO approves access. Nothing was started.');
        return;
      }
      try {
        const res = await fetch('/api/assistant/jobs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: text,
            workspace_mode: this.scope,
            company_id: this.scope === 'COMPANY' ? this.getCompanyId() : null,
            session_id: this.sessionId
          })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.success === false) throw new Error(data.error || `HTTP ${res.status}`);
        const job = data.job || {};
        this.openJobs();
        this.addToolStep('Started a background job');
        this.addMessage('assistant', `I started “${job.title || text}” in the background. It keeps running if you close the window; open Jobs to watch, pause or stop it.`);
        await this.refreshJobs();
      } catch (err) {
        this.addMessage('assistant', `I could not start that job: ${err.message}. Nothing was started.`);
      }
    }

    researchLast() {
      const input = document.getElementById('uraInput');
      let text = (input ? input.value : '').trim();
      if (input) { input.value = ''; input.style.height = 'auto'; }
      if (!text) {
        const lastUser = [...this.messages].reverse().find((m) => m.sender === 'user');
        text = lastUser ? lastUser.text : '';
      }
      if (!text) {
        this.addMessage('assistant', 'Tell me what to research first. Web access must be on in Assistant → Web access.');
        return;
      }
      this.send(`research ${text}`);
    }

    async watchJob(jobId) {
      if (!jobId) return;
      this.watchingJobId = jobId;
      this.openJobs();
      try {
        const res = await fetch(`/api/assistant/jobs/${encodeURIComponent(jobId)}/watch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: '{}'
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error || `HTTP ${res.status}`);
        }
        if (!res.body || !res.body.getReader) {
          const text = await res.text();
          text.split('\n').filter(Boolean).forEach((line) => {
            try { this.handleJobEvent(JSON.parse(line)); } catch (err) { /* skip partial line */ }
          });
        } else {
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
              if (!line.trim()) continue;
              try { this.handleJobEvent(JSON.parse(line)); } catch (err) { /* skip */ }
            }
          }
        }
      } catch (err) {
        this.addMessage('assistant', `I could not watch that job: ${err.message}.`);
      } finally {
        this.watchingJobId = null;
        await this.refreshJobs();
      }
    }

    handleJobEvent(event) {
      if (!event) return;
      if (event.type === 'job' || event.type === 'job_done') {
        const job = event.job;
        if (!job) return;
        const index = this.jobs.findIndex((j) => j.job_id === job.job_id);
        if (index >= 0) this.jobs[index] = job;
        else this.jobs.unshift(job);
        this.renderJobs();
        this.updateJobsBadge();
      }
      if (event.type === 'error') this.addMessage('assistant', event.message || 'The watch session ended.');
      if (event.type === 'job_done' && event.job) this.showJobResult(event.job.job_id);
    }

    showJobResult(jobId) {
      const job = this.jobs.find((j) => j.job_id === jobId);
      if (!job) return;
      const status = String(job.status || '').toUpperCase();
      if (status === 'FAILED') {
        this.addMessage('assistant', `Job “${job.title || jobId}” failed: ${job.error || 'no reason was recorded.'}`, {
          card: { type: 'JOB_RESULT', job }
        });
        return;
      }
      if (status === 'CANCELLED') {
        this.addMessage('assistant', `Job “${job.title || jobId}” was stopped.`, {
          card: { type: 'JOB_RESULT', job }
        });
        return;
      }
      const result = job.result || {};
      this.addMessage('assistant', result.summary || 'The job finished but recorded no summary.', {
        citations: Array.isArray(job.citations) ? job.citations : [],
        card: { type: 'JOB_RESULT', job }
      });
    }

    async markJobsSeen() {
      try {
        await fetch('/api/assistant/jobs/inbox/seen', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
        });
        this.jobs = this.jobs.map((job) => ({ ...job, notification_seen: 1 }));
        this.updateJobsBadge();
        this.renderJobs();
      } catch (err) { /* notifications are non-critical */ }
    }

    // ------------------------------------------------------------ web access
    async openWebAccess() {
      this.jobsOpen = false;
      this.webOpen = true;
      const jobsPanel = document.getElementById('uraJobsPanel');
      const webPanel = document.getElementById('uraWebPanel');
      if (jobsPanel) jobsPanel.hidden = true;
      if (webPanel) webPanel.hidden = false;
      const body = document.getElementById('uraWebBody');
      if (body) body.textContent = 'Loading…';
      try {
        const res = await fetch('/api/assistant/web-access');
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        this.renderWebAccess(data);
      } catch (err) {
        if (body) body.innerHTML = `<div class="ura-card-meta">Could not read web access: ${escapeHtml(err.message)}</div>`;
      }
    }

    closeWebAccess() {
      this.webOpen = false;
      const panel = document.getElementById('uraWebPanel');
      if (panel) panel.hidden = true;
    }

    renderWebAccess(data) {
      const body = document.getElementById('uraWebBody');
      if (!body) return;
      const access = data.access || {};
      const mode = access.mode || 'off';
      const providerNote = data.configured
        ? `${escapeHtml(data.provider_label || data.provider)}${data.sample_provider ? ' · sample data, not real pages' : ''}`
        : 'No web search provider is configured on the server.';
      body.innerHTML = `
        <label class="ura-field"><span>Web access</span>
          <select id="uraWebMode">
            <option value="off"${mode === 'off' ? ' selected' : ''}>Off — never read the web</option>
            <option value="allowlist"${mode === 'allowlist' ? ' selected' : ''}>Allow list — only these domains</option>
            <option value="open"${mode === 'open' ? ' selected' : ''}>Open — any domain except the block list</option>
          </select>
        </label>
        <label class="ura-field"><span>Allow list (comma-separated domains)</span>
          <textarea id="uraWebAllow" rows="2">${escapeHtml((access.allowlist || []).join(', '))}</textarea>
        </label>
        <label class="ura-field"><span>Block list (comma-separated domains)</span>
          <textarea id="uraWebBlock" rows="2">${escapeHtml((access.blocklist || []).join(', '))}</textarea>
        </label>
        <div class="ura-card-meta">${providerNote}</div>
        ${data.sample_provider ? '<div class="ura-sample-note">Sample provider is on. Results are labelled sample and are not real sources.</div>' : ''}
        <div class="ura-card-actions"><button class="ura-confirm-yes" type="button" data-web-save>Save</button></div>
      `;
    }

    async saveWebAccess() {
      const mode = document.getElementById('uraWebMode') ? document.getElementById('uraWebMode').value : 'off';
      const allowlist = document.getElementById('uraWebAllow') ? document.getElementById('uraWebAllow').value : '';
      const blocklist = document.getElementById('uraWebBlock') ? document.getElementById('uraWebBlock').value : '';
      const companyId = this.getCompanyId();
      if (!companyId) {
        this.addMessage('assistant', 'Web access is a company setting. Onboard a company or select one first.');
        return;
      }
      try {
        const res = await fetch('/api/assistant/web-access', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access: mode, allowlist, blocklist, company_id: companyId })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.success === false) throw new Error(data.error || `HTTP ${res.status}`);
        this.renderWebAccess(data.web_access || {});
        this.addToolStep('Saved web access');
        this.addMessage('assistant', `Web access is now “${mode}”. Research uses only sources allowed by these lists.`);
      } catch (err) {
        this.addMessage('assistant', `I could not save web access: ${err.message}. Nothing changed.`);
      }
    }

    clearConversation() {
      this.messages = [];
      this.pendingConfirmations = [];
      this.streamState = null;
      this.sessionId = `ura_${Math.random().toString(36).slice(2, 10)}`;
      this.save();
      this.renderMessages();
      this.addToolStep('Cleared this conversation');
    }

    // ------------------------------------------------------------------ send
    onComposerKey(event) {
      const input = event.target;
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        this.send();
      } else if (event.key === 'ArrowUp' && !input.value.trim()) {
        const lastUser = [...this.messages].reverse().find((m) => m.sender === 'user');
        if (lastUser) {
          event.preventDefault();
          input.value = lastUser.text;
          this.autoResize(input);
          input.setSelectionRange(input.value.length, input.value.length);
        }
      }
    }

    autoResize(input) {
      input.style.height = 'auto';
      input.style.height = `${Math.min(110, input.scrollHeight)}px`;
    }

    setLauncherState(state, count = 0) {
      if (!this.launcher) return;
      this.launcher.dataset.state = state;
      if (count > 0) {
        const badge = document.getElementById('uraBadge');
        if (badge) {
          badge.hidden = false;
          badge.textContent = String(count);
        }
      }
      const dot = document.getElementById('uraDot');
      if (dot) dot.hidden = state !== 'needs-you';
    }

    pageContext() {
      const page = this.currentPage();
      return {
        page,
        path: (window.location && window.location.hash) ? window.location.hash.slice(1) : `/${page}`,
      };
    }

    setAgentChip(role, label) {
      this.agentRole = role || null;
      const chip = document.getElementById('uraAgentChip');
      if (!chip) return;
      if (role && label) {
        chip.hidden = false;
        chip.textContent = `→ ${label}`;
        chip.title = `Routing to the ${label}`;
      } else {
        chip.hidden = true;
        chip.textContent = '';
      }
    }

    async send(text) {
      const input = document.getElementById('uraInput');
      const prompt = (text != null ? text : (input ? input.value : '')).trim();
      if (!prompt || this.busy) return;
      if (this.scope === 'COMPANY' && !this.companyGranted) {
        this.renderPermissionBanner();
        this.addMessage('assistant', 'Company scope is locked until the AI CEO approves access. Use “Ask the CEO” in the banner, or switch to Personal. Nothing was sent to company data.');
        return;
      }
      this.lastPrompt = prompt;
      if (input) { input.value = ''; input.style.height = 'auto'; }
      this.addMessage('user', prompt);
      this.busy = true;
      let failed = false;
      this.setLauncherState('working');
      this.addToolStep('Reading your request', true);
      this.pendingToolRow = this.messages.length - 1;

      const body = {
        prompt,
        workspace_mode: this.scope,
        company_id: this.scope === 'COMPANY' ? this.getCompanyId() : null,
        session_id: this.sessionId,
        page_context: this.pageContext(),
        attachments: this.pendingAttachments
      };

      try {
        const handled = await this.streamReply(body);
        if (!handled) {
          // Older server: fall back to the single-response contract.
          const data = await this.postInteract(body);
          this.pendingAttachments = [];
          const generic = this.pendingToolRow != null ? this.messages[this.pendingToolRow] : null;
          if (generic && generic.sender === 'tool' && generic.working) {
            generic.text = 'Checked live app data';
            generic.working = false;
            this.renderMessages();
          } else {
            this.addToolStep('Checked live app data');
          }
          this.addMessage('assistant', data.reply || 'The assistant returned no answer. Nothing was changed.', {
            deliverable: data.deliverable_card || null,
            actionCard: data.action_card || null,
            choices: data.choices || null,
            citations: data.citations || []
          });
        }
        this.pendingAttachments = [];
        this.checkCompanyPermission();
      } catch (err) {
        failed = true;
        this.addToolStep('Request failed', false);
        this.addMessage('assistant', `I could not answer: ${err.message}. Nothing was executed.`);
        this.setLauncherState('needs-you');
      } finally {
        this.busy = false;
        if (!failed) {
          this.setLauncherState('idle');
          setTimeout(() => {
            if (this.launcher && this.launcher.dataset.state !== 'needs-you') this.setLauncherState('idle');
          }, 1200);
        }
      }
    }

    async postInteract(body) {
      const res = await fetch('/api/assistant/interact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      return data;
    }

    /**
     * Consume the NDJSON assistant stream.
     * Returns false when the server does not expose the stream endpoint so the
     * caller can fall back to the single response endpoint.
     */
    async streamReply(body) {
      const res = await fetch('/api/assistant/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/x-ndjson' },
        body: JSON.stringify(body)
      });
      if (res.status === 404 || res.status === 405) return false;
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      this.streamState = { message: null, toolIndex: null };
      if (!res.body || !res.body.getReader) {
        const text = await res.text();
        this.consumeLines(text.split('\n'));
        this.finishStream();
        return true;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        this.consumeLines(lines);
      }
      buffer += decoder.decode();
      if (buffer.trim()) this.consumeLines([buffer]);
      this.finishStream();
      return true;
    }

    consumeLines(lines) {
      for (const raw of lines) {
        const line = (raw || '').trim();
        if (!line) continue;
        let event;
        try { event = JSON.parse(line); } catch (err) { continue; }
        this.handleStreamEvent(event);
      }
    }

    handleStreamEvent(event) {
      if (!event || !event.type) return;
      if (event.type === 'context') {
        const ctx = event.context || {};
        if (ctx.agent) this.setAgentChip(ctx.agent, ctx.agent_label);
        else this.setAgentChip(null, null);
        if (ctx.page) {
          const chip = document.getElementById('uraContextChip');
          const label = PAGE_LABELS[ctx.page] || String(ctx.page);
          if (chip) chip.innerHTML = `Looking at <b>${escapeHtml(label)}</b>`;
        }
        if (ctx.company_name) {
          const companyChip = document.getElementById('uraCompanyChip');
          if (companyChip) { companyChip.hidden = false; companyChip.textContent = ctx.company_name; }
        }
        return;
      }
      if (event.type === 'agent') {
        this.setAgentChip(event.role, event.label);
        this.addToolStep(`Routing to the ${event.label}`);
        return;
      }
      if (event.type === 'tool') {
        const label = event.label || event.tool || 'Working';
        if (event.status === 'running') {
          const generic = this.pendingToolRow != null ? this.messages[this.pendingToolRow] : null;
          if (generic && generic.sender === 'tool' && generic.working && !generic.toolName) {
            generic.text = label;
            generic.toolName = event.tool;
            this.streamState.toolIndex = this.pendingToolRow;
            this.renderMessages();
          } else {
            this.streamState.toolIndex = this.messages.length;
            this.addToolStep(label, true);
            this.messages[this.streamState.toolIndex].toolName = event.tool;
          }
        } else {
          const index = this.streamState.toolIndex;
          const existing = index != null ? this.messages[index] : null;
          if (existing && existing.sender === 'tool') {
            existing.text = label;
            existing.working = false;
            existing.ok = event.ok !== false;
            this.renderMessages();
          } else {
            this.addToolStep(label, false);
          }
        }
        return;
      }
      if (event.type === 'permission') {
        this.showPermissionState(event);
        return;
      }
      if (event.type === 'confirm') {
        this.addConfirmation(event);
        return;
      }
      if (event.type === 'answer') {
        this.appendAnswer(event.delta || '');
        return;
      }
      if (event.type === 'card') {
        this.attachCard(event.card);
        return;
      }
      if (event.type === 'error') {
        this.addMessage('assistant', event.message || 'The assistant stream failed. Nothing was executed.');
        return;
      }
      if (event.type === 'done') {
        if (this.streamState && this.streamState.message) {
          this.streamState.message.citations = event.citations || this.streamState.message.citations || [];
          this.streamState.message.agent = event.agent || null;
          this.save();
          this.renderMessages();
        }
      }
    }

    showPermissionState(event) {
      this.renderPermissionBanner();
      if (event.state === 'NO_COMPANY') {
        this.addMessage('assistant', event.message || 'Company scope needs a selected company.');
        return;
      }
      this.addToolStep('Company scope is locked');
      this.addMessage('assistant', event.message || 'Company access is not approved yet. Nothing was read.', {
        actionCard: { type: 'PERMISSION_REQUIRED', company_id: event.company_id || null }
      });
    }

    addConfirmation(event) {
      this.pendingConfirmations = this.pendingConfirmations || [];
      const index = this.pendingConfirmations.length;
      this.pendingConfirmations.push({
        tool: event.tool,
        arguments: event.arguments || {},
        preview: event.preview || ''
      });
      this.addMessage('assistant', event.preview || 'This action needs your confirmation.', {
        confirmationIndex: index,
        risk: event.risk || 'MEDIUM'
      });
    }

    appendAnswer(delta) {
      if (!this.streamState) this.streamState = { message: null, toolIndex: null };
      if (!this.streamState.message) {
        this.streamState.message = this.addMessage('assistant', '', { streaming: true });
        this.streamState.message = this.messages[this.messages.length - 1];
      }
      this.streamState.message.text += delta;
      this.renderMessages();
    }

    attachCard(card) {
      if (!card) return;
      if (this.streamState && this.streamState.message) {
        this.streamState.message.card = card;
      } else {
        this.addMessage('assistant', '', { card });
      }
      this.save();
      this.renderMessages();
    }

    finishStream() {
      if (this.streamState && this.streamState.message) {
        this.streamState.message.streaming = false;
      }
      if (this.pendingToolRow != null) {
        const generic = this.messages[this.pendingToolRow];
        if (generic && generic.sender === 'tool' && generic.working) {
          generic.working = false;
          generic.text = generic.toolName ? generic.text : 'Checked the request';
        }
      }
      this.streamState = null;
      this.pendingToolRow = null;
      this.save();
      this.renderMessages();
    }

    async confirmTool(index) {
      const pending = (this.pendingConfirmations || [])[index];
      if (!pending) return;
      this.addToolStep(`Confirmed: ${pending.preview || pending.tool}`, true);
      try {
        const res = await fetch('/api/assistant/tool', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: pending.tool,
            arguments: pending.arguments,
            workspace_mode: this.scope,
            company_id: this.scope === 'COMPANY' ? this.getCompanyId() : null
          })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
          throw new Error((data.result && data.result.summary) || data.error || `HTTP ${res.status}`);
        }
        const result = data.result || {};
        this.addToolStep(result.summary || 'Action completed', false);
        this.addMessage('assistant', result.summary || 'Action completed.', { card: result.card || null });
      } catch (err) {
        this.addMessage('assistant', `The action did not complete: ${err.message}. Nothing changed.`);
      }
    }

    // ---------------------------------------------------------------- memory
    async rememberLast() {
      const lastUser = [...this.messages].reverse().find((m) => m.sender === 'user');
      if (!lastUser) {
        this.addMessage('assistant', 'There is nothing to remember yet. Ask or tell me something first.');
        return;
      }
      const content = lastUser.text;
      try {
        const res = await fetch('/api/assistant/memory', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, scope: this.scope, session_id: this.sessionId })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) throw new Error(data.error || `HTTP ${res.status}`);
        this.addToolStep('Saved to memory');
        this.addMessage('assistant', `I will remember: “${content}”.`);
      } catch (err) {
        this.addMessage('assistant', `I could not save that memory: ${err.message}. Nothing was stored.`);
      }
    }

    async openMemory() {
      try {
        const res = await fetch(`/api/assistant/memory?scope=${encodeURIComponent(this.scope)}`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        const memories = data.memories || [];
        this.addMessage('assistant', memories.length
          ? `I am holding ${memories.length} saved ${this.scope.toLowerCase()} memory item(s).`
          : 'I am not holding any saved memory for this scope yet.', {
          memoryList: memories,
          memoryScope: this.scope
        });
      } catch (err) {
        this.addMessage('assistant', `I could not read saved memory: ${err.message}.`);
      }
    }

    async forgetMemory(memoryId) {
      try {
        const res = await fetch(`/api/assistant/memory/${encodeURIComponent(memoryId)}`, { method: 'DELETE' });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        this.messages = this.messages.map((m) => (
          m.memoryList ? { ...m, memoryList: m.memoryList.filter((x) => x.memory_id !== memoryId) } : m
        ));
        this.save();
        this.renderMessages();
        this.addToolStep('Forgot one memory item');
      } catch (err) {
        this.addMessage('assistant', `I could not forget that memory: ${err.message}.`);
      }
    }

    // ------------------------------------------------------------ attachments
    uploadFiles(event) {
      const files = event.target.files;
      if (!files || !files.length) return;
      const file = files[0];
      if (this.pendingAttachments.length >= MAX_ATTACHMENTS) {
        this.addMessage('assistant', `You can attach at most ${MAX_ATTACHMENTS} documents at a time.`);
        event.target.value = '';
        return;
      }
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const res = await fetch('/api/assistant/documents/upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              filename: file.name,
              content_base64: String(reader.result || ''),
              storage_boundary: this.scope === 'COMPANY' ? 'COMPANY' : 'PERSONAL'
            })
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || !data.document) throw new Error(data.error || `upload failed (HTTP ${res.status})`);
          this.pendingAttachments.push({
            doc_id: data.document.doc_id,
            name: data.document.name || file.name,
            size: data.document.size_bytes || file.size,
            storage_boundary: data.document.storage_boundary
          });
          this.addToolStep(`Attached ${data.document.name || file.name}`);
        } catch (err) {
          this.addMessage('assistant', `“${file.name}” was not uploaded, so it is not attached. Nothing was stored. (${err.message})`);
        }
        event.target.value = '';
      };
      reader.readAsDataURL(file);
    }

    observeScreen() {
      this.addMessage('assistant', 'Screen observation is not connected in this build. No screenshot was taken, nothing was sealed, and no company system was contacted. Connecting a host screen agent requires explicit device permission.');
    }

    async emergencyStop() {
      if (!window.confirm('Engage the emergency stop? This freezes company missions at the configured level.')) return;
      try {
        const res = await fetch('/api/assistant/emergency-stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'Emergency stop engaged by the owner in URA Assistant' })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) throw new Error(data.error || `HTTP ${res.status}`);
        this.addToolStep('Emergency stop engaged');
        this.addMessage('assistant', `Emergency stop engaged. Switch: \`${data.switch_id || 'unknown'}\`. ${data.message || ''}`.trim());
      } catch (err) {
        this.addMessage('assistant', `The emergency stop was not engaged: ${err.message}. Nothing changed.`);
      }
    }

    dictate() {
      const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!Recognition) {
        this.addMessage('assistant', 'Dictation is not available in this browser. You can still type the message.');
        return;
      }
      const recognition = new Recognition();
      recognition.lang = document.documentElement.lang || 'en-US';
      recognition.interimResults = false;
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const input = document.getElementById('uraInput');
        if (input) { input.value = transcript; this.autoResize(input); input.focus(); }
      };
      recognition.onerror = () => this.addMessage('assistant', 'Dictation stopped before a transcript was produced. Nothing was sent.');
      recognition.start();
    }
  }

  window.URAAssistant = new URAAssistantController();
  window.URA = window.URAAssistant;
})();
