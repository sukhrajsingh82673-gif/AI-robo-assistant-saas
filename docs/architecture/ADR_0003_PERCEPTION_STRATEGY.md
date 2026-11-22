# ADR 0003: Desktop Perception & Interaction Strategy

**Status:** Accepted  
**Date:** 2026-11-22  
**Context:** OpenCode Step 3A / 3C — Hands: Desktop perception & interaction  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement

Controlling a desktop operating system (Windows, macOS, Linux) requires perceiving screen contents and interacting with UI elements (buttons, inputs, menus, windows).

We evaluated two foundational perception paradigms:
1. **Vision-Only (Coordinate-based clicking via Vision LLM)**
2. **Accessibility-Tree First with Vision LLM Fallback (Two-Tier Hybrid)**

---

## 2. Evaluation of Alternatives

### Option 1: Vision-Only (Pure Multimodal LLM + Coordinate Clicking)
- **Mechanics:** Take full-screen screenshot, send to Vision LLM, receive `(x, y)` coordinates, issue synthetic mouse click / keystroke.
- **Failure Modes:**
  - **High Latency & Token Cost:** Each action requires sending high-resolution images to the `VISION` tier, incurring massive financial cost and 2–5 second latency per step.
  - **Fragility & Non-Determinism:** Screen resolution scaling (DPI scaling, 4K displays), UI animation shifts, and rendering artifacts cause clicks to miss target buttons.
  - **Budget Violations:** Violates Standing Rule 20 (budget ceilings and deterministic execution).
  - **Secret Exposure Risk:** Visual screenshots may inadvertently capture password managers, private notifications, or background windows, violating Rule 24 and Rule 28 (minimum capture).

### Option 2: Accessibility-Tree First + Vision Fallback (Chosen)
- **Mechanics:**
  - **Tier 1 (Accessibility Tree):** Query OS accessibility API (Microsoft UI Automation (UIA) on Windows, `AXUIElement` on macOS, AT-SPI on Linux) to obtain exact hierarchical UI elements, unique IDs, role types, bounding rects, and text content.
  - **Tier 2 (Vision LLM Fallback):** When an element cannot be located in the accessibility tree (e.g., custom Canvas, WebGL, games, non-standard Qt/GTK widgets) or visual layout confirmation is required, take a localized masked screenshot and invoke `LLMGateway` (`ModelTier.VISION`).
- **Advantages:**
  - Sub-millisecond deterministic element selection.
  - Zero token cost for standard GUI interactions.
  - Robust against DPI scaling and window movements.
  - Precise masking of sensitive password inputs and background windows.

---

## 3. Decision

We choose **Option 2: Accessibility-Tree First with Vision Fallback**.

### Operating Principles:
1. **Primary Route:** Inspect accessibility tree first. If target element matches by automation ID, name, or role, interact directly via accessibility action or exact bounding box center.
2. **Fallback Route:** If tree is unavailable or element missing, fall back to localized region capture, apply redacting masks (passwords, PII, system trays), and invoke `ModelTier.VISION`.
3. **Host Grant Check (Rule 23):** Every desktop action must match the granted application allowlist before execution.
4. **Reversibility (Rule 31):** Destructive actions (closing unsaved files, deleting data) require explicit human confirmation.
