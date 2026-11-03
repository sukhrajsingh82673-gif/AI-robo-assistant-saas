/**
 * URA / ZONATA — AppTile Component
 * Signature squircle tile with subtle top-to-bottom gradient, white glyph,
 * faint inner highlight, and layered soft shadow.
 */

(function() {
  'use strict';

  const ENTITY_CONFIG = {
    ceo: {
      label: 'AI CEO',
      glyph: 'compass',
      gradient: 'linear-gradient(180deg, #5E5CE6 0%, #3634A3 100%)'
    },
    coo: {
      label: 'COO (Operations)',
      glyph: 'flow',
      gradient: 'linear-gradient(180deg, #34C759 0%, #1E9E40 100%)'
    },
    cmo: {
      label: 'CMO (Marketing & Sales)',
      glyph: 'trend',
      gradient: 'linear-gradient(180deg, #FF9F0A 0%, #E37A00 100%)'
    },
    cto: {
      label: 'CTO (Technology)',
      glyph: 'chip',
      gradient: 'linear-gradient(180deg, #0A84FF 0%, #0060D0 100%)'
    },
    cfo: {
      label: 'CFO (Finance)',
      glyph: 'coins',
      gradient: 'linear-gradient(180deg, #30B0C7 0%, #1D8AA0 100%)'
    },
    chro: {
      label: 'CHRO (AI Workforce)',
      glyph: 'people',
      gradient: 'linear-gradient(180deg, #FF375F 0%, #D61F45 100%)'
    },
    security: {
      label: 'Cyber Security',
      glyph: 'shield',
      gradient: 'linear-gradient(180deg, #8E8E93 0%, #5A5A5F 100%)'
    },
    assistant: {
      label: 'Co-worker Assistant',
      glyph: 'sparkles',
      gradient: 'linear-gradient(135deg, #5E5CE6 0%, #0A84FF 50%, #30B0C7 100%)'
    },
    company: {
      label: 'Company',
      glyph: 'building',
      gradient: 'linear-gradient(180deg, #0071E3 0%, #0051A8 100%)'
    }
  };

  /**
   * Renders an AppTile squircle
   * @param {Object} props
   * @param {string} props.entity - 'ceo' | 'coo' | 'cmo' | 'cto' | 'cfo' | 'chro' | 'security' | 'assistant' | 'company'
   * @param {number} [props.size=40] - 28 | 40 | 64 | 96
   * @param {boolean} [props.active=false] - Whether active breathing ring is shown
   * @param {string} [props.className=''] - Additional classes
   * @returns {string} HTML markup string
   */
  function renderAppTile({ entity = 'company', size = 40, active = false, className = '' }) {
    const config = ENTITY_CONFIG[entity.toLowerCase()] || ENTITY_CONFIG['company'];
    const radius = Math.round(size * 0.22); // Concentric Apple squircle ~22%
    const iconSize = Math.max(14, Math.round(size * 0.52));

    const iconHtml = window.Icon ? window.Icon({
      name: config.glyph,
      size: iconSize,
      tone: 'white',
      ariaLabel: config.label
    }) : `<span style="color:white; font-size:${iconSize}px;">★</span>`;

    const activeRingStyle = active
      ? `box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px var(--accent), var(--shadow-2);`
      : `box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.28), var(--shadow-2);`;

    return `
      <div class="ura-app-tile ${className}"
           data-entity="${entity}"
           style="width:${size}px; height:${size}px; border-radius:${radius}px; background:${config.gradient};
                  display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;
                  ${activeRingStyle} position:relative; overflow:hidden; user-select:none; -webkit-user-select:none;
                  transition: transform 0.16s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.16s ease;">
        ${iconHtml}
      </div>
    `.trim();
  }

  window.AppTile = renderAppTile;
  window.APP_TILE_CONFIG = ENTITY_CONFIG;
})();
