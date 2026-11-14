/**
 * ZONATA — Add an existing company
 *
 * Three steps on one phone-friendly column:
 *
 *   1. The business   — facts the server needs to onboard it.
 *   2. Data sources   — the eight catalogue entries, each with what ZONATA
 *                       would read, why it helps and what is never copied.
 *                       Every source can be connected later or skipped with a
 *                       reason; nothing is required and nothing is simulated.
 *   3. Review         — exactly what will be saved, then create + submit.
 *
 * Submitting creates the company, records the chosen connections and skip
 * reasons, then starts the real onboarding workflow. Anything that needs a
 * provider adapter is reported as waiting, never as done.
 *
 * Routes: /company/existing
 */

(function() {
  'use strict';

  const DRAFT_ID_KEY = 'zonata_company_existing_draft_id';
  const DRAFT_DATA_KEY = 'zonata_company_existing_draft_data';
  const SAVE_DELAY = 700;

  const COUNTRIES = ['IN', 'AE', 'GB', 'US', 'SG', 'AU', 'CA', 'DE', 'FR', 'SA', 'QA', 'KW', 'OM', 'BH'];
  const CURRENCIES = ['INR', 'USD', 'AED', 'GBP', 'EUR', 'SGD', 'AUD', 'CAD', 'SAR', 'QAR', 'KWD', 'OMR', 'BHD'];
  const PERIODS = ['DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUAL', 'ONE_TIME'];
  const MIN_REASON = 5;

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

  function formatMoney(amount, currency, options) {
    const value = Number(amount);
    if (!Number.isFinite(value)) return '';
    if (window.I18n && window.I18n.formatCurrency) {
      return window.I18n.formatCurrency(value, currency || 'INR', options);
    }
    return `${currency || 'INR'} ${value}`;
  }

  function decodeTokenRole() {
    let token = '';
    try {
      token = localStorage.getItem('zonata_auth_token') || '';
      if (!token && window.state && window.state.host) token = window.state.host.token || '';
    } catch (err) {
      token = '';
    }
    if (!token || token.indexOf('.') < 0) return {};
    try {
      const payload = JSON.parse(token.slice(0, token.lastIndexOf('.')));
      return { role: payload.role, user_id: payload.user_id, principal_type: payload.principal_type };
    } catch (err) {
      return {};
    }
  }

  function viewer() {
    const host = (window.state && window.state.host) || {};
    const token = decodeTokenRole();
    const role = String(host.role || token.role || '').toUpperCase();
    const userId = String(host.user_id || host.id || token.user_id || '');
    const principalType = String(host.principal_type || token.principal_type || 'USER').toUpperCase();
    const agent = principalType.indexOf('AGENT') >= 0
      || role.indexOf('AGENT') >= 0
      || /^(agent_|agt_|ai_agent_)/i.test(userId);
    const allowedRoles = ['OWNER', 'SOVEREIGN_HOST', 'GLOBAL_ADMIN', 'EXECUTIVE'];
    return { role, userId, agent, allowed: !agent && (role === '' || allowedRoles.indexOf(role) >= 0) };
  }

  function emailOk(value) {
    return /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/.test(String(value || '').trim());
  }

  function urlOk(value) {
    return /^https?:\/\/[^\s<>"']{3,2048}$/i.test(String(value || '').trim());
  }

  function emptySources() {
    const map = {};
    const ids = ['accounting', 'banking', 'payments', 'commerce', 'crm', 'workspace', 'communications', 'uploads'];
    ids.forEach((id) => {
      map[id] = { choice: 'later', reason: '' };
    });
    return map;
  }

  function emptyData() {
    return {
      name: '',
      title: '',
      description: '',
      industry: '',
      country: 'IN',
      website: '',
      business_model: '',
      revenue_amount: '',
      revenue_currency: 'INR',
      revenue_period: 'ANNUAL',
      owner_name: '',
      owner_email: '',
      owner_role: '',
      sources: emptySources()
    };
  }

  function normaliseData(raw) {
    const data = emptyData();
    if (!raw || typeof raw !== 'object') return data;
    Object.keys(data).forEach((key) => {
      if (key === 'sources') return;
      if (raw[key] !== undefined && raw[key] !== null && typeof data[key] !== 'object') {
        data[key] = raw[key];
      }
    });
    if (raw.owner && typeof raw.owner === 'object') {
      if (raw.owner.name != null) data.owner_name = String(raw.owner.name);
      if (raw.owner.email != null) data.owner_email = String(raw.owner.email);
      if (raw.owner.role != null) data.owner_role = String(raw.owner.role);
    }
    if (raw.revenue && typeof raw.revenue === 'object') {
      if (raw.revenue.amount != null) data.revenue_amount = raw.revenue.amount;
      if (raw.revenue.currency) data.revenue_currency = String(raw.revenue.currency).toUpperCase();
      if (raw.revenue.period) data.revenue_period = String(raw.revenue.period).toUpperCase();
    }
    const incoming = Array.isArray(raw.sources) ? raw.sources : [];
    incoming.forEach((item) => {
      if (!item || !item.source_id || !data.sources[item.source_id]) return;
      const choice = String(item.choice || 'later').toLowerCase();
      if (choice !== 'connect' && choice !== 'skip') return;
      data.sources[item.source_id] = { choice, reason: String(item.reason || '') };
    });
    if (PERIODS.indexOf(data.revenue_period) < 0) data.revenue_period = 'ANNUAL';
    if (CURRENCIES.indexOf(data.revenue_currency) < 0) data.revenue_currency = 'INR';
    return data;
  }

  class ExistingCompanyFlow {
    constructor() {
      this.containerId = null;
      this.companyId = null;
      this.step = 'details';
      this.errors = {};
      this.sourceErrors = {};
      this.submitting = false;
      this.catalogue = null;
      this.catalogueError = null;
      this.catalogueLoading = false;
      this.draftId = null;
      this.saving = false;
      this.saveState = 'idle';
      this.saveTimer = null;
      this._onLanguageChange = this._onLanguageChange.bind(this);
      if (document && document.addEventListener) {
        document.addEventListener('zonata:languagechange', this._onLanguageChange);
      }
    }

    _onLanguageChange() {
      if (!this.containerId) return;
      const container = document.getElementById(this.containerId);
      if (container && container.querySelector('[data-company-existing]')) {
        this.render(this.containerId);
      }
    }

    data() {
      if (!this._data) this._data = emptyData();
      return this._data;
    }

    sources() {
      return this.data().sources;
    }

    // ------------------------------------------------------------ rendering
    render(containerOrId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;
      if (!container) return;
      this.containerId = container.id || this.containerId;

      const access = viewer();
      if (!access.allowed) {
        container.innerHTML = this._deniedHtml();
        this._bind(container);
        return;
      }

      this._restoreLocalDraft();
      if (!this._loadedRemote) {
        this._loadedRemote = true;
        this._loadRemoteDraft().then((loaded) => {
          if (loaded && this.containerId) this.render(this.containerId);
        });
      }

      if (this.step === 'sources' && !this.catalogue && !this.catalogueLoading && !this.catalogueError) {
        this.loadCatalogue();
      }

      let inner;
      if (this.step === 'review') inner = this._reviewHtml();
      else if (this.step === 'sources') inner = this._sourcesHtml();
      else inner = this._detailsHtml();

      container.innerHTML = `
        <div class="zc-flow-page" data-company-existing>
          ${this._topHtml()}
          ${inner}
        </div>
      `;
      this._bind(container);
      if (this.step === 'review') window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    _topHtml() {
      return `
        <div class="zc-flow-top">
          <button type="button" class="zc-back-link" id="zcExistingBack">
            <span class="zc-back-arrow" aria-hidden="true">←</span>
            <span>${escapeHtml(t('company.existing.back'))}</span>
          </button>
          <div class="zc-language-toggle" role="group" aria-label="${escapeHtml(t('common.language'))}">
            <button type="button" data-language="en" aria-pressed="${language() === 'en' ? 'true' : 'false'}">${escapeHtml(t('common.english'))}</button>
            <button type="button" data-language="ar" aria-pressed="${language() === 'ar' ? 'true' : 'false'}">${escapeHtml(t('common.arabic'))}</button>
          </div>
        </div>
      `;
    }

    _stepperHtml() {
      const order = ['details', 'sources', 'review'];
      const index = order.indexOf(this.step);
      const labels = [
        t('company.existing.step.business'),
        t('company.existing.step.sources'),
        t('company.existing.step.review')
      ];
      return `
        <ol class="zc-steps" aria-label="${escapeHtml(t('company.existing.steps_label'))}">
          ${labels.map((label, i) => {
            const state = i < index ? 'is-done' : (i === index ? 'is-current' : '');
            return `
              <li class="zc-step ${state}" ${i === index ? 'aria-current="step"' : ''}>
                <span class="zc-step-dot" aria-hidden="true">${i < index ? '✓' : i + 1}</span>
                <span>${escapeHtml(label)}</span>
              </li>
            `;
          }).join('')}
        </ol>
      `;
    }

    _fieldHtml(opts) {
      const {
        name, label, hint, example, value, type, required, multiline, rows,
        autocomplete, inputmode, placeholder
      } = opts;
      const error = this.errors[name];
      const describedBy = [];
      if (hint) describedBy.push(`zcExistHint-${name}`);
      if (error) describedBy.push(`zcExistErr-${name}`);
      const hintHtml = hint
        ? `<p class="zc-field-hint" id="zcExistHint-${name}">${escapeHtml(hint)}${example ? ` <span class="zc-field-example">${escapeHtml(t('company.create.example', { example }))}</span>` : ''}</p>`
        : '';
      const errorHtml = `<p class="zc-field-error" id="zcExistErr-${name}" role="alert"${error ? '' : ' hidden'}>${escapeHtml(error || '')}</p>`;
      const shared = `id="zcExistField-${name}" name="${name}" data-field="${name}"`;
      const aria = `aria-describedby="${describedBy.join(' ')}" aria-invalid="${error ? 'true' : 'false'}"${required ? ' aria-required="true"' : ''}`;
      const control = multiline
        ? `<textarea class="zc-input zc-textarea" ${shared} rows="${rows || 4}" ${aria}${autocomplete ? ` autocomplete="${autocomplete}"` : ''}${placeholder ? ` placeholder="${escapeHtml(placeholder)}"` : ''}>${escapeHtml(value == null ? '' : value)}</textarea>`
        : `<input class="zc-input" ${shared} type="${type || 'text'}" value="${escapeHtml(value == null ? '' : value)}" ${aria}${autocomplete ? ` autocomplete="${autocomplete}"` : ''}${inputmode ? ` inputmode="${inputmode}"` : ''}${placeholder ? ` placeholder="${escapeHtml(placeholder)}"` : ''} />`;
      const optional = required ? '' : `<span class="zc-optional">${escapeHtml(t('company.create.optional'))}</span>`;
      return `
        <div class="zc-field${error ? ' has-error' : ''}">
          <label class="zc-label" for="zcExistField-${name}">${escapeHtml(label)}${required ? ' <span class="zc-required" aria-hidden="true">*</span>' : ''}${optional}</label>
          ${control}
          ${hintHtml}
          ${errorHtml}
        </div>
      `;
    }

    _selectHtml(opts) {
      const { name, label, hint, value, options, required } = opts;
      const error = this.errors[name];
      return `
        <div class="zc-field${error ? ' has-error' : ''}">
          <label class="zc-label" for="zcExistField-${name}">${escapeHtml(label)}${required ? ' <span class="zc-required" aria-hidden="true">*</span>' : ''}</label>
          <select class="zc-input zc-select" id="zcExistField-${name}" name="${name}" data-field="${name}" aria-invalid="${error ? 'true' : 'false'}">
            ${options.map((option) => {
              const valueKey = option.value;
              const labelKey = option.label || valueKey;
              return `<option value="${escapeHtml(valueKey)}"${String(value || '') === valueKey ? ' selected' : ''}>${escapeHtml(labelKey)}</option>`;
            }).join('')}
          </select>
          ${hint ? `<p class="zc-field-hint">${escapeHtml(hint)}</p>` : ''}
          <p class="zc-field-error" id="zcExistErr-${name}" role="alert"${error ? '' : ' hidden'}>${escapeHtml(error || '')}</p>
        </div>
      `;
    }

    _detailsHtml() {
      const data = this.data();
      return `
        <header class="zc-flow-header">
          <h1 class="zc-flow-title">${escapeHtml(t('company.existing.title'))}</h1>
          <p class="zc-flow-subtitle">${escapeHtml(t('company.existing.subtitle'))}</p>
          ${this._stepperHtml()}
        </header>

        <p class="zc-save-state" id="zcExistSaveState" role="status" aria-live="polite">${escapeHtml(this._saveStateText())}</p>

        ${this._errorSummaryHtml()}

        <form id="zcExistingForm" class="zc-form" novalidate>
          <section class="zc-form-section" aria-labelledby="zcExistSectionBasics">
            <h2 class="zc-section-title" id="zcExistSectionBasics">${escapeHtml(t('company.existing.basics.title'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.existing.basics.note'))}</p>

            ${this._fieldHtml({
              name: 'name',
              label: t('company.existing.name.label'),
              hint: t('company.existing.name.hint'),
              example: 'Northwind Traders',
              value: data.name,
              required: true,
              autocomplete: 'organization'
            })}

            ${this._fieldHtml({
              name: 'title',
              label: t('company.create.tagline.label'),
              hint: t('company.create.tagline.hint'),
              example: t('company.create.tagline.example'),
              value: data.title,
              required: true
            })}

            ${this._fieldHtml({
              name: 'description',
              label: t('company.existing.description.label'),
              hint: t('company.existing.description.hint'),
              example: t('company.create.description.example'),
              value: data.description,
              required: true,
              multiline: true,
              rows: 5
            })}

            <div class="zc-field-row">
              ${this._fieldHtml({
                name: 'country',
                label: t('company.create.country.label'),
                hint: t('company.create.country.hint'),
                example: COUNTRIES.slice(0, 4).join(', '),
                value: data.country,
                required: true,
                autocomplete: 'country'
              })}
              ${this._fieldHtml({
                name: 'industry',
                label: t('company.create.industry.label'),
                hint: t('company.create.industry.hint'),
                example: t('company.create.industry.example'),
                value: data.industry,
                required: true
              })}
            </div>

            ${this._fieldHtml({
              name: 'website',
              label: t('company.create.website.label'),
              hint: t('company.create.website.hint'),
              example: 'https://example.com',
              value: data.website,
              type: 'url',
              autocomplete: 'url',
              inputmode: 'url'
            })}
          </section>

          <section class="zc-form-section" aria-labelledby="zcExistSectionModel">
            <h2 class="zc-section-title" id="zcExistSectionModel">${escapeHtml(t('company.existing.model.title'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.existing.model.note'))}</p>

            ${this._fieldHtml({
              name: 'business_model',
              label: t('company.existing.model.label'),
              hint: t('company.existing.model.hint'),
              example: t('company.existing.model.example'),
              value: data.business_model,
              required: true,
              multiline: true,
              rows: 4
            })}

            <div class="zc-field-row zc-field-row-revenue">
              ${this._fieldHtml({
                name: 'revenue_amount',
                label: t('company.existing.revenue.label'),
                hint: t('company.existing.revenue.hint'),
                value: data.revenue_amount,
                type: 'number',
                inputmode: 'decimal',
                required: true
              })}
              ${this._selectHtml({
                name: 'revenue_currency',
                label: t('company.existing.revenue.currency'),
                value: data.revenue_currency,
                options: CURRENCIES.map((code) => ({ value: code })),
                required: true
              })}
              ${this._selectHtml({
                name: 'revenue_period',
                label: t('company.existing.revenue.period'),
                value: data.revenue_period,
                options: PERIODS.map((period) => ({ value: period, label: t(`company.existing.period.${period.toLowerCase()}`) })),
                required: true
              })}
            </div>
            <p class="zc-revenue-preview" id="zcRevenuePreview" aria-live="polite">${escapeHtml(this._revenuePreview())}</p>
          </section>

          <section class="zc-form-section" aria-labelledby="zcExistSectionOwner">
            <h2 class="zc-section-title" id="zcExistSectionOwner">${escapeHtml(t('company.existing.owner.title'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.existing.owner.note'))}</p>

            ${this._fieldHtml({
              name: 'owner_name',
              label: t('company.create.owner.label'),
              hint: t('company.create.owner.hint'),
              value: data.owner_name,
              required: true,
              autocomplete: 'name'
            })}
            <div class="zc-field-row">
              ${this._fieldHtml({
                name: 'owner_role',
                label: t('company.create.role.label'),
                hint: t('company.existing.owner.role_hint'),
                example: t('company.create.role.example'),
                value: data.owner_role,
                required: true,
                autocomplete: 'organization-title'
              })}
              ${this._fieldHtml({
                name: 'owner_email',
                label: t('company.create.email.label'),
                hint: t('company.existing.owner.email_hint'),
                example: t('company.create.email.example'),
                value: data.owner_email,
                type: 'email',
                autocomplete: 'email',
                inputmode: 'email'
              })}
            </div>
          </section>

          <div class="zc-form-actions">
            <button type="button" class="zc-button zc-button-quiet" id="zcExistingCancel">${escapeHtml(t('common.cancel'))}</button>
            <button type="submit" class="zc-button zc-button-primary" id="zcExistingNext">${escapeHtml(t('company.existing.next'))}</button>
          </div>
          <p class="zc-form-footnote">${escapeHtml(t('company.existing.footnote'))}</p>
        </form>
      `;
    }

    _sourcesHtml() {
      const loading = this.catalogueLoading;
      const error = this.catalogueError;
      const catalogue = this.catalogue || [];
      return `
        <header class="zc-flow-header">
          <h1 class="zc-flow-title">${escapeHtml(t('company.existing.sources.title'))}</h1>
          <p class="zc-flow-subtitle">${escapeHtml(t('company.existing.sources.subtitle'))}</p>
          ${this._stepperHtml()}
        </header>

        <div class="zc-inline-notice zc-inline-notice-muted" role="note">
          <strong>${escapeHtml(t('company.existing.sources.promise_title'))}</strong>
          <span>${escapeHtml(t('company.existing.sources.promise_body'))}</span>
        </div>

        ${loading ? `
          <div class="zc-skeleton-stack" aria-hidden="true">
            <span class="zc-skeleton"></span>
            <span class="zc-skeleton"></span>
            <span class="zc-skeleton"></span>
          </div>
          <p class="zc-section-note" role="status">${escapeHtml(t('company.existing.sources.loading'))}</p>
        ` : ''}

        ${error ? `
          <div class="zc-inline-notice zc-inline-notice-warning" role="alert">
            <strong>${escapeHtml(t('company.existing.sources.unavailable_title'))}</strong>
            <span>${escapeHtml(t('company.existing.sources.unavailable_body'))}</span>
            <button type="button" class="zc-link-button" id="zcSourcesReload">${escapeHtml(t('common.retry'))}</button>
          </div>
        ` : ''}

        ${!loading && catalogue.length ? `
          <p class="zc-source-counts" id="zcSourceCounts" role="status" aria-live="polite">${escapeHtml(this._sourceCountsText())}</p>
          <ul class="zc-source-list">
            ${catalogue.map((source) => this._sourceCardHtml(source)).join('')}
          </ul>
        ` : ''}

        ${!loading && !catalogue.length && !error ? `
          <div class="zc-empty-card" role="status">
            <p>${escapeHtml(t('company.existing.sources.none'))}</p>
          </div>
        ` : ''}

        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-quiet" id="zcSourcesBack">${escapeHtml(t('common.back'))}</button>
          <button type="button" class="zc-button zc-button-primary" id="zcSourcesReview">${escapeHtml(t('company.existing.review_button'))}</button>
        </div>
        <p class="zc-form-footnote">${escapeHtml(t('company.existing.sources.footnote'))}</p>
      `;
    }

    _sourceCardHtml(source) {
      const state = this.sources()[source.id] || { choice: 'later', reason: '' };
      const choice = state.choice || 'later';
      const error = this.sourceErrors[source.id];
      const tone = choice === 'connect' ? 'accent' : (choice === 'skip' ? 'orange' : 'neutral');
      const statusKey = choice === 'connect'
        ? 'company.existing.sources.status.connect'
        : (choice === 'skip' ? 'company.existing.sources.status.skip' : 'company.existing.sources.status.later');
      const examples = Array.isArray(source.examples) ? source.examples.join(' · ') : '';
      return `
        <li class="zc-source-card${choice !== 'later' ? ` is-${choice}` : ''}" data-source-card="${escapeHtml(source.id)}">
          <div class="zc-source-head">
            <div class="zc-source-heading">
              <span class="zc-source-category">${escapeHtml(t(`company.existing.sources.category.${String(source.category || '').toLowerCase()}`))}</span>
              <h3 class="zc-source-name">${escapeHtml(source.name)}</h3>
              ${examples ? `<p class="zc-source-examples">${escapeHtml(examples)}</p>` : ''}
            </div>
            <span class="zc-pill zc-pill-${tone}" data-source-status>${escapeHtml(t(statusKey))}</span>
          </div>

          <dl class="zc-source-facts">
            <div><dt>${escapeHtml(t('company.existing.sources.reads'))}</dt><dd>${escapeHtml(source.reads)}</dd></div>
            <div><dt>${escapeHtml(t('company.existing.sources.why'))}</dt><dd>${escapeHtml(source.why)}</dd></div>
            <div><dt>${escapeHtml(t('company.existing.sources.never'))}</dt><dd>${escapeHtml(source.never)}</dd></div>
          </dl>

          <div class="zc-source-choice" role="group" aria-label="${escapeHtml(t('company.existing.sources.choice_label', { name: source.name }))}">
            <button type="button" class="zc-source-choice-button" data-source-choice="connect" data-source-id="${escapeHtml(source.id)}" aria-pressed="${choice === 'connect' ? 'true' : 'false'}">${escapeHtml(t('company.existing.sources.choice.connect'))}</button>
            <button type="button" class="zc-source-choice-button" data-source-choice="skip" data-source-id="${escapeHtml(source.id)}" aria-pressed="${choice === 'skip' ? 'true' : 'false'}">${escapeHtml(t('company.existing.sources.choice.skip'))}</button>
            <button type="button" class="zc-source-choice-button" data-source-choice="later" data-source-id="${escapeHtml(source.id)}" aria-pressed="${choice === 'later' ? 'true' : 'false'}">${escapeHtml(t('company.existing.sources.choice.later'))}</button>
          </div>

          <div class="zc-source-reason" data-source-reason-box="${escapeHtml(source.id)}"${choice === 'skip' ? '' : ' hidden'}>
            <label class="zc-label" for="zcSourceReason-${escapeHtml(source.id)}">${escapeHtml(t('company.existing.sources.reason.label'))} <span class="zc-required" aria-hidden="true">*</span></label>
            <textarea class="zc-input zc-textarea" id="zcSourceReason-${escapeHtml(source.id)}" rows="2" data-source-reason="${escapeHtml(source.id)}" aria-invalid="${error ? 'true' : 'false'}">${escapeHtml(state.reason || '')}</textarea>
            <p class="zc-field-hint">${escapeHtml(t('company.existing.sources.reason.hint'))}</p>
            <p class="zc-field-error" id="zcSourceReasonErr-${escapeHtml(source.id)}" role="alert"${error ? '' : ' hidden'}>${escapeHtml(error || '')}</p>
          </div>
        </li>
      `;
    }

    _reviewHtml() {
      const data = this.data();
      const catalogue = this.catalogue || [];
      const chosen = catalogue.filter((source) => {
        const state = this.sources()[source.id];
        return state && state.choice && state.choice !== 'later';
      });
      const revenue = data.revenue_amount === ''
        ? t('company.create.review.not_set')
        : `${formatMoney(data.revenue_amount, data.revenue_currency)} / ${t(`company.existing.period.${String(data.revenue_period).toLowerCase()}`)}`;
      return `
        <header class="zc-flow-header">
          <h1 class="zc-flow-title">${escapeHtml(t('company.existing.review.title'))}</h1>
          <p class="zc-flow-subtitle">${escapeHtml(t('company.existing.review.subtitle'))}</p>
          ${this._stepperHtml()}
        </header>

        ${this._errorSummaryHtml()}

        <div class="zc-review" role="region" aria-label="${escapeHtml(t('company.existing.review.region'))}">
          <section class="zc-review-block">
            <div class="zc-review-head">
              <h2>${escapeHtml(t('company.existing.review.basics'))}</h2>
              <button type="button" class="zc-link-button" data-edit-step="details">${escapeHtml(t('company.create.review.edit'))}</button>
            </div>
            <dl class="zc-review-list">
              <div><dt>${escapeHtml(t('company.create.name.label'))}</dt><dd>${escapeHtml(data.name)}</dd></div>
              <div><dt>${escapeHtml(t('company.create.tagline.label'))}</dt><dd>${escapeHtml(data.title)}</dd></div>
              <div><dt>${escapeHtml(t('company.create.where.title'))}</dt><dd>${escapeHtml([data.country, data.industry].filter(Boolean).join(' · '))}</dd></div>
              <div><dt>${escapeHtml(t('company.existing.revenue.label'))}</dt><dd>${escapeHtml(revenue)}</dd></div>
              <div><dt>${escapeHtml(t('company.existing.owner.title'))}</dt><dd>${escapeHtml([data.owner_name, data.owner_role].filter(Boolean).join(' · ') || t('company.create.review.not_set'))}</dd></div>
              ${data.owner_email ? `<div><dt>${escapeHtml(t('company.create.email.label'))}</dt><dd>${escapeHtml(data.owner_email)}</dd></div>` : ''}
            </dl>
            <div class="zc-review-description">
              <p class="zc-review-description-label">${escapeHtml(t('company.existing.model.label'))}</p>
              <p>${escapeHtml(data.business_model)}</p>
            </div>
          </section>

          <section class="zc-review-block">
            <div class="zc-review-head">
              <h2>${escapeHtml(t('company.existing.review.sources'))}</h2>
              <button type="button" class="zc-link-button" data-edit-step="sources">${escapeHtml(t('company.create.review.edit'))}</button>
            </div>
            ${chosen.length ? `
              <ul class="zc-review-sources">
                ${chosen.map((source) => {
                  const state = this.sources()[source.id];
                  const isSkip = state.choice === 'skip';
                  return `
                    <li class="zc-review-source">
                      <span class="zc-pill zc-pill-${isSkip ? 'orange' : 'accent'}">${escapeHtml(t(isSkip ? 'company.existing.sources.status.skip' : 'company.existing.sources.status.connect'))}</span>
                      <span class="zc-review-source-name">${escapeHtml(source.name)}</span>
                      ${isSkip && state.reason ? `<span class="zc-review-source-reason">${escapeHtml(state.reason)}</span>` : ''}
                    </li>
                  `;
                }).join('')}
              </ul>
            ` : `<p class="zc-section-note">${escapeHtml(t('company.existing.review.sources_none'))}</p>`}
          </section>

          <section class="zc-review-block zc-review-next">
            <h2>${escapeHtml(t('company.existing.review.next.title'))}</h2>
            <ul class="zc-review-next-list">
              <li>${escapeHtml(t('company.existing.review.next.one'))}</li>
              <li>${escapeHtml(t('company.existing.review.next.two'))}</li>
              <li>${escapeHtml(t('company.existing.review.next.three'))}</li>
            </ul>
            <p class="zc-review-estimate">${escapeHtml(t('company.existing.review.next.note'))}</p>
          </section>
        </div>

        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-quiet" id="zcReviewBack">${escapeHtml(t('common.back'))}</button>
          <button type="button" class="zc-button zc-button-primary" id="zcExistingSubmit"${this.submitting ? ' disabled aria-busy="true"' : ''}>
            ${escapeHtml(this.submitting ? t('company.existing.submitting') : t('company.existing.submit'))}
          </button>
        </div>
        <p class="zc-form-footnote">${escapeHtml(t('company.existing.review.footnote'))}</p>
      `;
    }

    _errorSummaryHtml() {
      const fields = Object.keys(this.errors);
      if (!fields.length) return '';
      return `
        <div class="zc-inline-notice zc-inline-notice-error" role="alert" id="zcExistingErrors">
          <strong>${escapeHtml(t('company.create.errors.title'))}</strong>
          <ul class="zc-error-list">
            ${fields.map((field) => `<li><a href="#zcExistField-${escapeHtml(field)}" data-error-field="${escapeHtml(field)}">${escapeHtml(this.errors[field])}</a></li>`).join('')}
          </ul>
        </div>
      `;
    }

    _deniedHtml() {
      return `
        <div class="zc-flow-page" data-company-existing>
          <div class="zc-inline-notice zc-inline-notice-warning" role="status">
            <strong>${escapeHtml(t('company.existing.denied.title'))}</strong>
            <span>${escapeHtml(t('company.existing.denied.body'))}</span>
            <button type="button" class="zc-link-button" id="zcExistingDeniedBack">${escapeHtml(t('company.existing.back'))}</button>
          </div>
        </div>
      `;
    }

    _revenuePreview() {
      const data = this.data();
      const amount = Number(data.revenue_amount);
      if (!Number.isFinite(amount) || amount <= 0) return t('company.existing.revenue.preview_empty');
      return t('company.existing.revenue.preview', {
        amount: formatMoney(amount, data.revenue_currency),
        compact: formatMoney(amount, data.revenue_currency, { compact: true }),
        period: t(`company.existing.period.${String(data.revenue_period).toLowerCase()}`)
      });
    }

    _sourceCountsText() {
      const entries = Object.keys(this.sources()).map((id) => this.sources()[id]);
      const connect = entries.filter((item) => item.choice === 'connect').length;
      const skip = entries.filter((item) => item.choice === 'skip').length;
      const later = entries.length - connect - skip;
      return t('company.existing.sources.counts', { connect, skip, later });
    }

    _saveStateText() {
      if (this.saving) return t('company.create.draft.saving');
      if (this.saveState === 'saved') return t('company.create.draft.saved');
      if (this.saveState === 'local') return t('company.create.draft.local');
      if (this.saveState === 'error') return t('company.create.draft.error');
      return t('company.create.draft.idle');
    }

    // ------------------------------------------------------------- binding
    _bind(container) {
      const back = container.querySelector('#zcExistingBack');
      if (back) back.addEventListener('click', () => this._goBack());
      const deniedBack = container.querySelector('#zcExistingDeniedBack');
      if (deniedBack) deniedBack.addEventListener('click', () => this._goBack());

      container.querySelectorAll('[data-language]').forEach((button) => {
        button.addEventListener('click', () => {
          if (window.I18n && window.I18n.setLanguage) window.I18n.setLanguage(button.getAttribute('data-language'));
        });
      });

      const form = container.querySelector('#zcExistingForm');
      if (form) {
        form.addEventListener('submit', (event) => {
          event.preventDefault();
          this.toSources();
        });
        form.addEventListener('input', (event) => this._onInput(event));
        form.addEventListener('change', (event) => this._onInput(event));
        form.addEventListener('focusout', (event) => {
          const target = event.target;
          if (target && target.getAttribute && target.getAttribute('data-field')) {
            this._validateField(target.getAttribute('data-field'));
          }
        });
      }

      const cancel = container.querySelector('#zcExistingCancel');
      if (cancel) cancel.addEventListener('click', () => this._goBack());

      const reload = container.querySelector('#zcSourcesReload');
      if (reload) reload.addEventListener('click', () => this.loadCatalogue());

      const sourcesBack = container.querySelector('#zcSourcesBack');
      if (sourcesBack) sourcesBack.addEventListener('click', () => this.toDetails());

      const sourcesReview = container.querySelector('#zcSourcesReview');
      if (sourcesReview) sourcesReview.addEventListener('click', () => this.toReview());

      container.querySelectorAll('[data-source-choice]').forEach((button) => {
        button.addEventListener('click', () => {
          this._setSourceChoice(button.getAttribute('data-source-id'), button.getAttribute('data-source-choice'));
        });
      });

      container.querySelectorAll('[data-source-reason]').forEach((input) => {
        input.addEventListener('input', () => {
          const id = input.getAttribute('data-source-reason');
          if (!this.sources()[id]) return;
          this.sources()[id].reason = input.value;
          if (this.sourceErrors[id] && String(input.value).trim().length >= MIN_REASON) {
            delete this.sourceErrors[id];
            const el = document.getElementById(`zcSourceReasonErr-${id}`);
            if (el) { el.textContent = ''; el.hidden = true; }
            input.setAttribute('aria-invalid', 'false');
          }
          this._updateSourceCounts();
          this._scheduleSave();
        });
      });

      container.querySelectorAll('[data-edit-step]').forEach((button) => {
        button.addEventListener('click', () => {
          this.step = button.getAttribute('data-edit-step') === 'sources' ? 'sources' : 'details';
          this.render(this.containerId);
        });
      });

      container.querySelectorAll('[data-error-field]').forEach((link) => {
        link.addEventListener('click', (event) => {
          event.preventDefault();
          this._focusField(link.getAttribute('data-error-field'));
        });
      });

      const reviewBack = container.querySelector('#zcReviewBack');
      if (reviewBack) reviewBack.addEventListener('click', () => {
        this.step = 'sources';
        this.render(this.containerId);
      });

      const submit = container.querySelector('#zcExistingSubmit');
      if (submit) submit.addEventListener('click', () => this.submit());
    }

    _onInput(event) {
      const target = event.target;
      if (!target || !target.getAttribute) return;
      const field = target.getAttribute('data-field');
      if (!field) return;
      this.data()[field] = target.value;
      if (this.errors[field]) {
        delete this.errors[field];
        const el = document.getElementById(`zcExistErr-${field}`);
        if (el) { el.textContent = ''; el.hidden = true; }
        const wrap = target.closest ? target.closest('.zc-field') : null;
        if (wrap) wrap.classList.remove('has-error');
        target.setAttribute('aria-invalid', 'false');
      }
      if (field === 'revenue_amount' || field === 'revenue_currency' || field === 'revenue_period') {
        const preview = document.getElementById('zcRevenuePreview');
        if (preview) preview.textContent = this._revenuePreview();
      }
      this.saveState = 'idle';
      this._scheduleSave();
    }

    // ---------------------------------------------------------- navigation
    toDetails() {
      this.step = 'details';
      this.render(this.containerId);
    }

    toSources() {
      this.errors = this._validate();
      const fields = Object.keys(this.errors);
      if (fields.length) {
        this.step = 'details';
        this.render(this.containerId);
        this._focusField(fields[0]);
        return false;
      }
      this.step = 'sources';
      this.saveDraft();
      this.render(this.containerId);
      return true;
    }

    toReview() {
      const invalid = this._validateSources();
      this.sourceErrors = invalid;
      if (Object.keys(invalid).length) {
        this.step = 'sources';
        this.render(this.containerId);
        const first = Object.keys(invalid)[0];
        const box = window.document.querySelector(`[data-source-card="${first}"]`);
        if (box && box.scrollIntoView) box.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const input = document.getElementById(`zcSourceReason-${first}`);
        if (input && input.focus) input.focus();
        return false;
      }
      this.step = 'review';
      this.saveDraft();
      this.render(this.containerId);
      return true;
    }

    _focusField(field) {
      const el = document.getElementById(`zcExistField-${field}`);
      if (el && el.focus) {
        el.focus();
        if (el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      const summary = document.getElementById('zcExistingErrors');
      if (summary && summary.focus) summary.focus();
    }

    // ---------------------------------------------------------- validation
    _validateField(field) {
      const errors = this._validate({ only: field });
      if (errors[field]) {
        this.errors[field] = errors[field];
        const el = document.getElementById(`zcExistErr-${field}`);
        if (el) { el.textContent = errors[field]; el.hidden = false; }
        const input = document.getElementById(`zcExistField-${field}`);
        if (input) {
          input.setAttribute('aria-invalid', 'true');
          if (input.closest) {
            const wrap = input.closest('.zc-field');
            if (wrap) wrap.classList.add('has-error');
          }
        }
      }
      return errors[field] || null;
    }

    _validate(options) {
      const only = options && options.only;
      const data = this.data();
      const errors = {};
      const check = (field, message) => {
        if (!only || only === field) errors[field] = message;
      };

      if (!only || only === 'name') {
        if (!String(data.name || '').trim()) check('name', t('company.create.error.name_required'));
        else if (String(data.name).trim().length < 2) check('name', t('company.create.error.name_short'));
      }
      if (!only || only === 'title') {
        if (!String(data.title || '').trim()) check('title', t('company.create.error.title_required'));
      }
      if (!only || only === 'description') {
        const description = String(data.description || '').trim();
        if (!description) check('description', t('company.create.error.description_required'));
        else if (description.length < 20) check('description', t('company.create.error.description_short'));
      }
      if (!only || only === 'country') {
        if (!String(data.country || '').trim()) check('country', t('company.create.error.country_required'));
      }
      if (!only || only === 'industry') {
        if (!String(data.industry || '').trim()) check('industry', t('company.create.error.industry_required'));
      }
      if (!only || only === 'website') {
        if (data.website && !urlOk(data.website)) check('website', t('company.create.error.url'));
      }
      if (!only || only === 'business_model') {
        if (!String(data.business_model || '').trim()) check('business_model', t('company.existing.error.business_model'));
      }
      if (!only || only === 'revenue_amount') {
        const amount = Number(data.revenue_amount);
        if (data.revenue_amount === '' || data.revenue_amount == null) {
          check('revenue_amount', t('company.existing.error.revenue_required'));
        } else if (!Number.isFinite(amount) || amount <= 0) {
          check('revenue_amount', t('company.existing.error.revenue_amount'));
        }
      }
      if (!only || only === 'revenue_currency') {
        if (String(data.revenue_currency || '').length !== 3) check('revenue_currency', t('company.create.error.currency'));
      }
      if (!only || only === 'revenue_period') {
        if (PERIODS.indexOf(String(data.revenue_period || '').toUpperCase()) < 0) {
          check('revenue_period', t('company.existing.error.revenue_period'));
        }
      }
      if (!only || only === 'owner_name') {
        if (!String(data.owner_name || '').trim()) check('owner_name', t('company.create.error.owner_required'));
      }
      if (!only || only === 'owner_role') {
        if (!String(data.owner_role || '').trim()) check('owner_role', t('company.existing.error.owner_role'));
      }
      if (!only || only === 'owner_email') {
        if (data.owner_email && !emailOk(data.owner_email)) check('owner_email', t('company.create.error.email'));
      }
      return errors;
    }

    _validateSources() {
      const errors = {};
      Object.keys(this.sources()).forEach((id) => {
        const state = this.sources()[id];
        if (state.choice !== 'skip') return;
        if (String(state.reason || '').trim().length < MIN_REASON) {
          errors[id] = t('company.existing.sources.reason.error');
        }
      });
      return errors;
    }

    // ------------------------------------------------------------ sources
    _setSourceChoice(sourceId, choice) {
      if (!sourceId || !this.sources()[sourceId]) return;
      const next = choice === 'connect' || choice === 'skip' ? choice : 'later';
      const state = this.sources()[sourceId];
      state.choice = next;
      if (next !== 'skip') {
        delete this.sourceErrors[sourceId];
      }

      const card = window.document.querySelector(`[data-source-card="${sourceId}"]`);
      if (card) {
        card.classList.toggle('is-connect', next === 'connect');
        card.classList.toggle('is-skip', next === 'skip');
        card.querySelectorAll('[data-source-choice]').forEach((button) => {
          const active = button.getAttribute('data-source-choice') === next;
          button.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
        const status = card.querySelector('[data-source-status]');
        if (status) {
          status.className = `zc-pill zc-pill-${next === 'connect' ? 'accent' : (next === 'skip' ? 'orange' : 'neutral')}`;
          status.textContent = t(next === 'connect'
            ? 'company.existing.sources.status.connect'
            : (next === 'skip' ? 'company.existing.sources.status.skip' : 'company.existing.sources.status.later'));
        }
        const box = card.querySelector(`[data-source-reason-box="${sourceId}"]`);
        if (box) box.hidden = next !== 'skip';
        if (next === 'skip') {
          const input = document.getElementById(`zcSourceReason-${sourceId}`);
          if (input && input.focus) input.focus();
        }
      }
      this._updateSourceCounts();
      this._scheduleSave();
    }

    _updateSourceCounts() {
      const el = document.getElementById('zcSourceCounts');
      if (el) el.textContent = this._sourceCountsText();
    }

    async loadCatalogue() {
      this.catalogueLoading = true;
      this.catalogueError = null;
      if (this.step === 'sources') this.render(this.containerId);
      try {
        const res = await fetch('/api/v1/companies/sources/catalogue');
        let data = {};
        try { data = await res.json(); } catch (err) { data = {}; }
        if (!res.ok || !Array.isArray(data.sources)) throw new Error(`HTTP ${res.status}`);
        this.catalogue = data.sources;
        // Keep only known sources in the draft state.
        const fresh = emptySources();
        data.sources.forEach((source) => {
          if (fresh[source.id]) fresh[source.id] = this.sources()[source.id] || fresh[source.id];
        });
        this._data.sources = fresh;
      } catch (err) {
        this.catalogueError = err && err.message ? err.message : 'load failed';
      } finally {
        this.catalogueLoading = false;
        if (this.containerId && this.step === 'sources') this.render(this.containerId);
      }
    }

    // --------------------------------------------------------------- drafts
    _restoreLocalDraft() {
      if (this._data) return;
      try {
        const savedId = localStorage.getItem(DRAFT_ID_KEY);
        const savedData = localStorage.getItem(DRAFT_DATA_KEY);
        if (savedId) this.draftId = savedId;
        if (savedData) this._data = normaliseData(JSON.parse(savedData));
      } catch (err) {
        this._data = null;
      }
    }

    async _loadRemoteDraft() {
      if (!this.draftId) return false;
      try {
        const res = await fetch(`/api/v1/companies/drafts/${encodeURIComponent(this.draftId)}`);
        if (!res.ok) {
          if (res.status === 404) {
            try { localStorage.removeItem(DRAFT_ID_KEY); } catch (err) { /* blocked */ }
            this.draftId = null;
          }
          return false;
        }
        const data = await res.json();
        if (!data || !data.payload || data.company_type !== 'EXISTING') return false;
        if (!this._data || !String(this._data.name || '').trim()) {
          this._data = normaliseData(data.payload);
          return true;
        }
        return false;
      } catch (err) {
        return false;
      }
    }

    _scheduleSave() {
      if (this.saveTimer) clearTimeout(this.saveTimer);
      this.saveTimer = setTimeout(() => this.saveDraft(), SAVE_DELAY);
    }

    async saveDraft() {
      if (this.saveTimer) {
        clearTimeout(this.saveTimer);
        this.saveTimer = null;
      }
      try {
        localStorage.setItem(DRAFT_DATA_KEY, JSON.stringify(this.data()));
        if (this.draftId) localStorage.setItem(DRAFT_ID_KEY, this.draftId);
      } catch (err) { /* storage blocked */ }

      this.saving = true;
      this._setSaveState(t('company.create.draft.saving'));
      try {
        const body = {
          company_type: 'EXISTING',
          payload: this._payload(),
          draft_id: this.draftId || undefined
        };
        let res = await fetch('/api/v1/companies/drafts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (res.status === 404 && this.draftId) {
          this.draftId = null;
          try { localStorage.removeItem(DRAFT_ID_KEY); } catch (err) { /* blocked */ }
          body.draft_id = undefined;
          res = await fetch('/api/v1/companies/drafts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
          });
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data && data.draft_id) {
          this.draftId = data.draft_id;
          try { localStorage.setItem(DRAFT_ID_KEY, this.draftId); } catch (err) { /* blocked */ }
        }
        this.saveState = 'saved';
      } catch (err) {
        this.saveState = (typeof navigator !== 'undefined' && navigator.onLine === false) ? 'local' : 'error';
      } finally {
        this.saving = false;
        this._setSaveState(this._saveStateText());
      }
    }

    _setSaveState(text) {
      const el = document.getElementById('zcExistSaveState');
      if (el) el.textContent = text;
    }

    _payload() {
      const data = this.data();
      const sources = Object.keys(this.sources())
        .map((id) => ({ source_id: id, choice: this.sources()[id].choice, reason: String(this.sources()[id].reason || '').trim() }))
        .filter((item) => item.choice === 'connect' || item.choice === 'skip');
      return {
        type: 'EXISTING',
        company_type: 'EXISTING',
        name: String(data.name || '').trim(),
        title: String(data.title || '').trim(),
        description: String(data.description || '').trim(),
        owner: {
          name: String(data.owner_name || '').trim(),
          email: String(data.owner_email || '').trim(),
          role: String(data.owner_role || '').trim()
        },
        country: String(data.country || '').trim().toUpperCase(),
        industry: String(data.industry || '').trim(),
        website: String(data.website || '').trim(),
        business_model: String(data.business_model || '').trim(),
        revenue: {
          amount: data.revenue_amount === '' ? null : Number(data.revenue_amount),
          currency: String(data.revenue_currency || 'INR').trim().toUpperCase(),
          period: String(data.revenue_period || 'ANNUAL').trim().toUpperCase()
        },
        sources
      };
    }

    // --------------------------------------------------------------- submit
    async submit() {
      if (this.submitting) return;
      this.errors = this._validate();
      this.sourceErrors = this._validateSources();
      if (Object.keys(this.errors).length) {
        this.step = 'details';
        this.render(this.containerId);
        this._focusField(Object.keys(this.errors)[0]);
        return;
      }
      if (Object.keys(this.sourceErrors).length) {
        this.step = 'sources';
        this.render(this.containerId);
        return;
      }

      this.submitting = true;
      const button = document.getElementById('zcExistingSubmit');
      if (button) {
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        button.textContent = t('company.existing.submitting');
      }

      try {
        const payload = this._payload();
        const created = await this._post('/api/v1/companies', payload);
        if (!created.ok) {
          this._handleCreateError(created);
          return;
        }
        this.companyId = created.data.id;
        await this._clearDraft();

        const failures = [];
        for (const source of payload.sources) {
          if (source.choice === 'skip') {
            const result = await this._post(
              `/api/v1/companies/${encodeURIComponent(this.companyId)}/sources/${encodeURIComponent(source.source_id)}/skip`,
              { reason: source.reason }
            );
            if (!result.ok) failures.push(`${source.source_id}: ${this._errorText(result)}`);
          } else if (source.choice === 'connect') {
            const result = await this._post(
              `/api/v1/companies/${encodeURIComponent(this.companyId)}/connections`,
              { source_id: source.source_id }
            );
            if (!result.ok) failures.push(`${source.source_id}: ${this._errorText(result)}`);
          }
        }

        const submitted = await this._post(
          `/api/v1/companies/${encodeURIComponent(this.companyId)}/submit`,
          {}
        );
        if (!submitted.ok) {
          this._toast(t('company.existing.error.submit_failed'), 'error');
          this._navigate(`/company/${this.companyId}/overview`);
          return;
        }

        if (failures.length) {
          // Honest: the company exists and onboarding started, but some source
          // choices were not saved. Say exactly that.
          this._toast(t('company.existing.error.sources_partial', { count: failures.length, detail: failures[0] }), 'warning');
        } else {
          this._toast(t('company.existing.created'), 'success');
        }
        this._navigate(`/company/${this.companyId}/build`);
      } catch (err) {
        this._toast(t('company.existing.error.network'), 'error');
      } finally {
        this.submitting = false;
      }
    }

    _errorText(result) {
      const data = (result && result.data) || {};
      return String(data.error || data.code || `HTTP ${result && result.status}`);
    }

    _handleCreateError(result) {
      const data = result.data || {};
      const code = String(data.code || '');
      if (code === 'DUPLICATE_COMPANY_NAME') {
        this.errors = { name: t('company.create.error.duplicate') };
      } else if (code === 'VALIDATION_FAILED' && Array.isArray(data.detail)) {
        this.errors = {};
        data.detail.forEach((item) => {
          const field = String(item.field || 'name')
            .replace(/^owner\.name$/, 'owner_name')
            .replace(/^owner\.role$/, 'owner_role')
            .replace(/^owner\.email$/, 'owner_email')
            .replace(/^revenue\.amount$/, 'revenue_amount')
            .replace(/^revenue\.currency$/, 'revenue_currency')
            .replace(/^revenue\.period$/, 'revenue_period')
            .replace(/\./g, '_');
          if (item.message) this.errors[field] = item.message;
        });
      } else if (code === 'FORBIDDEN') {
        this._toast(t('company.existing.denied.body'), 'warning');
        this._navigate('/company/add');
        return;
      } else {
        this.errors = { name: String(data.error || t('company.create.error.create_failed')) };
      }
      this.step = 'details';
      this.render(this.containerId);
      this._focusField(Object.keys(this.errors)[0]);
    }

    async _post(path, body) {
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      });
      let data = {};
      try { data = await res.json(); } catch (err) { data = {}; }
      return { ok: res.ok, status: res.status, data };
    }

    async _clearDraft() {
      const draftId = this.draftId;
      try {
        localStorage.removeItem(DRAFT_ID_KEY);
        localStorage.removeItem(DRAFT_DATA_KEY);
      } catch (err) { /* blocked */ }
      this.draftId = null;
      this._data = null;
      if (draftId) {
        try {
          await fetch(`/api/v1/companies/drafts/${encodeURIComponent(draftId)}`, { method: 'DELETE' });
        } catch (err) { /* best effort */ }
      }
    }

    // -------------------------------------------------------------- helpers
    _goBack() {
      this._navigate('/company/add');
    }

    _navigate(path) {
      if (typeof window.navigateTo === 'function') window.navigateTo(path);
      else window.location.hash = `#${path}`;
    }

    _toast(message, tone) {
      if (window.UI && typeof window.UI.showToast === 'function') {
        window.UI.showToast(message, tone || 'info');
      }
    }

    reset() {
      this._data = null;
      this.draftId = null;
      this.step = 'details';
      this.errors = {};
      this.sourceErrors = {};
      this.catalogue = null;
      this.catalogueError = null;
      this.catalogueLoading = false;
      this._loadedRemote = false;
      try {
        localStorage.removeItem(DRAFT_ID_KEY);
        localStorage.removeItem(DRAFT_DATA_KEY);
      } catch (err) { /* blocked */ }
    }
  }

  window.CompanySetupExisting = new ExistingCompanyFlow();
})();
