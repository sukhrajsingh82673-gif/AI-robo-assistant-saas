# ADR 0004: Host Agent Runtime and Packaging Architecture

**Status:** Accepted  
**Date:** 2026-11-22  
**Context:** OpenCode Step 3A / 3B — Hands: Host permission model and host agent  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement

To enable cloud-orchestrated assistance supervised by the human owner, a host-side agent must run directly on the user's workstation. 

Strict requirements mandate:
- **No Docker:** Must run without Docker or virtualization on standard user laptops/desktops.
- **Local Consent Enforcement (Rule 23):** Local allowlist validation; cloud cannot widen grants.
- **OS Keystore Integration:** Host private key must reside in the operating system's native secure key store.
- **Code-Signable & Auto-Updatable:** Must support native OS code signing (Microsoft Authenticode, Apple Developer ID, Linux GPG).
- **Minimal Resource Footprint:** Lightweight daemon with tray icon and kill switch hotkey.

---

## 2. Evaluation of Alternatives

### Option 1: Docker Container on Host
- **Rejected Reasons:** Fails user requirement ("run without Docker"). Standard non-technical users do not have Docker Desktop. Containers cannot natively access host GUI display or native OS accessibility APIs without complex X11/pipe mounts.

### Option 2: Electron Application
- **Rejected Reasons:** Heavyweight (>200 MB memory footprint, 150 MB binary size). Vast attack surface (bundled Chromium and Node.js). Unnecessary overhead for a supervisory daemon.

### Option 3: Lightweight Standalone Python Executable (Chosen)
- **Licence:** Python Software Foundation (PSF) / Apache-2.0.
- **Packaging:** Bundled via PyInstaller / Nuitka into a single standalone binary (`zonata-host-agent`).
- **OS Keystore Integration:**
  - Windows: DPAPI (Data Protection API) / Windows Credential Manager.
  - macOS: Apple Keychain Services (`Security.framework`).
  - Linux: Secret Service API (`libsecret` / FreeDesktop D-Bus).
- **Code Signing:** Fully compatible with standard OS signing pipelines (`signtool.exe`, `codesign`, `gpg`).
- **Codebase Reuse:** Shares cryptography (`cryptography` library / Ed25519), envelope serialization, and port contracts directly with core ZONATA repository.

---

## 3. Decision

We choose **Option 3: Lightweight Standalone Python Executable (`zonata-host-agent`)**.

### Security Architecture:
1. **Outbound-Only:** Never binds to inbound TCP ports.
2. **Local Grant Enforcement:** Grants stored locally in encrypted SQLite/JSON; incoming cloud commands are rejected locally if they exceed active human grants.
3. **Physical Kill Switch:** Always-visible system tray icon and global hotkey (`Ctrl+Shift+Escape` or platform equivalent) that immediately sever the WebSocket connection and kill child processes.
