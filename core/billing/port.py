"""
Billing Port and Provider Adapters (ADR 0048, Rules 24, 78, 79).
Decouples billing provider from domain logic. All money values in minor integer cents.
"""

import os
import uuid
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BillingPort(ABC):
    """Abstract interface for billing and payment providers."""

    @abstractmethod
    def create_customer(self, tenant_id: str, email: str, company_name: str) -> Dict[str, Any]:
        """Creates or registers a customer with the billing provider."""
        pass

    @abstractmethod
    def create_subscription(self, tenant_id: str, plan_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        """Subscribes tenant to a plan."""
        pass

    @abstractmethod
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancels a subscription."""
        pass

    @abstractmethod
    def report_usage(self, subscription_id: str, metric: str, quantity: int, idempotency_key: str) -> Dict[str, Any]:
        """Reports metered usage event."""
        pass

    @abstractmethod
    def calculate_invoice(self, tenant_id: str, subtotal_cents: int, tax_rate_bps: int = 0) -> Dict[str, Any]:
        """Calculates invoice total in minor units with exact integer math."""
        pass


class SandboxBillingAdapter(BillingPort):
    """
    Deterministic in-memory billing adapter for CI, local development, and sandboxed testing.
    Never interacts with external payment gateways.
    """

    def __init__(self):
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.reported_usage: Dict[str, List[Dict[str, Any]]] = {}
        self.seen_idempotency_keys: set = set()

    def create_customer(self, tenant_id: str, email: str, company_name: str) -> Dict[str, Any]:
        customer_id = f"cus_sandbox_{uuid.uuid4().hex[:12]}"
        record = {
            "customer_id": customer_id,
            "tenant_id": tenant_id,
            "email": email,
            "company_name": company_name,
            "sandbox": True,
            "created_at": time.time(),
        }
        self.customers[tenant_id] = record
        return record

    def create_subscription(self, tenant_id: str, plan_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        sub_id = f"sub_sandbox_{uuid.uuid4().hex[:12]}"
        now = time.time()
        sub = {
            "subscription_id": sub_id,
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "status": "active",
            "current_period_start": now,
            "current_period_end": now + (30 * 86400),
            "cancel_at_period_end": False,
            "sandbox": True,
        }
        self.subscriptions[sub_id] = sub
        return sub

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        if subscription_id not in self.subscriptions:
            raise KeyError(f"Subscription {subscription_id} not found")
        sub = self.subscriptions[subscription_id]
        if at_period_end:
            sub["cancel_at_period_end"] = True
            sub["status"] = "canceling"
        else:
            sub["status"] = "canceled"
            sub["canceled_at"] = time.time()
        return sub

    def report_usage(self, subscription_id: str, metric: str, quantity: int, idempotency_key: str) -> Dict[str, Any]:
        if idempotency_key in self.seen_idempotency_keys:
            return {"status": "deduplicated", "idempotency_key": idempotency_key}

        self.seen_idempotency_keys.add(idempotency_key)
        entry = {
            "subscription_id": subscription_id,
            "metric": metric,
            "quantity": quantity,
            "idempotency_key": idempotency_key,
            "timestamp": time.time(),
        }
        if subscription_id not in self.reported_usage:
            self.reported_usage[subscription_id] = []
        self.reported_usage[subscription_id].append(entry)
        return {"status": "recorded", "idempotency_key": idempotency_key}

    def calculate_invoice(self, tenant_id: str, subtotal_cents: int, tax_rate_bps: int = 0) -> Dict[str, Any]:
        """Tax calculated using basis points (1 bps = 0.01%, 100 bps = 1%). Integer math."""
        tax_cents = (subtotal_cents * tax_rate_bps) // 10000
        total_cents = subtotal_cents + tax_cents
        return {
            "tenant_id": tenant_id,
            "subtotal_cents": subtotal_cents,
            "tax_rate_bps": tax_rate_bps,
            "tax_cents": tax_cents,
            "total_cents": total_cents,
            "currency": "USD",
        }


class PaddleBillingAdapter(BillingPort):
    """
    Paddle Merchant of Record (MoR) Adapter.
    Reports NOT_CONFIGURED when live environment credentials are absent.
    """

    def __init__(self, api_key: Optional[str] = None, vendor_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("PADDLE_API_KEY")
        self.vendor_id = vendor_id or os.getenv("PADDLE_VENDOR_ID")

    def _check_configured(self):
        if not self.api_key or not self.vendor_id:
            raise NotImplementedError("NOT_CONFIGURED: Paddle MoR credentials not set (PADDLE_API_KEY/PADDLE_VENDOR_ID)")

    def create_customer(self, tenant_id: str, email: str, company_name: str) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def create_subscription(self, tenant_id: str, plan_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def report_usage(self, subscription_id: str, metric: str, quantity: int, idempotency_key: str) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def calculate_invoice(self, tenant_id: str, subtotal_cents: int, tax_rate_bps: int = 0) -> Dict[str, Any]:
        self._check_configured()
        return {}


class StripeBillingAdapter(BillingPort):
    """
    Stripe Billing Adapter. Reports NOT_CONFIGURED when credentials are absent.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY")

    def _check_configured(self):
        if not self.api_key:
            raise NotImplementedError("NOT_CONFIGURED: Stripe API credentials not set (STRIPE_SECRET_KEY)")

    def create_customer(self, tenant_id: str, email: str, company_name: str) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def create_subscription(self, tenant_id: str, plan_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def report_usage(self, subscription_id: str, metric: str, quantity: int, idempotency_key: str) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def calculate_invoice(self, tenant_id: str, subtotal_cents: int, tax_rate_bps: int = 0) -> Dict[str, Any]:
        self._check_configured()
        return {}


class LagoBillingAdapter(BillingPort):
    """
    Lago Self-Hosted Adapter. Reports NOT_CONFIGURED when service URL/key is absent.
    """

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url or os.getenv("LAGO_API_URL")
        self.api_key = api_key or os.getenv("LAGO_API_KEY")

    def _check_configured(self):
        if not self.api_url or not self.api_key:
            raise NotImplementedError("NOT_CONFIGURED: Lago billing endpoint credentials not set (LAGO_API_URL/LAGO_API_KEY)")

    def create_customer(self, tenant_id: str, email: str, company_name: str) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def create_subscription(self, tenant_id: str, plan_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def report_usage(self, subscription_id: str, metric: str, quantity: int, idempotency_key: str) -> Dict[str, Any]:
        self._check_configured()
        return {}

    def calculate_invoice(self, tenant_id: str, subtotal_cents: int, tax_rate_bps: int = 0) -> Dict[str, Any]:
        self._check_configured()
        return {}
