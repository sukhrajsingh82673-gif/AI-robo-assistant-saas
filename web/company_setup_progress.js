/**
 * ZONATA — Company Build progress
 *
 * Shows the real build that runs after a new company is submitted: the phase
 * list, a plain-language log, what is waiting on the user, and an honest
 * estimate. It polls only while something is actually running, and it never
 * turns a skipped or failed phase into a success.
 *
 * Route: /company/<company_id>/build
 */

(function() {
  'use strict';

  const POLL_MS = 3000;

  const PHASE_STATE = {
    PENDING: { key: 'company.build.phase.pending', tone: 'neutral' },
    RUNNING: { key: 'company.build.phase.running', tone: 'accent' },
    DONE: { key: 'company.build.phase.done', tone: 'green' },
    DONE_WITH_GAPS: { key: 'company.build.phase.done_with_gaps', tone: 'orange' },
    SKIPPED: { key: 'company.build.phase.skipped', tone: 'orange' },
    FAILED: { key: 'company.build.phase.failed', tone: 'red' }
  };

  const RUN_STATE = {
    PENDING: { key: 'company.build.run.pending', tone: 'neutral' },
    RUNNING: { key: 'company.build.run.running', tone: 'accent' },
    DONE: { key: 'company.build.run.done', tone: 'green' },
    DONE_WITH_GAPS: { key: 'company.build.run.gaps', tone: 'orange' },
    FAILED: { key: 'company.build.run.failed', tone: 'red' }
  };

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

  function statusLabel(value) {
    const key = `status.${String(value || '').toLowerCase()}`;
    const label = t(key);
    return label === key ? String(value || '') : label;
  }

  function phaseStateMeta(value) {
    return PHASE_STATE[String(value || '').toUpperCase()] || PHASE_STATE.PENDING;
  }

  function runStateMeta(value) {
    return RUN_STATE[String(value || '').toUpperCase()] || RUN_STATE.PENDING;
  }

  function language() {
    return (window.I18n && window.I18n.getLanguage && window.I18n.getLanguage()) || 'en';
  }

  function formatTime(seconds) {
    if (!seconds) return '';
    try {
      const date = new Date(Number(seconds) * 1000);
      const locale = language() === 'ar' ? 'ar-IN' : 'en-IN';
      return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(date);
    } catch (err) {
      return '';
    }
  }

  function formatEstimate(build) {
    const estimate = build && build.estimate ? build.estimate : {};
    const min = Number(estimate.min_days || 0);
    const max = Number(estimate.max_days || 0);
    if (!min && !max) return '';
    if (min && max && min !== max) return t('company.build.estimate.range', { min, max });
    return t('company.build.estimate.one', { days: min || max });
  }

  function isRunning(build) {
    // PENDING means queued, not running: nothing will change without a retry,
    // so polling would only burn requests and never update the page.
    return String((build && build.phase_state) || '').toUpperCase() === 'RUNNING';
  }

  class CompanyBuildProgress {
    constructor() {
      this.containerId = null;
      this.companyId = null;
      this.company = null;
      this.build = null;
      this.error = null;
      this.loading = true;
      this.retrying = false;
      this.showAllLog = false;
      this._timer = null;
      this._onLanguageChange = this._onLanguageChange.bind(this);
      if (document && document.addEventListener) {
        document.addEventListener('zonata:languagechange', this._onLanguageChange);
      }
    }

    _onLanguageChange() {
      if (!this.containerId) return;
      const container = document.getElementById(this.containerId);
      if (container && container.querySelector('[data-company-build]')) this._render();
    }

    async render(containerOrId, companyId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;
      if (!container) return;
      this.containerId = container.id || this.containerId;
      if (companyId) this.companyId = String(companyId);
      if (!this.companyId) this.companyId = this._companyIdFromHash();
      if (!this.companyId) {
        this.error = { code: 'NO_COMPANY', message: t('company.build.error.no_company') };
        this.loading = false;
        this._render();
        return;
      }
      this.loading = true;
      this.error = null;
      this._render();
      await this._load();
    }

    destroy() {
      if (this._timer) {
        clearTimeout(this._timer);
        this._timer = null;
      }
    }

    _companyIdFromHash() {
      const hash = String(window.location.hash || '').replace(/^#/, '');
      const match = hash.match(/^\/company\/([^/]+)\/build\/?$/);
      return match ? decodeURIComponent(match[1]) : null;
    }

    async _get(path) {
      const res = await fetch(path);
      let data = {};
      try {
        data = await res.json();
      } catch (err) {
        data = {};
      }
      return { ok: res.ok, status: res.status, data };
    }

    async _load() {
      this.destroy();
      this.error = null;
      try {
        const [company, build] = await Promise.all([
          this._get(`/api/v1/companies/${encodeURIComponent(this.companyId)}`),
          this._get(`/api/v1/companies/${encodeURIComponent(this.companyId)}/build`)
        ]);

        if (!company.ok) {
          this.loading = false;
          this.error = {
            code: company.status === 404 ? 'NOT_FOUND' : 'LOAD_FAILED',
            message: company.status === 404 || company.data.code === 'COMPANY_NOT_FOUND'
              ? t('company.build.error.not_found')
              : (company.data.error || t('company.build.error.load'))
          };
          this._render();
          return;
        }

        this.company = company.data;
        if (build.ok) {
          this.build = build.data;
        } else if (build.status === 404) {
          this.build = null;
        } else {
          this.build = null;
          this.error = { code: 'BUILD_LOAD_FAILED', message: build.data.error || t('company.build.error.load') };
        }
        this.loading = false;
        this._render();

        if (!this.error && this.build && isRunning(this.build)) {
          this._timer = setTimeout(() => this._load(), POLL_MS);
        }
      } catch (err) {
        this.loading = false;
        this.error = {
          code: 'OFFLINE',
          message: (typeof navigator !== 'undefined' && navigator.onLine === false)
            ? t('company.build.error.offline')
            : t('company.build.error.network')
        };
        this._render();
      }
    }

    canRetry() {
      if (!this.build || this.retrying) return false;
      const status = String(this.company && this.company.status || '').toUpperCase();
      const phaseState = String(this.build.phase_state || '').toUpperCase();
      if (phaseState === 'RUNNING') return false;
      // The server allows retry for CREATING, ONBOARDING and NEEDS_ATTENTION.
      return status === 'CREATING' || status === 'ONBOARDING' || status === 'NEEDS_ATTENTION';
    }

    async retry() {
      if (this.retrying) return;
      this.retrying = true;
      this._render();
      try {
        const res = await fetch(`/api/v1/companies/${encodeURIComponent(this.companyId)}/build/retry`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        let data = {};
        try { data = await res.json(); } catch (err) { data = {}; }
        if (!res.ok) {
          this.error = { code: data.code || 'RETRY_FAILED', message: data.error || t('company.build.error.retry') };
        } else if (data.workflow_started === false && data.workflow_note) {
          this._toast(data.workflow_note, 'warning');
        } else {
          this._toast(t('company.build.retry.started'), 'info');
          this.build = data.build || this.build;
        }
      } catch (err) {
        this.error = { code: 'OFFLINE', message: t('company.build.error.network') };
      } finally {
        this.retrying = false;
        await this._load();
      }
    }

    // ------------------------------------------------------------- rendering
    _render() {
      const container = document.getElementById(this.containerId);
      if (!container) return;

      if (this.loading) {
        container.innerHTML = this._shell(this._loadingHtml());
        return;
      }
      if (this.error) {
        container.innerHTML = this._shell(this._errorHtml());
        this._bind(container);
        return;
      }
      if (!this.build) {
        container.innerHTML = this._shell(this._emptyHtml());
        this._bind(container);
        return;
      }
      container.innerHTML = this._shell(this._buildHtml());
      this._bind(container);
    }

    _shell(inner) {
      return `
        <div class="zc-flow-page zc-progress-page" data-company-build>
          <div class="zc-flow-top">
            <button type="button" class="zc-back-link" id="zcBuildBack">
              <span class="zc-back-arrow" aria-hidden="true">←</span>
              <span>${escapeHtml(t('company.build.back'))}</span>
            </button>
            <div class="zc-language-toggle" role="group" aria-label="${escapeHtml(t('common.language'))}">
              <button type="button" data-language="en" aria-pressed="${language() === 'en' ? 'true' : 'false'}">${escapeHtml(t('common.english'))}</button>
              <button type="button" data-language="ar" aria-pressed="${language() === 'ar' ? 'true' : 'false'}">${escapeHtml(t('common.arabic'))}</button>
            </div>
          </div>
          ${inner}
        </div>
      `;
    }

    _loadingHtml() {
      return `
        <header class="zc-flow-header">
          <h1 class="zc-flow-title">${escapeHtml(t('company.build.title'))}</h1>
          <p class="zc-flow-subtitle" role="status">${escapeHtml(t('common.loading'))}</p>
        </header>
        <div class="zc-skeleton-stack" aria-hidden="true">
          <span class="zc-skeleton zc-skeleton-lg"></span>
          <span class="zc-skeleton"></span>
          <span class="zc-skeleton"></span>
        </div>
      `;
    }

    _errorHtml() {
      return `
        <div class="zc-inline-notice zc-inline-notice-error" role="alert">
          <strong>${escapeHtml(t('company.build.error.title'))}</strong>
          <span>${escapeHtml(this.error && this.error.message ? this.error.message : t('company.build.error.load'))}</span>
        </div>
        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-quiet" id="zcBuildErrorBack">${escapeHtml(t('company.build.back'))}</button>
          <button type="button" class="zc-button zc-button-primary" id="zcBuildReload">${escapeHtml(t('common.retry'))}</button>
        </div>
      `;
    }

    _emptyHtml() {
      return `
        <header class="zc-flow-header">
          <h1 class="zc-flow-title">${escapeHtml(this.company ? this.company.name : t('company.build.title'))}</h1>
          <p class="zc-flow-subtitle">${escapeHtml(t('company.build.empty.title'))}</p>
        </header>
        <div class="zc-empty-card" role="status">
          <p>${escapeHtml(t('company.build.empty.body'))}</p>
        </div>
        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-quiet" id="zcBuildEmptyBack">${escapeHtml(t('company.build.back'))}</button>
        </div>
      `;
    }

    _buildHtml() {
      const build = this.build;
      const company = this.company || {};
      const runMeta = runStateMeta(build.phase_state);
      const percent = Math.max(0, Math.min(100, Number(build.progress_percent || 0)));
      const estimate = formatEstimate(build);
      const gaps = Array.isArray(build.waiting_on) && build.waiting_on.length ? build.waiting_on : (build.gaps || []);
      const phases = Array.isArray(build.phases) ? build.phases : [];
      const log = Array.isArray(build.log) ? build.log : [];
      const visibleLog = this.showAllLog ? log.slice(-40) : log.slice(-8);
      const running = isRunning(build);
      const onboarding = String(build.run_type || '').toUpperCase() === 'ONBOARDING';

      return `
        <header class="zc-flow-header zc-build-header">
          <p class="zc-eyebrow">${escapeHtml(t(onboarding ? 'company.build.onboarding.eyebrow' : 'company.build.eyebrow'))}</p>
          <div class="zc-build-title-row">
            <h1 class="zc-flow-title">${escapeHtml(company.name || t('company.build.title'))}</h1>
            <span class="zc-pill zc-pill-${runMeta.tone}">${escapeHtml(t(runMeta.key))}</span>
          </div>
          <p class="zc-flow-subtitle">${escapeHtml(t(onboarding ? 'company.build.onboarding.subtitle' : 'company.build.subtitle'))}</p>
        </header>

        ${this._readinessHtml(build)}

        <section class="zc-build-summary" aria-labelledby="zcBuildSummaryTitle">
          <div class="zc-build-summary-top">
            <h2 class="zc-section-title" id="zcBuildSummaryTitle">${escapeHtml(t('company.build.progress.title'))}</h2>
            <span class="zc-build-percent">${percent}%</span>
          </div>
          <div class="zc-progress" role="progressbar" aria-labelledby="zcBuildSummaryTitle" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}" aria-valuetext="${escapeHtml(t('company.build.progress.value', { percent }))}">
            <span class="zc-progress-fill" style="width: ${percent}%"></span>
          </div>
          <p class="zc-build-meta" role="status" aria-live="polite">
            ${escapeHtml(t('company.build.progress.caption', {
              done: phases.filter((phase) => phase.state === 'DONE').length,
              total: phases.length || 7
            }))}
            ${estimate ? ` · ${escapeHtml(estimate)}` : ''}
            ${build.attempt > 1 ? ` · ${escapeHtml(t('company.build.attempt', { attempt: build.attempt }))}` : ''}
          </p>
          ${running ? `<p class="zc-build-live"><span class="zc-live-dot" aria-hidden="true"></span>${escapeHtml(t('company.build.live'))}</p>` : ''}
        </section>

        ${build.phase_state === 'FAILED' && build.failure_reason ? `
          <div class="zc-inline-notice zc-inline-notice-error" role="alert">
            <strong>${escapeHtml(t('company.build.failed.title'))}</strong>
            <span>${escapeHtml(build.failure_reason)}</span>
          </div>
        ` : ''}

        <section class="zc-build-phases" aria-labelledby="zcBuildPhasesTitle">
          <h2 class="zc-section-title" id="zcBuildPhasesTitle">${escapeHtml(t('company.build.phases.title'))}</h2>
          <ol class="zc-phase-list">
            ${phases.map((phase) => this._phaseHtml(phase)).join('')}
          </ol>
        </section>

        ${this._diagnosisHtml(build)}
        ${this._sourcesHtml(build)}

        ${gaps.length ? `
          <section class="zc-build-waiting" aria-labelledby="zcBuildWaitingTitle">
            <h2 class="zc-section-title" id="zcBuildWaitingTitle">${escapeHtml(t('company.build.waiting.title'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.build.waiting.note'))}</p>
            <ul class="zc-waiting-list">
              ${gaps.map((gap) => `
                <li class="zc-waiting-item">
                  <span class="zc-waiting-phase">${escapeHtml(gap.phase ? t(`company.build.phase_label.${gap.phase}`) : t('company.build.waiting.item'))}</span>
                  <span class="zc-waiting-message">${escapeHtml(gap.message || '')}</span>
                </li>
              `).join('')}
            </ul>
            ${this.canRetry() ? `
              <button type="button" class="zc-button zc-button-primary" data-build-retry${this.retrying ? ' disabled aria-busy="true"' : ''}>
                ${escapeHtml(this.retrying ? t('company.build.retry.running') : t('company.build.retry.button'))}
              </button>
            ` : ''}
          </section>
        ` : ''}

        ${!gaps.length && !running && build.phase_state === 'DONE' ? `
          <div class="zc-inline-notice zc-inline-notice-success" role="status">
            <strong>${escapeHtml(t('company.build.done.title'))}</strong>
            <span>${escapeHtml(t('company.build.done.body'))}</span>
          </div>
        ` : ''}

        <section class="zc-build-log" aria-labelledby="zcBuildLogTitle">
          <div class="zc-build-log-head">
            <h2 class="zc-section-title" id="zcBuildLogTitle">${escapeHtml(t('company.build.log.title'))}</h2>
            ${log.length > 8 ? `<button type="button" class="zc-link-button" id="zcBuildLogToggle" aria-expanded="${this.showAllLog ? 'true' : 'false'}">${escapeHtml(this.showAllLog ? t('company.build.log.less') : t('company.build.log.all'))}</button>` : ''}
          </div>
          ${visibleLog.length ? `
            <ol class="zc-log-list" aria-live="polite">
              ${visibleLog.map((entry) => `
                <li class="zc-log-item zc-log-${escapeHtml(entry.level || 'info')}">
                  <span class="zc-log-dot" aria-hidden="true"></span>
                  <span class="zc-log-time">${escapeHtml(formatTime(entry.at))}</span>
                  <span class="zc-log-message">${escapeHtml(entry.message || '')}</span>
                </li>
              `).join('')}
            </ol>
          ` : `<p class="zc-section-note">${escapeHtml(t('company.build.log.empty'))}</p>`}
        </section>

        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-quiet" id="zcBuildOverview">${escapeHtml(t('company.build.overview'))}</button>
          ${this.canRetry() ? `<button type="button" class="zc-button zc-button-primary" data-build-retry${this.retrying ? ' disabled aria-busy="true"' : ''}>${escapeHtml(this.retrying ? t('company.build.retry.running') : t('company.build.retry.button'))}</button>` : ''}
        </div>
        <p class="zc-form-footnote">${escapeHtml(t('company.build.footnote'))}</p>
      `;
    }

    _phaseHtml(phase) {
      const meta = phaseStateMeta(phase.state);
      const icon = phase.state === 'DONE' ? '✓' : (phase.state === 'FAILED' ? '!' : (phase.state === 'SKIPPED' ? '–' : (phase.state === 'RUNNING' ? '·' : '·')));
      const labelKey = `company.build.phase_label.${phase.id}`;
      const label = t(labelKey);
      return `
        <li class="zc-phase zc-phase-${meta.tone}${phase.state === 'RUNNING' ? ' is-running' : ''}">
          <span class="zc-phase-icon" aria-hidden="true">${icon}</span>
          <span class="zc-phase-body">
            <span class="zc-phase-head">
              <span class="zc-phase-label">${escapeHtml(label === labelKey ? (phase.label || phase.id) : label)}</span>
              <span class="zc-phase-state">${escapeHtml(t(meta.key))}</span>
            </span>
            ${phase.note ? `<span class="zc-phase-note">${escapeHtml(phase.note)}</span>` : ''}
            ${phase.description ? `<span class="zc-phase-description">${escapeHtml(phase.description)}</span>` : ''}
          </span>
        </li>
      `;
    }

    _readinessHtml(build) {
      const readiness = build && build.readiness;
      if (!readiness || readiness.score == null) return '';
      const score = Math.max(0, Math.min(100, Number(readiness.score) || 0));
      const band = String(readiness.band || '').toUpperCase();
      const bandKey = band === 'HIGH' ? 'high' : (band === 'MEDIUM' ? 'medium' : 'low');
      const reasons = Array.isArray(readiness.reasons) ? readiness.reasons : [];
      const counts = readiness.counts || {};
      return `
        <section class="zc-build-readiness" aria-labelledby="zcReadinessTitle">
          <div class="zc-build-summary-top">
            <h2 class="zc-section-title" id="zcReadinessTitle">${escapeHtml(t('company.build.readiness.title'))}</h2>
            <span class="zc-pill zc-pill-${band === 'HIGH' ? 'green' : (band === 'MEDIUM' ? 'orange' : 'neutral')}">${escapeHtml(t(`company.build.readiness.band.${bandKey}`))}</span>
          </div>
          <div class="zc-readiness-score">
            <div class="zc-readiness-ring" role="img" aria-label="${escapeHtml(t('company.build.readiness.value', { score }))}" style="--zc-readiness: ${score}">
              <span class="zc-readiness-number">${score}</span>
              <span class="zc-readiness-unit">/ 100</span>
            </div>
            <div class="zc-readiness-body">
              <p class="zc-readiness-counts">${escapeHtml(t('company.build.readiness.counts', {
                connected: Number(counts.sources_connected || 0),
                verified: Number(counts.sources_verified || 0),
                skipped: Number(counts.sources_skipped || 0),
                files: Number(counts.files || 0)
              }))}</p>
              ${reasons.length ? `
                <p class="zc-readiness-next-label">${escapeHtml(t('company.build.readiness.next'))}</p>
                <ul class="zc-readiness-reasons">
                  ${reasons.slice(0, 6).map((reason) => `
                    <li><strong>${escapeHtml(reason.label || reason.id)}</strong>${reason.detail ? ` — ${escapeHtml(reason.detail)}` : ''}</li>
                  `).join('')}
                </ul>
              ` : ''}
            </div>
          </div>
        </section>
      `;
    }

    _diagnosisHtml(build) {
      const diagnosis = build && build.diagnosis;
      if (!diagnosis || typeof diagnosis !== 'object') return '';
      const findings = Array.isArray(diagnosis.findings) ? diagnosis.findings : [];
      return `
        <section class="zc-build-diagnosis" aria-labelledby="zcDiagnosisTitle">
          <h2 class="zc-section-title" id="zcDiagnosisTitle">${escapeHtml(t('company.build.diagnosis.title'))}</h2>
          ${findings.length ? `
            <ul class="zc-diagnosis-list">
              ${findings.map((finding) => `
                <li class="zc-diagnosis-item">
                  <span class="zc-diagnosis-title">${escapeHtml(finding.title || finding.id || '')}</span>
                  ${finding.detail ? `<span class="zc-diagnosis-detail">${escapeHtml(finding.detail)}</span>` : ''}
                </li>
              `).join('')}
            </ul>
          ` : `
            <div class="zc-inline-notice zc-inline-notice-muted" role="status">
              <strong>${escapeHtml(t('company.build.diagnosis.unavailable'))}</strong>
              <span>${escapeHtml(t('company.build.diagnosis.none'))}</span>
            </div>
          `}
          ${diagnosis.reason ? `
            <p class="zc-diagnosis-reason"><span class="zc-diagnosis-reason-label">${escapeHtml(t('company.build.diagnosis.why'))}</span> ${escapeHtml(diagnosis.reason)}</p>
          ` : ''}
        </section>
      `;
    }

    _sourcesHtml(build) {
      const sources = build && Array.isArray(build.sources) ? build.sources : [];
      if (!sources.length) return '';
      return `
        <section class="zc-build-sources" aria-labelledby="zcSourcesTitle">
          <h2 class="zc-section-title" id="zcSourcesTitle">${escapeHtml(t('company.build.sources.title'))}</h2>
          <p class="zc-section-note">${escapeHtml(t('company.build.sources.note'))}</p>
          <ul class="zc-build-source-list">
            ${sources.map((source) => {
              const status = String(source.status || 'NOT_STARTED').toUpperCase();
              const key = status.toLowerCase();
              const tone = status === 'VERIFIED' ? 'green' : (status === 'SKIPPED' ? 'orange' : (status === 'NEEDS_CHECK' ? 'accent' : 'neutral'));
              return `
                <li class="zc-build-source">
                  <span class="zc-build-source-name">${escapeHtml(source.name || source.source_id || '')}</span>
                  <span class="zc-pill zc-pill-${tone}">${escapeHtml(t(`company.build.sources.status.${key}`))}</span>
                  ${source.skipped && source.skip_reason ? `<span class="zc-build-source-reason">${escapeHtml(source.skip_reason)}</span>` : ''}
                </li>
              `;
            }).join('')}
          </ul>
        </section>
      `;
    }

    _bind(container) {
      const back = container.querySelector('#zcBuildBack');
      if (back) back.addEventListener('click', () => this._navigate(`/company/${this.companyId}/overview`));
      const emptyBack = container.querySelector('#zcBuildEmptyBack');
      if (emptyBack) emptyBack.addEventListener('click', () => this._navigate(`/company/${this.companyId}/overview`));
      const overview = container.querySelector('#zcBuildOverview');
      if (overview) overview.addEventListener('click', () => this._navigate(`/company/${this.companyId}/overview`));
      const errorBack = container.querySelector('#zcBuildErrorBack');
      if (errorBack) errorBack.addEventListener('click', () => this._navigate('/company'));

      const reload = container.querySelector('#zcBuildReload');
      if (reload) reload.addEventListener('click', () => this._load());

      container.querySelectorAll('[data-language]').forEach((button) => {
        button.addEventListener('click', () => {
          if (window.I18n && window.I18n.setLanguage) window.I18n.setLanguage(button.getAttribute('data-language'));
        });
      });

      container.querySelectorAll('[data-build-retry]').forEach((button) => {
        button.addEventListener('click', () => this.retry());
      });

      const logToggle = container.querySelector('#zcBuildLogToggle');
      if (logToggle) {
        logToggle.addEventListener('click', () => {
          this.showAllLog = !this.showAllLog;
          this._render();
        });
      }
    }

    _navigate(path) {
      this.destroy();
      if (typeof window.navigateTo === 'function') window.navigateTo(path);
      else window.location.hash = `#${path}`;
    }

    _toast(message, tone) {
      if (window.UI && typeof window.UI.showToast === 'function') {
        window.UI.showToast(message, tone || 'info');
      }
    }
  }

  window.CompanySetupProgress = new CompanyBuildProgress();
})();
