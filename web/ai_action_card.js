/**
 * URA / ZONATA — ActionCard & ApprovalCard Primitives
 * Implements the 5-part AI action pattern: Intent • Reason • Progress • Result • Control
 * Plus "Why?" explainability sheet on demand.
 */

(function() {
  'use strict';

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * ActionCard Component
   * 1. Intent: short verb phrase
   * 2. Reason: why
   * 3. Progress: live state with status dot/badge
   * 4. Result: what changed / impact
   * 5. Control: Undo, Details, Stop
   */
  function renderActionCard({
    intent = '',
    reason = '',
    state = 'working', // 'queued' | 'working' | 'needs-you' | 'done' | 'needs-attention' | 'paused'
    result = '',
    actorEntity = 'assistant',
    actorName = 'AI Agent',
    timestamp = '',
    undoSeconds = null,
    onDetails = null,
    onUndo = null,
    className = ''
  }) {
    const stateConfig = {
      queued: { label: 'Queued', tone: 'neutral', icon: 'clock' },
      working: { label: 'Working', tone: 'accent', icon: 'zap' },
      'needs-you': { label: 'Needs You', tone: 'orange', icon: 'hand' },
      done: { label: 'Done', tone: 'green', icon: 'check' },
      'needs-attention': { label: 'Needs Attention', tone: 'red', icon: 'alert-triangle' },
      paused: { label: 'Paused', tone: 'neutral', icon: 'pause' }
    };

    const currentConf = stateConfig[state] || stateConfig['working'];

    const tileHtml = window.AppTile ? window.AppTile({ entity: actorEntity, size: 36 }) : '';
    const statusChip = window.UI ? window.UI.Chip({ label: currentConf.label, tone: currentConf.tone, icon: currentConf.icon }) : '';

    return `
      <div class="card-apple action-card-apple ${className}" style="padding:18px 20px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:8px;">
          <div style="display:flex; align-items:center; gap:10px;">
            ${tileHtml}
            <div>
              <div class="t-headline" style="font-size:15px; color:var(--label);">${escapeHtml(intent)}</div>
              <div class="t-caption" style="color:var(--label-2);">${escapeHtml(actorName)}${timestamp ? ` • ${escapeHtml(timestamp)}` : ''}</div>
            </div>
          </div>
          <div>${statusChip}</div>
        </div>

        <!-- 2. Reason -->
        <p class="t-body" style="color:var(--label-2); font-size:13.5px; line-height:1.45; margin-bottom:10px;">
          <strong style="color:var(--label); font-weight:600;">Reason:</strong> ${escapeHtml(reason)}
        </p>

        <!-- 4. Result -->
        ${result ? `
          <div style="background:var(--surface-2); padding:8px 12px; border-radius:var(--r-md); border:0.5px solid var(--separator); margin-bottom:10px; font-size:13px; color:var(--label); display:flex; align-items:center; gap:6px;">
            <span style="color:var(--green); font-weight:600;">Result:</span>
            <span>${escapeHtml(result)}</span>
          </div>
        ` : ''}

        <!-- 5. Controls -->
        <div style="display:flex; justify-content:space-between; align-items:center; pt:8px; border-top:0.5px solid var(--separator); margin-top:8px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="btn-apple btn-apple-plain spring-press"
                    style="padding:4px 8px; font-size:12px;"
                    onclick="ActionCard.openWhy('${escapeHtml(intent)}', '${escapeHtml(reason)}', '${escapeHtml(result || 'Action verified by constitutional policy.')}')">
              Why?
            </button>
            <button class="btn-apple btn-apple-plain spring-press"
                    style="padding:4px 8px; font-size:12px;"
                    onclick="UI.showToast('Showing technical log stream...', 'info')">
              Details
            </button>
          </div>

          ${undoSeconds ? `
            <button class="btn-apple btn-apple-secondary spring-press"
                    style="padding:4px 10px; font-size:12px;"
                    onclick="UI.showToast('Action undone.', 'success'); this.closest('.action-card-apple').remove();">
              Undo (${undoSeconds}s)
            </button>
          ` : ''}
        </div>
      </div>
    `.trim();
  }

  /**
   * ApprovalCard Component
   */
  function renderApprovalCard({
    id = '',
    title = '',
    actorEntity = 'cmo',
    actorName = 'AI CMO',
    riskLevel = 'Medium', // 'Low' | 'Medium' | 'High'
    reason = '',
    worstCase = '',
    alternative = '',
    onApprove = null,
    onDecline = null,
    className = ''
  }) {
    const riskTones = {
      Low: 'neutral',
      Medium: 'orange',
      High: 'red'
    };
    const tone = riskTones[riskLevel] || 'orange';

    const tileHtml = window.AppTile ? window.AppTile({ entity: actorEntity, size: 40 }) : '';
    const riskChip = window.UI ? window.UI.Chip({ label: `${riskLevel} Risk`, tone, icon: riskLevel === 'High' ? 'alert-triangle' : 'shield' }) : '';

    return `
      <div class="card-apple approval-card-apple ${className}" style="padding:20px; border-left:3px solid var(--${tone}); margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:10px;">
          <div style="display:flex; align-items:center; gap:12px;">
            ${tileHtml}
            <div>
              <div class="t-headline" style="font-size:15px; color:var(--label);">${escapeHtml(title)}</div>
              <div class="t-caption" style="color:var(--label-2);">Requested by ${escapeHtml(actorName)}</div>
            </div>
          </div>
          <div>${riskChip}</div>
        </div>

        <p class="t-body" style="color:var(--label-2); font-size:13.5px; line-height:1.5; margin-bottom:10px;">
          ${escapeHtml(reason)}
        </p>

        <!-- Worst Case & Cheaper Alternative -->
        <div style="background:var(--surface-2); padding:10px 14px; border-radius:var(--r-md); border:0.5px solid var(--separator); margin-bottom:12px; display:flex; flex-direction:column; gap:6px; font-size:12.5px;">
          ${worstCase ? `<div><strong style="color:var(--red);">Worst Case:</strong> ${escapeHtml(worstCase)}</div>` : ''}
          ${alternative ? `<div><strong style="color:var(--label-2);">Cheaper Safe Alternative:</strong> ${escapeHtml(alternative)}</div>` : ''}
        </div>

        <!-- Action Buttons -->
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="btn-apple btn-apple-plain spring-press"
                    style="padding:4px 8px; font-size:12px;"
                    onclick="ActionCard.openWhy('${escapeHtml(title)}', '${escapeHtml(reason)}', 'Worst case: ${escapeHtml(worstCase || 'None')}')">
              Why?
            </button>
            <button class="btn-apple btn-apple-plain spring-press"
                    style="padding:4px 8px; font-size:12px;"
                    onclick="UI.showToast('Opening consultation chat with ${escapeHtml(actorName)}...', 'info')">
              Ask a Question
            </button>
          </div>

          <div style="display:flex; gap:8px;">
            <button class="btn-apple btn-apple-plain"
                    onclick="UI.showToast('Deferred for later review.', 'info'); this.closest('.approval-card-apple').remove();">
              Not Now
            </button>
            <button class="btn-apple btn-apple-primary"
                    onclick="${riskLevel === 'High' ? `ActionCard.confirmHighRisk('${escapeHtml(title)}', this)` : `UI.showToast('Approved.', 'success'); this.closest('.approval-card-apple').remove();`}">
              Approve
            </button>
          </div>
        </div>
      </div>
    `.trim();
  }

  function openWhySheet(title, reason, outcome) {
    if (!window.UI || !window.UI.openModal) return;

    window.UI.openModal(
      'Why the AI decided this',
      `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="display:flex; align-items:center; gap:10px;">
            ${window.AppTile ? window.AppTile({ entity: 'ceo', size: 36 }) : ''}
            <div>
              <div class="t-headline" style="font-size:15px;">${escapeHtml(title)}</div>
              <div class="t-caption" style="color:var(--label-2);">Autonomous Decision Provenance</div>
            </div>
          </div>

          <div style="background:var(--surface-2); padding:16px; border-radius:var(--r-md); border:0.5px solid var(--separator); display:flex; flex-direction:column; gap:10px;">
            <div>
              <span class="t-caption" style="font-weight:600; color:var(--label);">Data Evaluated:</span>
              <p class="t-footnote" style="color:var(--label-2); margin-top:2px;">
                Persistent general ledger snapshots, competitor pricing feeds, and 14-day booking elasticity records.
              </p>
            </div>
            <div>
              <span class="t-caption" style="font-weight:600; color:var(--label);">Options Considered:</span>
              <p class="t-footnote" style="color:var(--label-2); margin-top:2px;">
                1) Direct rate discounting (Rejected: lowers luxury brand perception).<br>
                2) Targeted package value add-ons (Selected: protects ADR while expanding margin).
              </p>
            </div>
            <div>
              <span class="t-caption" style="font-weight:600; color:var(--label);">Confidence Level:</span>
              <div style="margin-top:4px;">
                <span class="chip-apple chip-green">High Confidence (94% empirical fit)</span>
              </div>
            </div>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center;">
            <button class="btn-apple btn-apple-plain" onclick="UI.showToast('Log hash: sha256:7f83b1657...', 'info')">
              Technical Details
            </button>
            <button class="btn-apple btn-apple-secondary" onclick="UI.closeModal()">
              Close
            </button>
          </div>
        </div>
      `
    );
  }

  function confirmHighRisk(title, btn) {
    if (!window.UI || !window.UI.openModal) return;

    window.UI.openModal(
      'Confirm High-Risk Executive Action',
      `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="display:flex; align-items:center; gap:12px;">
            <span class="chip-apple chip-red" style="font-size:13px; padding:6px 12px;">High Risk Consequence</span>
          </div>
          <p class="t-body" style="color:var(--label); line-height:1.5;">
            You are about to authorize <strong>${escapeHtml(title)}</strong>. This will execute financial transactions or production code deploys exceeding standard L2 limits.
          </p>
          <div style="background:var(--red-tint); padding:12px; border-radius:var(--r-md); border:0.5px solid var(--red); color:var(--red); font-size:13px;">
            Consequence cannot be automatically undone once dispatched to live networks.
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button class="btn-apple btn-apple-secondary" onclick="UI.closeModal()">Cancel</button>
            <button class="btn-apple btn-apple-destructive" onclick="UI.showToast('High-risk action confirmed and executed.', 'success'); if('${btn.id}') document.getElementById('${btn.id}').closest('.approval-card-apple').remove(); UI.closeModal();">
              Confirm & Execute
            </button>
          </div>
        </div>
      `
    );
  }

  window.ActionCard = renderActionCard;
  window.ActionCard.openWhy = openWhySheet;
  window.ActionCard.confirmHighRisk = confirmHighRisk;
  window.ApprovalCard = renderApprovalCard;
})();
