# ZONATA CAPABILITY CONTRACT SPECIFICATION
## Machine-Readable Capability Schema, Typing & Evidence Guarantees

**Version**: 1.0.0  
**Classification**: SPECIFICATION & CONTRACT DEFINITION  

---

## 1. Capability Schema Definition

Every capability in the ZONATA Co-worker Fabric is defined as a machine-readable typed contract:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "capability_id",
    "name",
    "category",
    "providers",
    "preferred_provider",
    "risk_level",
    "requires_authorization",
    "requires_verification"
  ],
  "properties": {
    "capability_id": { "type": "string", "pattern": "^[a-z_]+(\\.[a-z_]+)+$" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "category": { "enum": ["DESKTOP", "BROWSER", "API", "RPA", "VISUAL_CUA", "FILE", "SYSTEM"] },
    "providers": { "type": "array", "items": { "type": "string" } },
    "preferred_provider": { "type": "string" },
    "fallback_providers": { "type": "array", "items": { "type": "string" } },
    "supported_platforms": { "type": "array", "items": { "enum": ["linux", "windows", "darwin"] } },
    "risk_level": { "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
    "requires_authorization": { "type": "boolean" },
    "requires_human_approval": { "type": "boolean" },
    "requires_verification": { "type": "boolean" },
    "supports_rollback": { "type": "boolean" },
    "supports_dry_run": { "type": "boolean" },
    "supports_idempotency": { "type": "boolean" },
    "timeout_sec": { "type": "number" },
    "retry_policy": {
      "type": "object",
      "properties": {
        "max_retries": { "type": "integer" },
        "backoff_factor": { "type": "number" }
      }
    },
    "cost_class": { "enum": ["FREE", "LOW", "MEDIUM", "HIGH"] },
    "latency_class": { "enum": ["SUB_SECOND", "FAST", "MEDIUM", "SLOW"] },
    "evidence_requirements": { "type": "array", "items": { "type": "string" } }
  }
}
```

---

## 2. Core Capability Catalog

| Capability ID | Category | Preferred Provider | Risk Level | Human Approval | Evidence Requirement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `api.crm_update` | API | `provider_api_mcp` | MEDIUM | Policy-Gated | Read-after-write confirmation |
| `api.crm_read` | API | `provider_api_mcp` | LOW | No | Record payload hash |
| `api.email_send` | API | `provider_api_mcp` | MEDIUM | Yes (Policy) | Mail transport message receipt |
| `browser.navigate` | BROWSER | `provider_playwright` | LOW | No | HTTP status code & title |
| `browser.extract` | BROWSER | `provider_playwright` | LOW | No | Extracted item count & DOM hash |
| `desktop.workflow` | DESKTOP | `provider_openadapt` | MEDIUM | No | Execution step trace & output file hash |
| `desktop.accessibility_tree` | DESKTOP | `provider_linux_desktop` | LOW | No | Tree structure JSON |
| `desktop.click_element` | DESKTOP | `provider_linux_desktop` | LOW | No | OS pattern invocation ACK |
| `rpa.excel_update` | RPA | `provider_robocorp` | LOW | No | Workbook modification audit |
| `visual.screen_understanding` | VISUAL_CUA | `provider_visual_cua` | HIGH | Yes (Grounding) | Modality tag & screenshot hash |
| `financial.purchase_software`| API | `provider_api_mcp` | CRITICAL | Mandatory | Payment receipt & ledger signature |

---

## 3. Strict Input/Output Typing & Evidence Guarantees

Every provider invocation returns an `ExecutionResult`:
```python
@dataclass
class ExecutionResult:
    provider_id: str
    capability_id: str
    execution_id: str
    status: str  # "SUCCESS", "FAILED", "UNCERTAIN", "CANCELLED", "AUTH_REQUIRED"
    output: Any
    confidence: float
    evidence: List[Dict[str, Any]]
    rollback_available: bool
    rollback_data: Optional[Dict[str, Any]]
    idempotency_key: Optional[str]
    error_message: Optional[str]
    duration_ms: float
```

The system refuses to mark a task as `SUCCESS` unless corroborating physical truth evidence matches the declared `evidence_requirements`.
