/**
 * URA / ZONATA — Apple-Grade Co-Worker AI Assistant (The Real-World Jarvis)
 * Quiet • Spacious • Fast • Obvious
 * Seamless toggle between Personal Mode (Unrestricted) and Company Mode (AI CEO Supervised).
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

  const INITIAL_MESSAGES = {
    personal: [
      {
        sender: 'ai',
        time: '10:45 AM',
        text: 'Good morning. I’m ready in Personal Mode. Your personal tasks, research, and desktop actions run completely free without company policy gating. What can I do for you today?'
      }
    ],
    company: [
      {
        sender: 'ai',
        time: '10:48 AM',
        text: 'Switched to Company Mode. I am operating under direct supervision of the AI CEO and ZONATA Constitution. All database mutations, customer touches, and financial allocations require executive authorization.'
      },
      {
        sender: 'user',
        time: '10:50 AM',
        text: 'Can we rebalance ad spend toward European luxury suites for the upcoming weekend?'
      },
      {
        sender: 'ai',
        time: '10:51 AM',
        isActionCard: true,
        actionData: {
          intent: 'Formulated strategic ad reallocation proposal',
          reason: 'Weekend search intent in Zurich and Munich expanded by 24%.',
          state: 'needs-you',
          result: 'Shift ₹45,000 from generic search to high-intent luxury terms. Expected extra profit: ₹1,20,000.',
          actorEntity: 'cmo',
          actorName: 'AI CMO & Growth Engine',
          timestamp: 'Just now'
        }
      }
    ]
  };

  class AppleCoworkerAssistantController {
    constructor() {
      this.containerId = 'view-assistant';
      this.currentMode = 'company'; // 'personal' | 'company'
      this.orbState = 'idle';
      this.messages = {
        personal: [...INITIAL_MESSAGES.personal],
        company: [...INITIAL_MESSAGES.company]
      };
    }

    render(containerOrId = this.containerId, initialMode = null) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;

      if (!container) return;

      if (initialMode) {
        this.currentMode = initialMode;
      }

      const activeList = this.messages[this.currentMode] || [];

      container.innerHTML = `
        <div style="max-width:960px; margin:0 auto; display:flex; flex-direction:column; gap:24px; min-height:80vh;">

          <!-- 1. TOP HEADER & MODE SWITCHER -->
          <header style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; padding-bottom:12px; border-bottom:0.5px solid var(--separator);">
            <div style="display:flex; align-items:center; gap:16px;">
              <div id="coworkerOrbSlot">
                ${window.AiOrb ? window.AiOrb({ state: this.orbState, size: 56 }) : ''}
              </div>
              <div>
                <h1 class="t-title-1" style="margin:0;">ZONATA Co-Worker Assistant</h1>
                <div class="t-caption" style="color:var(--label-2); margin-top:2px;">
                  Your sovereign companion for desktop automation, personal support, and enterprise execution.
                </div>
              </div>
            </div>

            <!-- Mode Switch Segmented Control -->
            <div style="background:var(--surface-2); padding:3px; border-radius:var(--r-md); border:0.5px solid var(--separator); display:inline-flex;">
              <button class="spring-press"
                      onclick="AppleCoworkerAssistant.setMode('personal')"
                      style="padding:6px 16px; border-radius:var(--r-sm); border:none; background:${this.currentMode === 'personal' ? 'var(--surface)' : 'transparent'}; color:var(--label); font-weight:${this.currentMode === 'personal' ? '600' : '400'}; font-size:13px; box-shadow:${this.currentMode === 'personal' ? 'var(--shadow-1)' : 'none'}; cursor:pointer;">
                Personal Mode
              </button>
              <button class="spring-press"
                      onclick="AppleCoworkerAssistant.setMode('company')"
                      style="padding:6px 16px; border-radius:var(--r-sm); border:none; background:${this.currentMode === 'company' ? 'var(--surface)' : 'transparent'}; color:var(--label); font-weight:${this.currentMode === 'company' ? '600' : '400'}; font-size:13px; box-shadow:${this.currentMode === 'company' ? 'var(--shadow-1)' : 'none'}; cursor:pointer;">
                Company Mode (Governed)
              </button>
            </div>
          </header>

          <!-- 2. MODE STATUS BANNER -->
          ${this.currentMode === 'personal' ? `
            <div class="card-apple" style="padding:14px 20px; background:var(--surface-2); border-left:4px solid var(--accent); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div class="t-headline" style="font-size:13.5px; color:var(--label);">Personal Assistant Mode Active</div>
                <div class="t-caption" style="color:var(--label-2); margin-top:2px;">
                  Free and unrestricted for your personal notes, travel, and research. Does not alter company records.
                </div>
              </div>
              <span class="chip-apple chip-accent" style="font-size:11px;">Unrestricted</span>
            </div>
          ` : `
            <div class="card-apple" style="padding:14px 20px; background:linear-gradient(135deg, var(--green-tint) 0%, var(--surface-2) 100%); border-left:4px solid var(--green); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div class="t-headline" style="font-size:13.5px; color:var(--label);">Company Mode — AI CEO Supervised</div>
                <div class="t-caption" style="color:var(--label-2); margin-top:2px;">
                  Actions touching company workflows, budgets, or customer data require constitutional policy verification.
                </div>
              </div>
              <span class="chip-apple chip-green" style="font-size:11px;">Constitutional Safeguards Active</span>
            </div>
          `}

          <!-- 3. CHAT MESSAGE STREAM -->
          <div style="flex:1; display:flex; flex-direction:column; gap:16px; overflow-y:auto; padding-right:4px;" id="coworkerChatBox">
            ${activeList.map(msg => {
              if (msg.isActionCard && window.ActionCard) {
                return `
                  <div style="max-width:85%; align-self:flex-start;">
                    ${window.ActionCard(msg.actionData)}
                  </div>
                `;
              }

              const isUser = msg.sender === 'user';
              return `
                <div style="display:flex; flex-direction:column; gap:4px; align-self:${isUser ? 'flex-end' : 'flex-start'}; max-width:80%;">
                  <div class="apple-chat-bubble ${isUser ? 'apple-chat-bubble-user' : 'apple-chat-bubble-ai'}">
                    ${escapeHtml(msg.text)}
                  </div>
                  <span class="t-caption" style="color:var(--label-3); font-size:11px; align-self:${isUser ? 'flex-end' : 'flex-start'}; padding:0 4px;">
                    ${escapeHtml(msg.time)}
                  </span>
                </div>
              `;
            }).join('')}
          </div>

          <!-- 4. BOTTOM INPUT COMPOSER & SUGGESTION CHIPS -->
          <div style="display:flex; flex-direction:column; gap:10px; padding-top:12px; border-top:0.5px solid var(--separator);">
            
            <!-- Suggestion Chips based on mode -->
            <div style="display:flex; flex-wrap:wrap; gap:8px;">
              ${this.currentMode === 'personal' ? `
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleCoworkerAssistant.sendPreset('Summarize my pending personal agenda for today')"
                        style="cursor:pointer; font-size:12px; padding:4px 10px;">
                  🗓️ Summarize my day
                </button>
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleCoworkerAssistant.sendPreset('Compare direct flights from Zurich to London this Friday')"
                        style="cursor:pointer; font-size:12px; padding:4px 10px;">
                  ✈️ Search weekend flights
                </button>
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleCoworkerAssistant.sendPreset('Draft quick private note on personal investment thesis')"
                        style="cursor:pointer; font-size:12px; padding:4px 10px;">
                  📝 Draft personal note
                </button>
              ` : `
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleCoworkerAssistant.sendPreset('Ask AI CEO for approval to expand search marketing budget')"
                        style="cursor:pointer; font-size:12px; padding:4px 10px;">
                  🧠 Ask CEO for budget review
                </button>
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleCoworkerAssistant.sendPreset('Scan booking funnel for customer checkout dropouts')"
                        style="cursor:pointer; font-size:12px; padding:4px 10px;">
                  🔍 Run loophole scan on checkout
                </button>
                <button class="chip-apple chip-neutral spring-press"
                        onclick="AppleCoworkerAssistant.sendPreset('Check employee SOP compliance rating and tool isolation')"
                        style="cursor:pointer; font-size:12px; padding:4px 10px;">
                  🛡️ Audit workforce compliance
                </button>
              `}
            </div>

            <!-- Composer Input Bar -->
            <div style="display:flex; gap:10px; align-items:center;">
              <input type="text"
                     id="coworkerMessageInput"
                     class="input-apple"
                     placeholder="${this.currentMode === 'personal' ? 'Message personal assistant...' : 'Dispatch directive in Company Mode...'}"
                     onkeydown="if(event.key === 'Enter') AppleCoworkerAssistant.sendFromInput();"
                     style="flex:1; box-sizing:border-box; font-size:14px; padding:12px 16px;">
              
              <button class="btn-apple btn-apple-secondary spring-press"
                      onclick="UI.showToast('Voice transcription active...', 'info')"
                      style="padding:10px 14px; font-size:14px;"
                      title="Voice Input">
                🎙️
              </button>

              <button class="btn-apple btn-apple-primary spring-press"
                      onclick="AppleCoworkerAssistant.sendFromInput()"
                      style="padding:10px 20px; font-size:14px;">
                Send
              </button>
            </div>

          </div>

        </div>
      `;

      this.scrollToBottom();
    }

    setMode(mode) {
      this.currentMode = mode;
      this.render();
      if (window.UI && window.UI.showToast) {
        window.UI.showToast(mode === 'personal' ? 'Switched to Personal Mode' : 'Switched to Company Mode (CEO Supervised)', 'info');
      }
    }

    sendPreset(text) {
      const input = document.getElementById('coworkerMessageInput');
      if (input) {
        input.value = text;
        this.sendFromInput();
      }
    }

    sendFromInput() {
      const input = document.getElementById('coworkerMessageInput');
      if (!input || !input.value.trim()) return;

      const text = input.value.trim();
      input.value = '';

      this.sendMessage(text);
    }

    sendMessage(text) {
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const currentList = this.messages[this.currentMode];

      // Add user message
      currentList.push({
        sender: 'user',
        time: now,
        text
      });

      this.orbState = 'thinking';
      this.render();

      setTimeout(() => {
        this.orbState = 'idle';
        if (this.currentMode === 'personal') {
          currentList.push({
            sender: 'ai',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            text: `Processed your personal request: "${text}". Action completed in your private local workspace.`
          });
        } else {
          currentList.push({
            sender: 'ai',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            text: `AI CEO received your company directive: "${text}". Constitutional review verified. Specialized execution agent dispatched with SOP conformity.`
          });
        }
        this.render();
      }, 700);
    }

    scrollToBottom() {
      setTimeout(() => {
        const box = document.getElementById('coworkerChatBox');
        if (box) box.scrollTop = box.scrollHeight;
      }, 50);
    }
  }

  window.AppleCoworkerAssistant = new AppleCoworkerAssistantController();
})();
