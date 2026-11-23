# ADR 0006: Remote View and Human Takeover Architecture

**Status:** Accepted  
**Date:** 2026-11-22  
**Context:** OpenCode Step 3A / 3C / 3G — Hands: Remote view and human intervention  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement

When an autonomous agent encounters an ambiguous state, a verification challenge (Rule 25), or requires human intervention (Rule 27), the human owner must be able to view the screen in real time and seamlessly take over mouse/keyboard control.

Crucially, **Standing Rule 5** strictly forbids embedding GPL, AGPL, or non-permissive licensed code in the application process.

---

## 2. Evaluation of Alternatives & License Audits

### Option 1: Embedded VNC / RFB Engine (TightVNC / TigerVNC / LibVNCServer)
- **Licence Audit:**
  - TigerVNC: GPL-2.0.
  - TightVNC: GPL-2.0.
  - LibVNCServer: GPL-2.0.
  - noVNC: MPL-2.0 (client UI is MPL-2.0, but backend RFB servers are GPL).
- **Rejected Reasons:** Incorporating GPL-2.0 libraries into the ZONATA application process would trigger copyleft viral licensing contamination. Standing Rule 5 explicitly prohibits GPL/AGPL libraries within the core codebase.

### Option 2: WebRTC Media Stream with DataChannel Control (Chosen)
- **Licence Audit:**
  - W3C WebRTC Standard / Google WebRTC Native Implementation: BSD-3-Clause.
  - `aiortc` (Python WebRTC implementation): BSD-3-Clause (fully permissive).
- **Architecture:**
  - Host agent captures display frames via native OS APIs (Desktop Duplication API on Windows, ScreenCaptureKit on macOS, PipeWire / X11 on Linux).
  - Encoded H.264 / VP8 video stream sent peer-to-peer or via TURN/SFU relay directly to the web console.
  - Mouse and keyboard inputs sent over encrypted WebRTC `DataChannel` or authenticated WebSocket.
  - Ultra-low latency (<100ms) suitable for interactive human takeover.

### Option 3: Periodic JPEG/PNG WebSocket Frame Stream (Fallback)
- **Licence:** 100% standard library / Pillow (HPND/BSD-like).
- **Role:** Fallback when WebRTC UDP traffic is blocked by corporate firewall proxies. Screen captures are throttled to 5–10 FPS and streamed over the existing outbound TLS WebSocket.

---

## 3. Decision

We choose **Option 2 (WebRTC with BSD-3-Clause `aiortc` / Native WebRTC)** as the primary remote view solution, with **Option 3 (WebSocket Frame Stream)** as the deterministic zero-dependency fallback.

### Privacy and Security Controls:
1. **Rule 28 (Minimum Necessary Capture):** Only windows belonging to granted applications are captured; background desktop area and system taskbar are blurred or cropped out.
2. **Rule 24 (Secret Masking):** Detected password fields and sensitive credential regions are rendered as solid black rectangles before frame transmission.
3. **Immediate Handover:** When human moves physical mouse or presses any key on the host machine, agent automation yields control immediately.
