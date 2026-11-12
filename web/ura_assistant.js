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
              <button type="button" data-plus="clear">🗑️ Clear this conversation</button>
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
        ? `<div class="ura-citations">${message.citations.map((c) => `<span>${escapeHtml(c.label || c.source_type || 'Source')}</span>`).join('')}</div>`
        : '';
      return `
        <div class="ura-msg ${mine ? 'user' : 'assistant'}">
          <div class="ura-body">${mine ? escapeHtml(message.text) : formatText(message.text || '')}${this.renderExtra(message)}</div>
          ${citations}
          <div class="ura-meta">${mine ? 'You' : 'URA'} · ${time}</div>
        </div>
      `;
    }

    renderExtra(message) {
      let html = '';
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
        }
      }
      if (Array.isArray(message.choices) && message.choices.length) {
        html += `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">${message.choices.map((c) => `<button class="ura-choice" type="button" onclick="window.URAAssistant.chooseScope('${escapeHtml(c.mode)}','${escapeHtml(c.label)}')"><span class="ura-chip">${escapeHtml(c.label)}</span></button>`).join('')}</div>`;
      }
      return html;
    }

    chooseScope(mode, label) {
      this.setScope(mode === 'COMPANY' ? 'COMPANY' : 'PERSONAL');
      if (this.lastPrompt) this.send(this.lastPrompt);
      else if (label) this.send(label);
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

    clearConversation() {
      this.messages = [];
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
      const badge = document.getElementById('uraBadge');
      if (badge) {
        badge.hidden = !count;
        badge.textContent = String(count);
      }
      const dot = document.getElementById('uraDot');
      if (dot) dot.hidden = state !== 'needs-you';
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

      try {
        const companyId = this.getCompanyId();
        const res = await fetch('/api/assistant/interact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt,
            workspace_mode: this.scope,
            company_id: this.scope === 'COMPANY' ? companyId : null,
            session_id: this.sessionId,
            attachments: this.pendingAttachments
          })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        this.pendingAttachments = [];
        this.addToolStep('Checked live app data');
        this.addMessage('assistant', data.reply || 'The assistant returned no answer. Nothing was changed.', {
          deliverable: data.deliverable_card || null,
          actionCard: data.action_card || null,
          choices: data.choices || null,
          citations: data.citations || []
        });
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
