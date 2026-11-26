"""ZONATA Sovereign Core — Enterprise External Adapter Ports.

Implements Law L9: Adapters for the outside world.
Payments, email, CRM, calendar, web search, transcription, storage and models
sit behind abstract ports with a fake provider for tests and a real one per tenant.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str
    amount: float
    currency: str
    status: str  # "SETTLED" | "PENDING" | "FAILED"
    idempotency_key: str
    evidence_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PaymentPort(ABC):
    @abstractmethod
    def process_charge(
        self,
        tenant_id: str,
        company_id: str,
        amount: float,
        currency: str,
        customer_id: str,
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Process an inbound payment transaction."""
        pass

    @abstractmethod
    def process_payout(
        self,
        tenant_id: str,
        company_id: str,
        amount: float,
        currency: str,
        recipient_id: str,
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Process an outbound disbursement/payout."""
        pass


@dataclass
class EmailResult:
    delivered: bool
    message_id: str
    recipient: str
    status: str  # "SENT" | "QUEUED" | "DROPPED"
    error: Optional[str] = None


class EmailPort(ABC):
    @abstractmethod
    def send_email(
        self,
        tenant_id: str,
        company_id: str,
        to_address: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> EmailResult:
        """Deliver transactional or workflow email."""
        pass


@dataclass
class CalendarEvent:
    event_id: str
    title: str
    start_time: float
    end_time: float
    organizer: str
    attendees: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class CalendarPort(ABC):
    @abstractmethod
    def create_event(
        self,
        tenant_id: str,
        company_id: str,
        title: str,
        start_time: float,
        end_time: float,
        organizer: str,
        attendees: List[str]
    ) -> CalendarEvent:
        """Schedule an enterprise calendar event."""
        pass

    @abstractmethod
    def check_conflict(
        self,
        tenant_id: str,
        company_id: str,
        attendees: List[str],
        start_time: float,
        end_time: float
    ) -> List[str]:
        """Check for scheduling conflicts across requested attendees."""
        pass


@dataclass
class CRMContact:
    contact_id: str
    email: str
    name: str
    company_name: str
    status: str
    lifecycle_stage: str
    custom_fields: Dict[str, Any] = field(default_factory=dict)


class CRMPort(ABC):
    @abstractmethod
    def upsert_contact(
        self,
        tenant_id: str,
        company_id: str,
        email: str,
        name: str,
        company_name: str,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> CRMContact:
        """Upsert CRM contact with deduplication."""
        pass

    @abstractmethod
    def get_contact(self, tenant_id: str, email: str) -> Optional[CRMContact]:
        """Retrieve CRM contact by primary email."""
        pass


@dataclass
class StorageObject:
    bucket: str
    key: str
    size_bytes: int
    content_type: str
    sha256_hash: str
    presigned_url: Optional[str] = None


class StoragePort(ABC):
    @abstractmethod
    def upload_object(
        self,
        tenant_id: str,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> StorageObject:
        """Store binary payload into tenant storage bucket."""
        pass

    @abstractmethod
    def download_object(self, tenant_id: str, bucket: str, key: str) -> bytes:
        """Download binary payload from tenant storage bucket."""
        pass
