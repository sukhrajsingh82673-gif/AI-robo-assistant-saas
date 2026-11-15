/**
 * ZONATA — Protected company deletion
 *
 * A five-step sheet that is deliberately slower than a single "Delete" button:
 *
 *   1. what happens, with real counts from the server;
 *   2. the exact company name, typed again;
 *   3. the signed-in password (and a two-step code when one is configured);
 *   4. the export: generated first, emailed if delivery is configured,
 *      otherwise downloaded here;
 *   5. the recovery window, where the owner can still cancel.
 *
 * The server owns every rule. This module never invents a state, never treats a
 * failed export as success, and never claims an email was sent when SMTP is not
 * configured. When the deployment has no two-step verifier it says so instead
 * of bypassing the requirement.
 *
 * Phone: bottom sheet. Desktop: centred dialog. Keyboard and screen readers get
 * the same flow: role=dialog, focus trap, Escape, visible focus, labelled
 * fields and live status text.
 */

(function() {
  'use strict';

  const STEP_ORDER = ['what', 'name', 'identity', 'export', 'recovery'];

  function t(key, vars) {
    if (window.I18n && typeof window.I18n.t === 'function') return window.I18n.t(key, vars);
    return String(key || '');
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function language() {
    return (window.I18n && window.I18n.getLanguage && window.I18n.getLanguage()) || 'en';
  }

  function locale() {
    return language() === 'ar' ? 'ar-IN' : 'en-IN';
  }

  function formatTime(seconds) {
    if (!seconds) return '';
    try {
      return new Intl.DateTimeFormat(locale(), {
        day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
      }).format(new Date(Number(seconds) * 1000));
    } catch (err) {
      return '';
    }
  }

  function formatSize(bytes) {
    const value = Number(bytes || 0);
    if (!value) return '';
    if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    if (value >= 1024) return `${Math.round(value / 1024)} KB`;
    return `${value} B`;
  }

  function countdown(purgeAfter) {
    const target = Number(purgeAfter || 0);
    if (!target) return '';
    const remaining = target - Math.floor(Date.now() / 1000);
    if (remaining <= 0) return t('company.delete.window.due');
    const days = Math.floor(remaining / 86400);
    const hours = Math.max(0, Math.floor((remaining % 86400) / 3600));
    if (days > 0) return t('company.delete.window.remaining_days', { days, hours });
    return t('company.delete.window.remaining_hours', { hours });
  }

  function statusText(deletion) {
    const status = String((deletion && deletion.status) || '').toLowerCase();
    const key = `company.delete.status.${status}`;
    const label = t(key);
    return label === key ? String((deletion && deletion.status) || '') : label;
  }

  class CompanySetupDelete {
    constructor() {
      this.root = null;
      this.containerId = null;
      this.companyId = null;
      this.company = null;
      this.plan = null;
      this.deletion = null;
      this.step = 'what';
      this.loading = true;
      this.busy = false;
      this.error = null;
      this.notice = null;
      this.nameInput = '';
      this.password = '';
      this.twoStep = '';
      this.completed = false;
      this.cancelled = false;
      this.cancelledStatus = '';
      this.startAt = null;
      this.onDone = null;
      this._previousFocus = null;
      this._keydown = this._keydown.bind(this);
      this._onLanguageChange = this._onLanguageChange.bind(this);
    }

    open(options) {
      const opts = options || {};
      if (!opts.companyId) return;
      this.close(false);
      this.companyId = String(opts.companyId);
      this.containerId = opts.containerId || null;
      this.companyName = opts.companyName || '';
      this.startAt = opts.startAt || null;
      this.onDone = typeof opts.onDone === 'function' ? opts.onDone : null;
      this.company = null;
      this.plan = null;
      this.deletion = null;
      this.step = 'what';
      this.loading = true;
      this.busy = false;
      this.error = null;
      this.notice = null;
      this.nameInput = '';
      this.password = '';
      this.twoStep = '';
      this.completed = false;
      this.cancelled = false;
      this.cancelledStatus = '';
      this._previousFocus = document.activeElement;
      this._mount();
      this._render();
      if (document && document.addEventListener) {
        document.addEventListener('zonata:languagechange', this._onLanguageChange);
      }
      this._load();
    }

    close(notify) {
      if (document && document.removeEventListener) {
        document.removeEventListener('keydown', this._keydown, true);
        document.removeEventListener('zonata:languagechange', this._onLanguageChange);
      }
      if (this.root && this.root.parentNode) this.root.parentNode.removeChild(this.root);
      this.root = null;
      if (this._previousFocus && this._previousFocus.focus) {
        try { this._previousFocus.focus(); } catch (err) { /* removed node */ }
      }
      this._previousFocus = null;
      const callback = this.onDone;
      this.onDone = null;
      if (notify !== false && callback) callback();
    }

    _mount() {
      const root = document.createElement('div');
      root.className = 'zc-sheet-overlay zc-delete-overlay';
      root.id = 'zcDeleteRoot';
      root.setAttribute('data-company-delete', '');
      document.body.appendChild(root);
      this.root = root;
      document.addEventListener('keydown', this._keydown, true);
      root.addEventListener('click', (event) => {
        if (event.target === root) this.close(true);
      });
    }

    _onLanguageChange() {
      if (this.root) this._render();
    }

    _keydown(event) {
      if (!this.root) return;
      if (event.key === 'Escape') {
        if (!this.busy) {
          event.preventDefault();
          this.close(true);
        }
        return;
      }
      if (event.key !== 'Tab') return;
      const sheet = this.root.querySelector('.zc-delete-sheet');
      if (!sheet) return;
      const focusables = Array.from(
        sheet.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href]')
      ).filter((node) => node.offsetParent !== null || node === document.activeElement);
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    async _get(path) {
      try {
        const response = await fetch(path);
        let data = {};
        try { data = await response.json(); } catch (err) { data = {}; }
        return { ok: response.ok, status: response.status, data };
      } catch (err) {
        return { ok: false, status: 0, data: {}, offline: true };
      }
    }

    async _send(method, path, body) {
      try {
        const response = await fetch(path, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: body === undefined ? undefined : JSON.stringify(body)
        });
        let data = {};
        try { data = await response.json(); } catch (err) { data = {}; }
        return { ok: response.ok, status: response.status, data };
      } catch (err) {
        return { ok: false, status: 0, data: {}, offline: true };
      }
    }

    async _load() {
      const base = `/api/v1/companies/${encodeURIComponent(this.companyId)}`;
      const [company, deletion, plan] = await Promise.all([
        this._get(base),
        this._get(`${base}/deletion`),
        this._get(`${base}/delete/plan`)
      ]);
      if (!company.ok) {
        this.loading = false;
        this.error = {
          code: company.status === 404 ? 'NOT_FOUND' : (company.offline ? 'OFFLINE' : 'LOAD_FAILED'),
          message: company.status === 404
            ? t('company.overview.error.not_found')
            : (company.offline ? t('company.overview.error.offline') : t('company.overview.error.load'))
        };
        this.step = 'error';
        this._render();
        return;
      }
      this.company = company.data;
      if (!this.companyName) this.companyName = this.company.name || '';
      this.deletion = deletion.ok && deletion.data.deletion ? deletion.data.deletion : (company.data.deletion || null);
      this.plan = plan.ok ? plan.data : null;
      if (!this.plan && this.company.permissions && !this.company.permissions.delete) {
        this.error = { code: 'FORBIDDEN', message: t('company.delete.error.forbidden') };
        this.step = 'error';
      } else {
        this.step = this._resolveStep();
      }
      this.loading = false;
      this._render();
    }

    _resolveStep() {
      if (this.completed) return 'done';
      const deletion = this.deletion;
      if (deletion) {
        if (deletion.status === 'COMPLETED') {
          this.completed = true;
          return 'done';
        }
        if (deletion.status === 'AWAITING_NAME') return 'name';
        if (deletion.status === 'AWAITING_IDENTITY') return 'identity';
        if (deletion.status === 'EXPORTING') return 'export';
        if (deletion.status === 'PENDING_DELETION') {
          return deletion.export_status === 'FAILED' ? 'export' : 'recovery';
        }
      }
      if (this.startAt === 'export' && deletion && deletion.export_available) return 'recovery';
      return 'what';
    }

    _asset(path) {
      const base = `/api/v1/companies/${encodeURIComponent(this.companyId)}`;
      return `${base}${path}`;
    }

    // ------------------------------------------------------------- rendering
    _render() {
      if (!this.root) return;
      const focusField = this._activeFieldId();
      this.root.innerHTML = `
        <div class="zc-sheet zc-delete-sheet" role="dialog" aria-modal="true"
          aria-labelledby="zcDeleteTitle" tabindex="-1" data-delete-step="${escapeHtml(this.step)}">
          ${this._headerHtml()}
          ${this._stepperHtml()}
          <div class="zc-delete-body" id="zcDeleteBody">
            ${this.loading ? this._loadingHtml() : this._bodyHtml()}
          </div>
          ${this.loading ? '' : this._actionsHtml()}
        </div>
      `;
      this._bind();
      const sheet = this.root.querySelector('.zc-delete-sheet');
      if (focusField) {
        const restored = document.getElementById(focusField);
        if (restored && restored.focus) restored.focus();
      } else if (sheet && sheet.focus) {
        sheet.focus();
      }
    }

    _activeFieldId() {
      const active = document.activeElement;
      if (active && active.id && this.root && this.root.contains(active)) return active.id;
      return null;
    }

    _headerHtml() {
      return `
        <div class="zc-delete-head">
          <div>
            <p class="zc-eyebrow">${escapeHtml(t('company.delete.eyebrow'))}</p>
            <h2 class="zc-delete-title" id="zcDeleteTitle">${escapeHtml(this._title())}</h2>
          </div>
          <button type="button" class="zc-icon-button" data-delete-action="close"
            aria-label="${escapeHtml(t('common.close'))}"${this.busy ? ' disabled' : ''}>
            <span aria-hidden="true">×</span>
          </button>
        </div>
      `;
    }

    _title() {
      if (this.loading) return t('company.delete.loading');
      if (this.step === 'what') return t('company.delete.what.title', { name: this.companyName });
      if (this.step === 'name') return t('company.delete.name.title');
      if (this.step === 'identity') return t('company.delete.identity.title');
      if (this.step === 'export') return t('company.delete.export.title');
      if (this.step === 'recovery') return t('company.delete.recovery.title');
      if (this.step === 'done') {
        return this.cancelled ? t('company.delete.cancelled.title') : t('company.delete.done.title');
      }
      return t('company.delete.error.title');
    }

    _stepperHtml() {
      if (this.loading || this.step === 'done' || this.step === 'error') return '';
      const current = STEP_ORDER.indexOf(this.step);
      return `
        <ol class="zc-delete-steps" aria-label="${escapeHtml(t('company.delete.steps'))}">
          ${STEP_ORDER.map((step, index) => `
            <li class="${index < current ? 'is-done' : ''}${index === current ? ' is-current' : ''}"
              ${index === current ? 'aria-current="step"' : ''}>
              <span class="zc-delete-step-dot" aria-hidden="true">${index < current ? '✓' : index + 1}</span>
              <span class="zc-delete-step-label">${escapeHtml(t(`company.delete.step.${step}`))}</span>
            </li>
          `).join('')}
        </ol>
      `;
    }

    _loadingHtml() {
      return `
        <div class="zc-skeleton-stack" aria-hidden="true">
          <span class="zc-skeleton zc-skeleton-lg"></span>
          <span class="zc-skeleton"></span>
          <span class="zc-skeleton"></span>
        </div>
        <p class="zc-section-note" role="status">${escapeHtml(t('common.loading'))}</p>
      `;
    }

    _bodyHtml() {
      if (this.step === 'error') return this._errorBodyHtml();
      if (this.step === 'what') return this._whatHtml();
      if (this.step === 'name') return this._nameHtml();
      if (this.step === 'identity') return this._identityHtml();
      if (this.step === 'export') return this._exportHtml();
      if (this.step === 'recovery') return this._recoveryHtml();
      if (this.step === 'done') return this._doneHtml();
      return '';
    }

    _alertHtml() {
      if (this.error) {
        return `
          <div class="zc-inline-notice zc-inline-notice-error" role="alert">
            <strong>${escapeHtml(t('company.delete.error.title'))}</strong>
            <span>${escapeHtml(this.error.message || t('company.delete.error.generic'))}</span>
          </div>
        `;
      }
      if (this.notice) {
        return `<div class="zc-inline-notice zc-inline-notice-success" role="status">${escapeHtml(this.notice)}</div>`;
      }
      return '';
    }

    _errorBodyHtml() {
      return `
        <div class="zc-inline-notice zc-inline-notice-error" role="alert">
          <span>${escapeHtml((this.error && this.error.message) || t('company.delete.error.generic'))}</span>
        </div>
      `;
    }

    _whatHtml() {
      const plan = this.plan || {};
      const summary = plan.removal_summary || {};
      const counts = summary.will_remove || {};
      const rows = [
        ['departments', counts.departments],
        ['employees', counts.employees],
        ['workflows', counts.workflows],
        ['connections', counts.connections],
        ['files', counts.files],
        ['approvals', counts.approvals]
      ];
      const recovery = plan.recovery_days == null ? 7 : Number(plan.recovery_days);
      const emailLine = plan.email_available
        ? t('company.delete.what.email_yes', { recipient: plan.email_recipient || '' })
        : t('company.delete.what.email_no');
      return `
        ${this._alertHtml()}
        <p class="zc-delete-lead">${escapeHtml(t('company.delete.what.lead'))}</p>

        <section class="zc-delete-section">
          <h3>${escapeHtml(t('company.delete.what.remove_title'))}</h3>
          <ul class="zc-delete-counts">
            ${rows.map(([key, value]) => `
              <li><span>${escapeHtml(t(`company.delete.remove.${key}`))}</span><strong>${Number(value || 0)}</strong></li>
            `).join('')}
          </ul>
        </section>

        <section class="zc-delete-section">
          <h3>${escapeHtml(t('company.delete.what.stop_title'))}</h3>
          <ul class="zc-delete-list">
            <li>${escapeHtml(t('company.delete.what.stop_workflows'))}</li>
            <li>${escapeHtml(t('company.delete.what.stop_schedules'))}</li>
            <li>${escapeHtml(t('company.delete.what.stop_connections'))}</li>
          </ul>
        </section>

        <section class="zc-delete-section">
          <h3>${escapeHtml(t('company.delete.what.keep_title'))}</h3>
          <ul class="zc-delete-list">
            <li>${escapeHtml(t('company.delete.what.keep_audit'))}</li>
            <li>${escapeHtml(t('company.delete.what.keep_record'))}</li>
          </ul>
        </section>

        <div class="zc-inline-notice zc-inline-notice-muted" role="status">
          ${escapeHtml(t('company.delete.what.export_promise'))}
        </div>
        <dl class="zc-delete-facts">
          <div><dt>${escapeHtml(t('company.delete.what.recovery'))}</dt><dd>${escapeHtml(recovery === 0 ? t('company.delete.what.recovery_none') : t('company.delete.what.recovery_days', { days: recovery }))}</dd></div>
          <div><dt>${escapeHtml(t('company.delete.what.email'))}</dt><dd>${escapeHtml(emailLine)}</dd></div>
        </dl>
        ${plan.mfa_required ? `
          <div class="zc-inline-notice zc-inline-notice-warning" role="status">
            ${escapeHtml(plan.two_step_configured ? t('company.delete.what.mfa') : t('company.delete.what.mfa_missing'))}
          </div>
        ` : ''}
      `;
    }

    _nameHtml() {
      const expected = String((this.company && this.company.name) || this.companyName || '');
      const enabled = this.nameInput.trim() === expected.trim() && !this.busy;
      return `
        ${this._alertHtml()}
        <p class="zc-delete-lead">${escapeHtml(t('company.delete.name.lead'))}</p>
        <p class="zc-delete-name">${escapeHtml(expected)}</p>
        <div class="zc-field${this.error && this.error.code === 'NAME_MISMATCH' ? ' has-error' : ''}">
          <label class="zc-label" for="zcDeleteName">${escapeHtml(t('company.delete.name.label'))}</label>
          <input class="zc-input" id="zcDeleteName" data-delete-field="name" type="text"
            value="${escapeHtml(this.nameInput)}" autocomplete="off" autocapitalize="off" spellcheck="false"
            aria-describedby="zcDeleteNameHint" />
          <p class="zc-field-hint" id="zcDeleteNameHint">${escapeHtml(t('company.delete.name.hint'))}</p>
        </div>
        <p class="zc-form-footnote">${escapeHtml(t('company.delete.name.footnote'))}</p>
        <button type="button" class="zc-button zc-button-primary" data-delete-action="name-continue"
          ${enabled ? '' : ' disabled'}>${escapeHtml(t('company.delete.name.continue'))}</button>
      `;
    }

    _identityHtml() {
      const plan = this.plan || {};
      const mfaRequired = !!plan.mfa_required;
      const twoStepConfigured = !!plan.two_step_configured;
      return `
        ${this._alertHtml()}
        <p class="zc-delete-lead">${escapeHtml(t('company.delete.identity.lead'))}</p>
        <div class="zc-field">
          <label class="zc-label" for="zcDeletePassword">${escapeHtml(t('company.delete.identity.password'))}</label>
          <input class="zc-input" id="zcDeletePassword" data-delete-field="password" type="password"
            value="${escapeHtml(this.password)}" autocomplete="current-password"
            aria-describedby="zcDeletePasswordHint" />
          <p class="zc-field-hint" id="zcDeletePasswordHint">${escapeHtml(t('company.delete.identity.password_hint'))}</p>
        </div>
        ${mfaRequired && twoStepConfigured ? `
          <div class="zc-field">
            <label class="zc-label" for="zcDeleteCode">${escapeHtml(t('company.delete.identity.code'))}</label>
            <input class="zc-input" id="zcDeleteCode" data-delete-field="code" type="text"
              value="${escapeHtml(this.twoStep)}" inputmode="numeric" autocomplete="one-time-code" />
          </div>
        ` : ''}
        ${mfaRequired ? `
          <div class="zc-inline-notice zc-inline-notice-warning" role="status">
            ${escapeHtml(twoStepConfigured ? t('company.delete.identity.mfa') : t('company.delete.identity.mfa_missing'))}
          </div>
        ` : ''}
        <p class="zc-form-footnote">${escapeHtml(t('company.delete.identity.footnote'))}</p>
        <button type="button" class="zc-button zc-button-primary" data-delete-action="identity-confirm"
          ${this.password && !this.busy ? '' : ' disabled'}>${escapeHtml(t('company.delete.identity.confirm'))}</button>
      `;
    }

    _exportHtml() {
      const deletion = this.deletion || {};
      const failed = deletion.export_status === 'FAILED';
      return `
        ${this._alertHtml()}
        <p class="zc-delete-lead">${escapeHtml(failed ? t('company.delete.export.failed_lead') : t('company.delete.export.lead'))}</p>
        ${failed ? `
          <div class="zc-inline-notice zc-inline-notice-error" role="alert">
            ${escapeHtml(t('company.delete.export.failed_note'))}
          </div>
          <button type="button" class="zc-button zc-button-primary" data-delete-action="export-retry"
            ${this.busy ? ' disabled' : ''}>${escapeHtml(t('company.delete.export.retry'))}</button>
        ` : `
          <div class="zc-delete-progress" role="status" aria-live="polite">
            <span class="zc-live-dot" aria-hidden="true"></span>
            <span>${escapeHtml(t('company.delete.export.progress'))}</span>
          </div>
        `}
        <p class="zc-form-footnote">${escapeHtml(t('company.delete.export.footnote'))}</p>
      `;
    }

    _recoveryHtml() {
      const deletion = this.deletion || {};
      const emailStatus = String(deletion.email_status || 'NOT_SENT');
      const delivered = emailStatus === 'SENT' || !!deletion.download_confirmed_at;
      const purgeAfter = Number(deletion.purge_after || 0);
      const due = purgeAfter > 0 && purgeAfter <= Math.floor(Date.now() / 1000);
      return `
        ${this._alertHtml()}
        <p class="zc-delete-lead">${escapeHtml(t('company.delete.recovery.lead'))}</p>

        <section class="zc-delete-section zc-delete-export-card">
          <h3>${escapeHtml(t('company.delete.recovery.export_title'))}</h3>
          <dl class="zc-delete-facts">
            <div><dt>${escapeHtml(t('company.delete.recovery.file'))}</dt><dd>${escapeHtml(deletion.export_filename || t('company.delete.recovery.file_pending'))}</dd></div>
            <div><dt>${escapeHtml(t('company.delete.recovery.size'))}</dt><dd>${escapeHtml(formatSize(deletion.export_size_bytes) || '—')}</dd></div>
            <div><dt>${escapeHtml(t('company.delete.recovery.parts'))}</dt><dd>${Number(deletion.export_parts || 1)}</dd></div>
            <div><dt>${escapeHtml(t('company.delete.recovery.checksum'))}</dt><dd class="zc-mono">${escapeHtml(String(deletion.export_sha256 || '').slice(0, 16))}${deletion.export_sha256 ? '…' : ''}</dd></div>
          </dl>
          <button type="button" class="zc-button zc-button-primary" data-delete-action="download"
            ${this.busy || !deletion.export_available ? ' disabled' : ''}>
            ${escapeHtml(t('company.delete.recovery.download'))}
          </button>
          <p class="zc-form-footnote">${escapeHtml(t('company.delete.recovery.download_note'))}</p>
        </section>

        <section class="zc-delete-section">
          <h3>${escapeHtml(t('company.delete.recovery.email_title'))}</h3>
          <p class="zc-delete-email-status">${escapeHtml(this._emailText(emailStatus, deletion))}</p>
          ${emailStatus !== 'SENT' ? `<p class="zc-form-footnote">${escapeHtml(t('company.delete.recovery.email_fallback'))}</p>` : ''}
        </section>

        <section class="zc-delete-section">
          <h3>${escapeHtml(t('company.delete.recovery.window_title'))}</h3>
          <p class="zc-delete-window">${escapeHtml(countdown(purgeAfter) || t('company.delete.window.due'))}</p>
          <p class="zc-section-note">${escapeHtml(t('company.delete.recovery.window_note', { time: formatTime(purgeAfter) || '—' }))}</p>
          ${deletion.purge_blocked_reason === 'WAITING_FOR_DOWNLOAD' ? `
            <div class="zc-inline-notice zc-inline-notice-warning" role="status">
              ${escapeHtml(t('company.delete.recovery.blocked_download'))}
            </div>
          ` : ''}
          ${due && delivered ? `
            <button type="button" class="zc-button zc-button-quiet zc-button-danger" data-delete-action="purge"
              ${this.busy ? ' disabled' : ''}>${escapeHtml(t('company.delete.recovery.purge_now'))}</button>
          ` : ''}
        </section>

        <div class="zc-delete-actions">
          <button type="button" class="zc-button zc-button-quiet zc-button-danger" data-delete-action="cancel"
            ${this.busy ? ' disabled' : ''}>${escapeHtml(t('company.delete.recovery.cancel'))}</button>
          <button type="button" class="zc-button zc-button-quiet" data-delete-action="close"
            ${this.busy ? ' disabled' : ''}>${escapeHtml(t('common.close'))}</button>
        </div>
        <p class="zc-form-footnote">${escapeHtml(t('company.delete.recovery.footnote'))}</p>
      `;
    }

    _emailText(status, deletion) {
      const recipient = deletion.email_recipient || '';
      if (status === 'SENT') return t('company.delete.email.sent', { recipient });
      if (status === 'NOT_CONFIGURED') return t('company.delete.email.not_configured');
      if (status === 'SKIPPED_UNVERIFIED') return t('company.delete.email.unverified');
      if (status === 'FAILED') return t('company.delete.email.failed');
      if (status === 'TOO_LARGE') return t('company.delete.email.too_large');
      return t('company.delete.email.not_sent');
    }

    _doneHtml() {
      if (this.cancelled) {
        return `
          <div class="zc-delete-done">
            <div class="zc-delete-done-mark zc-delete-done-cancel" aria-hidden="true">✓</div>
            <p class="zc-delete-lead">${escapeHtml(t('company.delete.cancelled.body'))}</p>
            <p class="zc-section-note">${escapeHtml(t('company.delete.cancelled.restored', { status: this._statusLabel(this.cancelledStatus) }))}</p>
          </div>
          <div class="zc-delete-actions">
            <button type="button" class="zc-button zc-button-primary" data-delete-action="close">${escapeHtml(t('common.close'))}</button>
          </div>
        `;
      }
      return `
        <div class="zc-delete-done">
          <div class="zc-delete-done-mark" aria-hidden="true">✓</div>
          <p class="zc-delete-lead">${escapeHtml(t('company.delete.done.body'))}</p>
          <ul class="zc-delete-list">
            <li>${escapeHtml(t('company.delete.done.removed'))}</li>
            <li>${escapeHtml(t('company.delete.done.kept'))}</li>
            <li>${escapeHtml(t('company.delete.done.audit'))}</li>
          </ul>
        </div>
        <div class="zc-delete-actions">
          <button type="button" class="zc-button zc-button-primary" data-delete-action="close">${escapeHtml(t('common.close'))}</button>
        </div>
      `;
    }

    _statusLabel(status) {
      const key = `status.${String(status || '').toLowerCase()}`;
      const label = t(key);
      return label === key ? String(status || '') : label;
    }

    _actionsHtml() {
      if (this.step === 'error') {
        return `<div class="zc-delete-actions"><button type="button" class="zc-button zc-button-primary" data-delete-action="close">${escapeHtml(t('common.close'))}</button></div>`;
      }
      if (this.step === 'what') {
        return `
          <div class="zc-delete-actions">
            <button type="button" class="zc-button zc-button-quiet" data-delete-action="close"${this.busy ? ' disabled' : ''}>${escapeHtml(t('common.cancel'))}</button>
            <button type="button" class="zc-button zc-button-danger" data-delete-action="request"${this.busy ? ' disabled' : ''}>${escapeHtml(t('company.delete.what.continue'))}</button>
          </div>
        `;
      }
      if (this.step === 'name') {
        return `
          <div class="zc-delete-actions">
            <button type="button" class="zc-button zc-button-quiet zc-button-danger" data-delete-action="cancel"${this.busy ? ' disabled' : ''}>${escapeHtml(t('company.delete.cancel.action'))}</button>
          </div>
        `;
      }
      if (this.step === 'identity') {
        return `
          <div class="zc-delete-actions">
            <button type="button" class="zc-button zc-button-quiet zc-button-danger" data-delete-action="cancel"${this.busy ? ' disabled' : ''}>${escapeHtml(t('company.delete.cancel.action'))}</button>
          </div>
        `;
      }
      if (this.step === 'export') {
        return `
          <div class="zc-delete-actions">
            <button type="button" class="zc-button zc-button-quiet zc-button-danger" data-delete-action="cancel"${this.busy ? ' disabled' : ''}>${escapeHtml(t('company.delete.cancel.action'))}</button>
          </div>
        `;
      }
      return '';
    }

    // --------------------------------------------------------------- binding
    _bind() {
      if (!this.root) return;
      const buttons = this.root.querySelectorAll('[data-delete-action]');
      buttons.forEach((button) => {
        button.addEventListener('click', () => {
          const action = button.getAttribute('data-delete-action');
          if (action === 'close') this.close(true);
          else if (action === 'request') this.requestDeletion();
          else if (action === 'name-continue') this.confirmName();
          else if (action === 'identity-confirm') this.confirmIdentity();
          else if (action === 'export-retry') this.retryExport();
          else if (action === 'download') this.download();
          else if (action === 'purge') this.purgeNow();
          else if (action === 'cancel') this.cancelDeletion();
        });
      });

      const name = this.root.querySelector('#zcDeleteName');
      if (name) {
        name.addEventListener('input', () => {
          this.nameInput = name.value;
          if (this.error && this.error.code === 'NAME_MISMATCH') {
            this.error = null;
            const alert = this.root.querySelector('.zc-inline-notice-error');
            if (alert) alert.remove();
          }
          const expected = String((this.company && this.company.name) || this.companyName || '').trim();
          const next = this.root.querySelector('[data-delete-action="name-continue"]');
          if (next) next.disabled = name.value.trim() !== expected;
        });
      }

      const password = this.root.querySelector('#zcDeletePassword');
      if (password) {
        password.addEventListener('input', () => {
          this.password = password.value;
          const next = this.root.querySelector('[data-delete-action="identity-confirm"]');
          if (next) next.disabled = !password.value;
        });
      }

      const code = this.root.querySelector('#zcDeleteCode');
      if (code) code.addEventListener('input', () => { this.twoStep = code.value; });
    }

    // ---------------------------------------------------------------- actions
    async requestDeletion() {
      if (this.busy) return;
      this.busy = true;
      this.error = null;
      this.notice = null;
      this._render();
      const result = await this._send(
        'POST',
        this._asset('/delete/request')
      );
      this.busy = false;
      if (!result.ok) {
        this._setError(result, t('company.delete.error.request'));
        this._render();
        return;
      }
      this.deletion = result.data;
      this.step = 'name';
      this._render();
    }

    async confirmName() {
      if (this.busy) return;
      const expected = String((this.company && this.company.name) || this.companyName || '').trim();
      if (this.nameInput.trim() !== expected) {
        this.error = { code: 'NAME_MISMATCH', message: t('company.delete.error.name_mismatch') };
        this._render();
        return;
      }
      this.busy = true;
      this.error = null;
      this._render();
      const result = await this._send(
        'POST',
        this._asset('/delete/confirm-name'),
        { name: this.nameInput }
      );
      this.busy = false;
      if (!result.ok) {
        this._setError(result, t('company.delete.error.name'));
        this._render();
        return;
      }
      this.deletion = result.data;
      this.step = 'identity';
      this._render();
    }

    async confirmIdentity() {
      if (this.busy || !this.password) return;
      this.busy = true;
      this.error = null;
      this._render();
      const result = await this._send(
        'POST',
        this._asset('/delete/confirm-identity'),
        { password: this.password, two_step_code: this.twoStep || undefined }
      );
      this.busy = false;
      this.password = '';
      if (!result.ok) {
        this._setError(result, t('company.delete.error.identity'));
        this._render();
        return;
      }
      this.deletion = result.data.deletion || this.deletion;
      if (result.data.purged) {
        this.completed = true;
        this.step = 'done';
        this._render();
        return;
      }
      const exportInfo = result.data.export || {};
      if (exportInfo.status === 'FAILED') {
        this.step = 'export';
        this._render();
        return;
      }
      this.notice = exportInfo.message || t('company.delete.recovery.ready');
      this.step = 'recovery';
      this._render();
    }

    async retryExport() {
      if (this.busy) return;
      this.busy = true;
      this.error = null;
      this._render();
      const result = await this._send('POST', this._asset('/delete/export'));
      this.busy = false;
      if (!result.ok) {
        this._setError(result, t('company.delete.error.export'));
        this._render();
        return;
      }
      this.deletion = result.data.deletion || this.deletion;
      if (result.data.purged) {
        this.completed = true;
        this.step = 'done';
      } else {
        this.notice = (result.data.export && result.data.export.message) || t('company.delete.recovery.ready');
        this.step = 'recovery';
      }
      this._render();
    }

    async download() {
      if (this.busy) return;
      this.busy = true;
      this.error = null;
      this.notice = null;
      this._render();
      let response;
      try {
        response = await fetch(this._asset('/export'));
      } catch (err) {
        this.busy = false;
        this.error = { code: 'OFFLINE', message: t('company.delete.error.offline') };
        this._render();
        return;
      }
      if (!response.ok) {
        let data = {};
        try { data = await response.json(); } catch (err) { data = {}; }
        this.busy = false;
        this._setError({ ok: false, status: response.status, data }, t('company.delete.error.download'));
        this._render();
        return;
      }
      let blob = null;
      try { blob = await response.blob(); } catch (err) { blob = null; }
      this.busy = false;
      if (!blob) {
        this.error = { code: 'DOWNLOAD_FAILED', message: t('company.delete.error.download') };
        this._render();
        return;
      }
      const filename = (this.deletion && this.deletion.export_filename) || 'company-export';
      const url = window.URL && typeof window.URL.createObjectURL === 'function'
        ? window.URL.createObjectURL(blob)
        : '';
      if (url) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.rel = 'noopener';
        document.body.appendChild(link);
        link.click();
        link.remove();
        if (typeof window.setTimeout === 'function') {
          window.setTimeout(() => {
            try { window.URL.revokeObjectURL(url); } catch (err) { /* already gone */ }
          }, 1000);
        }
      }
      this.notice = t('company.delete.downloaded', { filename });
      await this._refreshDeletion();
      if (this.completed) {
        this.step = 'done';
      } else {
        this.step = 'recovery';
      }
      this._render();
    }

    async _refreshDeletion() {
      const result = await this._get(this._asset('/deletion'));
      if (!result.ok) return;
      const deletion = result.data.deletion;
      if (deletion) {
        this.deletion = deletion;
        if (deletion.status === 'COMPLETED') this.completed = true;
        return;
      }
      // A completed purge leaves no active request. Keep the last known export
      // details for the final screen, but only call it complete when this sheet
      // already saw a pending deletion.
      if (this.deletion && this.deletion.status === 'PENDING_DELETION') {
        this.completed = true;
      }
    }

    async purgeNow() {
      if (this.busy) return;
      this.busy = true;
      this.error = null;
      this._render();
      const result = await this._send('POST', this._asset('/delete/purge'));
      this.busy = false;
      if (!result.ok) {
        this._setError(result, t('company.delete.error.purge'));
        this._render();
        return;
      }
      this.completed = true;
      this.step = 'done';
      this._render();
    }

    async cancelDeletion() {
      if (this.busy) return;
      this.busy = true;
      this.error = null;
      this._render();
      const result = await this._send('POST', this._asset('/delete/cancel'));
      this.busy = false;
      if (!result.ok) {
        this._setError(result, t('company.delete.error.cancel'));
        this._render();
        return;
      }
      this.cancelled = true;
      this.cancelledStatus = String(result.data.company_status || '');
      this.deletion = null;
      this.step = 'done';
      this._render();
    }

    _setError(result, fallback) {
      const data = (result && result.data) || {};
      const code = String(data.code || '');
      if (result && result.offline) {
        this.error = { code: 'OFFLINE', message: t('company.delete.error.offline') };
        return;
      }
      if (code === 'TWO_STEP_NOT_CONFIGURED') {
        this.error = { code, message: t('company.delete.error.mfa_missing') };
        return;
      }
      if (code === 'TWO_STEP_REQUIRED') {
        this.error = { code, message: t('company.delete.error.mfa_required') };
        return;
      }
      if (code === 'INVALID_PASSWORD') {
        this.error = { code, message: t('company.delete.error.password') };
        return;
      }
      if (code === 'NAME_MISMATCH') {
        this.error = { code, message: t('company.delete.error.name_mismatch') };
        return;
      }
      if (code === 'EXPORT_NOT_DELIVERED') {
        this.error = { code, message: t('company.delete.error.deliver_first') };
        return;
      }
      if (code === 'RECOVERY_WINDOW_ACTIVE') {
        this.error = { code, message: t('company.delete.error.window_active') };
        return;
      }
      if (code === 'FORBIDDEN') {
        this.error = { code, message: t('company.delete.error.forbidden') };
        return;
      }
      if (code === 'COMPANY_NOT_FOUND' || (result && result.status === 404)) {
        this.error = { code, message: t('company.overview.error.not_found') };
        return;
      }
      if (result && result.status === 0) {
        this.error = { code: 'NETWORK', message: t('company.delete.error.offline') };
        return;
      }
      this.error = { code: code || 'ERROR', message: data.error || fallback || t('company.delete.error.generic') };
    }
  }

  window.CompanySetupDelete = new CompanySetupDelete();
})();
