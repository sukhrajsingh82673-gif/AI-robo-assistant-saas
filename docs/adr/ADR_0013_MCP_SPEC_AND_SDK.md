# ADR 0013: Model Context Protocol (MCP) Official SDK and Rug-Pull Defense

**Status:** Accepted  
**Date:** 2026-11-23  
**Context:** OpenCode Step 4A / 4G — Governed external tool integration  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement
The legacy codebase implemented a 2,140-line custom JSON-RPC transport (`core/mcp_interoperability_runtime.py`). ZONATA requires the official Model Context Protocol (`mcp`) SDK to support standardized enterprise tool discovery, prompts, and resources.

Standing Rules 24, 26, 34, and 39 dictate:
- External tool definitions and schemas are untrusted data.
- Prompt injection or schema mutation (rug-pull attacks) must not bypass authority.
- Stdio servers must execute in isolated sandboxes, never in the core API process.

## 2. Upstream Specification & Licensing
- **Package:** Official `mcp` Python SDK (v1.x).
- **Licence:** MIT (Permissive; compliant with Rule 5).
- **Specification Norm:** Spec revision 2025-11-25 incorporating RFC 9728 OAuth 2.0 Protected Resource Metadata and resource indicators.

## 3. Decision & Security Architecture (Rug-Pull Defense)
The official Model Context Protocol (`mcp`) Python SDK is adopted behind ZONATA ports. External tool definitions are treated as untrusted data, requiring schema hash pinning and human-reviewed descriptions.

### Rug-Pull Defenses and Sandboxing:
1. **Schema Hash Pinning:** Upon human review and approval of an MCP tool, ZONATA calculates and stores the SHA-256 hash of its input schema and description. If a remote server modifies either, the tool is immediately disabled and flagged for re-approval.
2. **Reviewed Prompt Override:** Models are shown the **reviewed ZONATA-authored description**, neutralizing prompt injections embedded in external server descriptions.
3. **Stdio Process Isolation:** Local stdio MCP servers execute inside lightweight sandboxes with no host file system or network access.
4. **Server-Initiated Restrictions:**
   - Server-initiated sampling requests are blocked by default, or routed through `LLMGateway` with strict spend caps.
   - Server-initiated elicitation requests are converted into human inbox items and never answered automatically by an agent.
