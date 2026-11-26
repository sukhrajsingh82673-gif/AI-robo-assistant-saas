"""
Department Base Port Specification (ZONATA Step 7 Department Platform)
======================================================================
Defines the standard port interface that every departmental integration,
service adapter, and process pack must implement.
Adheres to:
- Rule 59: Systems of Record are Ports
- Rule 60: Copyleft Systems Stay Separate Network Services
- Rule 62: Reserved Human Decisions
- Rule 66: Department Performance Measurement
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PortHealthStatus(BaseModel):
    status: str = Field(..., description="'healthy', 'degraded', or 'unhealthy'")
    department_id: str
    tenant_id: str
    company_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)
    active_circuit_breakers: List[str] = Field(default_factory=list)


class DepartmentAuditEvent(BaseModel):
    event_id: str
    department_id: str
    tenant_id: str
    company_id: str
    action: str
    principal_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)
    gateway_approved: bool = False
    approval_signature: Optional[str] = None


class DepartmentMetricPoint(BaseModel):
    metric_name: str
    department_id: str
    tenant_id: str
    company_id: str
    value: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: Dict[str, str] = Field(default_factory=dict)


class DepartmentBasePort(ABC):
    """Abstract Base Class for all Department Ports."""

    def __init__(self, department_id: str, tenant_id: str, company_id: str, config: Optional[Dict[str, Any]] = None):
        self.department_id = department_id
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.config = config or {}
        self.audit_log: List[DepartmentAuditEvent] = []
        self.metric_series: List[DepartmentMetricPoint] = []
        self.validate_config(self.config)

    @abstractmethod
    def health_check(self) -> PortHealthStatus:
        """Executes active probes against dependent adapters and databases."""
        pass

    @abstractmethod
    def status(self) -> Dict[str, Any]:
        """Returns the current operational status, queue depths, and sync state."""
        pass

    @abstractmethod
    def config_schema(self) -> Dict[str, Any]:
        """Returns the JSON schema describing required and optional configuration keys."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validates configuration against the port's declared schema."""
        # Derived classes implement or rely on pydantic
        return True

    def audit_tap(self, action: str, principal_id: str, payload: Dict[str, Any],
                  gateway_approved: bool = False, approval_signature: Optional[str] = None) -> DepartmentAuditEvent:
        """Emits an immutable structured audit event to the department audit stream."""
        import uuid
        event = DepartmentAuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            department_id=self.department_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            action=action,
            principal_id=principal_id,
            payload=payload,
            gateway_approved=gateway_approved,
            approval_signature=approval_signature
        )
        self.audit_log.append(event)
        return event

    def metric_tap(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> DepartmentMetricPoint:
        """Emits a structured KPI metric measurement to the analytical bus."""
        point = DepartmentMetricPoint(
            metric_name=metric_name,
            department_id=self.department_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            value=value,
            tags=tags or {}
        )
        self.metric_series.append(point)
        return point
