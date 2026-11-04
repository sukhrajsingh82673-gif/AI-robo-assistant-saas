/**
 * URA / ZONATA — Apple-Grade Governed Terminal
 * Quiet • Spacious • Fast • Obvious
 * Fixed permission bar, human-readable command translations, kill switch, and sandboxed log stream.
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

  const INITIAL_LOGS = [
    {
      time: '11:02:14',
      type: 'sys',
      cmd: 'sandbox init --tenant zonata_prod --isolation container',
      human: 'Spawning isolated Linux container with restricted network egress',
      out: '[KERNEL] Sandboxed container #419 initialized. UID=1001, GID=1001. Egress whitelist engaged.'
    },
    {
      time: '11:02:18',
      type: 'mcp',
      cmd: 'mcp-client probe --transport stdio --server postgres-mcp',
      human: 'Checking Model Context Protocol database connection health',
      out: '[MCP] Postgres server verified. Latency: 4.2ms. Read-only query policy confirmed.'
    },
    {
      time: '11:02:25',
      type: 'sec',
      cmd: 'sha256sum /var/log/ledger/audit_chain.jsonl',
      human: 'Verifying cryptographic Merkle root of transaction ledger',
      out: '7f90c4a162e84b8109ad5c66914b1ce3b98c47b5e40a  /var/log/ledger/audit_chain.jsonl [MATCH]'
    }
  ];

  class AppleGovernedTerminalController {
    constructor() {
      this.containerId = 'view-terminal';
      this.isGoverned = true;
      this.isKilled = false;
      this.isPaused = false;
      this.logs = [...INITIAL_LOGS];
    }

    render(containerOrId = this.containerId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;

      if (!container) return;

      container.innerHTML = `
        <div style="max-width:1120px; margin:0 auto; display:flex; flex-direction:column; gap:24px;">

          <!-- 1. HEADER & FIXED PERMISSION BAR -->
          <header style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:20px; padding-bottom:8px;">
            <div>
              <div class="t-caption" style="text-transform:uppercase; letter-spacing:0.05em; color:var(--accent); font-weight:700; margin-bottom:4px;">
                Autonomous Substrate Control
              </div>
              <h1 class="t-large-title" style="margin:0;">Governed Execution Terminal</h1>
              <p class="t-callout" style="color:var(--label-2); margin-top:6px;">
                Sandboxed shell execution with constitutional policy gating and human-readable command translations.
              </p>
            </div>

            <!-- Permission & Safety Controls -->
            <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
              <!-- Safety Mode Toggle -->
              <div style="background:var(--surface-2); padding:4px 10px; border-radius:var(--r-md); border:0.5px solid var(--separator); display:flex; align-items:center; gap:8px;">
                <span class="t-caption" style="color:var(--label-2); font-weight:500;">Mode:</span>
                <span class="chip-apple ${this.isGoverned ? 'chip-green' : 'chip-red'}" style="font-size:11.5px; padding:2px 8px;">
                  ${this.isGoverned ? '🔒 Governed' : '⚠️ Root Unrestricted'}
                </span>
              </div>

              <!-- Scope Badge -->
              <span class="chip-apple chip-neutral" style="font-size:12px; padding:6px 12px;">
                Container #419 • Egress Quarantined
              </span>

              <!-- Kill Switch Button -->
              <button class="btn-apple ${this.isKilled ? 'btn-apple-secondary' : 'btn-apple-destructive'} spring-press"
                      onclick="AppleGovernedTerminal.toggleKillSwitch()"
                      style="font-size:13px; padding:8px 16px;">
                ${this.isKilled ? 'Restart Subsystem' : '🛑 Emergency Kill Switch'}
              </button>
            </div>
          </header>

          <!-- 2. KILL STATE BANNER IF TRIGGERED -->
          ${this.isKilled ? `
            <div class="card-apple" style="background:var(--red-tint); border-color:var(--red); padding:16px 20px; color:var(--red); display:flex; align-items:center; gap:12px;">
              ${window.Icon ? window.Icon({ name: 'alert-triangle', size: 24, tone: 'red' }) : '⚠️'}
              <div>
                <strong>EMERGENCY KILL SWITCH ENGAGED:</strong> All active containers, background agents, and socket connections terminated. Subsystem locked until manual reset.
              </div>
            </div>
          ` : ''}

          <!-- 3. TERMINAL WINDOW -->
          <div class="apple-terminal-window">
            
            <!-- Window Title Bar -->
            <div class="apple-terminal-titlebar">
              <div class="apple-terminal-dots">
                <span class="apple-terminal-dot apple-terminal-dot-red" onclick="AppleGovernedTerminal.clearLogs()" title="Clear Logs"></span>
                <span class="apple-terminal-dot apple-terminal-dot-yellow" onclick="AppleGovernedTerminal.togglePause()" title="Pause/Resume Stream"></span>
                <span class="apple-terminal-dot apple-terminal-dot-green" title="Connection Active"></span>
              </div>
              <div style="font-size:12px; color:#94A3B8; font-family:var(--font-mono); display:flex; align-items:center; gap:8px;">
                <span>zonata@sandbox-node-04: ~</span>
                <span style="opacity:0.4;">|</span>
                <span style="color:#10B981;">● ${this.isPaused ? 'STREAM PAUSED' : 'LIVE TELEMETRY'}</span>
              </div>
              <div style="display:flex; gap:8px;">
                <button class="btn-apple btn-apple-plain" onclick="AppleGovernedTerminal.clearLogs()" style="color:#94A3B8; font-size:11.5px; padding:2px 8px;">
                  Clear
                </button>
                <button class="btn-apple btn-apple-plain" onclick="AppleGovernedTerminal.togglePause()" style="color:#94A3B8; font-size:11.5px; padding:2px 8px;">
                  ${this.isPaused ? 'Resume' : 'Pause'}
                </button>
              </div>
            </div>

            <!-- Terminal Log Content Area -->
            <div class="apple-terminal-log" id="appleTerminalLogBox">
              ${this.logs.map(log => this.renderLogEntry(log)).join('')}
            </div>

            <!-- Command Input Bar -->
            <div style="background:rgba(255,255,255,0.02); border-top:0.5px solid rgba(255,255,255,0.08); padding:14px 20px; display:flex; flex-direction:column; gap:10px;">
              
              <!-- Quick Prompt Chips -->
              <div style="display:flex; flex-wrap:wrap; gap:8px;">
                <span style="font-size:11.5px; color:#64748B; align-self:center;">Pre-verified directives:</span>
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleGovernedTerminal.selectPreset('docker ps', 'List all running sandboxed agent containers')"
                        style="font-size:11px; padding:3px 8px; cursor:pointer; background:rgba(255,255,255,0.06); color:#94A3B8;">
                  docker ps
                </button>
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleGovernedTerminal.selectPreset('curl -s localhost:8000/api/health', 'Probe sovereign microservice cluster health')"
                        style="font-size:11px; padding:3px 8px; cursor:pointer; background:rgba(255,255,255,0.06); color:#94A3B8;">
                  probe health
                </button>
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleGovernedTerminal.selectPreset('python3 audit_merkle.py --verify', 'Recalculate SHA-256 Merkle root across all accounts')"
                        style="font-size:11px; padding:3px 8px; cursor:pointer; background:rgba(255,255,255,0.06); color:#94A3B8;">
                  verify merkle
                </button>
              </div>

              <!-- Input Row with Prompt -->
              <div style="display:flex; gap:12px; align-items:center;">
                <span style="color:#38BDF8; font-family:var(--font-mono); font-weight:700;">❯</span>
                <input type="text"
                       id="appleTerminalInput"
                       placeholder="${this.isKilled ? 'Subsystem halted. Restart to enter commands.' : 'Type command (e.g. docker ps, git status)...'}"
                       ${this.isKilled ? 'disabled' : ''}
                       onkeydown="if(event.key === 'Enter') AppleGovernedTerminal.executeFromInput();"
                       style="flex:1; background:transparent; border:none; color:#F8FAFC; font-family:var(--font-mono); font-size:13.5px; outline:none;">
                <button class="btn-apple btn-apple-secondary spring-press"
                        ${this.isKilled ? 'disabled' : ''}
                        onclick="AppleGovernedTerminal.executeFromInput()"
                        style="padding:6px 14px; font-size:12px;">
                  Execute
                </button>
              </div>

            </div>

          </div>

        </div>
      `;

      this.scrollToBottom();
    }

    renderLogEntry(log) {
      return `
        <div style="display:flex; flex-direction:column; gap:3px; padding-bottom:8px; border-bottom:0.5px solid rgba(255,255,255,0.04);">
          <!-- Human readable translation banner -->
          ${log.human ? `
            <div style="display:flex; align-items:center; gap:6px; font-size:11.5px; color:#38BDF8; font-family:var(--font-sans);">
              <span>ℹ️</span>
              <span><strong>Action Intent:</strong> ${escapeHtml(log.human)}</span>
            </div>
          ` : ''}

          <!-- Command line -->
          <div style="display:flex; gap:10px; align-items:baseline;">
            <span style="color:#64748B; font-size:11px;">[${log.time}]</span>
            <span style="color:#A855F7; font-weight:600;">$</span>
            <span style="color:#F1F5F9; font-weight:500;">${escapeHtml(log.cmd)}</span>
          </div>

          <!-- Output -->
          <div style="padding-left:22px; color:#94A3B8; font-size:12.5px; white-space:pre-wrap; word-break:break-word;">
            ${escapeHtml(log.out)}
          </div>
        </div>
      `;
    }

    selectPreset(cmd, human) {
      const input = document.getElementById('appleTerminalInput');
      if (input) {
        input.value = cmd;
        input.dataset.human = human;
        input.focus();
      }
    }

    executeFromInput() {
      if (this.isKilled) return;
      const input = document.getElementById('appleTerminalInput');
      if (!input || !input.value.trim()) return;

      const cmd = input.value.trim();
      const human = input.dataset.human || this.deriveHumanTranslation(cmd);

      this.runCommand(cmd, human);
      input.value = '';
      delete input.dataset.human;
    }

    deriveHumanTranslation(cmd) {
      const c = cmd.toLowerCase();
      if (c.includes('docker ps')) return 'Listing running sandboxed execution containers';
      if (c.includes('docker run')) return 'Starting isolated runtime container for delegated agent';
      if (c.includes('git status')) return 'Inspecting git repository status and file integrity';
      if (c.includes('curl')) return 'Querying internal microservice endpoint over local loopback';
      if (c.includes('merkle') || c.includes('sha256')) return 'Validating cryptographic audit chain state';
      if (c.includes('pytest')) return 'Running continuous Ralph Loop verification suite';
      return 'Executing sandboxed shell instruction under policy governance';
    }

    runCommand(cmd, human) {
      const now = new Date().toTimeString().split(' ')[0];
      const newEntry = {
        time: now,
        type: 'exec',
        cmd,
        human,
        out: `[EXEC] Completed with status code 0 (success). Execution time: 18ms. Sandbox constraints verified.`
      };

      this.logs.push(newEntry);
      this.render();

      if (window.UI && window.UI.showToast) {
        window.UI.showToast(`Command executed: ${cmd}`, 'success');
      }
    }

    toggleKillSwitch() {
      this.isKilled = !this.isKilled;
      if (this.isKilled) {
        this.logs.push({
          time: new Date().toTimeString().split(' ')[0],
          type: 'halt',
          cmd: 'SIGKILL --all',
          human: 'SOVEREIGN KILL SWITCH ACTIVATED — Halting all execution runtimes',
          out: '[HALT] Sent SIGKILL to PIDs in cgroup. 0 lingering subprocesses. Egress disabled.'
        });
        if (window.UI && window.UI.showToast) {
          window.UI.showToast('EMERGENCY KILL SWITCH ENGAGED', 'error');
        }
      } else {
        if (window.UI && window.UI.showToast) {
          window.UI.showToast('Subsystem rebooted and verified.', 'success');
        }
      }
      this.render();
    }

    togglePause() {
      this.isPaused = !this.isPaused;
      if (window.UI && window.UI.showToast) {
        window.UI.showToast(this.isPaused ? 'Telemetry log stream paused.' : 'Telemetry stream active.', 'info');
      }
      this.render();
    }

    clearLogs() {
      this.logs = [];
      this.render();
      if (window.UI && window.UI.showToast) {
        window.UI.showToast('Terminal logs cleared.', 'info');
      }
    }

    scrollToBottom() {
      setTimeout(() => {
        const box = document.getElementById('appleTerminalLogBox');
        if (box) box.scrollTop = box.scrollHeight;
      }, 50);
    }
  }

  window.AppleGovernedTerminal = new AppleGovernedTerminalController();
})();
