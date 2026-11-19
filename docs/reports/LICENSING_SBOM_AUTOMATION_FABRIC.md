# URA / ZONATA Universal Automation Fabric — Open-Source Licensing & SBOM Audit

## 1. Licensing & Sovereignty Mandate

The **URA / ZONATA Universal Automation Fabric** provides enterprise workflow orchestration and cross-system automation built strictly upon **OSI-approved open-source software** with commercial SaaS deployment rights.

### Sovereign Authority Invariant
> [!IMPORTANT]
> External open-source components, workflow orchestrators, and MCP servers function strictly as **execution providers**. Under no circumstances does an open-source library, runtime, agent framework, or external protocol acquire sovereign authority over ZONATA. All executions remain subordinate to the **Company Kernel**, **UniversalControlKernel**, **PolicyEngine**, **AuthorityGateway**, **ApprovalEngine**, and **EvidenceLedger**.

---

## 2. Pinned Open-Source Components & License Inventory

| Component | Upstream Repository | Version | SPDX License | Commercial SaaS Rights | Confinement & Architecture Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Kestra Open-Source Core** | `https://github.com/kestra-io/kestra` | `v0.18.2` | **Apache-2.0** | Permissive (Unrestricted) | Declarative YAML/JSON workflow model, task DAG specification, parallel/each flowables. |
| **LangGraph Core** | `https://github.com/langchain-ai/langgraph` | `v0.2.14` | **MIT** | Permissive (Unrestricted) | Zero-secret SQLite thread checkpointing, human-in-the-loop StateGraph nodes. |
| **Model Context Protocol (MCP) SDK** | `https://github.com/modelcontextprotocol/python-sdk` | `v1.1.0` | **MIT** | Permissive (Unrestricted) | Untrusted boundary interprocess tool discovery and stdio/SSE communication. |
| **Playwright Automation** | `https://github.com/microsoft/playwright-python` | `v1.44.0` | **Apache-2.0** | Permissive (Unrestricted) | Headless browser execution worker with ephemeral session contexts. |
| **OpenHands** | `https://github.com/All-Hands-AI/OpenHands` | `v0.9.1` | **MIT** | Permissive (Unrestricted) | Sandboxed software engineering and repository manipulation agent. |
| **PyYAML** | `https://github.com/yaml/pyyaml` | `v6.0.3` | **MIT** | Permissive (Unrestricted) | Deterministic Kestra Flow specification serializer/deserializer. |

---

## 3. Dependency Vulnerability & Supply Chain Assessment

1. **Non-OSI & Copyleft Isolation**:
   - Strict prohibition of unapproved proprietary SDKs or restrictive copyleft (GPL/AGPL) within core SaaS boundaries.
   - All runtime execution is hosted within tenant-isolated environments with zero cross-tenant state leakage.
2. **SSRF & Loopback Defense**:
   - Connector endpoints are pre-screened to reject cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`) and unauthorized private IP addresses.
3. **Execution Leases & Authority Boundaries**:
   - No workflow definition, graph configuration, or LLM output is self-authorizing. All privileged side-effects require cryptographic HMAC-SHA256 execution leases (`ExecutionLease`) validated immediately prior to execution.
4. **Zero Silent Failures & Terminal States**:
   - Every execution is mandated to terminate in an evidence-backed state: `TASK_SUCCESS`, `BUSINESS_OUTCOME_VERIFIED`, `FAILED`, `BLOCKED`, `CANCELLED`, or `UNKNOWN_OUTCOME`.

---

## 4. Software Bill of Materials (CycloneDX JSON Schema)

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "serialNumber": "urn:uuid:zonata-automation-fabric-v1",
  "version": 1,
  "metadata": {
    "component": {
      "name": "URA Universal Automation Fabric",
      "version": "1.0.0",
      "type": "application",
      "license": "Apache-2.0"
    }
  },
  "components": [
    {
      "component_id": "kestra-core",
      "name": "Kestra Open-Source Core",
      "version": "v0.18.2",
      "license_spdx": "Apache-2.0",
      "repository": "https://github.com/kestra-io/kestra"
    },
    {
      "component_id": "langgraph-core",
      "name": "LangGraph Core Engine",
      "version": "v0.2.14",
      "license_spdx": "MIT",
      "repository": "https://github.com/langchain-ai/langgraph"
    },
    {
      "component_id": "mcp-python-sdk",
      "name": "Model Context Protocol Python SDK",
      "version": "v1.1.0",
      "license_spdx": "MIT",
      "repository": "https://github.com/modelcontextprotocol/python-sdk"
    }
  ]
}
```

---

## 5. Certification & Compliance Verdict

- **OSI Licensing Status**: **100% COMPLIANT**
- **Commercial SaaS Integrability**: **APPROVED**
- **Verification Authority**: `AutomationLicenseValidator`
