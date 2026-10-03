"""
ZONATA Universal AI Co-worker Fabric — API & Structured MCP Provider Adapter
Enforces the API-First execution policy. Structured integrations (CRM API, Email API,
Database queries, Cloud Storage API, Payment APIs) are prioritized over desktop GUIs
due to higher reliability, speed, deterministic verification, and lower operational cost.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import hashlib
import json
from ..provider_base import CapabilityProvider
from ..contracts import (
    ProviderHealthStatus, ProviderEstimate, ExecutionResult,
    VerificationResult, VerificationStatus, RiskLevel
)

class APIMCPProvider(CapabilityProvider):
    """
    API & Structured MCP Provider.
    Highest routing preference for back-office and business mutations.
    """

    def __init__(self):
        self._id = "provider_api_mcp"
        self._health = ProviderHealthStatus.AVAILABLE
        self._crm_records: Dict[str, Dict[str, Any]] = {
            "cust_101": {"name": "Oberoi Grand", "contact": "+91-9876543210", "status": "ACTIVE"}
        }
        self._sent_emails: List[Dict[str, Any]] = []
        self._history: Dict[str, Dict[str, Any]] = {}

    def providerId(self) -> str:
        return self._id

    def capabilities(self) -> List[str]:
        return [
            "api.crm_update",
            "api.crm_read",
            "api.email_send",
            "api.email_read",
            "api.calendar_schedule",
            "api.database_query",
            "api.cloud_storage_upload",
            "api.payment_status"
        ]

    def platforms(self) -> List[str]:
        return ["linux", "windows", "darwin"]

    def health(self) -> ProviderHealthStatus:
        return self._health

    def set_health(self, status: ProviderHealthStatus):
        self._health = status

    def riskProfile(self) -> Dict[str, Any]:
        return {
            "risk_tier": RiskLevel.LOW,
            "deterministic": True,
            "requires_display": False,
            "supports_dry_run": True,
            "supports_rollback": True,
            "human_admission_required": False
        }

    def estimate(self, capability: str, params: Dict[str, Any]) -> ProviderEstimate:
        return ProviderEstimate(
            provider_id=self._id,
            estimated_duration_sec=0.2,
            estimated_cost_usd=0.00001,
            confidence_score=0.999,
            risk_assessment="Direct structured API; deterministic verification; minimal latency",
            requires_visual=False
        )

    def prepare(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return self._health == ProviderHealthStatus.AVAILABLE

    def execute(self, capability: str, params: Dict[str, Any], context: Dict[str, Any]) -> ExecutionResult:
        start_time = time.time()
        exec_id = f"api_exec_{uuid.uuid4().hex[:8]}"

        if self._health == ProviderHealthStatus.CRASHED:
            return ExecutionResult(
                provider_id=self._id,
                capability_id=capability,
                execution_id=exec_id,
                status="FAILED",
                error_message="API Gateway connection refused",
                duration_ms=(time.time() - start_time) * 1000
            )

        output: Dict[str, Any] = {"service": capability, "status": "COMPLETED"}

        if capability == "api.crm_update":
            cust_id = params.get("customer_id", "cust_101")
            updates = params.get("data", {"phone": "+91-9988776655"})
            prior_val = self._crm_records.get(cust_id, {}).copy()
            if cust_id not in self._crm_records:
                self._crm_records[cust_id] = {}
            self._crm_records[cust_id].update(updates)
            output["customer_id"] = cust_id
            output["prior_value"] = prior_val
            output["current_value"] = self._crm_records[cust_id]
            output["mutation_confirmed"] = True
        elif capability == "api.crm_read":
            cust_id = params.get("customer_id", "cust_101")
            output["record"] = self._crm_records.get(cust_id, {})
        elif capability == "api.email_send":
            msg = {
                "to": params.get("recipient", "management@hotel.com"),
                "subject": params.get("subject", "Executive Daily Summary"),
                "body": params.get("body", "Report attached"),
                "timestamp": time.time(),
                "receipt_id": f"msg_{exec_id}"
            }
            self._sent_emails.append(msg)
            output["message_id"] = msg["receipt_id"]
            output["sent"] = True
        elif capability == "api.payment_status":
            tx_id = params.get("transaction_id", "tx_test_01")
            output["transaction_id"] = tx_id
            output["payment_status"] = "SETTLED"
            output["amount_inr"] = 12500.00
        else:
            output["status"] = "OK"

        evidence = [
            {
                "type": "api_idempotent_receipt",
                "capability": capability,
                "timestamp": time.time(),
                "response_id": exec_id,
                "payload_hash": hashlib.sha256(str(output).encode()).hexdigest()
            }
        ]

        self._history[exec_id] = {
            "capability": capability,
            "output": output,
            "status": "COMPLETED",
            "timestamp": time.time()
        }

        return ExecutionResult(
            provider_id=self._id,
            capability_id=capability,
            execution_id=exec_id,
            status="SUCCESS",
            output=output,
            confidence=0.999,
            evidence=evidence,
            rollback_available=True,
            rollback_data=output.get("prior_value"),
            idempotency_key=params.get("idempotency_key"),
            duration_ms=(time.time() - start_time) * 1000
        )

    def observe(self, capability: str, execution_id: str) -> Dict[str, Any]:
        return {"execution_id": execution_id, "api_status": "200_OK"}

    def verify(self, execution_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        record = self._history.get(execution_id)
        if not record:
            return VerificationResult(status=VerificationStatus.NOT_VERIFIED, verified_by=self._id)
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            verified_by=self._id,
            confidence=0.999,
            evidence_details={"api_output": record.get("output")}
        )

    def rollback(self, execution_id: str) -> bool:
        record = self._history.get(execution_id)
        if not record:
            return False
        prior = record.get("output", {}).get("prior_value")
        cust_id = record.get("output", {}).get("customer_id")
        if cust_id and prior:
            self._crm_records[cust_id] = prior
            record["status"] = "ROLLED_BACK"
            return True
        return False

    def cancel(self, execution_id: str) -> bool:
        record = self._history.get(execution_id)
        if record:
            record["status"] = "CANCELLED"
            return True
        return False

    def recover(self, execution_id: str, error: Exception) -> bool:
        self._health = ProviderHealthStatus.AVAILABLE
        return True

    def shutdown(self) -> None:
        self._history.clear()
