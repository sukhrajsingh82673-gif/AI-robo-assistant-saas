/**
 * URA / ZONATA — Apple-Grade Motion System
 * Fast to start, soft to land • Physical springs & progressive disclosure
 */

(function() {
  'use strict';

  const spring = {
    snappy: { stiffness: 520, damping: 38, mass: 0.9 }, // taps, toggles, chips
    smooth: { stiffness: 300, damping: 30, mass: 1 },   // panels, cards, layout
    gentle: { stiffness: 180, damping: 26, mass: 1 },   // sheets, large surfaces
    bouncy: { stiffness: 360, damping: 20, mass: 1 }    // celebratory only
  };

  const ease = {
    standard: 'cubic-bezier(0.25, 0.1, 0.25, 1)',   // general
    out:      'cubic-bezier(0.22, 1, 0.36, 1)',     // entering elements
    in:       'cubic-bezier(0.64, 0, 0.78, 0)',     // leaving elements
    inOut:    'cubic-bezier(0.65, 0, 0.35, 1)'      // moving across screen
  };

  const dur = {
    instant: 0.08, // press feedback (80ms)
    fast:    0.16, // hover, icon states (160ms)
    base:    0.28, // most transitions (280ms)
    slow:    0.45, // page and sheet (450ms)
    hero:    0.70  // reveals (700ms)
  };

  const stagger = 0.04; // 40ms stagger between siblings

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /**
   * Smoothly animates numbers with tabular figure alignment
   */
  function animateCountUp(element, endVal, options = {}) {
    if (!element) return;
    if (prefersReducedMotion()) {
      element.textContent = options.formatter ? options.formatter(endVal) : endVal.toLocaleString();
      return;
    }

    const duration = options.duration || 600;
    const startVal = options.startVal !== undefined ? options.startVal : 0;
    const startTime = performance.now();
    const formatter = options.formatter || ((v) => Math.round(v).toLocaleString());

    element.classList.add('tabular-nums');

    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Apple-style ease-out curve: 1 - Math.pow(1 - progress, 3)
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = startVal + (endVal - startVal) * eased;

      element.textContent = formatter(current);

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        element.textContent = formatter(endVal);
      }
    }

    requestAnimationFrame(update);
  }

  /**
   * Element appearance with subtle 8px lift and fade
   */
  function animateAppear(element, delayMs = 0) {
    if (!element) return;
    if (prefersReducedMotion()) {
      element.style.opacity = '1';
      element.style.transform = 'none';
      return;
    }

    element.style.opacity = '0';
    element.style.transform = 'translateY(8px)';
    element.style.transition = `opacity ${dur.base}s ${ease.out}, transform ${dur.base}s ${ease.out}`;

    setTimeout(() => {
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
    }, delayMs);
  }

  /**
   * Staggered list entrance animation
   */
  function animateStaggerList(container, selector = '.animate-item', maxItems = 8) {
    if (!container || prefersReducedMotion()) return;
    const items = container.querySelectorAll(selector);
    items.forEach((item, index) => {
      if (index < maxItems) {
        animateAppear(item, index * (stagger * 1000));
      }
    });
  }

  // Export Motion namespace
  window.Motion = {
    spring,
    ease,
    dur,
    stagger,
    prefersReducedMotion,
    animateCountUp,
    animateAppear,
    animateStaggerList
  };
})();
