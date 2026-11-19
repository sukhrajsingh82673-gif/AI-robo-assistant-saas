/**
 * URA / ZONATA — AiOrb Component
 * Signature AI Presence: Organic breathing gradient orb with physical states
 */

(function() {
  'use strict';

  // Inject Keyframe styles once
  if (!document.getElementById('ura-ai-orb-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'ura-ai-orb-styles';
    styleEl.textContent = `
      @keyframes orb-breathe {
        0%, 100% { transform: scale(1.00); opacity: 0.92; }
        50%      { transform: scale(1.04); opacity: 1.00; }
      }

      @keyframes orb-rotate {
        0%   { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }

      @keyframes orb-pulse-speak {
        0%, 100% { transform: scale(1.00); filter: blur(10px) brightness(1.0); }
        50%      { transform: scale(1.08); filter: blur(14px) brightness(1.2); }
      }

      @keyframes orb-needs-you {
        0%, 100% { transform: translateY(0); }
        50%      { transform: translateY(-4px); }
      }

      .ura-ai-orb-wrap {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        position: relative;
        flex-shrink: 0;
      }

      .ura-ai-orb-core {
        position: absolute;
        inset: 10%;
        border-radius: 50%;
        filter: blur(10px);
        transition: background 0.45s ease, filter 0.45s ease;
      }

      .ura-ai-orb-wrap.state-idle .ura-ai-orb-core {
        background: radial-gradient(circle at 35% 35%, #0A84FF 0%, #5E5CE6 55%, #30B0C7 100%);
        animation: orb-breathe 3.2s ease-in-out infinite;
      }

      .ura-ai-orb-wrap.state-thinking .ura-ai-orb-core {
        background: conic-gradient(from 0deg, #5E5CE6, #0A84FF, #30B0C7, #5E5CE6);
        animation: orb-rotate 2.4s linear infinite;
        filter: blur(12px);
      }

      .ura-ai-orb-wrap.state-speaking .ura-ai-orb-core {
        background: radial-gradient(circle at 50% 50%, #30B0C7 0%, #0A84FF 50%, #5E5CE6 100%);
        animation: orb-pulse-speak 0.9s ease-in-out infinite;
      }

      .ura-ai-orb-wrap.state-needs-you .ura-ai-orb-core {
        background: radial-gradient(circle at 40% 40%, #FFCC00 0%, #FF9500 60%, #FF3B30 100%);
        animation: orb-needs-you 2.0s ease-in-out infinite;
      }

      /* Thin Orbit Ring for Thinking State */
      .ura-ai-orb-ring {
        position: absolute;
        inset: 0;
        border-radius: 50%;
        border: 1.5px solid transparent;
        border-top-color: var(--accent);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.28s ease;
      }

      .ura-ai-orb-wrap.state-thinking .ura-ai-orb-ring {
        opacity: 0.85;
        animation: orb-rotate 1.2s linear infinite;
      }

      @media (prefers-reduced-motion: reduce) {
        .ura-ai-orb-wrap .ura-ai-orb-core,
        .ura-ai-orb-wrap .ura-ai-orb-ring {
          animation: none !important;
        }
      }
    `;
    document.head.appendChild(styleEl);
  }

  /**
   * Renders the AiOrb markup
   * @param {Object} props
   * @param {string} [props.state='idle'] - 'idle' | 'thinking' | 'speaking' | 'needs-you'
   * @param {number} [props.size=48] - 24 | 48 | 96 | 220
   * @param {string} [props.className=''] - Additional classes
   * @returns {string} HTML markup string
   */
  function renderAiOrb({ state = 'idle', size = 48, className = '' }) {
    return `
      <div class="ura-ai-orb-wrap state-${state} ${className}"
           style="width:${size}px; height:${size}px;"
           data-orb-state="${state}"
           aria-label="URA AI Status: ${state}"
           role="status">
        <div class="ura-ai-orb-core"></div>
        <div class="ura-ai-orb-ring"></div>
      </div>
    `.trim();
  }

  window.AiOrb = renderAiOrb;
})();
