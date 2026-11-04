/**
 * URA / ZONATA — Apple-Grade Primitive Components Library
 * High-performance, accessible, token-driven component primitives attached to window.UI.
 */

(function() {
  'use strict';

  const UI = {};

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // --------------------------------------------------------------------------
  // 1. Button Component
  // --------------------------------------------------------------------------
  UI.Button = function({
    label = '',
    variant = 'primary', // 'primary' | 'secondary' | 'plain' | 'destructive' | 'icon'
    icon = null,
    iconTrailing = null,
    loading = false,
    disabled = false,
    className = '',
    id = '',
    ariaLabel = '',
    onClick = ''
  }) {
    const variantClass = `btn-apple-${variant}`;
    const loadingClass = loading ? 'btn-apple-loading' : '';
    const idAttr = id ? `id="${escapeHtml(id)}"` : '';
    const clickAttr = onClick ? `onclick="${onClick}"` : '';
    const ariaAttr = ariaLabel ? `aria-label="${escapeHtml(ariaLabel)}"` : '';
    const disabledAttr = disabled || loading ? 'disabled aria-disabled="true"' : '';

    const iconHtml = icon && window.Icon ? window.Icon({ name: icon, size: 18, tone: variant === 'primary' ? 'white' : 'accent' }) : '';
    const trailingHtml = iconTrailing && window.Icon ? window.Icon({ name: iconTrailing, size: 16, tone: variant === 'primary' ? 'white' : 'accent' }) : '';

    return `
      <button class="btn-apple ${variantClass} ${loadingClass} ${className}"
              ${idAttr} ${clickAttr} ${ariaAttr} ${disabledAttr}>
        ${iconHtml}
        ${label ? `<span>${escapeHtml(label)}</span>` : ''}
        ${trailingHtml}
      </button>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 2. Input / Text Field Component
  // --------------------------------------------------------------------------
  UI.Input = function({
    type = 'text',
    label = '',
    placeholder = '',
    value = '',
    icon = null,
    helperText = '',
    errorMessage = '',
    disabled = false,
    id = '',
    className = '',
    onInput = ''
  }) {
    const errorClass = errorMessage ? 'input-apple-error' : '';
    const iconHtml = icon && window.Icon
      ? `<span style="position:absolute; left:12px; display:flex; align-items:center; pointer-events:none; z-index:1;">
           ${window.Icon({ name: icon, size: 16, tone: 'muted' })}
         </span>`
      : '';
    const paddingLeft = icon ? 'padding-left:38px;' : '';
    const idAttr = id ? `id="${escapeHtml(id)}"` : '';
    const disabledAttr = disabled ? 'disabled' : '';
    const inputAttr = onInput ? `oninput="${onInput}"` : '';

    return `
      <div class="field-group-apple ${className}">
        ${label ? `<label class="field-label-apple" for="${escapeHtml(id)}">${escapeHtml(label)}</label>` : ''}
        <div class="input-wrap-apple">
          ${iconHtml}
          <input type="${escapeHtml(type)}"
                 class="input-apple ${errorClass}"
                 style="${paddingLeft}"
                 placeholder="${escapeHtml(placeholder)}"
                 value="${escapeHtml(value)}"
                 ${idAttr} ${disabledAttr} ${inputAttr} />
        </div>
        ${errorMessage ? `<div class="field-msg-error">${window.Icon ? window.Icon({ name: 'alert-circle', size: 14, tone: 'red' }) : ''} ${escapeHtml(errorMessage)}</div>` : ''}
        ${helperText && !errorMessage ? `<div class="field-msg-helper">${escapeHtml(helperText)}</div>` : ''}
      </div>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 3. Card Component
  // --------------------------------------------------------------------------
  UI.Card = function({
    content = '',
    interactive = false,
    hero = false,
    glass = false,
    className = '',
    id = '',
    onClick = ''
  }) {
    const interClass = interactive ? 'card-apple-interactive spring-press' : '';
    const heroClass = hero ? 'card-apple-hero' : '';
    const glassClass = glass ? 'glass' : '';
    const clickAttr = onClick ? `onclick="${onClick}" role="button" tabindex="0"` : '';
    const idAttr = id ? `id="${escapeHtml(id)}"` : '';

    return `
      <div class="card-apple ${interClass} ${heroClass} ${glassClass} ${className}" ${idAttr} ${clickAttr}>
        ${content}
      </div>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 4. Chip Component
  // --------------------------------------------------------------------------
  UI.Chip = function({
    label = '',
    tone = 'neutral', // 'green' | 'orange' | 'red' | 'accent' | 'purple' | 'teal' | 'neutral'
    icon = null,
    removable = false,
    onClick = '',
    className = ''
  }) {
    const toneClass = `chip-${tone}`;
    const clickAttr = onClick ? `onclick="${onClick}" role="button" tabindex="0"` : '';
    const iconHtml = icon && window.Icon ? window.Icon({ name: icon, size: 12, tone }) : '';
    const removeHtml = removable
      ? `<span class="spring-press" style="margin-left:4px; cursor:pointer;" onclick="event.stopPropagation(); this.closest('.chip-apple').remove();">
           ${window.Icon ? window.Icon({ name: 'x', size: 12, tone }) : '✕'}
         </span>`
      : '';

    return `
      <span class="chip-apple ${toneClass} ${className}" ${clickAttr}>
        ${iconHtml}
        <span>${escapeHtml(label)}</span>
        ${removeHtml}
      </span>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 5. Toggle Switch Component
  // --------------------------------------------------------------------------
  UI.Toggle = function({
    checked = false,
    id = '',
    label = '',
    onChange = '',
    className = ''
  }) {
    const checkedAttr = checked ? 'checked' : '';
    const idAttr = id ? `id="${escapeHtml(id)}"` : '';
    const changeAttr = onChange ? `onchange="${onChange}"` : '';

    return `
      <div class="toggle-wrap-apple ${className}" style="display:inline-flex; align-items:center; gap:12px;">
        <label class="toggle-apple">
          <input type="checkbox" ${idAttr} ${checkedAttr} ${changeAttr} />
          <span class="toggle-track-apple"></span>
        </label>
        ${label ? `<span class="t-body" style="cursor:pointer;" onclick="document.getElementById('${escapeHtml(id)}').click()">${escapeHtml(label)}</span>` : ''}
      </div>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 6. Segmented Control Component
  // --------------------------------------------------------------------------
  UI.SegmentedControl = function({
    items = [], // Array of { id, label }
    activeId = '',
    id = '',
    onChange = ''
  }) {
    const idAttr = id ? `id="${escapeHtml(id)}"` : '';

    const buttonsHtml = items.map(item => {
      const isActive = item.id === activeId;
      return `
        <button type="button"
                class="segmented-item-apple ${isActive ? 'active' : ''}"
                data-segment-id="${escapeHtml(item.id)}"
                onclick="UI.handleSegmentClick(this, '${escapeHtml(onChange)}')">
          ${escapeHtml(item.label)}
        </button>
      `;
    }).join('');

    return `
      <div class="segmented-apple" ${idAttr} role="tablist">
        ${buttonsHtml}
      </div>
    `.trim();
  };

  UI.handleSegmentClick = function(btn, callbackName) {
    const parent = btn.closest('.segmented-apple');
    if (!parent) return;
    parent.querySelectorAll('.segmented-item-apple').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const segmentId = btn.getAttribute('data-segment-id');
    if (callbackName && typeof window[callbackName] === 'function') {
      window[callbackName](segmentId);
    }
  };

  // --------------------------------------------------------------------------
  // 7. Grouped List Row Component
  // --------------------------------------------------------------------------
  UI.ListRow = function({
    title = '',
    subtitle = '',
    tileEntity = null,
    trailingValue = '',
    chevron = true,
    onClick = '',
    className = ''
  }) {
    const tileHtml = tileEntity && window.AppTile
      ? window.AppTile({ entity: tileEntity, size: 36 })
      : '';
    const chevronHtml = chevron && window.Icon
      ? window.Icon({ name: 'chevron-right', size: 16, tone: 'muted' })
      : '';
    const clickAttr = onClick ? `onclick="${onClick}"` : '';

    return `
      <div class="list-row-apple ${className}" ${clickAttr} role="button" tabindex="0">
        <div class="list-row-left">
          ${tileHtml}
          <div>
            <div class="t-headline" style="font-size:15px;">${escapeHtml(title)}</div>
            ${subtitle ? `<div class="t-footnote" style="color:var(--label-2); margin-top:2px;">${escapeHtml(subtitle)}</div>` : ''}
          </div>
        </div>
        <div class="list-row-right">
          ${trailingValue ? `<span class="t-callout tabular-nums" style="color:var(--label-2);">${escapeHtml(trailingValue)}</span>` : ''}
          ${chevronHtml}
        </div>
      </div>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 8. Shimmering Skeleton Loader
  // --------------------------------------------------------------------------
  UI.Skeleton = function({
    type = 'text', // 'text' | 'card' | 'avatar'
    width = '100%',
    height = '14px',
    className = ''
  }) {
    const typeClass = type === 'avatar' ? 'skeleton-avatar' : 'skeleton-text';
    return `
      <div class="skeleton-apple ${typeClass} ${className}"
           style="width:${width}; height:${height};"
           aria-hidden="true"></div>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 9. Progress Bar Component
  // --------------------------------------------------------------------------
  UI.ProgressBar = function({
    progress = 0, // 0 - 100
    color = 'var(--accent)',
    className = ''
  }) {
    const clamped = Math.min(100, Math.max(0, progress));
    return `
      <div class="progress-bar-apple ${className}" role="progressbar" aria-valuenow="${clamped}" aria-valuemin="0" aria-valuemax="100">
        <div class="progress-bar-fill" style="width:${clamped}%; background:${color};"></div>
      </div>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 10. Empty State Component
  // --------------------------------------------------------------------------
  UI.EmptyState = function({
    icon = 'sparkles',
    title = '',
    description = '',
    actionButton = ''
  }) {
    const iconHtml = window.Icon ? window.Icon({ name: icon, size: 28, tone: 'primary' }) : '★';

    return `
      <div class="empty-state-apple">
        <div class="empty-state-icon">${iconHtml}</div>
        <h3 class="t-title-2">${escapeHtml(title)}</h3>
        <p class="t-callout" style="color:var(--label-2); line-height:1.5;">${escapeHtml(description)}</p>
        ${actionButton ? `<div style="margin-top:12px;">${actionButton}</div>` : ''}
      </div>
    `.trim();
  };

  // --------------------------------------------------------------------------
  // 11. Toast Notifications Stack
  // --------------------------------------------------------------------------
  UI.showToast = function(message, type = 'info', duration = 3500) {
    let container = document.getElementById('appleToastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'appleToastContainer';
      container.className = 'toast-container-apple';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast-apple glass';

    const toneMap = {
      success: 'green',
      warning: 'orange',
      error: 'red',
      info: 'accent'
    };
    const iconMap = {
      success: 'check-circle',
      warning: 'alert-triangle',
      error: 'alert-circle',
      info: 'info'
    };
    const tone = toneMap[type] || 'accent';
    const icon = iconMap[type] || 'info';

    const iconHtml = window.Icon ? window.Icon({ name: icon, size: 18, tone }) : '';

    toast.innerHTML = `
      ${iconHtml}
      <span style="color:var(--label);">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-8px) scale(0.96)';
      toast.style.transition = 'all 0.22s ease';
      setTimeout(() => toast.remove(), 250);
    }, duration);
  };

  // --------------------------------------------------------------------------
  // 12. Modal & Sheet Controller
  // --------------------------------------------------------------------------
  UI.openModal = function(title, bodyHtml) {
    let overlay = document.getElementById('appleModalOverlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'appleModalOverlay';
      overlay.className = 'modal-overlay-apple';
      overlay.innerHTML = `
        <div class="modal-dialog-apple" role="dialog" aria-modal="true" aria-labelledby="appleModalTitle">
          <div class="modal-header-apple">
            <h3 class="t-headline" id="appleModalTitle"></h3>
            <button class="btn-apple-icon spring-press" onclick="UI.closeModal()" aria-label="Close Dialog">
              ${window.Icon ? window.Icon({ name: 'x', size: 18, tone: 'default' }) : '✕'}
            </button>
          </div>
          <div class="modal-body-apple" id="appleModalBody"></div>
        </div>
      `;
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) UI.closeModal();
      });
      document.body.appendChild(overlay);
    }

    document.getElementById('appleModalTitle').textContent = title;
    document.getElementById('appleModalBody').innerHTML = bodyHtml;

    requestAnimationFrame(() => {
      overlay.classList.add('open');
      // Trap focus or keyboard Esc
      document.addEventListener('keydown', UI._handleEscKey);
    });
  };

  UI.closeModal = function() {
    const overlay = document.getElementById('appleModalOverlay');
    if (overlay) {
      overlay.classList.remove('open');
      document.removeEventListener('keydown', UI._handleEscKey);
    }
  };

  UI._handleEscKey = function(e) {
    if (e.key === 'Escape') {
      UI.closeModal();
    }
  };

  window.UI = UI;
})();
