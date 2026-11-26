# ADR 0030: Clean-Room Tool Replication Protocol and Legal Gate

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Security Arbiter, Repository Owner
- **Governing Rules:** Rule 53 (Mandatory Provenance), Rule 55 (No Licence Circumvention / No Code Copying)

---

## 1. Context & Problem Statement
When a critical third-party commercial tool is required but cannot be purchased, hosted, or integrated due to vendor deprecation, prohibitive licensing, or embargo, the owner may need a functionally equivalent tool. We must establish a legally sound, air-gapped clean-room methodology that avoids copyright infringement, trade-secret misappropriation, or circumvention of anti-piracy controls.

## 2. Decision
1. **Decision Ladder (First Match Wins):**
   - Step 1: Open-source or self-hostable alternative via Sub-Step 6G.
   - Step 2: Official vendor API / integration at acceptable commercial terms.
   - Step 3: Clean-room build of minimum viable equivalent limited strictly to owner requirements.
   - Step 4: Formal declaration of infeasibility without commercial license.
2. **Clean-Room Air-Gap Architecture:**
   - **Specifier Session:** Reads only public documentation, open standards, and owner-provided black-box observations. Drafts functional specifications with zero implementation code.
   - **Implementer Session:** Receives ONLY the functional specification. Completely isolated from external documentation, disassembly tools, or vendor binaries.
   - **Reviewer Session:** Performs AST code-similarity analysis against known public/vendor code to verify zero copied identifiers, strings, or structure.
3. **Prohibited Inputs & Actions:** Disassembly, decompilation, cracked binaries, leaked source, model weight extraction, and terms-of-service scraping are strictly blocked.
4. **Mandatory Human Legal Gate:** The repository owner must explicitly review the contractual analysis and approve any clean-room replication task before execution begins.

## 3. Consequences
- Guarantees strict non-infringement and clean-room provenance.
- Clean-room replicated tools are marked `REPLICA` in the tool registry with independent test coverage.
