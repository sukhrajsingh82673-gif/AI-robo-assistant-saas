/**
 * ZONATA — Create a new company
 *
 * One phone-friendly column: the brief, who you are, where you operate, and an
 * optional section that stays collapsed until asked for. The description can be
 * written freely or assembled from four guided answers.
 *
 * Everything is validated on the client for speed and again on the server as
 * the real gate. Nothing is created until the review screen is confirmed.
 * Drafts are saved to the existing company drafts endpoint, so a refresh or a
 * dead connection never silently loses the brief.
 *
 * Routes: /company/create (review and submit live in this module).
 */

(function() {
  'use strict';

  const DRAFT_ID_KEY = 'zonata_company_create_draft_id';
  const DRAFT_DATA_KEY = 'zonata_company_create_draft_data';
  const SAVE_DELAY = 700;

  const COUNTRIES = ['IN', 'AE', 'GB', 'US', 'SG', 'AU', 'CA', 'DE', 'FR', 'SA', 'QA', 'KW', 'OM', 'BH'];
  const CURRENCIES = ['INR', 'USD', 'AED', 'GBP', 'EUR', 'SGD', 'AUD', 'CAD', 'SAR', 'QAR', 'KWD', 'OMR', 'BHD'];

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

  function isPhone() {
    try {
      return !!(window.matchMedia && window.matchMedia('(max-width: 640px)').matches);
    } catch (err) {
      return false;
    }
  }

  function emptyData() {
    return {
      name: '',
      title: '',
      description: '',
      description_mode: 'free',
      guided: { offer: '', audience: '', difference: '', revenue: '' },
      owner_name: '',
      owner_email: '',
      owner_role: '',
      country: 'IN',
      industry: '',
      website: '',
      target_customers: '',
      budget_amount: '',
      budget_currency: 'INR',
      timeline: '',
      setup_notes: '',
      assets: ''
    };
  }

  function normaliseData(raw) {
    const data = emptyData();
    if (!raw || typeof raw !== 'object') return data;
    Object.keys(data).forEach((key) => {
      if (raw[key] !== undefined && raw[key] !== null && typeof data[key] !== 'object') {
        data[key] = raw[key];
      }
    });
    if (raw.guided && typeof raw.guided === 'object') {
      ['offer', 'audience', 'difference', 'revenue'].forEach((key) => {
        if (raw.guided[key] != null) data.guided[key] = String(raw.guided[key]);
      });
    }
    if (raw.budget && typeof raw.budget === 'object') {
      if (raw.budget.amount != null) data.budget_amount = raw.budget.amount;
      if (raw.budget.currency) data.budget_currency = raw.budget.currency;
    }
    if (Array.isArray(raw.assets)) data.assets = raw.assets.join('\n');
    if (data.description_mode !== 'guided') data.description_mode = 'free';
    return data;
  }

  function parseAssets(value) {
    return String(value || '')
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function urlOk(value) {
    return /^https?:\/\/[^\s<>"']{3,2048}$/i.test(String(value || '').trim());
  }

  function emailOk(value) {
    return /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/.test(String(value || '').trim());
  }

  class CreateCompanyFlow {
    constructor() {
      this.containerId = null;
      this.companyId = null;
      this.step = 'form';
      this.optionalOpen = false;
      this.errors = {};
      this.submitting = false;
      this.draftId = null;
      this.saving = false;
      this.saveState = 'idle';
      this.saveTimer = null;
      this.loadingDraft = false;
      this._onLanguageChange = this._onLanguageChange.bind(this);
      if (document && document.addEventListener) {
        document.addEventListener('zonata:languagechange', this._onLanguageChange);
      }
    }

    _onLanguageChange() {
      if (!this.containerId) return;
      const container = document.getElementById(this.containerId);
      if (container && container.querySelector('[data-company-create]')) {
        this.render(this.containerId);
      }
    }

    data() {
      if (!this._data) this._data = emptyData();
      return this._data;
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

      container.innerHTML = this.step === 'review' ? this._reviewHtml() : this._formHtml();
      this._bind(container);
      if (this.step === 'review') window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    _topHtml() {
      return `
        <div class="zc-flow-top">
          <button type="button" class="zc-back-link" id="zcCreateBack">
            <span class="zc-back-arrow" aria-hidden="true">←</span>
            <span>${escapeHtml(t('company.create.back'))}</span>
          </button>
          <div class="zc-language-toggle" role="group" aria-label="${escapeHtml(t('common.language'))}">
            <button type="button" data-language="en" aria-pressed="${language() === 'en' ? 'true' : 'false'}">${escapeHtml(t('common.english'))}</button>
            <button type="button" data-language="ar" aria-pressed="${language() === 'ar' ? 'true' : 'false'}">${escapeHtml(t('common.arabic'))}</button>
          </div>
        </div>
      `;
    }

    _stepperHtml() {
      const review = this.step === 'review';
      return `
        <ol class="zc-steps" aria-label="${escapeHtml(t('company.create.steps_label'))}">
          <li class="zc-step ${review ? 'is-done' : 'is-current'}" ${review ? '' : 'aria-current="step"'}>
            <span class="zc-step-dot" aria-hidden="true">1</span>
            <span>${escapeHtml(t('company.create.step.details'))}</span>
          </li>
          <li class="zc-step ${review ? 'is-current' : ''}" ${review ? 'aria-current="step"' : ''}>
            <span class="zc-step-dot" aria-hidden="true">2</span>
            <span>${escapeHtml(t('company.create.step.review'))}</span>
          </li>
        </ol>
      `;
    }

    _fieldHtml(opts) {
      const {
        name,
        label,
        hint,
        example,
        value,
        type,
        required,
        multiline,
        rows,
        autocomplete,
        inputmode
      } = opts;
      const error = this.errors[name];
      const describedBy = [];
      if (hint) describedBy.push(`zcHint-${name}`);
      if (error) describedBy.push(`zcErr-${name}`);
      const hintHtml = hint
        ? `<p class="zc-field-hint" id="zcHint-${name}">${escapeHtml(hint)}${example ? ` <span class="zc-field-example">${escapeHtml(t('company.create.example', { example }))}</span>` : ''}</p>`
        : '';
      const errorHtml = `<p class="zc-field-error" id="zcErr-${name}" role="alert"${error ? '' : ' hidden'}>${escapeHtml(error || '')}</p>`;
      const shared = `id="zcField-${name}" name="${name}" data-field="${name}"`;
      const aria = `aria-describedby="${describedBy.join(' ')}" aria-invalid="${error ? 'true' : 'false'}"${required ? ' aria-required="true"' : ''}`;
      const control = multiline
        ? `<textarea class="zc-input zc-textarea" ${shared} rows="${rows || 4}" ${aria}${autocomplete ? ` autocomplete="${autocomplete}"` : ''}>${escapeHtml(value == null ? '' : value)}</textarea>`
        : `<input class="zc-input" ${shared} type="${type || 'text'}" value="${escapeHtml(value == null ? '' : value)}" ${aria}${autocomplete ? ` autocomplete="${autocomplete}"` : ''}${inputmode ? ` inputmode="${inputmode}"` : ''} />`;
      const optional = required ? '' : `<span class="zc-optional">${escapeHtml(t('company.create.optional'))}</span>`;
      return `
        <div class="zc-field${error ? ' has-error' : ''}">
          <label class="zc-label" for="zcField-${name}">${escapeHtml(label)}${required ? ' <span class="zc-required" aria-hidden="true">*</span>' : ''}${optional}</label>
          ${control}
          ${hintHtml}
          ${errorHtml}
        </div>
      `;
    }

    _formHtml() {
      const data = this.data();
      const guided = data.description_mode === 'guided';
      const access = viewer();
      const denied = access.allowed ? '' : this._deniedHtml();
      const composed = this._composeGuided();
      const descriptionValue = guided ? (composed || data.description) : data.description;
      const optionalOpen = this.optionalOpen;

      return `
        <div class="zc-flow-page" data-company-create>
          ${this._topHtml()}

          <header class="zc-flow-header">
            <h1 class="zc-flow-title">${escapeHtml(t('company.create.title'))}</h1>
            <p class="zc-flow-subtitle">${escapeHtml(t('company.create.subtitle'))}</p>
            ${this._stepperHtml()}
          </header>

          ${denied}

          <p class="zc-save-state" id="zcSaveState" role="status" aria-live="polite">${escapeHtml(this._saveStateText())}</p>

          ${this._errorSummaryHtml()}

          <form id="zcCreateForm" class="zc-form" novalidate>
            <section class="zc-form-section" aria-labelledby="zcSectionBasics">
              <h2 class="zc-section-title" id="zcSectionBasics">${escapeHtml(t('company.create.basics.title'))}</h2>
              <p class="zc-section-note">${escapeHtml(t('company.create.basics.note'))}</p>

              ${this._fieldHtml({
                name: 'name',
                label: t('company.create.name.label'),
                hint: t('company.create.name.hint'),
                example: t('company.create.name.example'),
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

              <fieldset class="zc-field zc-fieldset">
                <legend class="zc-label">${escapeHtml(t('company.create.description.label'))} <span class="zc-required" aria-hidden="true">*</span></legend>
                <div class="zc-segmented" role="group" aria-label="${escapeHtml(t('company.create.description.mode_label'))}">
                  <button type="button" class="zc-segment" data-description-mode="free" aria-pressed="${guided ? 'false' : 'true'}">${escapeHtml(t('company.create.description.free'))}</button>
                  <button type="button" class="zc-segment" data-description-mode="guided" aria-pressed="${guided ? 'true' : 'false'}">${escapeHtml(t('company.create.description.guided'))}</button>
                </div>

                <div class="zc-guided" id="zcGuided" ${guided ? '' : 'hidden'}>
                  ${this._fieldHtml({
                    name: 'guided_offer',
                    label: t('company.create.guided.offer.label'),
                    hint: t('company.create.guided.offer.hint'),
                    example: t('company.create.guided.offer.example'),
                    value: data.guided.offer,
                    multiline: true,
                    rows: 2
                  })}
                  ${this._fieldHtml({
                    name: 'guided_audience',
                    label: t('company.create.guided.audience.label'),
                    hint: t('company.create.guided.audience.hint'),
                    example: t('company.create.guided.audience.example'),
                    value: data.guided.audience,
                    multiline: true,
                    rows: 2
                  })}
                  ${this._fieldHtml({
                    name: 'guided_difference',
                    label: t('company.create.guided.difference.label'),
                    hint: t('company.create.guided.difference.hint'),
                    example: t('company.create.guided.difference.example'),
                    value: data.guided.difference,
                    multiline: true,
                    rows: 2
                  })}
                  ${this._fieldHtml({
                    name: 'guided_revenue',
                    label: t('company.create.guided.revenue.label'),
                    hint: t('company.create.guided.revenue.hint'),
                    example: t('company.create.guided.revenue.example'),
                    value: data.guided.revenue,
                    multiline: true,
                    rows: 2
                  })}
                  <div class="zc-guided-preview">
                    <p class="zc-guided-preview-label">${escapeHtml(t('company.create.guided.preview'))}</p>
                    <p class="zc-guided-preview-text" id="zcGuidedPreview" tabindex="-1" aria-live="polite">${escapeHtml(composed || t('company.create.guided.empty'))}</p>
                    <p class="zc-field-error" id="zcErr-description-guided" role="alert"${this.errors.description ? '' : ' hidden'}>${escapeHtml(this.errors.description || '')}</p>
                  </div>
                </div>

                <div class="zc-free" id="zcFree" ${guided ? 'hidden' : ''}>
                  ${this._fieldHtml({
                    name: 'description',
                    label: t('company.create.description.free_label'),
                    hint: t('company.create.description.hint'),
                    example: t('company.create.description.example'),
                    value: descriptionValue,
                    required: true,
                    multiline: true,
                    rows: 5
                  })}
                </div>
              </fieldset>
            </section>

            <section class="zc-form-section" aria-labelledby="zcSectionYou">
              <h2 class="zc-section-title" id="zcSectionYou">${escapeHtml(t('company.create.you.title'))}</h2>
              <p class="zc-section-note">${escapeHtml(t('company.create.you.note'))}</p>
              ${this._fieldHtml({
                name: 'owner_name',
                label: t('company.create.owner.label'),
                hint: t('company.create.owner.hint'),
                value: data.owner_name,
                required: true,
                autocomplete: 'name'
              })}
              ${this._fieldHtml({
                name: 'owner_email',
                label: t('company.create.email.label'),
                hint: t('company.create.email.hint'),
                example: t('company.create.email.example'),
                value: data.owner_email,
                type: 'email',
                autocomplete: 'email',
                inputmode: 'email'
              })}
              ${this._fieldHtml({
                name: 'owner_role',
                label: t('company.create.role.label'),
                hint: t('company.create.role.hint'),
                example: t('company.create.role.example'),
                value: data.owner_role,
                autocomplete: 'organization-title'
              })}
            </section>

            <section class="zc-form-section" aria-labelledby="zcSectionWhere">
              <h2 class="zc-section-title" id="zcSectionWhere">${escapeHtml(t('company.create.where.title'))}</h2>
              <p class="zc-section-note">${escapeHtml(t('company.create.where.note'))}</p>
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
            </section>

            <section class="zc-form-section zc-form-section-collapsible">
              <button type="button" class="zc-collapse-toggle" id="zcOptionalToggle" aria-expanded="${optionalOpen ? 'true' : 'false'}" aria-controls="zcOptional">
                <span class="zc-collapse-title">${escapeHtml(t('company.create.optional.title'))}</span>
                <span class="zc-collapse-note">${escapeHtml(t('company.create.optional.note'))}</span>
                <span class="zc-collapse-chevron" aria-hidden="true">${optionalOpen ? '−' : '+'}</span>
              </button>
              <div class="zc-optional-body" id="zcOptional" ${optionalOpen ? '' : 'hidden'}>
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
                ${this._fieldHtml({
                  name: 'assets',
                  label: t('company.create.assets.label'),
                  hint: t('company.create.assets.hint'),
                  example: 'https://drive.example.com/brand-kit',
                  value: data.assets,
                  multiline: true,
                  rows: 3
                })}
                ${this._fieldHtml({
                  name: 'target_customers',
                  label: t('company.create.customers.label'),
                  hint: t('company.create.customers.hint'),
                  example: t('company.create.customers.example'),
                  value: data.target_customers,
                  multiline: true,
                  rows: 2
                })}
                <div class="zc-field-row">
                  ${this._fieldHtml({
                    name: 'budget_amount',
                    label: t('company.create.budget.label'),
                    hint: t('company.create.budget.hint'),
                    example: '250000',
                    value: data.budget_amount,
                    type: 'number',
                    inputmode: 'decimal'
                  })}
                  ${this._fieldHtml({
                    name: 'budget_currency',
                    label: t('company.create.budget.currency'),
                    hint: t('company.create.budget.currency_hint'),
                    value: data.budget_currency
                  })}
                </div>
                ${this._fieldHtml({
                  name: 'timeline',
                  label: t('company.create.timeline.label'),
                  hint: t('company.create.timeline.hint'),
                  example: t('company.create.timeline.example'),
                  value: data.timeline
                })}
                ${this._fieldHtml({
                  name: 'setup_notes',
                  label: t('company.create.notes.label'),
                  hint: t('company.create.notes.hint'),
                  value: data.setup_notes,
                  multiline: true,
                  rows: 3
                })}
              </div>
            </section>

            <div class="zc-form-actions">
              <button type="button" class="zc-button zc-button-quiet" id="zcCreateCancel">${escapeHtml(t('common.cancel'))}</button>
              <button type="submit" class="zc-button zc-button-primary" id="zcCreateReview">${escapeHtml(t('company.create.review_button'))}</button>
            </div>
            <p class="zc-form-footnote">${escapeHtml(t('company.create.footnote'))}</p>
          </form>
        </div>
      `;
    }

    _reviewHtml() {
      const data = this.data();
      const description = this.effectiveDescription();
      const assets = parseAssets(data.assets);
      const budget = data.budget_amount === '' ? null : Number(data.budget_amount);
      const budgetText = budget == null || !Number.isFinite(budget)
        ? t('company.create.review.not_set')
        : (window.I18n && window.I18n.formatCurrency
          ? window.I18n.formatCurrency(budget, data.budget_currency || 'INR')
          : `${data.budget_currency || 'INR'} ${budget}`);
      const owner = [data.owner_name, data.owner_role].filter(Boolean).join(' · ') || t('company.create.review.not_set');
      const optionalRows = [
        [t('company.create.website.label'), data.website],
        [t('company.create.customers.label'), data.target_customers],
        [t('company.create.budget.label'), budgetText],
        [t('company.create.timeline.label'), data.timeline],
        [t('company.create.notes.label'), data.setup_notes],
        [t('company.create.assets.label'), assets.length ? String(assets.length) : '']
      ].filter((row) => row[1]);

      return `
        <div class="zc-flow-page" data-company-create>
          ${this._topHtml()}

          <header class="zc-flow-header">
            <h1 class="zc-flow-title">${escapeHtml(t('company.create.review.title'))}</h1>
            <p class="zc-flow-subtitle">${escapeHtml(t('company.create.review.subtitle'))}</p>
            ${this._stepperHtml()}
          </header>

          ${this._errorSummaryHtml()}

          <div class="zc-review" role="region" aria-label="${escapeHtml(t('company.create.review.region'))}">
            <section class="zc-review-block">
              <div class="zc-review-head">
                <h2>${escapeHtml(t('company.create.review.basics'))}</h2>
                <button type="button" class="zc-link-button" data-edit="name">${escapeHtml(t('company.create.review.edit'))}</button>
              </div>
              <dl class="zc-review-list">
                <div><dt>${escapeHtml(t('company.create.name.label'))}</dt><dd>${escapeHtml(data.name)}</dd></div>
                <div><dt>${escapeHtml(t('company.create.tagline.label'))}</dt><dd>${escapeHtml(data.title)}</dd></div>
                <div><dt>${escapeHtml(t('company.create.where.title'))}</dt><dd>${escapeHtml([data.country, data.industry].filter(Boolean).join(' · '))}</dd></div>
                <div><dt>${escapeHtml(t('company.create.review.owner'))}</dt><dd>${escapeHtml(owner)}</dd></div>
                ${data.owner_email ? `<div><dt>${escapeHtml(t('company.create.email.label'))}</dt><dd>${escapeHtml(data.owner_email)}</dd></div>` : ''}
              </dl>
              <div class="zc-review-description">
                <p class="zc-review-description-label">${escapeHtml(t('company.create.description.free_label'))}</p>
                <p>${escapeHtml(description)}</p>
              </div>
            </section>

            ${optionalRows.length ? `
              <section class="zc-review-block">
                <div class="zc-review-head">
                  <h2>${escapeHtml(t('company.create.optional.title'))}</h2>
                  <button type="button" class="zc-link-button" data-edit="website">${escapeHtml(t('company.create.review.edit'))}</button>
                </div>
                <dl class="zc-review-list">
                  ${optionalRows.map((row) => `<div><dt>${escapeHtml(row[0])}</dt><dd>${escapeHtml(row[1])}</dd></div>`).join('')}
                </dl>
              </section>
            ` : ''}

            <section class="zc-review-block zc-review-next">
              <h2>${escapeHtml(t('company.create.review.next.title'))}</h2>
              <ul class="zc-review-next-list">
                <li>${escapeHtml(t('company.create.review.next.one'))}</li>
                <li>${escapeHtml(t('company.create.review.next.two'))}</li>
                <li>${escapeHtml(t('company.create.review.next.three'))}</li>
              </ul>
              <p class="zc-review-estimate">${escapeHtml(t('company.create.review.next.estimate'))}</p>
            </section>
          </div>

          <div class="zc-form-actions">
            <button type="button" class="zc-button zc-button-quiet" id="zcReviewBack">${escapeHtml(t('common.back'))}</button>
            <button type="button" class="zc-button zc-button-primary" id="zcCreateSubmit"${this.submitting ? ' disabled aria-busy="true"' : ''}>
              ${escapeHtml(this.submitting ? t('company.create.submitting') : t('company.create.submit'))}
            </button>
          </div>
          <p class="zc-form-footnote">${escapeHtml(t('company.create.review.footnote'))}</p>
        </div>
      `;
    }

    _errorSummaryHtml() {
      const fields = Object.keys(this.errors);
      if (!fields.length) return '';
      return `
        <div class="zc-inline-notice zc-inline-notice-error" role="alert" id="zcCreateErrors">
          <strong>${escapeHtml(t('company.create.errors.title'))}</strong>
          <ul class="zc-error-list">
            ${fields.map((field) => `<li><a href="#zcField-${escapeHtml(field)}" data-error-field="${escapeHtml(field)}">${escapeHtml(this.errors[field])}</a></li>`).join('')}
          </ul>
        </div>
      `;
    }

    _deniedHtml() {
      return `
        <div class="zc-flow-page" data-company-create>
          <div class="zc-inline-notice zc-inline-notice-warning" role="status">
            <strong>${escapeHtml(t('company.create.denied.title'))}</strong>
            <span>${escapeHtml(t('company.create.denied.body'))}</span>
            <button type="button" class="zc-link-button" id="zcCreateDeniedBack">${escapeHtml(t('company.create.back'))}</button>
          </div>
        </div>
      `;
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
      const back = container.querySelector('#zcCreateBack');
      if (back) back.addEventListener('click', () => this._goBack());

      const deniedBack = container.querySelector('#zcCreateDeniedBack');
      if (deniedBack) deniedBack.addEventListener('click', () => this._goBack());

      container.querySelectorAll('[data-language]').forEach((button) => {
        button.addEventListener('click', () => {
          if (window.I18n && window.I18n.setLanguage) window.I18n.setLanguage(button.getAttribute('data-language'));
        });
      });

      const form = container.querySelector('#zcCreateForm');
      if (form) {
        form.addEventListener('submit', (event) => {
          event.preventDefault();
          this.review();
        });
        form.addEventListener('input', (event) => this._onInput(event));
        form.addEventListener('change', (event) => this._onInput(event));
        form.addEventListener('focusout', (event) => {
          if (event.target && event.target.getAttribute && event.target.getAttribute('data-field')) this._validateField(event.target.getAttribute('data-field'));
        });
      }

      container.querySelectorAll('[data-description-mode]').forEach((button) => {
        button.addEventListener('click', () => this._setDescriptionMode(button.getAttribute('data-description-mode')));
      });

      const toggle = container.querySelector('#zcOptionalToggle');
      const body = container.querySelector('#zcOptional');
      if (toggle && body) {
        toggle.addEventListener('click', () => {
          this.optionalOpen = body.hidden;
          body.hidden = !this.optionalOpen;
          toggle.setAttribute('aria-expanded', this.optionalOpen ? 'true' : 'false');
          const chevron = toggle.querySelector('.zc-collapse-chevron');
          if (chevron) chevron.textContent = this.optionalOpen ? '−' : '+';
        });
      }

      const cancel = container.querySelector('#zcCreateCancel');
      if (cancel) cancel.addEventListener('click', () => this._goBack());

      const reviewBack = container.querySelector('#zcReviewBack');
      if (reviewBack) reviewBack.addEventListener('click', () => this.edit());

      const submit = container.querySelector('#zcCreateSubmit');
      if (submit) submit.addEventListener('click', () => this.submit());

      container.querySelectorAll('[data-edit]').forEach((button) => {
        button.addEventListener('click', () => this.edit(button.getAttribute('data-edit')));
      });

      container.querySelectorAll('[data-error-field]').forEach((link) => {
        link.addEventListener('click', (event) => {
          event.preventDefault();
          this.edit(link.getAttribute('data-error-field'));
        });
      });
    }

    _onInput(event) {
      const target = event.target;
      if (!target || !target.getAttribute) return;
      const field = target.getAttribute('data-field');
      if (!field) return;
      const value = target.value;

      if (field.indexOf('guided_') === 0) {
        this.data().guided[field.slice('guided_'.length)] = value;
        this.data().description = this._composeGuided();
        const preview = document.getElementById('zcGuidedPreview');
        if (preview) preview.textContent = this.data().description || t('company.create.guided.empty');
      } else {
        this.data()[field] = value;
      }
      if (field.indexOf('guided_') === 0 && this.errors.description) {
        const composed = this.effectiveDescription();
        if (composed && composed.length >= 20) {
          delete this.errors.description;
          const guidedError = document.getElementById('zcErr-description-guided');
          if (guidedError) {
            guidedError.textContent = '';
            guidedError.hidden = true;
          }
        }
      }
      if (this.errors[field]) {
        delete this.errors[field];
        const el = document.getElementById(`zcErr-${field}`);
        if (el) {
          el.textContent = '';
          el.hidden = true;
        }
        const wrap = target.closest('.zc-field');
        if (wrap) wrap.classList.remove('has-error');
        target.setAttribute('aria-invalid', 'false');
      }
      this.saveState = 'idle';
      this._scheduleSave();
    }

    _setDescriptionMode(mode) {
      const next = mode === 'guided' ? 'guided' : 'free';
      const data = this.data();
      if (next === 'guided') {
        if (!this._composeGuided() && data.description) {
          data.guided.offer = data.description;
          data.description = this._composeGuided();
        }
      }
      data.description_mode = next;
      this.render(this.containerId);
      const first = document.getElementById(next === 'guided' ? 'zcField-guided_offer' : 'zcField-description');
      if (first) first.focus();
    }

    _composeGuided() {
      const guided = this.data().guided || {};
      const sentence = (prefixKey, value) => {
        const text = String(value || '').trim().replace(/[.!?]+$/, '');
        if (!text) return '';
        return `${t(prefixKey)} ${text}.`;
      };
      const parts = [];
      if (guided.offer) parts.push(String(guided.offer).trim());
      const audience = sentence('company.create.guided.sentence.audience', guided.audience);
      const difference = sentence('company.create.guided.sentence.difference', guided.difference);
      const revenue = sentence('company.create.guided.sentence.revenue', guided.revenue);
      if (audience) parts.push(audience);
      if (difference) parts.push(difference);
      if (revenue) parts.push(revenue);
      return parts.join(' ');
    }

    effectiveDescription() {
      const data = this.data();
      if (data.description_mode === 'guided') return (this._composeGuided() || data.description || '').trim();
      return String(data.description || '').trim();
    }

    // ---------------------------------------------------------- validation
    _validateField(field) {
      const errors = this._validate({ only: field });
      if (errors[field]) {
        this.errors[field] = errors[field];
        const el = document.getElementById(`zcErr-${field}`);
        if (el) {
          el.textContent = errors[field];
          el.hidden = false;
        }
        const input = document.getElementById(`zcField-${field}`);
        if (input) {
          input.setAttribute('aria-invalid', 'true');
          input.closest('.zc-field') && input.closest('.zc-field').classList.add('has-error');
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
      if (!only || only === 'description' || only === 'guided_offer') {
        const description = this.effectiveDescription();
        if (!description && (!only || only !== 'guided_offer')) check('description', t('company.create.error.description_required'));
        else if (description && description.length < 20) check('description', t('company.create.error.description_short'));
      }
      if (!only || only === 'owner_name') {
        if (!String(data.owner_name || '').trim()) check('owner_name', t('company.create.error.owner_required'));
      }
      if (!only || only === 'owner_email') {
        if (data.owner_email && !emailOk(data.owner_email)) check('owner_email', t('company.create.error.email'));
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
      if (!only || only === 'assets') {
        const bad = parseAssets(data.assets).filter((url) => !urlOk(url));
        if (bad.length) check('assets', t('company.create.error.assets'));
      }
      if (!only || only === 'budget_amount') {
        if (data.budget_amount !== '' && data.budget_amount != null) {
          const amount = Number(data.budget_amount);
          if (!Number.isFinite(amount) || amount < 0) check('budget_amount', t('company.create.error.budget'));
        }
      }
      if (!only || only === 'budget_currency') {
        if (data.budget_currency && String(data.budget_currency).trim().length !== 3) {
          check('budget_currency', t('company.create.error.currency'));
        }
      }
      return errors;
    }

    review() {
      this.errors = this._validate();
      const fields = Object.keys(this.errors);
      if (fields.length) {
        const guidedFields = fields.filter((field) => field === 'description');
        if (this.data().description_mode === 'guided' && guidedFields.length) {
          // Keep the description error visible on the guided field set.
          this.optionalOpen = false;
        }
        this._renderFormWithErrors(fields[0]);
        return;
      }
      this.step = 'review';
      this.saveDraft();
      this.render(this.containerId);
    }

    _renderFormWithErrors(focusField) {
      this.step = 'form';
      this.render(this.containerId);
      const guidedDescription = focusField === 'description' && this.data().description_mode === 'guided';
      let target = guidedDescription ? null : document.getElementById(`zcField-${focusField}`);
      if (!target && guidedDescription) target = document.getElementById('zcGuidedPreview');
      if (!target) target = document.getElementById('zcCreateErrors');
      if (target && target.focus) target.focus();
    }

    edit(field) {
      this.step = 'form';
      this.errors = {};
      if (field === 'website' || field === 'assets' || field === 'target_customers' || field === 'budget_amount' || field === 'timeline' || field === 'setup_notes') {
        this.optionalOpen = true;
      }
      this.render(this.containerId);
      if (field === 'website' || field === 'name') {
        const el = document.getElementById(`zcField-${field}`);
        if (el) el.focus();
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
      this.loadingDraft = true;
      try {
        const res = await fetch(`/api/v1/companies/drafts/${encodeURIComponent(this.draftId)}`);
        if (!res.ok) {
          if (res.status === 404) {
            try {
              localStorage.removeItem(DRAFT_ID_KEY);
            } catch (err) { /* blocked */ }
            this.draftId = null;
          }
          return false;
        }
        const data = await res.json();
        if (!data || !data.payload) return false;
        if (!this._data || !String(this._data.name || '').trim()) {
          this._data = normaliseData(data.payload);
          return true;
        }
        return false;
      } catch (err) {
        return false;
      } finally {
        this.loadingDraft = false;
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
      const payload = this._payload();
      try {
        localStorage.setItem(DRAFT_DATA_KEY, JSON.stringify(this.data()));
        if (this.draftId) localStorage.setItem(DRAFT_ID_KEY, this.draftId);
      } catch (err) { /* storage blocked */ }

      if (this.step === 'review') {
        // A review snapshot is useful but not worth a network round trip.
      }

      this.saving = true;
      this._setSaveState(t('company.create.draft.saving'));
      try {
        const body = {
          company_type: 'NEW',
          payload,
          draft_id: this.draftId || undefined
        };
        let res = await fetch('/api/v1/companies/drafts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (res.status === 404 && this.draftId) {
          // The stored draft was removed elsewhere. Start a fresh one once.
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
          try {
            localStorage.setItem(DRAFT_ID_KEY, this.draftId);
          } catch (err) { /* blocked */ }
        }
        this.saveState = 'saved';
      } catch (err) {
        // The brief stays on this device; the review screen says so honestly.
        this.saveState = navigator && navigator.onLine === false ? 'local' : 'error';
      } finally {
        this.saving = false;
        this._setSaveState(this._saveStateText());
      }
    }

    _setSaveState(text) {
      const el = document.getElementById('zcSaveState');
      if (el) el.textContent = text;
    }

    _payload() {
      const data = this.data();
      const assets = parseAssets(data.assets);
      const payload = {
        type: 'NEW',
        company_type: 'NEW',
        name: String(data.name || '').trim(),
        title: String(data.title || '').trim(),
        description: this.effectiveDescription(),
        owner: {
          name: String(data.owner_name || '').trim(),
          email: String(data.owner_email || '').trim(),
          role: String(data.owner_role || '').trim()
        },
        country: String(data.country || '').trim().toUpperCase(),
        industry: String(data.industry || '').trim(),
        website: String(data.website || '').trim(),
        target_customers: String(data.target_customers || '').trim(),
        timeline: String(data.timeline || '').trim(),
        setup_notes: String(data.setup_notes || '').trim(),
        currency: String(data.budget_currency || 'INR').trim().toUpperCase(),
        budget: {
          amount: data.budget_amount === '' ? null : Number(data.budget_amount),
          currency: String(data.budget_currency || 'INR').trim().toUpperCase()
        },
        assets
      };
      return payload;
    }

    // --------------------------------------------------------------- submit
    async submit() {
      if (this.submitting) return;
      this.errors = this._validate();
      if (Object.keys(this.errors).length) {
        this.step = 'form';
        this._renderFormWithErrors(Object.keys(this.errors)[0]);
        return;
      }

      this.submitting = true;
      this.errors = {};
      const submitButton = document.getElementById('zcCreateSubmit');
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.setAttribute('aria-busy', 'true');
        submitButton.textContent = t('company.create.submitting');
      }

      try {
        const created = await this._post('/api/v1/companies', this._payload());
        if (!created.ok) {
          this._handleCreateError(created);
          return;
        }
        this.companyId = created.data.id;
        // The brief has become a real company; the draft is no longer needed
        // even if the submit call below fails.
        await this._clearDraft();

        const submitted = await this._post(`/api/v1/companies/${encodeURIComponent(this.companyId)}/submit`, {});
        if (!submitted.ok) {
          // The company exists and is a draft; say exactly that instead of
          // pretending the build started.
          this._toast(t('company.create.error.submit_failed'), 'error');
          this._navigate(`/company/${this.companyId}/overview`);
          return;
        }

        if (submitted.data && submitted.data.workflow_started === false && submitted.data.workflow_note) {
          this._toast(submitted.data.workflow_note, 'warning');
        } else {
          this._toast(t('company.create.created'), 'success');
        }
        this._navigate(`/company/${this.companyId}/build`);
      } catch (err) {
        this._toast(t('company.create.error.network'), 'error');
      } finally {
        this.submitting = false;
      }
    }

    _handleCreateError(result) {
      const data = result.data || {};
      const code = String(data.code || '');
      if (code === 'DUPLICATE_COMPANY_NAME') {
        this.errors = { name: t('company.create.error.duplicate') };
      } else if (code === 'VALIDATION_FAILED' && Array.isArray(data.detail)) {
        this.errors = {};
        data.detail.forEach((item) => {
          const field = String(item.field || 'name').replace(/^owner\./, 'owner_').replace(/\./g, '_');
          if (item.message) this.errors[field] = item.message;
        });
      } else if (code === 'FORBIDDEN') {
        this._toast(t('company.create.denied.body'), 'warning');
        this._navigate('/company/add');
        return;
      } else {
        this.errors = { name: String(data.error || t('company.create.error.create_failed')) };
      }
      this.step = 'form';
      if (this.errors.website || this.errors.assets || this.errors.budget_amount) this.optionalOpen = true;
      this._renderFormWithErrors(Object.keys(this.errors)[0]);
    }

    async _post(path, body) {
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      });
      let data = {};
      try {
        data = await res.json();
      } catch (err) {
        data = {};
      }
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
        } catch (err) { /* best effort; the draft belongs to this user */ }
      }
    }

    // --------------------------------------------------------------- helpers
    _goBack() {
      this._navigate('/company');
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
      this.step = 'form';
      this.errors = {};
      this.optionalOpen = false;
      this._loadedRemote = false;
      try {
        localStorage.removeItem(DRAFT_ID_KEY);
        localStorage.removeItem(DRAFT_DATA_KEY);
      } catch (err) { /* blocked */ }
    }
  }

  window.CompanySetupCreate = new CreateCompanyFlow();
})();
