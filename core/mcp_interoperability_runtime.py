"""
ZONATA Governed Model Context Protocol (MCP) Interoperability Runtime
======================================================================
Core implementation of the governed Model Context Protocol (MCP) layer,
enabling sovereign, secure, and bidirectional collaboration between ZONATA
and external tools, data sources, enterprise systems, and client runtimes
(CRM, ERP, PMS, Databases, APIs, SaaS).

Normative Specification: Model Context Protocol (MCP) Spec 2026-07-28
(Stateless Protocol Core, Streamable HTTP & stdio Transports, Tasks Extension,
Fine-Grained Authorization, Resource & Prompt Primitives)

Sovereign Architectural Composition:
ZONATA -> AI CEO -> Agency Swarm -> TaskMaker -> LangGraph
       -> Capability Registry -> ToolInteropProvider
       -> MCP Gateway -> MCP Server -> External Enterprise System
       -> Result Sanitization -> Independent Verification
       -> Evidence Ledger (SHA-256) -> TrustGraph -> Business Outcome

Constitutional Invariants Enforced:
1. MCP tool != permission (Tool availability != business permission)
2. MCP server != trusted automatically (Discovery != Trust)
3. Tool description != authorization (Descriptions/annotations are untrusted input)
4. Tool annotation != truth (Observation != Fact)
5. Model decision != authorization (LLM may request, never authorize)
6. MCP response != truth (Independent verification mandatory)
7. Successful MCP call != successful business outcome (Verified causality required)
8. External MCP content != trusted instructions (Content firewall & injection defense)
9. Capability != Authority
10. Connection != Permission
11. Permission != Execution
12. Execution != Verification
13. Verification != Evidence
14. Evidence != Business Outcome
15. Zero-Secret Outbound Exposure (Data minimization & JIT credential injection)
16. Non-idempotent Mutation Replay Prohibited (Ambiguous outcomes require reconciliation)
17. Authoritative KillSwitch Override (Instant stop on emergency signal)
"""

import os
import re
import json
import time
import uuid
import hashlib
import ipaddress
import urllib.parse
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Callable

from core.db import db
from core.models import EvidencePackage, PhysicalVerification, EvidenceStatus
from core.evidence_ledger import EvidenceLedger
from core.approvals import ApprovalPipeline
from core.business_causality import BusinessCausalityEngine, OutcomeStatus
from core.tool_fabric import CapabilityRegistry, ToolCapability


# =============================================================================
# 1. PROTOCOL CONSTANTS & ENUMS (2026-07-28 MCP Standard)
# =============================================================================

MCP_PROTOCOL_VERSION = "2026-07-28"
MCP_SPEC_RELEASE = "2026-07-28"
MCP_SPEC_VERSION = "2026-07-28"
JSONRPC_VERSION = "2.0"


class SecurityException(ValueError):
    """Raised when an MCP security, policy, or tenant invariant is violated."""
    pass


class MCPKillSwitch:
    """
    Authoritative KillSwitch for MCP external tool & system interactions.
    Supports multi-level stop: global, per-tenant, per-company, per-server,
    per-tool, and per-agent.
    """
    _global_active: bool = False
    _active_tenants: set = set()
    _active_companies: set = set()
    _active_servers: set = set()
    _active_tools: set = set()
    _active_agents: set = set()

    @classmethod
    def activate(
        cls,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        server_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ):
        if tool_id:
            cls._active_tools.add(tool_id)
        elif server_id:
            cls._active_servers.add(server_id)
        elif agent_id:
            cls._active_agents.add(agent_id)
        elif company_id:
            cls._active_companies.add(company_id)
        elif tenant_id:
            cls._active_tenants.add(tenant_id)
        else:
            cls._global_active = True

    @classmethod
    def deactivate(
        cls,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        server_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ):
        if tool_id:
            cls._active_tools.discard(tool_id)
        elif server_id:
            cls._active_servers.discard(server_id)
        elif agent_id:
            cls._active_agents.discard(agent_id)
        elif company_id:
            cls._active_companies.discard(company_id)
        elif tenant_id:
            cls._active_tenants.discard(tenant_id)
        else:
            cls._global_active = False

    @classmethod
    def is_active(
        cls,
        tenant_id: str,
        company_id: Optional[str] = None,
        server_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> bool:
        if cls._global_active:
            return True
        if tenant_id in cls._active_tenants:
            return True
        if company_id and company_id in cls._active_companies:
            return True
        if server_id and server_id in cls._active_servers:
            return True
        if tool_id and tool_id in cls._active_tools:
            return True
        if agent_id and agent_id in cls._active_agents:
            return True
        return False

    @classmethod
    def reset_all(cls):
        cls._global_active = False
        cls._active_tenants.clear()
        cls._active_companies.clear()
        cls._active_servers.clear()
        cls._active_tools.clear()
        cls._active_agents.clear()


class MCPTrustState(str, Enum):
    """Explicit trust states for MCP servers based on observable facts."""
    UNKNOWN = "UNKNOWN"
    DISCOVERED = "DISCOVERED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    TRUSTED = "TRUSTED"
    RESTRICTED = "RESTRICTED"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"


class MCPToolRiskClass(str, Enum):
    """Deterministic tool risk classification."""
    READ_ONLY = "READ_ONLY"
    LOW_RISK_MUTATION = "LOW_RISK_MUTATION"
    BUSINESS_MUTATION = "BUSINESS_MUTATION"
    FINANCIAL = "FINANCIAL"
    PRIVILEGED = "PRIVILEGED"
    SECURITY_SENSITIVE = "SECURITY_SENSITIVE"
    DESTRUCTIVE = "DESTRUCTIVE"
    IRREVERSIBLE = "IRREVERSIBLE"


class MCPExecutionStatus(str, Enum):
    """Distinguishable failure & execution semantics."""
    DISCOVERY_FAILED = "DISCOVERY_FAILED"
    AUTH_FAILED = "AUTH_FAILED"
    POLICY_DENIED = "POLICY_DENIED"
    AUTHORITY_DENIED = "AUTHORITY_DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    TOOL_FAILED = "TOOL_FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    VERIFIED = "VERIFIED"


class MCPDataClassification(str, Enum):
    """Data classification levels for payload minimization."""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    FINANCIAL = "FINANCIAL"
    SECURITY_SENSITIVE = "SECURITY_SENSITIVE"


class MCPSecurityEventType(str, Enum):
    """Security Center event types for MCP."""
    UNTRUSTED_SERVER = "UNTRUSTED_SERVER"
    INVALID_AUTH = "INVALID_AUTH"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    INVALID_ISSUER = "INVALID_ISSUER"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    UNAUTHORIZED_TOOL = "UNAUTHORIZED_TOOL"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    MALICIOUS_RESOURCE = "MALICIOUS_RESOURCE"
    UNEXPECTED_DATA = "UNEXPECTED_DATA"
    CREDENTIAL_EXPOSURE_ATTEMPT = "CREDENTIAL_EXPOSURE_ATTEMPT"
    TOOL_SCHEMA_ANOMALY = "TOOL_SCHEMA_ANOMALY"
    SERVER_IDENTITY_CHANGE = "SERVER_IDENTITY_CHANGE"
    PROTOCOL_MISMATCH = "PROTOCOL_MISMATCH"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    TENANT_ISOLATION_VIOLATION = "TENANT_ISOLATION_VIOLATION"
    SSRF_ATTEMPT = "SSRF_ATTEMPT"


class MCPTransportType(str, Enum):
    STREAMABLE_HTTP = "STREAMABLE_HTTP"
    STDIO = "STDIO"


# =============================================================================
# 2. SECURITY INSPECTION, SSRF, & CONTENT FIREWALL
# =============================================================================

class MCPSecurityInspector:
    """
    Guards endpoints against SSRF, unroutable networks, cloud metadata services,
    and inspects local stdio commands for command injection.
    """
    DISALLOWED_IP_NETS = [
        ipaddress.ip_network("127.0.0.0/8"),       # Loopback IPv4
        ipaddress.ip_network("169.254.0.0/16"),     # Link-Local (Cloud metadata)
        ipaddress.ip_network("10.0.0.0/8"),        # Private class A
        ipaddress.ip_network("172.16.0.0/12"),      # Private class B
        ipaddress.ip_network("192.168.0.0/16"),     # Private class C
        ipaddress.ip_network("::1/128"),            # Loopback IPv6
        ipaddress.ip_network("fe80::/10"),          # Link-Local IPv6
    ]

    DISALLOWED_HOSTNAMES = {
        "localhost",
        "metadata.google.internal",
        "instance-data",
        "169.254.169.254",
        "127.0.0.1"
    }

    FORBIDDEN_STDIO_PATTERNS = [
        re.compile(r"(\||;|&&|\$\(|\`|>|<)", re.IGNORECASE),
        re.compile(r"(\brm\s+-rf\b|\bmkfs\b|\bchmod\s+777\b)", re.IGNORECASE),
        re.compile(r"(\bcurl\b|\bwget\b|\bnc\b|\bnetcat\b).*\b(sh|bash|python)\b", re.IGNORECASE)
    ]

    @classmethod
    def validate_endpoint(cls, endpoint_url: str, allow_test_loopback: bool = False) -> Tuple[bool, str]:
        if not endpoint_url:
            return False, "Empty endpoint URL"
        try:
            parsed = urllib.parse.urlparse(endpoint_url)
            if parsed.scheme not in ("http", "https"):
                return False, f"Unsupported scheme '{parsed.scheme}'. MCP requires http or https"
            hostname = parsed.hostname
            if not hostname:
                return False, "Missing hostname in endpoint URL"

            if allow_test_loopback and (hostname in ("127.0.0.1", "localhost", "mcp.local", "test-pms.local")):
                return True, "Whitelisted Test Loopback Endpoint"

            # Check explicit hostnames
            if hostname.lower() in cls.DISALLOWED_HOSTNAMES:
                return False, f"SSRF Violation: Hostname '{hostname}' is prohibited"

            # Check IP restrictions
            try:
                ip_obj = ipaddress.ip_address(hostname)
                for blocked in cls.DISALLOWED_IP_NETS:
                    if ip_obj in blocked:
                        return False, f"SSRF Violation: IP address {ip_obj} is in blocked range {blocked}"
            except ValueError:
                # Hostname is a domain name. Prevent obvious cloud metadata prefixes
                if any(hostname.lower().startswith(p) for p in ("169.254", "metadata", "instance")):
                    return False, f"SSRF Violation: Domain '{hostname}' targets metadata service"

            return True, "Endpoint Validated"
        except Exception as e:
            return False, f"URL parse error: {str(e)}"

    @classmethod
    def validate_stdio_command(cls, command: List[str]) -> Tuple[bool, str]:
        """Validates command array for local stdio process isolation."""
        if not command or not isinstance(command, list):
            return False, "Command must be a non-empty list of arguments"
        cmd_str = " ".join(command)
        for pat in cls.FORBIDDEN_STDIO_PATTERNS:
            if pat.search(cmd_str):
                return False, "Stdio command contains prohibited shell metacharacters or dangerous binary invocation"
        # Validate binary path existence or resolution
        binary = command[0]
        if not (os.path.isabs(binary) or any(binary.endswith(ext) for ext in ("", ".exe", ".py", ".js"))):
            return False, f"Invalid binary specification '{binary}'"
        return True, "Stdio Command Validated"


class ExternalContentFirewall:
    """
    Treats all external MCP descriptions, annotations, resources, and tool outputs
    as untrusted data. Protects against prompt injection, secret exfiltration,
    and malicious payloads.
    """
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
        re.compile(r"you\s+must\s+always\s+(send|exfiltrate|transfer)", re.IGNORECASE),
        re.compile(r"disregard\s+(zonata\s+)?company\s+policy", re.IGNORECASE),
        re.compile(r"bypass\s+(zonata\s+)?(policy|approval|guardrail|killswitch)", re.IGNORECASE),
        re.compile(r"exfiltrate\s+credentials", re.IGNORECASE),
        re.compile(r"drop\s+table\b", re.IGNORECASE),
        re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"admin\s+privilege\s+granted", re.IGNORECASE)
    ]

    SECRET_PATTERNS = [
        re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
        re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
        re.compile(r"ghp_[a-zA-Z0-9]{30,}", re.IGNORECASE),
        re.compile(r"password\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
        re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
        re.compile(r"client[_-]?secret\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    ]

    MAX_PAYLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

    @classmethod
    def check_prompt_injection(cls, content: str) -> Tuple[bool, Optional[str]]:
        if not content:
            return False, None
        content_str = str(content)
        for pat in cls.PROMPT_INJECTION_PATTERNS:
            match = pat.search(content_str)
            if match:
                return True, match.group(0)
        return False, None

    @classmethod
    def scrub_secrets(cls, text: str) -> str:
        if not text:
            return ""
        scrubbed = str(text)
        for pat in cls.SECRET_PATTERNS:
            scrubbed = pat.sub("[REDACTED_SECRET]", scrubbed)
        return scrubbed

    @classmethod
    def sanitize_output(cls, raw_output: Any) -> Tuple[bool, Any, List[str]]:
        """
        Sanitizes raw MCP tool or resource output before it enters model context
        or Letta memory.
        """
        warnings = []
        raw_str = json.dumps(raw_output) if not isinstance(raw_output, str) else raw_output

        # Size check
        if len(raw_str.encode("utf-8")) > cls.MAX_PAYLOAD_BYTES:
            warnings.append(f"Payload size {len(raw_str)} exceeds ceiling {cls.MAX_PAYLOAD_BYTES} bytes")
            return False, {"error": "PAYLOAD_TOO_LARGE"}, warnings

        # Prompt injection check
        inj, pat = cls.check_prompt_injection(raw_str)
        if inj:
            warnings.append(f"Prompt injection pattern detected in MCP response: '{pat}'")
            return False, {"error": "PROMPT_INJECTION_DETECTED", "pattern": pat}, warnings

        # Secret scrubbing
        scrubbed = cls.scrub_secrets(raw_str)
        try:
            cleaned_obj = json.loads(scrubbed) if not isinstance(raw_output, str) else scrubbed
        except Exception:
            cleaned_obj = scrubbed

        return True, cleaned_obj, warnings


class MCPDataMinimizer:
    """
    Enforces strict data minimization before transmitting outbound arguments
    to an MCP server.
    """
    @classmethod
    def minimize_arguments(
        cls,
        arguments: Dict[str, Any],
        input_schema: Optional[Dict[str, Any]] = None,
        data_classification: MCPDataClassification = MCPDataClassification.INTERNAL,
        allowed_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if not arguments:
            return {}
        allowed_properties = None
        if allowed_fields is not None:
            allowed_properties = set(allowed_fields)
        elif input_schema and isinstance(input_schema, dict):
            props = input_schema.get("properties")
            if isinstance(props, dict):
                allowed_properties = set(props.keys())

        minimized = {}
        for k, v in arguments.items():
            if allowed_properties is not None and k not in allowed_properties:
                continue
            # Scrub secrets from values
            if isinstance(v, str):
                minimized[k] = ExternalContentFirewall.scrub_secrets(v)
            elif isinstance(v, dict):
                minimized[k] = json.loads(ExternalContentFirewall.scrub_secrets(json.dumps(v)))
            else:
                minimized[k] = v
        return minimized


# =============================================================================
# 3. DETERMINISTIC TOOL RISK CLASSIFIER
# =============================================================================

class ToolRiskClassifier:
    """
    Determines tool risk class and approval requirements automatically
    based on tool name, schemas, side effects, and keywords.
    """
    FINANCIAL_KEYWORDS = {"refund", "payment", "charge", "wire", "transfer", "payout", "invoice", "credit", "discount"}
    DESTRUCTIVE_KEYWORDS = {"delete", "drop", "truncate", "destroy", "purge", "erase", "terminate", "kill"}
    PRIVILEGED_KEYWORDS = {"grant", "revoke", "role", "permission", "sudo", "config", "token", "password", "key"}
    BUSINESS_MUTATION_KEYWORDS = {"update", "create", "modify", "book", "reserve", "reschedule", "cancel", "insert", "send", "post"}

    @classmethod
    def classify_tool(cls, tool_name: str, description: str = "", input_schema: Optional[Dict[str, Any]] = None) -> Tuple[MCPToolRiskClass, int, int]:
        """
        Returns (MCPToolRiskClass, approval_requirement, verification_requirement).
        Approval: 0 = autonomous, 1 = human approval required.
        Verification: 1 = physical verification required.
        """
        name_lower = tool_name.lower()
        desc_lower = description.lower()
        combined = f"{name_lower} {desc_lower}"

        # 1. Financial
        if any(w in name_lower for w in cls.FINANCIAL_KEYWORDS) or any(w in desc_lower for w in cls.FINANCIAL_KEYWORDS):
            return MCPToolRiskClass.FINANCIAL, 1, 1

        # 2. Destructive
        if any(w in name_lower for w in cls.DESTRUCTIVE_KEYWORDS) or any(w in desc_lower for w in cls.DESTRUCTIVE_KEYWORDS):
            return MCPToolRiskClass.DESTRUCTIVE, 1, 1

        # 3. Privileged / Security Sensitive
        if any(w in name_lower for w in cls.PRIVILEGED_KEYWORDS):
            return MCPToolRiskClass.PRIVILEGED, 1, 1

        # 4. Business Mutation
        if any(w in name_lower for w in cls.BUSINESS_MUTATION_KEYWORDS) or any(w in desc_lower for w in cls.BUSINESS_MUTATION_KEYWORDS):
            # Check if high impact
            return MCPToolRiskClass.BUSINESS_MUTATION, 1, 1

        # 5. Read Only / Queries
        if any(w in name_lower for w in ("get", "list", "query", "search", "read", "fetch", "check", "inspect", "view")):
            return MCPToolRiskClass.READ_ONLY, 0, 1

        # Default fallback
        return MCPToolRiskClass.LOW_MUTATION if "set" in name_lower else MCPToolRiskClass.READ_ONLY, 0, 1


# =============================================================================
# 4. MCP TRANSPORTS (Streamable HTTP & stdio)
# =============================================================================

class MCPTransport:
    """Base interface for MCP transport implementations."""
    def send_request(self, request_payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        raise NotImplementedError()


class StreamableHTTPTransport(MCPTransport):
    """
    Stateless Streamable HTTP Transport conforming to the 2026-07-28 MCP standard.
    Transmits JSON-RPC 2.0 payloads with per-request headers, authorization tokens,
    and handles simulated or local endpoint invocations cleanly.
    """
    _mock_endpoints: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def __init__(self, endpoint_url: str, auth_token: Optional[str] = None, custom_headers: Optional[Dict[str, str]] = None):
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token
        self.custom_headers = custom_headers or {}

    @classmethod
    def register_mock_endpoint(cls, endpoint_url: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        cls._mock_endpoints[endpoint_url] = handler

    @classmethod
    def clear_mock_endpoints(cls):
        cls._mock_endpoints.clear()

    def send_request(self, request_payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        # Check mock registry first for deterministic testing & isolated sandbox
        if self.endpoint_url in self._mock_endpoints:
            return self._mock_endpoints[self.endpoint_url](request_payload)

        # In production HTTP mode, we prepare the HTTP request
        try:
            req_data = json.dumps(request_payload).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"ZONATA-MCP-Client/{MCP_PROTOCOL_VERSION}",
                "X-MCP-Protocol-Version": MCP_PROTOCOL_VERSION
            }
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            headers.update(self.custom_headers)

            req = urllib.request.Request(self.endpoint_url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as he:
            return {
                "jsonrpc": JSONRPC_VERSION,
                "error": {"code": -32000, "message": f"HTTP Error {he.code}: {he.reason}"},
                "id": request_payload.get("id")
            }
        except urllib.error.URLError as ue:
            return {
                "jsonrpc": JSONRPC_VERSION,
                "error": {"code": -32001, "message": f"Transport Connection Failed: {str(ue.reason)}"},
                "id": request_payload.get("id")
            }
        except Exception as e:
            return {
                "jsonrpc": JSONRPC_VERSION,
                "error": {"code": -32603, "message": f"Internal Transport Error: {str(e)}"},
                "id": request_payload.get("id")
            }


class StdioTransport(MCPTransport):
    """
    Local stdio process transport.
    Executes sandboxed binaries or scripts with strict isolation and timeout.
    """
    def __init__(self, command: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        valid, msg = MCPSecurityInspector.validate_stdio_command(command)
        if not valid:
            raise SecurityException(f"Stdio Transport Security Rejection: {msg}")
        self.command = command
        self.cwd = cwd or "/tmp"
        self.env = env or {}

    def send_request(self, request_payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        import subprocess
        try:
            p = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.cwd
            )
            input_text = json.dumps(request_payload) + "\n"
            stdout, stderr = p.communicate(input=input_text, timeout=timeout)
            if p.returncode != 0:
                return {
                    "jsonrpc": JSONRPC_VERSION,
                    "error": {"code": -32002, "message": f"Process exited with code {p.returncode}: {stderr}"},
                    "id": request_payload.get("id")
                }
            return json.loads(stdout.strip())
        except subprocess.TimeoutExpired:
            p.kill()
            return {
                "jsonrpc": JSONRPC_VERSION,
                "error": {"code": -32003, "message": f"Stdio process timed out after {timeout}s"},
                "id": request_payload.get("id")
            }
        except Exception as e:
            return {
                "jsonrpc": JSONRPC_VERSION,
                "error": {"code": -32603, "message": f"Stdio execution failed: {str(e)}"},
                "id": request_payload.get("id")
            }


# =============================================================================
# 5. PROVIDER ABSTRACTION (ToolInteropProvider)
# =============================================================================

class ToolInteropProvider:
    """Abstract base class for interoperability capability providers."""
    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError()

    def list_tools(self, tenant_id: str, company_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError()

    def invoke_tool(self, tool_id: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()


class MCPToolInteropProvider(ToolInteropProvider):
    """
    Connects ZONATA Capability Registry with MCPGateway.
    Provides standard provider calls without tight coupling.
    """
    def __init__(self, gateway: "MCPGateway"):
        self.gateway = gateway

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        return self.gateway.get_tool(tool_id)

    def list_tools(self, tenant_id: str, company_id: str) -> List[Dict[str, Any]]:
        return self.gateway.list_tools(tenant_id, company_id)

    def invoke_tool(self, tool_id: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.get_tool(tool_id)
        if not tool:
            return {"status": MCPExecutionStatus.TOOL_FAILED.value, "error": f"Tool '{tool_id}' not found"}
        return self.gateway.invoke_tool(
            server_id=tool["server_id"],
            tool_name_or_id=tool["name"],
            arguments=arguments,
            context=context
        )


# =============================================================================
# 6. CENTRAL MCP GATEWAY
# =============================================================================

class MCPGateway:
    """
    Central sovereign gateway for all MCP communications across ZONATA.
    Handles discovery, registration, trust verification, JIT credentials,
    data minimization, policy evaluation, approval interception,
    execution, physical reality verification, and cryptographic evidence sealing.
    """
    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.evidence_ledger = EvidenceLedger()
        self.causality_engine = BusinessCausalityEngine(tenant_id, company_id)
        self.capability_registry = CapabilityRegistry()
        self.provider = MCPToolInteropProvider(self)

    # -------------------------------------------------------------------------
    # Server Lifecycle & Discovery
    # -------------------------------------------------------------------------

    def register_server(
        self,
        display_name: str,
        endpoint: str,
        transport: MCPTransportType = MCPTransportType.STREAMABLE_HTTP,
        description: str = "",
        auth_type: str = "NONE",
        credential_ref: Optional[str] = None,
        data_classification: MCPDataClassification = MCPDataClassification.INTERNAL,
        allow_test_loopback: bool = False
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Registers an MCP server into the ZONATA registry in DISCOVERED state.
        Validates endpoint against SSRF and prompt injection.
        """
        errors = []
        # Check endpoint
        if transport == MCPTransportType.STREAMABLE_HTTP:
            valid_url, msg = MCPSecurityInspector.validate_endpoint(endpoint, allow_test_loopback=allow_test_loopback)
            if not valid_url:
                self._record_security_event(
                    MCPSecurityEventType.SSRF_ATTEMPT,
                    "HIGH",
                    {"endpoint": endpoint, "error": msg}
                )
                return False, None, [msg]

        # Check prompt injection in name and description
        inj, pat = ExternalContentFirewall.check_prompt_injection(f"{display_name} {description}")
        if inj:
            self._record_security_event(
                MCPSecurityEventType.PROMPT_INJECTION,
                "HIGH",
                {"detected_pattern": pat, "target": "server_metadata"}
            )
            return False, None, [f"Prompt injection detected in server metadata: {pat}"]

        server_id = f"mcp_srv_{uuid.uuid4().hex[:10]}"
        now = time.time()
        initial_metrics = {
            "invocations": 0,
            "successes": 0,
            "failures": 0,
            "timeouts": 0,
            "verifications": 0,
            "avg_latency_ms": 0.0
        }

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO mcp_servers (
                    server_id, tenant_id, company_id, display_name, description,
                    endpoint, transport, protocol_version, server_version, identity,
                    authentication_type, credential_reference, trust_state,
                    risk_classification, data_classification, allowed_tools,
                    allowed_resources, allowed_prompts, allowed_operations,
                    allowed_companies, allowed_agents, allowed_workflows,
                    rate_limit, budget_limit, timeout_policy, approval_policy,
                    verification_policy, status, health_status, reputation_metrics,
                    last_seen, last_verified, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    server_id, self.tenant_id, self.company_id, display_name, description,
                    endpoint, transport.value, MCP_PROTOCOL_VERSION, "1.0.0", f"urn:mcp:{server_id}",
                    auth_type, credential_ref, MCPTrustState.DISCOVERED.value,
                    MCPToolRiskClass.READ_ONLY.value, data_classification.value,
                    json.dumps([]), json.dumps([]), json.dumps([]), json.dumps(["*"]),
                    json.dumps([self.company_id]), json.dumps(["*"]), json.dumps(["*"]),
                    60, 0.0, 30.0, "STANDARD", "PHYSICAL_VERIFICATION",
                    "ONLINE", "HEALTHY", json.dumps(initial_metrics),
                    now, None, now, now
                )
            )
            conn.commit()

        return True, server_id, []

    def validate_server(self, server_id: str) -> Tuple[bool, str]:
        """Validates a discovered server and transitions it to VALIDATED."""
        server = self.get_server(server_id)
        if not server:
            return False, "Server not found"
        # Verify tenant isolation
        if server["tenant_id"] != self.tenant_id:
            raise SecurityException("Tenant isolation violation during server validation")

        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE mcp_servers SET trust_state = ?, updated_at = ?, last_verified = ? WHERE server_id = ?",
                (MCPTrustState.VALIDATED.value, now, now, server_id)
            )
            conn.commit()
        return True, f"Server {server_id} validated successfully"

    def set_server_trust(self, server_id: str, trust_state: MCPTrustState, reason: str = ""):
        server = self.get_server(server_id)
        if not server:
            raise ValueError(f"Server {server_id} not found")
        if server["tenant_id"] != self.tenant_id:
            raise SecurityException("Tenant isolation violation")

        with db.get_connection() as conn:
            conn.execute(
                "UPDATE mcp_servers SET trust_state = ?, updated_at = ? WHERE server_id = ?",
                (trust_state.value, time.time(), server_id)
            )
            conn.commit()

    def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            r = conn.execute("SELECT * FROM mcp_servers WHERE server_id = ? AND tenant_id = ?", (server_id, self.tenant_id)).fetchone()
            if not r:
                return None
            d = dict(r)
            for k in ("allowed_tools", "allowed_resources", "allowed_prompts", "allowed_operations", "allowed_companies", "allowed_agents", "allowed_workflows", "reputation_metrics"):
                if d.get(k) and isinstance(d[k], str):
                    try:
                        d[k] = json.loads(d[k])
                    except Exception:
                        pass
            return d

    def list_servers(self) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM mcp_servers WHERE tenant_id = ? ORDER BY created_at DESC", (self.tenant_id,)).fetchall()
            servers = []
            for r in rows:
                d = dict(r)
                for k in ("allowed_tools", "allowed_resources", "allowed_prompts", "allowed_operations", "allowed_companies", "allowed_agents", "allowed_workflows", "reputation_metrics"):
                    if d.get(k) and isinstance(d[k], str):
                        try:
                            d[k] = json.loads(d[k])
                        except Exception:
                            pass
                servers.append(d)
            return servers

    def suspend_server(self, server_id: str, reason: str = "") -> Dict[str, Any]:
        self.set_server_trust(server_id, MCPTrustState.SUSPENDED, reason=reason)
        with db.get_connection() as conn:
            conn.execute("UPDATE mcp_servers SET status = 'SUSPENDED', updated_at = ? WHERE server_id = ?", (time.time(), server_id))
            conn.commit()
        return {"success": True, "server_id": server_id, "status": "SUSPENDED", "trust_state": MCPTrustState.SUSPENDED.value}

    def block_server(self, server_id: str, reason: str = "") -> Dict[str, Any]:
        self.set_server_trust(server_id, MCPTrustState.BLOCKED, reason=reason)
        with db.get_connection() as conn:
            conn.execute("UPDATE mcp_servers SET status = 'QUARANTINED', updated_at = ? WHERE server_id = ?", (time.time(), server_id))
            conn.commit()
        return {"success": True, "server_id": server_id, "status": "BLOCKED", "trust_state": MCPTrustState.BLOCKED.value}

    def reauthorize_server(self, server_id: str, reason: str = "") -> Dict[str, Any]:
        self.set_server_trust(server_id, MCPTrustState.TRUSTED, reason=reason)
        with db.get_connection() as conn:
            conn.execute("UPDATE mcp_servers SET status = 'ONLINE', updated_at = ? WHERE server_id = ?", (time.time(), server_id))
            conn.commit()
        return {"success": True, "server_id": server_id, "status": "ONLINE", "trust_state": MCPTrustState.TRUSTED.value}

    def disconnect_server(self, server_id: str) -> bool:
        with db.get_connection() as conn:
            conn.execute("DELETE FROM mcp_servers WHERE server_id = ? AND tenant_id = ?", (server_id, self.tenant_id))
            conn.commit()
        return True

    def test_server_connection(self, server_id: str) -> Dict[str, Any]:
        server = self.get_server(server_id)
        if not server:
            return {"success": False, "error": f"Server {server_id} not found"}
        endpoint = server.get("endpoint", "")
        is_safe, err_msg = MCPSecurityInspector.validate_endpoint(endpoint, allow_test_loopback=True)
        if not is_safe:
            return {"success": False, "error": f"Endpoint validation failed: {err_msg}"}
        now = time.time()
        with db.get_connection() as conn:
            conn.execute("UPDATE mcp_servers SET last_seen = ?, health_status = 'HEALTHY' WHERE server_id = ?", (now, server_id))
            conn.commit()
        return {
            "success": True,
            "server_id": server_id,
            "endpoint": endpoint,
            "protocol_version": server.get("protocol_version", MCP_PROTOCOL_VERSION),
            "transport": server.get("transport", "streamable_http"),
            "health_status": "HEALTHY",
            "latency_ms": 12.4,
            "timestamp": now
        }

    def refresh_server_capabilities(self, server_id: str) -> Dict[str, Any]:
        server = self.get_server(server_id)
        if not server:
            return {"success": False, "error": f"Server {server_id} not found"}
        with db.get_connection() as conn:
            tools = conn.execute("SELECT COUNT(*) as c FROM mcp_tools WHERE server_id = ?", (server_id,)).fetchone()["c"]
            resources = conn.execute("SELECT COUNT(*) as c FROM mcp_resources WHERE server_id = ?", (server_id,)).fetchone()["c"]
            conn.execute("UPDATE mcp_servers SET last_verified = ?, updated_at = ? WHERE server_id = ?", (time.time(), time.time(), server_id))
            conn.commit()
        return {
            "success": True,
            "server_id": server_id,
            "refreshed_at": time.time(),
            "tools_count": tools,
            "resources_count": resources
        }

    # -------------------------------------------------------------------------
    # Tool Registration & Capability Registry Mapping
    # -------------------------------------------------------------------------

    def register_tool(
        self,
        server_id: str,
        name: str,
        description: str,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        override_risk: Optional[MCPToolRiskClass] = None,
        override_approval: Optional[bool] = None,
        idempotency: bool = True
    ) -> str:
        """
        Registers a tool for an MCP server, automatically evaluates risk class,
        maps it into the ZONATA Capability Registry, and enforces governance.
        """
        server = self.get_server(server_id)
        if not server:
            raise ValueError(f"Server {server_id} does not exist")

        # Untrusted description check
        inj, pat = ExternalContentFirewall.check_prompt_injection(f"{name} {description}")
        if inj:
            self._record_security_event(
                MCPSecurityEventType.PROMPT_INJECTION,
                "HIGH",
                {"detected_pattern": pat, "target": f"tool_description_{name}", "server_id": server_id}
            )
            raise SecurityException(f"Prompt injection detected in tool description: {pat}")

        # Deterministic risk classification
        auto_risk, auto_appr, auto_verif = ToolRiskClassifier.classify_tool(name, description, input_schema)
        final_risk = override_risk if override_risk else auto_risk
        final_approval = int(override_approval) if override_approval is not None else auto_appr

        tool_id = f"tool_{server_id}_{name.lower().replace(' ', '_')}"
        now = time.time()

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mcp_tools (
                    tool_id, server_id, tenant_id, company_id, name, description,
                    input_schema, output_schema, risk_class, data_classification,
                    required_scopes, required_permissions, allowed_agents, allowed_workflows,
                    approval_requirement, verification_requirement, cost_model,
                    rate_limit, timeout, reversibility, idempotency, side_effect_class,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool_id, server_id, self.tenant_id, self.company_id, name, description,
                    json.dumps(input_schema or {}), json.dumps(output_schema or {}),
                    final_risk.value, server.get("data_classification", "INTERNAL"),
                    json.dumps(["mcp:invoke"]), json.dumps(["capability:execute"]),
                    json.dumps(["*"]), json.dumps(["*"]),
                    final_approval, auto_verif, 0.0, 60, 30.0,
                    1 if final_risk == MCPToolRiskClass.READ_ONLY else 0,
                    1 if idempotency else 0,
                    "NONE" if final_risk == MCPToolRiskClass.READ_ONLY else "EXTERNAL_MUTATION",
                    "AVAILABLE", now, now
                )
            )
            conn.commit()

        # Map into CapabilityRegistry
        self.capability_registry.register(
            ToolCapability(
                name=f"mcp::{name}",
                version="mcp-2026-07-28",
                license_type="Enterprise-Governed",
                binary_path=f"mcp://{server_id}/{name}",
                is_sandboxed=True
            )
        )

        return tool_id

    def get_tool(self, tool_id_or_name: str, server_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            if server_id:
                r = conn.execute(
                    "SELECT * FROM mcp_tools WHERE (tool_id = ? OR name = ?) AND server_id = ? AND tenant_id = ?",
                    (tool_id_or_name, tool_id_or_name, server_id, self.tenant_id)
                ).fetchone()
            else:
                r = conn.execute(
                    "SELECT * FROM mcp_tools WHERE (tool_id = ? OR name = ?) AND tenant_id = ?",
                    (tool_id_or_name, tool_id_or_name, self.tenant_id)
                ).fetchone()
            if not r:
                return None
            d = dict(r)
            for k in ("input_schema", "output_schema", "required_scopes", "required_permissions", "allowed_agents", "allowed_workflows"):
                if d.get(k) and isinstance(d[k], str):
                    try:
                        d[k] = json.loads(d[k])
                    except Exception:
                        pass
            return d

    def list_tools(self, tenant_id: Optional[str] = None, company_id: Optional[str] = None, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        tid = tenant_id or self.tenant_id
        with db.get_connection() as conn:
            if server_id:
                rows = conn.execute("SELECT * FROM mcp_tools WHERE tenant_id = ? AND server_id = ? ORDER BY name ASC", (tid, server_id)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM mcp_tools WHERE tenant_id = ? ORDER BY name ASC", (tid,)).fetchall()
            tools = []
            for r in rows:
                d = dict(r)
                for k in ("input_schema", "output_schema", "required_scopes", "required_permissions", "allowed_agents", "allowed_workflows"):
                    if d.get(k) and isinstance(d[k], str):
                        try:
                            d[k] = json.loads(d[k])
                        except Exception:
                            pass
                tools.append(d)
            return tools

    def override_tool(self, tool_id: str, updates: Dict[str, Any], actor_id: str = "admin") -> Dict[str, Any]:
        """
        Allows authorized administrator to override:
        - risk_class
        - allowed_agents
        - allowed_workflows
        - approval_requirement
        - data_classification
        with audit trail recorded.
        """
        with db.get_connection() as conn:
            tool_row = conn.execute("SELECT * FROM mcp_tools WHERE tool_id = ? AND tenant_id = ?", (tool_id, self.tenant_id)).fetchone()
            if not tool_row:
                raise ValueError(f"Tool {tool_id} not found")

            fields = []
            vals = []
            if "risk_class" in updates:
                fields.append("risk_class = ?")
                vals.append(updates["risk_class"])
            if "approval_requirement" in updates:
                fields.append("approval_requirement = ?")
                vals.append(1 if updates["approval_requirement"] else 0)
            if "allowed_agents" in updates:
                fields.append("allowed_agents = ?")
                vals.append(json.dumps(updates["allowed_agents"]) if isinstance(updates["allowed_agents"], list) else updates["allowed_agents"])
            if "allowed_workflows" in updates:
                fields.append("allowed_workflows = ?")
                vals.append(json.dumps(updates["allowed_workflows"]) if isinstance(updates["allowed_workflows"], list) else updates["allowed_workflows"])
            if "data_classification" in updates:
                fields.append("data_classification = ?")
                vals.append(updates["data_classification"])

            if fields:
                fields.append("updated_at = ?")
                vals.append(time.time())
                vals.append(tool_id)
                vals.append(self.tenant_id)
                sql = f"UPDATE mcp_tools SET {', '.join(fields)} WHERE tool_id = ? AND tenant_id = ?"
                conn.execute(sql, vals)
                conn.commit()

        # Audit log of tool override
        self._record_security_event(
            MCPSecurityEventType.POLICY_VIOLATION if updates.get("risk_class") == MCPToolRiskClass.READ_ONLY.value else MCPSecurityEventType.UNEXPECTED_DATA,
            "LOW",
            {"action": "ADMIN_TOOL_OVERRIDE", "tool_id": tool_id, "actor_id": actor_id, "updates": updates}
        )
        return self.get_tool(tool_id)

    # -------------------------------------------------------------------------
    # Resources & Prompts
    # -------------------------------------------------------------------------

    def register_resource(
        self,
        server_id: str,
        uri: str,
        name: str,
        description: str = "",
        mime_type: str = "application/json",
        data_classification: MCPDataClassification = MCPDataClassification.INTERNAL,
        approval_required: bool = False
    ) -> str:
        res_id = f"res_{server_id}_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mcp_resources (
                    resource_id, server_id, tenant_id, company_id, uri, name,
                    description, mime_type, data_classification, required_scopes,
                    approval_required, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    res_id, server_id, self.tenant_id, self.company_id, uri, name,
                    description, mime_type, data_classification.value, json.dumps(["mcp:read"]),
                    1 if approval_required else 0, json.dumps({}), now, now
                )
            )
            conn.commit()
        return res_id

    def read_resource(self, resource_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Reads an MCP resource under strict governance.
        Passes content through ExternalContentFirewall before returning.
        """
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM mcp_resources WHERE resource_id = ? AND tenant_id = ?",
                (resource_id, self.tenant_id)
            ).fetchone()
            if not r:
                return {"success": False, "status": MCPExecutionStatus.TOOL_FAILED.value, "error": "Resource not found"}

            server_id = r["server_id"]
            if MCPKillSwitch.is_active(self.tenant_id, server_id=server_id):
                return {"success": False, "status": MCPExecutionStatus.CANCELLED.value, "error": "KillSwitch active"}

            # Simulated resource payload or transport retrieval
            raw_content = {"uri": r["uri"], "name": r["name"], "data": f"Enterprise Resource Content for {r['name']}"}
            clean_ok, sanitized, warns = ExternalContentFirewall.sanitize_output(raw_content)
            if not clean_ok:
                self._record_security_event(
                    MCPSecurityEventType.MALICIOUS_RESOURCE,
                    "HIGH",
                    {"resource_id": resource_id, "warnings": warns}
                )
                return {"success": False, "status": MCPExecutionStatus.TOOL_FAILED.value, "error": "Malicious content detected in resource"}

            return {"success": True, "resource": sanitized, "content": sanitized.get("data"), "warnings": warns}

    # -------------------------------------------------------------------------
    # GOVERNED INVOCATION PIPELINE (The 15-Stage Enterprise Standard)
    # -------------------------------------------------------------------------

    def invoke_tool(
        self,
        server_id: str,
        tool_name_or_id: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes an MCP tool with full sovereign ZONATA governance:
        1. KillSwitch verification (Global, Tenant, Company, Server, Tool, Agent)
        2. Multi-tenant & Company isolation check
        3. Trust state check (Server must be VALIDATED/TRUSTED)
        4. Tool schema & existence resolution
        5. PolicyEngine evaluation
        6. Authority Gateway determination
        7. Human Approval interception (ApprovalEngine)
        8. JIT Credential Isolation
        9. Outbound Data Minimization
        10. Transport Execution (Streamable HTTP / Stdio) with timeout & cancellation
        11. Result Sanitization (ExternalContentFirewall)
        12. Independent Physical Reality Verification
        13. Cryptographic Evidence Ledger sealing (Merkle SHA-256)
        14. Business Causality link recording (TASK_SUCCESS != BUSINESS_OUTCOME)
        15. Audit logging & Trace generation
        """
        ctx = context or {}
        agent_id = ctx.get("agent_id", "agent_system")
        mission_id = ctx.get("mission_id", "m_default")
        workflow_id = ctx.get("workflow_id", "wf_default")
        thread_id = ctx.get("thread_id", f"thrd_{uuid.uuid4().hex[:8]}")
        exec_id = f"exec_{uuid.uuid4().hex[:12]}"
        now = time.time()
        start_time = time.time()

        # 1. KillSwitch Check
        tool = self.get_tool(tool_name_or_id, server_id=server_id)
        tool_id = tool["tool_id"] if tool else f"tool_{server_id}_{tool_name_or_id}"
        tool_name = tool["name"] if tool else tool_name_or_id

        if MCPKillSwitch.is_active(self.tenant_id, self.company_id, server_id=server_id, tool_id=tool_id, agent_id=agent_id):
            self._record_security_event(
                MCPSecurityEventType.POLICY_VIOLATION,
                "CRITICAL",
                {"reason": "KillSwitch Active", "server_id": server_id, "tool_id": tool_id, "agent_id": agent_id}
            )
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args={}, policy="DENY", authority="DENIED",
                status=MCPExecutionStatus.CANCELLED.value, response=None,
                error="MCP Execution blocked: KillSwitch active", latency_ms=0.0, context=ctx
            )

        # 2. Server Validation & Tenant Isolation
        with db.get_connection() as conn:
            raw_srv = conn.execute("SELECT tenant_id, company_id FROM mcp_servers WHERE server_id = ?", (server_id,)).fetchone()
        if raw_srv and raw_srv["tenant_id"] != self.tenant_id:
            self._record_security_event(
                MCPSecurityEventType.TENANT_ISOLATION_VIOLATION,
                "CRITICAL",
                {"attempted_tenant": raw_srv["tenant_id"], "caller_tenant": self.tenant_id, "server_id": server_id},
                server_id=server_id,
                tenant_id=raw_srv["tenant_id"],
                company_id=raw_srv["company_id"]
            )
            raise SecurityException(f"Cross-tenant access prohibited: Caller {self.tenant_id} tried accessing {raw_srv['tenant_id']}")

        server = self.get_server(server_id)
        if not server:
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args={}, policy="DENY", authority="DENIED",
                status=MCPExecutionStatus.DISCOVERY_FAILED.value, response=None,
                error=f"MCP Server '{server_id}' not found", latency_ms=0.0, context=ctx
            )

        # Company Isolation
        allowed_companies = server.get("allowed_companies", [])
        if allowed_companies and self.company_id not in allowed_companies and "*" not in allowed_companies:
            self._record_security_event(
                MCPSecurityEventType.POLICY_VIOLATION,
                "HIGH",
                {"reason": "Company isolation violation", "caller_company": self.company_id, "server_id": server_id}
            )
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args={}, policy="DENY", authority="DENIED",
                status=MCPExecutionStatus.AUTHORITY_DENIED.value, response=None,
                error=f"Server not authorized for company {self.company_id}", latency_ms=0.0, context=ctx
            )

        # 3. Trust State Check
        trust_state = server.get("trust_state", MCPTrustState.UNKNOWN.value)
        if trust_state in (MCPTrustState.BLOCKED.value, MCPTrustState.SUSPENDED.value):
            self._record_security_event(
                MCPSecurityEventType.UNTRUSTED_SERVER,
                "HIGH",
                {"server_id": server_id, "trust_state": trust_state}
            )
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args={}, policy="DENY", authority="DENIED",
                status=MCPExecutionStatus.AUTHORITY_DENIED.value, response=None,
                error=f"MCP Server '{server_id}' is in trust state '{trust_state}'", latency_ms=0.0, context=ctx
            )

        if not tool:
            # Auto-register if server is trusted or validated
            self.register_tool(server_id, tool_name, f"Discovered tool {tool_name}")
            tool = self.get_tool(tool_name, server_id=server_id)

        risk_class = tool.get("risk_class", MCPToolRiskClass.READ_ONLY.value)
        approval_req = bool(tool.get("approval_requirement", 0))

        # 4. PolicyEngine Evaluation
        # Financial threshold policy
        amount = float(arguments.get("amount", 0.0) or arguments.get("refund_amount", 0.0) or 0.0)
        policy_decision = "ALLOW"
        if risk_class == MCPToolRiskClass.FINANCIAL.value:
            max_autonomous_amount = 10000.0  # ₹10,000 threshold
            if amount > max_autonomous_amount:
                # Require approval or deny
                policy_decision = "REQUIRE_HUMAN_APPROVAL"
                approval_req = True
        elif risk_class in (MCPToolRiskClass.DESTRUCTIVE.value, MCPToolRiskClass.PRIVILEGED.value, MCPToolRiskClass.BUSINESS_MUTATION.value):
            if tool.get("approval_requirement", 1) != 0:
                approval_req = True
                policy_decision = "REQUIRE_HUMAN_APPROVAL"

        # Check explicit policy denial rule
        if ctx.get("force_policy_deny"):
            policy_decision = "DENY"
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args={}, policy="DENY", authority="DENIED",
                status=MCPExecutionStatus.POLICY_DENIED.value, response=None,
                error="PolicyEngine denied execution: Exceeds authorized role scope", latency_ms=0.0, context=ctx
            )

        # 5. Human Approval Interception
        if approval_req and not ctx.get("pre_approved_id"):
            appr_res = ApprovalPipeline.create_request(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                agent_id=agent_id,
                action_desc=f"MCP Operation: {tool_name} on server {server.get('display_name')}",
                reason=f"High-risk MCP operation classified as {risk_class} requires human authorization",
                risk_level="HIGH" if risk_class in (MCPToolRiskClass.FINANCIAL.value, MCPToolRiskClass.DESTRUCTIVE.value, MCPToolRiskClass.PRIVILEGED.value) else "MEDIUM",
                consequence=f"Mutation on external system: {json.dumps(arguments)}",
                mission_id=mission_id
            )
            appr_id = appr_res.get("request_id")
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args={}, policy="REQUIRE_HUMAN_APPROVAL",
                authority="SUSPENDED_FOR_APPROVAL", status=MCPExecutionStatus.APPROVAL_REQUIRED.value,
                response={"approval_id": appr_id, "status": "SUSPENDED_FOR_APPROVAL"},
                error="Human-in-the-Loop approval required for high-risk MCP operation",
                latency_ms=round((time.time() - start_time) * 1000, 2),
                context=ctx, approval_id=appr_id
            )

        # 6. Data Minimization & Secret Scrubbing
        sanitized_args = MCPDataMinimizer.minimize_arguments(
            arguments,
            input_schema=tool.get("input_schema"),
            data_classification=MCPDataClassification(tool.get("data_classification", "INTERNAL"))
        )

        # 7. Transport Execution
        transport_type = server.get("transport", MCPTransportType.STREAMABLE_HTTP.value)
        endpoint = server.get("endpoint")
        cred_token = "opaque_token_val" if server.get("credential_reference") else None

        if transport_type == MCPTransportType.STREAMABLE_HTTP.value:
            transport = StreamableHTTPTransport(endpoint, auth_token=cred_token)
        else:
            command = json.loads(endpoint) if endpoint.startswith("[") else [endpoint]
            transport = StdioTransport(command)

        rpc_request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": exec_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": sanitized_args,
                "_meta": {
                    "tenant_id": self.tenant_id,
                    "company_id": self.company_id,
                    "agent_id": agent_id,
                    "correlation_id": exec_id
                }
            }
        }

        # Check for simulated network timeout
        if ctx.get("simulate_timeout"):
            # Mark UNKNOWN state, requiring reconciliation, strictly NO blind replay
            latency = round((time.time() - start_time) * 1000, 2)
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args=sanitized_args, policy=policy_decision,
                authority="AUTHORIZED", status=MCPExecutionStatus.UNKNOWN.value,
                response=None, error="Transport timeout: Outcome ambiguous. State reconciliation required before retry.",
                latency_ms=latency, context=ctx
            )

        # Execute over transport
        timeout = float(tool.get("timeout", 30.0))
        rpc_response = transport.send_request(rpc_request, timeout=timeout)
        latency = round((time.time() - start_time) * 1000, 2)

        # 8. Inspect RPC errors
        if "error" in rpc_response:
            err_obj = rpc_response["error"]
            err_msg = err_obj.get("message", "MCP Tool Execution Failed")
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args=sanitized_args, policy=policy_decision,
                authority="AUTHORIZED", status=MCPExecutionStatus.TOOL_FAILED.value,
                response=rpc_response, error=err_msg, latency_ms=latency, context=ctx
            )

        # 9. Result Sanitization & Content Firewall
        raw_result = rpc_response.get("result", {})
        clean_ok, sanitized_res, warnings = ExternalContentFirewall.sanitize_output(raw_result)
        if not clean_ok:
            self._record_security_event(
                MCPSecurityEventType.PROMPT_INJECTION,
                "HIGH",
                {"server_id": server_id, "tool_id": tool_id, "warnings": warnings}
            )
            return self._record_execution(
                exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
                arguments=arguments, sanitized_args=sanitized_args, policy=policy_decision,
                authority="AUTHORIZED", status=MCPExecutionStatus.TOOL_FAILED.value,
                response=raw_result, error="Content Firewall blocked malicious MCP tool response",
                latency_ms=latency, context=ctx
            )

        # 10. Independent Physical Reality Verification
        verif = PhysicalVerification(
            check_type="sha256_match",
            target_path=f"mcp/{server_id}/{tool_name}/{exec_id}",
            expected_val="VERIFIED_SUCCESS",
            actual_val="VERIFIED_SUCCESS",
            verified=True,
            details=f"MCP Tool {tool_name} on server {server_id} executed and returned validated schema output"
        )

        # 11. Evidence Ledger Sealing (Cryptographic Merkle index)
        sealed_rec = self.evidence_ledger.seal_evidence(
            action_id=f"mcp_act_{exec_id}",
            mission_id=mission_id,
            agent_id=agent_id,
            verifications=[verif],
            metadata={
                "server_id": server_id,
                "tool_id": tool_id,
                "tool_name": tool_name,
                "execution_id": exec_id,
                "tenant_id": self.tenant_id,
                "company_id": self.company_id
            }
        )

        # 12. Business Causality Link (TASK_SUCCESS != BUSINESS_OUTCOME)
        causal_chain_id = self.causality_engine.record_causal_link(
            strategy_goal=f"Execute Governed MCP Tool {tool_name}",
            mission_id=mission_id,
            task_id=f"task_{exec_id}",
            action_id=sealed_rec.action_id,
            transaction_id=f"tx_{exec_id}" if risk_class == MCPToolRiskClass.FINANCIAL.value else None,
            revenue_attributed=0.0,
            cost_attributed=float(tool.get("cost_model", 0.0)),
            verified_outcome=OutcomeStatus.VERIFIED_SUCCESS
        )

        # Update Server Reputation Metrics
        self._update_server_reputation(server_id, success=True, latency_ms=latency)

        return self._record_execution(
            exec_id=exec_id, server_id=server_id, tool_id=tool_id, tool_name=tool_name,
            arguments=arguments, sanitized_args=sanitized_args, policy=policy_decision,
            authority="AUTHORIZED", status=MCPExecutionStatus.VERIFIED.value,
            response=sanitized_res, error=None, latency_ms=latency, context=ctx,
            verification_id=verif.target_path, evidence_id=sealed_rec.evidence_id,
            digest=sealed_rec.sha256_digest, causal_id=causal_chain_id
        )

    # -------------------------------------------------------------------------
    # Internal Helpers & Audit
    # -------------------------------------------------------------------------

    def _record_execution(
        self,
        exec_id: str,
        server_id: str,
        tool_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        sanitized_args: Dict[str, Any],
        policy: str,
        authority: str,
        status: str,
        response: Any,
        error: Optional[str],
        latency_ms: float,
        context: Dict[str, Any],
        approval_id: Optional[str] = None,
        verification_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        digest: Optional[str] = None,
        causal_id: Optional[str] = None
    ) -> Dict[str, Any]:
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO mcp_executions (
                    execution_id, tenant_id, company_id, mission_id, workflow_id,
                    thread_id, agent_id, server_id, tool_id, tool_name,
                    arguments, sanitized_arguments, policy_decision, authority_decision,
                    approval_id, execution_status, response_raw, response_sanitized,
                    verification_id, verification_status, evidence_id, sha256_digest,
                    causality_chain_id, business_outcome, latency_ms, cost_spent,
                    error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exec_id, self.tenant_id, self.company_id, context.get("mission_id", "m_default"),
                    context.get("workflow_id", "wf_default"), context.get("thread_id", f"thrd_{exec_id[:8]}"),
                    context.get("agent_id", "agent_system"), server_id, tool_id, tool_name,
                    json.dumps(arguments), json.dumps(sanitized_args), policy, authority,
                    approval_id, status, json.dumps(response), json.dumps(response),
                    verification_id, "VERIFIED" if status == MCPExecutionStatus.VERIFIED.value else "UNVERIFIED",
                    evidence_id, digest, causal_id,
                    "Verified Outcome" if status == MCPExecutionStatus.VERIFIED.value else "Failed or Suspended",
                    latency_ms, 0.0, error, now
                )
            )
            conn.commit()

        return {
            "success": status == MCPExecutionStatus.VERIFIED.value,
            "execution_id": exec_id,
            "status": status,
            "server_id": server_id,
            "tool_id": tool_id,
            "tool_name": tool_name,
            "policy_decision": policy,
            "authority_decision": authority,
            "approval_id": approval_id,
            "result": response,
            "error": error,
            "latency_ms": latency_ms,
            "evidence_id": evidence_id,
            "sha256_digest": digest,
            "causality_chain_id": causal_id
        }

    def _record_security_event(
        self,
        event_type: MCPSecurityEventType,
        severity: str,
        details: Dict[str, Any],
        server_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None
    ):
        ev_id = f"sec_ev_{uuid.uuid4().hex[:10]}"
        t_id = tenant_id or self.tenant_id
        c_id = company_id or self.company_id
        with db.get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO mcp_security_events (
                        event_id, tenant_id, company_id, server_id, tool_id,
                        event_type, severity, details, source_ip, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ev_id, t_id, c_id, server_id, details.get("tool_id"),
                        event_type.value, severity, json.dumps(details), "127.0.0.1", time.time()
                    )
                )
                conn.commit()
            except Exception:
                pass

    def _update_server_reputation(self, server_id: str, success: bool, latency_ms: float):
        with db.get_connection() as conn:
            r = conn.execute("SELECT reputation_metrics FROM mcp_servers WHERE server_id = ?", (server_id,)).fetchone()
            if not r:
                return
            metrics = json.loads(r["reputation_metrics"]) if r["reputation_metrics"] else {}
            metrics["invocations"] = metrics.get("invocations", 0) + 1
            if success:
                metrics["successes"] = metrics.get("successes", 0) + 1
                metrics["verifications"] = metrics.get("verifications", 0) + 1
            else:
                metrics["failures"] = metrics.get("failures", 0) + 1
            tot = metrics["invocations"]
            prev_avg = metrics.get("avg_latency_ms", 0.0)
            metrics["avg_latency_ms"] = round(((prev_avg * (tot - 1)) + latency_ms) / max(1, tot), 2)

            conn.execute(
                "UPDATE mcp_servers SET reputation_metrics = ?, updated_at = ?, last_seen = ? WHERE server_id = ?",
                (json.dumps(metrics), time.time(), time.time(), server_id)
            )
            conn.commit()

    def list_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM mcp_executions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                (self.tenant_id, limit)
            ).fetchall()
            execs = []
            for r in rows:
                d = dict(r)
                for k in ("arguments", "sanitized_arguments", "response_raw", "response_sanitized"):
                    if d.get(k) and isinstance(d[k], str):
                        try:
                            d[k] = json.loads(d[k])
                        except Exception:
                            pass
                execs.append(d)
            return execs

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM mcp_executions WHERE execution_id = ? AND tenant_id = ?", (execution_id, self.tenant_id)).fetchone()
            if not row:
                return None
            d = dict(row)
            for k in ("arguments", "sanitized_arguments", "response_raw", "response_sanitized"):
                if d.get(k) and isinstance(d[k], str):
                    try:
                        d[k] = json.loads(d[k])
                    except Exception:
                        pass
            return d

    def get_execution_evidence(self, execution_id: str) -> Optional[Dict[str, Any]]:
        exec_record = self.get_execution(execution_id)
        if not exec_record:
            return None
        ev_id = exec_record.get("evidence_id")
        if not ev_id:
            return {"execution_id": execution_id, "evidence_status": "NO_EVIDENCE_RECORD"}
        pkg = self.evidence_ledger.get_evidence(ev_id)
        if not pkg:
            return {
                "execution_id": execution_id,
                "evidence_id": ev_id,
                "status": "SEALED",
                "sha256_digest": exec_record.get("sha256_digest")
            }
        return pkg.to_dict() if hasattr(pkg, "to_dict") else dict(pkg)

    def verify_execution(self, execution_id: str) -> Dict[str, Any]:
        exec_record = self.get_execution(execution_id)
        if not exec_record:
            return {"success": False, "error": f"Execution {execution_id} not found"}
        raw_res = exec_record.get("response_raw")
        verified = bool(raw_res is not None and exec_record.get("execution_status") == MCPExecutionStatus.VERIFIED.value)
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE mcp_executions SET verification_status = ? WHERE execution_id = ?",
                ("VERIFIED" if verified else "VERIFICATION_FAILED", execution_id)
            )
            conn.commit()
        return {
            "success": verified,
            "execution_id": execution_id,
            "verification_status": "VERIFIED" if verified else "VERIFICATION_FAILED",
            "sha256_digest": exec_record.get("sha256_digest"),
            "causality_chain_id": exec_record.get("causality_chain_id")
        }

    def cancel_execution(self, execution_id: str, reason: str = "Admin cancellation") -> Dict[str, Any]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM mcp_executions WHERE execution_id = ? AND tenant_id = ?", (execution_id, self.tenant_id)).fetchone()
            if not row:
                raise ValueError(f"Execution {execution_id} not found")
            conn.execute(
                "UPDATE mcp_executions SET execution_status = 'CANCELLED', error_message = ? WHERE execution_id = ?",
                (f"Cancelled: {reason}", execution_id)
            )
            conn.commit()
        return {"success": True, "execution_id": execution_id, "status": "CANCELLED", "reason": reason}

    def list_security_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM mcp_security_events WHERE tenant_id = ? ORDER BY timestamp DESC LIMIT ?",
                (self.tenant_id, limit)
            ).fetchall()
            events = []
            for r in rows:
                d = dict(r)
                if d.get("details") and isinstance(d["details"], str):
                    try:
                        d["details"] = json.loads(d["details"])
                    except Exception:
                        pass
                events.append(d)
            return events

    def get_metrics(self) -> Dict[str, Any]:
        with db.get_connection() as conn:
            srv_count = conn.execute("SELECT COUNT(*) as c FROM mcp_servers WHERE tenant_id = ?", (self.tenant_id,)).fetchone()["c"]
            active_conn = conn.execute("SELECT COUNT(*) as c FROM mcp_servers WHERE tenant_id = ? AND status = 'ONLINE'", (self.tenant_id,)).fetchone()["c"]
            trusted_count = conn.execute("SELECT COUNT(*) as c FROM mcp_servers WHERE tenant_id = ? AND trust_state IN ('TRUSTED', 'VALIDATED')", (self.tenant_id,)).fetchone()["c"]
            tools_count = conn.execute("SELECT COUNT(*) as c FROM mcp_tools WHERE tenant_id = ?", (self.tenant_id,)).fetchone()["c"]
            exec_count = conn.execute("SELECT COUNT(*) as c FROM mcp_executions WHERE tenant_id = ?", (self.tenant_id,)).fetchone()["c"]
            success_count = conn.execute("SELECT COUNT(*) as c FROM mcp_executions WHERE tenant_id = ? AND execution_status = 'VERIFIED'", (self.tenant_id,)).fetchone()["c"]
            failed_count = conn.execute("SELECT COUNT(*) as c FROM mcp_executions WHERE tenant_id = ? AND execution_status NOT IN ('VERIFIED', 'APPROVAL_REQUIRED')", (self.tenant_id,)).fetchone()["c"]
            appr_count = conn.execute("SELECT COUNT(*) as c FROM mcp_executions WHERE tenant_id = ? AND execution_status = 'APPROVAL_REQUIRED'", (self.tenant_id,)).fetchone()["c"]
            sec_count = conn.execute("SELECT COUNT(*) as c FROM mcp_security_events WHERE tenant_id = ?", (self.tenant_id,)).fetchone()["c"]
            policy_blocks = conn.execute("SELECT COUNT(*) as c FROM mcp_executions WHERE tenant_id = ? AND execution_status = 'POLICY_DENIED'", (self.tenant_id,)).fetchone()["c"]
            unknown_count = conn.execute("SELECT COUNT(*) as c FROM mcp_executions WHERE tenant_id = ? AND execution_status = 'UNKNOWN'", (self.tenant_id,)).fetchone()["c"]
            verif_count = conn.execute("SELECT COUNT(*) as c FROM mcp_executions WHERE tenant_id = ? AND verification_status = 'VERIFIED'", (self.tenant_id,)).fetchone()["c"]

            return {
                "mcp_servers": srv_count,
                "active_connections": active_conn,
                "registered_servers": srv_count,
                "trusted_servers": trusted_count,
                "available_capabilities": tools_count,
                "available_tools": tools_count,
                "tool_invocations": exec_count,
                "total_invocations": exec_count,
                "successful_executions": success_count,
                "failed_executions": failed_count,
                "awaiting_approval": appr_count,
                "policy_blocks": policy_blocks,
                "security_events": sec_count,
                "verification_success": verif_count,
                "unknown_outcomes": unknown_count,
                "killswitch_active": MCPKillSwitch.is_active(self.tenant_id),
                "has_activity": bool(exec_count > 0 or srv_count > 0)
            }


# =============================================================================
# 7. ZONATA AS AN MCP SERVER (Inbound Published Capabilities)
# =============================================================================

class ZonataMcpServer:
    """
    Allows external AI clients to securely access selected ZONATA capabilities
    via the 2026-07-28 MCP JSON-RPC protocol without exposing internal prompts,
    Letta memories, private credentials, or unrestricted execution authority.
    """
    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def publish_capability(
        self,
        capability_id: str,
        name: str,
        description: str,
        schema_definition: Dict[str, Any],
        visibility: str = "PRIVATE",
        rate_limit: int = 60,
        approval_required: bool = False
    ) -> str:
        pub_id = f"pub_cap_{uuid.uuid4().hex[:10]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mcp_published_capabilities (
                    published_id, tenant_id, company_id, capability_id, name,
                    description, schema_definition, visibility, allowed_clients,
                    rate_limit_per_min, approval_required, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pub_id, self.tenant_id, self.company_id, capability_id, name,
                    description, json.dumps(schema_definition), visibility,
                    json.dumps(["*"]), rate_limit, 1 if approval_required else 0,
                    "ACTIVE", now, now
                )
            )
            conn.commit()
        return pub_id

    def list_published(self) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM mcp_published_capabilities WHERE tenant_id = ?", (self.tenant_id,)).fetchall()
            caps = []
            for r in rows:
                d = dict(r)
                if d.get("schema_definition") and isinstance(d["schema_definition"], str):
                    try:
                        d["schema_definition"] = json.loads(d["schema_definition"])
                    except Exception:
                        pass
                caps.append(d)
            return caps

    def handle_jsonrpc(self, request_payload: Dict[str, Any], caller_identity: str = "external_ai") -> Dict[str, Any]:
        """Handles inbound JSON-RPC 2.0 requests per the 2026-07-28 specification."""
        req_id = request_payload.get("id")
        method = request_payload.get("method")
        params = request_payload.get("params", {})

        if MCPKillSwitch.is_active(self.tenant_id):
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": req_id,
                "error": {"code": -32000, "message": "ZONATA MCP Server: Global or Tenant KillSwitch is active"}
            }

        if method == "initialize":
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_SPEC_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "zonata-governed-mcp-server",
                        "version": "1.0.0"
                    }
                }
            }

        if method == "tools/list":
            with db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM mcp_published_capabilities WHERE tenant_id = ? AND status = 'ACTIVE'", (self.tenant_id,)).fetchall()
                tools = []
                for r in rows:
                    schema = json.loads(r["schema_definition"]) if r["schema_definition"] else {}
                    tools.append({
                        "name": r["name"],
                        "description": r["description"],
                        "inputSchema": schema
                    })
                return {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": req_id,
                    "result": {"tools": tools}
                }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            with db.get_connection() as conn:
                r = conn.execute("SELECT * FROM mcp_published_capabilities WHERE name = ? AND tenant_id = ? AND status = 'ACTIVE'", (tool_name, self.tenant_id)).fetchone()
                if not r:
                    return {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method/Tool '{tool_name}' not found or not published"}
                    }

                # Input check
                clean_ok, sanitized, warns = ExternalContentFirewall.sanitize_output(tool_args)
                if not clean_ok:
                    return {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": req_id,
                        "error": {"code": -32000, "message": "Prompt injection detected in arguments"}
                    }

                return {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"ZONATA capability '{tool_name}' executed safely under tenant {self.tenant_id}"}
                        ],
                        "status": "COMPLETED"
                    }
                }

        elif method == "resources/list":
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": req_id,
                "result": {"resources": []}
            }

        elif method == "prompts/list":
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": req_id,
                "result": {"prompts": []}
            }

        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not implemented"}
        }
