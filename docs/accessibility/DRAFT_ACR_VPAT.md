# ZONATA Accessibility Conformance Report (VPAT 2.5)

## Executive Summary
This document provides the Accessibility Conformance Report (ACR) based on VPAT® Version 2.5 for the **ZONATA Autonomous AI Company Operating System** web consoles, developer portal, and Progressive Web App (PWA).

**Standard / Guideline:** Web Content Accessibility Guidelines (WCAG) 2.2 AA / European Accessibility Act (Directive 2019/882).  
**Evaluation Methods Used:** Automated CI/CD quality gate checks (`AccessibilityChecker`), manual keyboard navigation inspection, and screen reader testing (NVDA, VoiceOver).

---

## WCAG 2.2 Level A and AA Conformance Table

| Criterion | Level | Status | Remarks and Explanations |
| :--- | :--- | :--- | :--- |
| **1.1.1 Non-text Content** | Level A | **Supports** | All non-text UI icons and charts provide programmatic `alt` text or `aria-label`. |
| **1.3.1 Info and Relationships** | Level A | **Supports** | Semantic HTML5 structure (headers, landmarks, lists, tables with `scope`) utilized across all consoles. |
| **1.4.3 Contrast (Minimum)** | Level AA | **Supports** | Text elements maintain at least 4.5:1 contrast against backgrounds in light and dark modes. |
| **2.1.1 Keyboard Navigation** | Level A | **Supports** | All interactive controls (buttons, links, modals, disclosures) are fully operable via keyboard without mouse. |
| **2.1.2 No Keyboard Trap** | Level A | **Supports** | Focus is safely trapped inside modal dialogs and released cleanly on `Escape` key. |
| **2.4.3 Focus Order** | Level A | **Supports** | Logical DOM sequence matches visual reading order. |
| **2.4.7 Focus Visible** | Level AA | **Supports** | High-contrast visible focus rings (`outline: 2px solid #38bdf8`) enforced globally. |
| **3.2.1 On Focus** | Level A | **Supports** | Focusing elements does not automatically trigger context switches or submit forms. |
| **4.1.2 Name, Role, Value** | Level A | **Supports** | Custom ARIA components declare explicit role, state (`aria-expanded`, `aria-checked`), and accessible name. |

---

## Certification & CI Enforcement
Continuous accessibility testing is enforced via `tests/test_step9g_mobile_accessibility.py`. Any PR introducing unlabelled inputs, unkeyboard-focusable elements, or low contrast fails automated CI gates.
