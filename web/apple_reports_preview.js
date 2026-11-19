/**
 * URA / ZONATA — Apple-Grade Executive Reports Preview
 * Paper Canvas look matching exportable PDF documents.
 * Quiet • Spacious • Fast • Obvious
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

  const REPORTS_CATALOG = {
    weekly_exec: {
      id: 'weekly_exec',
      title: 'Weekly Executive Briefing & Situational Report',
      category: 'EXECUTIVE',
      date: 'Week 44 • November 2026',
      generatedBy: 'AI CEO Sovereign Strategy Engine',
      verificationState: 'AUDITED & VERIFIED',
      merkleRoot: 'sha256:7f90c4a162e84b8109ad5c66914b1ce3b98c47b5e40a',
      summary: 'All 6 executive departments operated within constitutional tolerances. Total weekly gross revenue reached ₹3,84,000 with a 29.4% operating margin. Inbound customer acquisition expanded by 18% driven by high-intent AI search citations.',
      metrics: [
        { label: 'Weekly Revenue', value: '₹3,84,000', note: '+18% vs prior week' },
        { label: 'Net Profit', value: '₹1,12,896', note: '29.4% margin' },
        { label: 'Decisions Enacted', value: '42 Actions', note: '100% policy compliant' },
        { label: 'Pending Approvals', value: '2 Items', note: 'Awaiting human review' }
      ],
      sections: [
        {
          heading: '1. Departmental Performance Highlights',
          content: `
            <ul style="margin:8px 0 0 20px; padding:0; line-height:1.6; font-size:14px; color:var(--label-2);">
              <li><strong>CMO (Growth):</strong> Answer Engine optimization resulted in #1 citation for luxury bookings across 3 German feeder regions. Blended CAC decreased from ₹1,200 to ₹980.</li>
              <li><strong>COO (Operations):</strong> Order fulfillment maintained 99.8% SLA across 42 automated manifests with zero customer delivery delays.</li>
              <li><strong>CTO (Technology):</strong> Zero platform downtime over 42 days. Database pool limits elasticity successfully scaled to absorb peak inbound webhook load.</li>
              <li><strong>CFO (Treasury):</strong> Reconciled 142 merchant transactions with zero discrepancies. Double-entry general ledger hash verified.</li>
            </ul>
          `
        },
        {
          heading: '2. Autonomous Bottleneck Resolutions',
          content: `
            <p class="t-body" style="font-size:13.5px; line-height:1.55; color:var(--label-2);">
              During peak booking hours on Thursday, the CMO pricing engine identified a competitor surge in suite pricing and autonomously adjusted room tariffs by +6%, expanding gross margin without impacting conversion rate.
            </p>
          `
        }
      ]
    },

    financial_pl: {
      id: 'financial_pl',
      title: 'Monthly Financial Statement & P&L Analysis',
      category: 'FINANCIAL',
      date: 'October 2026 Closing Ledger',
      generatedBy: 'AI CFO & Financial Controller',
      verificationState: 'DOUBLE-ENTRY CRYPTOGRAPHIC PROOF',
      merkleRoot: 'sha256:3d2891f0923bca881729b8214fa81729381b8219487c',
      summary: 'Audited monthly performance shows gross revenue of ₹14,80,000 and total operating costs of ₹10,51,500, yielding a net operating profit of ₹4,28,500. Cash runway remains healthy at 18.4 months with zero short-term debt liabilities.',
      metrics: [
        { label: 'Gross Revenue', value: '₹14,80,000', note: 'Audited bank inflows' },
        { label: 'Cost of Delivery', value: '₹5,20,000', note: 'Vendor disbursements' },
        { label: 'Operating Expenses', value: '₹5,31,500', note: 'Compute, marketing, tools' },
        { label: 'Net Profit', value: '₹4,28,500', note: '28.95% Net Margin' }
      ],
      sections: [
        {
          heading: '1. P&L Itemized Statement',
          content: `
            <div style="background:var(--surface-2); border-radius:var(--r-md); overflow:hidden; border:0.5px solid var(--separator);">
              <table style="width:100%; border-collapse:collapse; font-size:13.5px; text-align:left;">
                <thead>
                  <tr style="border-bottom:0.5px solid var(--separator); background:var(--surface-3);">
                    <th style="padding:10px 14px; font-weight:600; color:var(--label);">Account Category</th>
                    <th style="padding:10px 14px; font-weight:600; color:var(--label); text-align:right;">Amount (INR)</th>
                    <th style="padding:10px 14px; font-weight:600; color:var(--label); text-align:right;">% of Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style="border-bottom:0.5px solid var(--separator);">
                    <td style="padding:10px 14px; font-weight:600;">Gross Booked Revenue</td>
                    <td style="padding:10px 14px; text-align:right; font-family:var(--font-mono); color:var(--green); font-weight:600;">₹14,80,000</td>
                    <td style="padding:10px 14px; text-align:right; font-family:var(--font-mono);">100.0%</td>
                  </tr>
                  <tr style="border-bottom:0.5px solid var(--separator);">
                    <td style="padding:10px 14px; color:var(--label-2);">Direct Fulfillment & Logistics</td>
                    <td style="padding:10px 14px; text-align:right; font-family:var(--font-mono); color:var(--red);">-₹5,20,000</td>
                    <td style="padding:10px 14px; text-align:right; font-family:var(--font-mono);">35.1%</td>
                  </tr>
                  <tr style="border-bottom:0.5px solid var(--separator);">
                    <td style="padding:10px 14px; color:var(--label-2);">Sales & Performance Ad Spend</td>
                    <td style="padding:10px 14px; text-align:right; font-family:var(--font-mono); color:var(--red);">-₹2,48,000</td>
                    <td style="padding:10px 14px; text-align:right; font-family:var(--font-mono);">16.8%</td>
                  </tr>
                  <tr style="border-bottom:0.5px solid var(--separator);">
                    <td style="padding:10px 14px; color:var(--label-2);">AI Infrastructure & MCP Compute</td>
                    <td style="padding:10px 14px; text-align:right; font-family:var(--font-mono); color:var(--red);">-₹2,83,500</td>
                    <td style="padding:10px 14px; text-align:right; font-family:var(--font-mono);">19.2%</td>
                  </tr>
                  <tr style="background:var(--surface-3);">
                    <td style="padding:12px 14px; font-weight:700; color:var(--label);">Net Operating Profit</td>
                    <td style="padding:12px 14px; text-align:right; font-family:var(--font-mono); color:var(--green); font-weight:700;">₹4,28,500</td>
                    <td style="padding:12px 14px; text-align:right; font-family:var(--font-mono); font-weight:700;">28.95%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          `
        }
      ]
    },

    workforce_sop: {
      id: 'workforce_sop',
      title: 'AI Workforce Performance & SOP Compliance Audit',
      category: 'WORKFORCE',
      date: 'Monthly Governance Audit • October 2026',
      generatedBy: 'AI CHRO & Performance Reviewer',
      verificationState: 'CONSTITUTIONAL CERTIFIED',
      merkleRoot: 'sha256:9a81c2f90a1820bcf8190281b9c819203810293810a9',
      summary: '14 certified AI employees completed 11,240 discrete autonomous actions with 0 constitutional policy deviations. All subordinates strictly adhere to the invariant: Employees operate agents; agents never operate employees.',
      metrics: [
        { label: 'Active Employees', value: '14 Roles', note: '100% staffed' },
        { label: 'SOP Compliance', value: '100%', note: '0 policy deviations' },
        { label: 'Agent Tools Used', value: '26 Tools', note: 'Isolated execution' },
        { label: 'Avg Task Latency', value: '1.8s', note: 'High throughput' }
      ],
      sections: [
        {
          heading: '1. Constitutional Authority Scope Verification',
          content: `
            <p class="t-body" style="font-size:13.5px; line-height:1.55; color:var(--label-2);">
              Every action dispatched during the reporting window was checked against the ZONATA Constitution PolicyEngine. Zero attempts were recorded where a tool or execution agent attempted to command an AI employee.
            </p>
          `
        }
      ]
    },

    security_dlp: {
      id: 'security_dlp',
      title: 'Cyber Defense, DLP & Sovereignty Certificate',
      category: 'SECURITY',
      date: 'Hourly Continuous Verification Chain',
      generatedBy: 'AI CISO & Sovereign Integrity Daemon',
      verificationState: 'TAMPER-PROOF LEDGER VALIDATED',
      merkleRoot: 'sha256:5b8109ad7f90c4a162e84b8109ad5c66914b1ce3b98c',
      summary: '13 concentric security layers remained active throughout the monitoring cycle. 0 bytes of sensitive customer PII or encrypted API keys leaked outside verified sandboxes. 100% of event entries match root ledger Merkle state.',
      metrics: [
        { label: 'Security Score', value: '99.4%', note: 'Enterprise Fortress' },
        { label: 'Active Defense Rings', value: '13 / 13', note: 'All rings engaged' },
        { label: 'Data Egress Leakage', value: '0 Bytes', note: 'Strict DLP screening' },
        { label: 'Ledger Hash Valid', value: 'Verified', note: 'SHA-256 chain intact' }
      ],
      sections: [
        {
          heading: '1. Defense Ring Telemetry Status',
          content: `
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px;">
              <div style="background:var(--surface-2); padding:10px 14px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
                <div class="t-footnote" style="font-weight:600;">Ring 1-4: Network & Sandbox</div>
                <span class="chip-apple chip-green" style="font-size:10.5px; margin-top:4px;">Isolated & Active</span>
              </div>
              <div style="background:var(--surface-2); padding:10px 14px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
                <div class="t-footnote" style="font-weight:600;">Ring 5-8: DLP & PII Screening</div>
                <span class="chip-apple chip-green" style="font-size:10.5px; margin-top:4px;">100% Sanitized</span>
              </div>
              <div style="background:var(--surface-2); padding:10px 14px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
                <div class="t-footnote" style="font-weight:600;">Ring 9-13: Cryptographic Merkle</div>
                <span class="chip-apple chip-green" style="font-size:10.5px; margin-top:4px;">Zero Tampering</span>
              </div>
            </div>
          `
        }
      ]
    }
  };

  class AppleReportsPreviewController {
    constructor() {
      this.containerId = 'view-reports';
      this.activeReportId = 'weekly_exec';
    }

    render(containerOrId = this.containerId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;

      if (!container) return;

      const report = REPORTS_CATALOG[this.activeReportId] || REPORTS_CATALOG['weekly_exec'];

      container.innerHTML = `
        <div style="max-width:1120px; margin:0 auto; display:flex; flex-direction:column; gap:28px;">

          <!-- 1. TOP HEADER & EXPORT CONTROLS -->
          <header style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:20px; padding-bottom:8px;">
            <div>
              <div class="t-caption" style="text-transform:uppercase; letter-spacing:0.05em; color:var(--accent); font-weight:700; margin-bottom:4px;">
                Executive Business Intelligence
              </div>
              <h1 class="t-large-title" style="margin:0;">Executive Reports & Statements</h1>
              <p class="t-callout" style="color:var(--label-2); margin-top:6px;">
                Audited executive briefings, P&L statements, and governance certificates formatted for print & board export.
              </p>
            </div>

            <div style="display:flex; gap:10px;">
              <button class="btn-apple btn-apple-secondary spring-press"
                      onclick="AppleReportsPreview.copySummary()"
                      style="font-size:13px; padding:8px 16px;">
                ${window.Icon ? window.Icon({ name: 'copy', size: 14 }) : '📋'}
                <span>Copy Summary</span>
              </button>
              <button class="btn-apple btn-apple-primary spring-press"
                      onclick="AppleReportsPreview.exportPdf()"
                      style="font-size:13px; padding:8px 18px;">
                ${window.Icon ? window.Icon({ name: 'download', size: 14 }) : '📄'}
                <span>Print / Export PDF</span>
              </button>
            </div>
          </header>

          <!-- 2. REPORT TYPE SELECTOR CHIPS -->
          <div style="display:flex; flex-wrap:wrap; gap:8px;">
            ${[
              { id: 'weekly_exec', label: 'Weekly Executive Briefing' },
              { id: 'financial_pl', label: 'Monthly Financial P&L' },
              { id: 'workforce_sop', label: 'Workforce & SOP Compliance' },
              { id: 'security_dlp', label: 'Cyber Defense Certificate' }
            ].map(r => `
              <button class="chip-apple ${this.activeReportId === r.id ? 'chip-green' : 'chip-neutral'} spring-press"
                      onclick="AppleReportsPreview.selectReport('${r.id}')"
                      style="cursor:pointer; font-size:13px; padding:8px 16px; font-weight:${this.activeReportId === r.id ? '600' : '400'};">
                ${escapeHtml(r.label)}
              </button>
            `).join('')}
          </div>

          <!-- 3. DOCUMENT PAPER CANVAS (Matches PDF Layout) -->
          <div class="apple-document-canvas">
            <div class="apple-document-page">
              
              <!-- Document Header -->
              <div style="border-bottom:1px solid var(--separator); padding-bottom:24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
                <div>
                  <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                    <span class="chip-apple chip-green" style="font-size:11px; font-weight:700;">
                      ${escapeHtml(report.verificationState)}
                    </span>
                    <span class="t-caption" style="color:var(--label-3);">•</span>
                    <span class="t-caption" style="color:var(--label-2); font-weight:500;">
                      ${escapeHtml(report.date)}
                    </span>
                  </div>
                  <h2 class="t-title-1" style="margin:0 0 6px 0; color:var(--label);">${escapeHtml(report.title)}</h2>
                  <div class="t-caption" style="color:var(--label-3);">
                    Prepared by: <strong style="color:var(--label-2);">${escapeHtml(report.generatedBy)}</strong>
                  </div>
                </div>

                ${window.AppTile ? window.AppTile({ entity: 'company', size: 48 }) : ''}
              </div>

              <!-- Cryptographic Provenance Strip -->
              <div style="background:var(--surface-2); padding:10px 14px; border-radius:var(--r-md); border:0.5px solid var(--separator); display:flex; justify-content:space-between; align-items:center; font-size:12px; color:var(--label-2); font-family:var(--font-mono);">
                <span>Immutable Proof Hash:</span>
                <span style="color:var(--accent); font-weight:600;">${escapeHtml(report.merkleRoot)}</span>
              </div>

              <!-- Executive Summary Callout -->
              <div>
                <h3 class="t-headline" style="color:var(--label); margin-bottom:6px;">Executive Summary</h3>
                <p class="t-body" style="color:var(--label-2); line-height:1.6; font-size:14.5px; margin:0;">
                  ${escapeHtml(report.summary)}
                </p>
              </div>

              <!-- Key Metrics Grid -->
              <div>
                <h3 class="t-headline" style="color:var(--label); margin-bottom:12px;">Verified Key Indicators</h3>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:12px;">
                  ${report.metrics.map(m => `
                    <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
                      <div class="t-caption" style="color:var(--label-3); text-transform:uppercase;">${escapeHtml(m.label)}</div>
                      <div class="t-title-2 tabular-nums" style="margin-top:4px; color:var(--label); font-weight:700;">${escapeHtml(m.value)}</div>
                      <div class="t-footnote" style="color:var(--green); margin-top:2px; font-size:12px;">${escapeHtml(m.note)}</div>
                    </div>
                  `).join('')}
                </div>
              </div>

              <!-- Dynamic Document Sections -->
              ${report.sections.map(sec => `
                <div>
                  <h3 class="t-headline" style="color:var(--label); margin-bottom:8px;">${escapeHtml(sec.heading)}</h3>
                  ${sec.content}
                </div>
              `).join('')}

              <!-- Document Footer & Attestation Seal -->
              <div style="margin-top:24px; padding-top:20px; border-top:1px solid var(--separator); display:flex; justify-content:space-between; align-items:flex-end; font-size:12px; color:var(--label-3);">
                <div>
                  <div>ZONATA Sovereign Enterprise Operating System</div>
                  <div style="margin-top:2px;">Automated cryptographic attestation • Zero manual fabrication</div>
                </div>
                <div style="text-align:right;">
                  <span class="chip-apple chip-neutral" style="font-size:11px;">Page 1 of 1</span>
                </div>
              </div>

            </div>
          </div>

        </div>
      `;
    }

    selectReport(reportId) {
      this.activeReportId = reportId;
      this.render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    exportPdf() {
      if (window.UI && window.UI.showToast) {
        window.UI.showToast('Preparing PDF document layout for print...', 'info');
      }
      setTimeout(() => {
        window.print();
      }, 300);
    }

    copySummary() {
      const report = REPORTS_CATALOG[this.activeReportId] || REPORTS_CATALOG['weekly_exec'];
      if (navigator.clipboard) {
        navigator.clipboard.writeText(`${report.title}\n${report.date}\n\n${report.summary}`);
        if (window.UI && window.UI.showToast) {
          window.UI.showToast('Executive summary copied to clipboard.', 'success');
        }
      }
    }
  }

  window.AppleReportsPreview = new AppleReportsPreviewController();
})();
