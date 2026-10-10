"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Autonomous AI DLP & Outbound Security Enforcement Gateway
============================================================
Central outbound data-loss prevention, destination trust mediation, and
autonomous security containment plane for ZONATA AI.

Enforces data protection across all outbound boundaries:
  1. LLM Gateway & Provider Dispatch
  2. MCP Tool Invocations
  3. Agent-to-Agent (A2A) Protocols
  4. Memory Persistence (Letta / SQLite)
  5. Browser & Network Egress
  6. Terminal & Workspace Execution
  7. Logging, Telemetry, and Tracing

Constitutional Invariants:
  1. AGENT != TRUST: Agent-supplied tenant, role, or trust is never trusted without server-side verification.
  2. ZERO_UNGOVERNED_EGRESS: No enterprise data leaves trust boundary without classification & policy evaluation.
  3. CONTINUOUS_AUTONOMY: Routine operations, safe redaction, and local failover continue unattended (offline owner).
  4. SCOPED_FAIL_CLOSED: Security failures fail closed for the affected operation without halting unrelated tasks.
  5. PROGRESSIVE_RESPONSE: Implements 5 Response Classes (Allow, Transform, Restrict, Contain, Require Approval).
"""

import time
import uuid
import hashlib
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field

from core.data_classification_engine import (
    classification_engine,
    DataClassificationLevel,
    SensitivityCategory,
    CLASSIFICATION_ORDER
)
from core.presidio_dlp_engine import (
    presidio_analyzer,
    presidio_anonymizer,
    RecognizerResult,
    AnonymizerResult
)
from core.security_center import (
    security_center,
    SecurityThreatSeverity,
    ThreatCategory
)
from core.evidence_service import evidence_service
from core.killswitch_matrix import KillSwitchMatrix, KillSwitchLevel

logger = logging.getLogger("zonata.ai.dlp.gateway")


# =============================================================================
# 1. ENUMS & DATA STRUCTURES
# =============================================================================

class DestinationTrustLevel(str, Enum):
    LOCAL_SOVEREIGN = "LOCAL_SOVEREIGN"         # Sovereign container, local models, internal DB
    INTERNAL_SECURE = "INTERNAL_SECURE"         # Controlled internal services (Vault, NATS, local MCP)
    APPROVED_SAAS = "APPROVED_SAAS"             # Authorized SaaS partners with signed contracts
    UNAPPROVED_EXTERNAL = "UNAPPROVED_EXTERNAL" # General Internet APIs or external agents
    PUBLIC_INTERNET = "PUBLIC_INTERNET"         # Untrusted web endpoints, search, raw egress


class SecurityResponseClass(str, Enum):
    CLASS_1_ALLOW = "CLASS_1_ALLOW"                         # Routine low-risk action allowed automatically
    CLASS_2_TRANSFORM = "CLASS_2_TRANSFORM"                 # Redact/tokenize/fallback local; continue work
    CLASS_3_RESTRICT = "CLASS_3_RESTRICT"                   # Block single operation; keep others running
    CLASS_4_CONTAIN = "CLASS_4_CONTAIN"                     # Auto-isolate offending agent/tool via KillSwitch
    CLASS_5_REQUIRE_APPROVAL = "CLASS_5_REQUIRE_APPROVAL"   # High-impact irreversible mutation needing owner


class OutboundChannel(str, Enum):
    LLM_PROMPT = "LLM_PROMPT"
    MCP_TOOL = "MCP_TOOL"
    A2A_MESSAGE = "A2A_MESSAGE"
    MEMORY_STORE = "MEMORY_STORE"
    BROWSER_EGRESS = "BROWSER_EGRESS"
    CONNECTOR_MUTATION = "CONNECTOR_MUTATION"
    TERMINAL_COMMAND = "TERMINAL_COMMAND"
    LOG_TELEMETRY = "LOG_TELEMETRY"


@dataclass
class OutboundSecurityContext:
    tenant_id: str
    principal_id: str
    principal_role: str
    calling_agent_id: str
    channel: OutboundChannel
    destination_name: str
    destination_trust: DestinationTrustLevel
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    approval_receipt: Optional[Dict[str, Any]] = None
    policy_version: str = "2026.10-sovereign-v1"


@dataclass
class DLPInspectionDecision:
    is_allowed: bool
    response_class: SecurityResponseClass
    sanitized_payload: Any
    detected_classification: str
    detected_sensitivities: List[str]
    entities_detected: List[str]
    items_transformed: int
    blocking_reason: Optional[str] = None
    token_map: Dict[str, str] = field(default_factory=dict)
    use_local_model_fallback: bool = False
    containment_action_taken: Optional[str] = None
    trace_id: str = field(default_factory=lambda: f"dlp_trc_{uuid.uuid4().hex[:12]}")
    execution_time_ms: float = 0.0


# =============================================================================
# 2. CENTRAL AUTONOMOUS AI DLP GATEWAY
# =============================================================================

class AutonomousAIDLPGateway:
    """
    Sovereign AI Data Loss Prevention & Outbound Enforcement Gateway.
    Mediates all outbound channels to protect enterprise assets while ensuring
    autonomous, unattended continuous business operations.
    """

    # Prohibited destinations for HIGHLY_RESTRICTED (credentials, private keys, live tokens)
    STRICT_SOVEREIGN_ONLY_LEVELS = {
        DataClassificationLevel.HIGHLY_RESTRICTED
    }

    # Destinations requiring sanitization/redaction for CONFIDENTIAL & RESTRICTED
    TRANSFORM_REQUIRED_LEVELS = {
        DataClassificationLevel.CONFIDENTIAL,
        DataClassificationLevel.RESTRICTED
    }

    def __init__(self):
        self.killswitch = KillSwitchMatrix()
        # In-memory violation tracker for automated Class 4 containment
        self._agent_violation_counts: Dict[str, int] = {}
        self._max_violations_before_containment = 3

    def _sanitize_string(
        self,
        text: str,
        target_trust: DestinationTrustLevel,
        allow_tokenization: bool = True
    ) -> Tuple[str, List[RecognizerResult], AnonymizerResult]:
        """Runs Presidio analysis and applies transformation operators."""
        recognizer_results = presidio_analyzer.analyze(text)
        
        # Configure operators based on destination trust
        if target_trust == DestinationTrustLevel.APPROVED_SAAS and allow_tokenization:
            # Tokenize customer identifiers so business references remain stable
            operators = {
                "ZONATA_CUSTOMER_ID": {"type": "tokenize"},
                "FINANCIAL_ACCOUNT": {"type": "mask", "chars_to_preserve": 4},
                "CREDIT_CARD": {"type": "mask", "chars_to_preserve": 4},
                "US_SSN": {"type": "replace", "new_value": "<REDACTED_SSN>"},
                "CRYPTO_PRIVATE_KEY": {"type": "redact"},
                "API_KEY_OR_SECRET": {"type": "replace", "new_value": "<REDACTED_SECRET>"}
            }
        else:
            operators = {
                "DEFAULT": {"type": "replace"}
            }

        anon_result = presidio_anonymizer.anonymize(text, recognizer_results, operators=operators)
        return anon_result.text, recognizer_results, anon_result

    def inspect_and_enforce(
        self,
        ctx: OutboundSecurityContext,
        payload: Any,
        explicit_classification: Optional[str] = None
    ) -> DLPInspectionDecision:
        """
        Universal inspection & enforcement gate for outbound data transfers.
        """
        start_time = time.time()
        trace_id = f"dlp_trc_{uuid.uuid4().hex[:12]}"

        # 1. KillSwitch Pre-check: Verify calling agent or tool is not quarantined
        if self.killswitch.is_activated(level=KillSwitchLevel.AGENT, target_id=ctx.calling_agent_id):
            return DLPInspectionDecision(
                is_allowed=False,
                response_class=SecurityResponseClass.CLASS_4_CONTAIN,
                sanitized_payload=None,
                detected_classification="N/A",
                detected_sensitivities=[],
                entities_detected=[],
                items_transformed=0,
                blocking_reason=f"Calling agent '{ctx.calling_agent_id}' is quarantined under active KillSwitch.",
                trace_id=trace_id,
                execution_time_ms=(time.time() - start_time) * 1000.0
            )

        # 2. Extract textual content for deep inspection
        if isinstance(payload, str):
            text_to_scan = payload
        elif isinstance(payload, dict) or isinstance(payload, list):
            text_to_scan = json.dumps(payload, default=str)
        else:
            text_to_scan = str(payload)

        # 3. Presidio Entity Recognition & Classification
        eff_level, categories, reasons = classification_engine.classify_content(
            text_content=text_to_scan,
            admin_policy_level=explicit_classification
        )
        sanitized_text, rec_results, anon_res = self._sanitize_string(
            text=text_to_scan,
            target_trust=ctx.destination_trust
        )

        detected_entities = [r.entity_type for r in rec_results]
        has_secrets = any(e in ("CRYPTO_PRIVATE_KEY", "API_KEY_OR_SECRET", "ZONATA_INTERNAL_TOKEN") for e in detected_entities)

        # 4. Fail-Closed Security Policy Evaluation

        # SCENARIO A: Prohibited Secret / Private Key Exfiltration
        if has_secrets and ctx.destination_trust not in (DestinationTrustLevel.LOCAL_SOVEREIGN, DestinationTrustLevel.INTERNAL_SECURE):
            # Check if this is an attempted credential theft or exfiltration
            self._agent_violation_counts[ctx.calling_agent_id] = self._agent_violation_counts.get(ctx.calling_agent_id, 0) + 1
            viol_count = self._agent_violation_counts[ctx.calling_agent_id]

            containment_action = None
            resp_class = SecurityResponseClass.CLASS_3_RESTRICT

            # Trigger Class 4 containment if agent repeatedly attempts credential egress
            if viol_count >= self._max_violations_before_containment:
                self.killswitch.activate(
                    level=KillSwitchLevel.AGENT,
                    target_id=ctx.calling_agent_id,
                    reason=f"Automated containment: repeated credential exfiltration attempts ({viol_count} violations).",
                    activated_by="AUTONOMOUS_DLP_GATEWAY"
                )
                containment_action = f"AGENT_ISOLATED_KILLSWITCH_{ctx.calling_agent_id}"
                resp_class = SecurityResponseClass.CLASS_4_CONTAIN

            # Record incident in SecurityCenter without logging raw secrets
            security_center.record_incident(
                tenant_id=ctx.tenant_id,
                company_id="comp_primary",
                category=ThreatCategory.DLP_EXFILTRATION_ATTEMPT,
                severity=SecurityThreatSeverity.CRITICAL if has_secrets else SecurityThreatSeverity.HIGH,
                source_entity_id=ctx.calling_agent_id,
                description=f"Outbound transfer to '{ctx.destination_name}' blocked: detected unencrypted credentials/keys.",
                details={
                    "trace_id": trace_id,
                    "channel": ctx.channel.value,
                    "destination": ctx.destination_name,
                    "trust_level": ctx.destination_trust.value,
                    "detected_entities": list(set(detected_entities)),
                    "violation_count": viol_count,
                    "containment_action": containment_action
                }
            )

            return DLPInspectionDecision(
                is_allowed=False,
                response_class=resp_class,
                sanitized_payload=None,
                detected_classification=eff_level,
                detected_sensitivities=categories,
                entities_detected=detected_entities,
                items_transformed=0,
                blocking_reason=f"Outbound transmission of raw credentials or private keys to '{ctx.destination_name}' strictly forbidden.",
                containment_action_taken=containment_action,
                trace_id=trace_id,
                execution_time_ms=(time.time() - start_time) * 1000.0
            )

        # SCENARIO B: HIGHLY_RESTRICTED Data to Cloud/External
        if eff_level in self.STRICT_SOVEREIGN_ONLY_LEVELS and ctx.destination_trust not in (DestinationTrustLevel.LOCAL_SOVEREIGN, DestinationTrustLevel.INTERNAL_SECURE):
            # Check if local model failover can safely preserve autonomous continuity
            if ctx.channel == OutboundChannel.LLM_PROMPT:
                logger.info(f"[DLP CLASS 2] Switching prompt to local sovereign model for classification '{eff_level}'.")
                return DLPInspectionDecision(
                    is_allowed=True,
                    response_class=SecurityResponseClass.CLASS_2_TRANSFORM,
                    sanitized_payload=sanitized_text,
                    detected_classification=eff_level,
                    detected_sensitivities=categories,
                    entities_detected=detected_entities,
                    items_transformed=anon_res.items_count,
                    use_local_model_fallback=True,
                    token_map=anon_res.token_map,
                    trace_id=trace_id,
                    execution_time_ms=(time.time() - start_time) * 1000.0
                )
            else:
                return DLPInspectionDecision(
                    is_allowed=False,
                    response_class=SecurityResponseClass.CLASS_3_RESTRICT,
                    sanitized_payload=None,
                    detected_classification=eff_level,
                    detected_sensitivities=categories,
                    entities_detected=detected_entities,
                    items_transformed=0,
                    blocking_reason=f"Classification '{eff_level}' cannot leave sovereign trust boundary.",
                    trace_id=trace_id,
                    execution_time_ms=(time.time() - start_time) * 1000.0
                )

        # SCENARIO B2: Prohibited egress of CONFIDENTIAL / RESTRICTED data to UNAPPROVED_EXTERNAL or PUBLIC_INTERNET
        if eff_level in (DataClassificationLevel.CONFIDENTIAL, DataClassificationLevel.RESTRICTED, DataClassificationLevel.HIGHLY_RESTRICTED) and ctx.destination_trust in (DestinationTrustLevel.UNAPPROVED_EXTERNAL, DestinationTrustLevel.PUBLIC_INTERNET):
            return DLPInspectionDecision(
                is_allowed=False,
                response_class=SecurityResponseClass.CLASS_3_RESTRICT,
                sanitized_payload=None,
                detected_classification=eff_level,
                detected_sensitivities=categories,
                entities_detected=detected_entities,
                items_transformed=0,
                blocking_reason=f"Classification '{eff_level}' cannot be transmitted to untrusted destination '{ctx.destination_name}' ({ctx.destination_trust.value}).",
                trace_id=trace_id,
                execution_time_ms=(time.time() - start_time) * 1000.0
            )

        # SCENARIO C: PII / Customer / Financial Data (CONFIDENTIAL / RESTRICTED) -> Class 2 Transform & Continue
        if rec_results and anon_res.items_count > 0:
            # Reconstruct payload if input was dict
            final_payload = sanitized_text
            if isinstance(payload, dict):
                try:
                    final_payload = json.loads(sanitized_text)
                except Exception:
                    final_payload = sanitized_text

            return DLPInspectionDecision(
                is_allowed=True,
                response_class=SecurityResponseClass.CLASS_2_TRANSFORM,
                sanitized_payload=final_payload,
                detected_classification=eff_level,
                detected_sensitivities=categories,
                entities_detected=detected_entities,
                items_transformed=anon_res.items_count,
                token_map=anon_res.token_map,
                trace_id=trace_id,
                execution_time_ms=(time.time() - start_time) * 1000.0
            )

        # SCENARIO D: Routine Low-Risk Action -> Class 1 Allow Automatically
        return DLPInspectionDecision(
            is_allowed=True,
            response_class=SecurityResponseClass.CLASS_1_ALLOW,
            sanitized_payload=payload,
            detected_classification=eff_level,
            detected_sensitivities=categories,
            entities_detected=[],
            items_transformed=0,
            trace_id=trace_id,
            execution_time_ms=(time.time() - start_time) * 1000.0
        )

    # -------------------------------------------------------------------------
    # BOUNDARY-SPECIFIC MEDIATION METHODS
    # -------------------------------------------------------------------------

    def inspect_llm_prompt(
        self,
        prompt: str,
        tenant_id: str,
        agent_id: str,
        provider_name: str,
        is_sovereign_local: bool
    ) -> DLPInspectionDecision:
        """Enforces DLP before external LLM dispatch."""
        trust = DestinationTrustLevel.LOCAL_SOVEREIGN if is_sovereign_local else DestinationTrustLevel.APPROVED_SAAS
        ctx = OutboundSecurityContext(
            tenant_id=tenant_id,
            principal_id=f"usr_{tenant_id}",
            principal_role="OPERATOR",
            calling_agent_id=agent_id,
            channel=OutboundChannel.LLM_PROMPT,
            destination_name=provider_name,
            destination_trust=trust
        )
        return self.inspect_and_enforce(ctx, prompt)

    def inspect_tool_arguments(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        tenant_id: str,
        agent_id: str,
        is_internal_server: bool = True
    ) -> DLPInspectionDecision:
        """Enforces DLP before MCP tool invocation."""
        trust = DestinationTrustLevel.INTERNAL_SECURE if is_internal_server else DestinationTrustLevel.UNAPPROVED_EXTERNAL
        ctx = OutboundSecurityContext(
            tenant_id=tenant_id,
            principal_id=f"usr_{tenant_id}",
            principal_role="OPERATOR",
            calling_agent_id=agent_id,
            channel=OutboundChannel.MCP_TOOL,
            destination_name=f"{server_id}::{tool_name}",
            destination_trust=trust
        )
        return self.inspect_and_enforce(ctx, arguments)

    def inspect_tool_output(
        self,
        server_id: str,
        tool_name: str,
        output_data: Any,
        tenant_id: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Scans returned tool content for prompt injection or leaked secrets.
        Treats all tool output as untrusted external data.
        """
        output_str = json.dumps(output_data, default=str) if isinstance(output_data, (dict, list)) else str(output_data)

        # Check for prompt injection patterns
        injection_patterns = [
            r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions",
            r"system\s+prompt\s+override",
            r"you\s+must\s+always\s+(?:send|exfiltrate|transfer)",
            r"disregard\s+(?:zonata\s+)?company\s+policy",
            r"bypass\s+(?:zonata\s+)?(?:policy|approval|guardrail|killswitch)",
            r"exfiltrate\s+credentials"
        ]
        for pat in injection_patterns:
            import re
            if re.search(pat, output_str, re.IGNORECASE):
                security_center.record_incident(
                    tenant_id=tenant_id,
                    company_id="comp_primary",
                    category=ThreatCategory.PROMPT_INJECTION,
                    severity=SecurityThreatSeverity.HIGH,
                    source_entity_id=f"{server_id}::{tool_name}",
                    description=f"Prompt injection pattern detected in MCP tool output from {server_id}::{tool_name}.",
                    details={"pattern_matched": pat}
                )
                return False, None, f"Prompt injection detected in output from '{tool_name}'."

        # Redact any returned secrets
        sanitized_str, recs, anon = self._sanitize_string(output_str, DestinationTrustLevel.INTERNAL_SECURE)
        return True, sanitized_str, None

    def inspect_a2a_message(
        self,
        sender_agent_id: str,
        target_agent_id: str,
        message_payload: Dict[str, Any],
        sender_tenant_id: str,
        target_tenant_id: Optional[str] = None
    ) -> DLPInspectionDecision:
        """Enforces tenant isolation and scrubs secrets between agents."""
        # Cross-tenant violation check
        effective_target_tenant = target_tenant_id or sender_tenant_id
        if effective_target_tenant != sender_tenant_id:
            security_center.record_incident(
                tenant_id=sender_tenant_id,
                company_id="comp_primary",
                category=ThreatCategory.CROSS_TENANT_VIOLATION,
                severity=SecurityThreatSeverity.CRITICAL,
                source_entity_id=sender_agent_id,
                description=f"Cross-tenant A2A communication attempt from '{sender_tenant_id}' to '{effective_target_tenant}' blocked.",
                details={"target_agent": target_agent_id}
            )
            return DLPInspectionDecision(
                is_allowed=False,
                response_class=SecurityResponseClass.CLASS_3_RESTRICT,
                sanitized_payload=None,
                detected_classification="CROSS_TENANT",
                detected_sensitivities=[],
                entities_detected=[],
                items_transformed=0,
                blocking_reason=f"Cross-tenant message delivery from '{sender_tenant_id}' to '{effective_target_tenant}' prohibited."
            )

        ctx = OutboundSecurityContext(
            tenant_id=sender_tenant_id,
            principal_id=sender_agent_id,
            principal_role="AGENT",
            calling_agent_id=sender_agent_id,
            channel=OutboundChannel.A2A_MESSAGE,
            destination_name=target_agent_id,
            destination_trust=DestinationTrustLevel.INTERNAL_SECURE
        )
        return self.inspect_and_enforce(ctx, message_payload)

    def inspect_memory_persistence(
        self,
        tier_name: str,
        key: str,
        value: Any,
        tenant_id: str,
        worker_id: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Scans memory records before persistence to prevent raw secret leakage."""
        val_str = json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value)
        recs = presidio_analyzer.analyze(val_str)
        has_secrets = any(r.entity_type in ("CRYPTO_PRIVATE_KEY", "API_KEY_OR_SECRET", "ZONATA_INTERNAL_TOKEN") for r in recs)

        if has_secrets:
            # Class 2 Transform: scrub credentials before storing in memory
            operators = {
                "CRYPTO_PRIVATE_KEY": {"type": "redact"},
                "API_KEY_OR_SECRET": {"type": "replace", "new_value": "<REDACTED_MEMORY_SECRET>"},
                "ZONATA_INTERNAL_TOKEN": {"type": "replace", "new_value": "<REDACTED_MEMORY_TOKEN>"}
            }
            anon = presidio_anonymizer.anonymize(val_str, recs, operators=operators)
            logger.info(f"[MEMORY DLP] Scrubbed {anon.items_count} secrets before storing in {tier_name} key '{key}'.")
            return True, anon.text, None

        return True, value, None


# Global singleton
ai_dlp_gateway = AutonomousAIDLPGateway()
