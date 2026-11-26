"""
Billing, Metering, Plans, and Cost Caps package (Rule 78 & Rule 79).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

from .port import BillingPort, SandboxBillingAdapter, PaddleBillingAdapter, StripeBillingAdapter, LagoBillingAdapter
from .plans import PlanRegistry, SubscriptionPlan
from .metering import UsageLedger, UsageRecord
from .cost_caps import CostCapManager, SpendAlert
from .lifecycle import BillingLifecycleManager, AccountStatus

_LEGACY_NAME = "core._legacy_billing"
if _LEGACY_NAME not in sys.modules:
    _legacy_path = pathlib.Path(__file__).resolve().parent.parent / "billing.py"
    _spec = importlib.util.spec_from_file_location(_LEGACY_NAME, _legacy_path)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Unable to load legacy billing module at {_legacy_path}")
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_LEGACY_NAME] = _module
    _spec.loader.exec_module(_module)

_legacy = sys.modules[_LEGACY_NAME]
for _name, _value in vars(_legacy).items():
    if not _name.startswith("_"):
        globals()[_name] = _value

__all__ = [
    _name for _name in vars(_legacy) if not _name.startswith("_")
] + [
    "BillingPort",
    "SandboxBillingAdapter",
    "PaddleBillingAdapter",
    "StripeBillingAdapter",
    "LagoBillingAdapter",
    "PlanRegistry",
    "SubscriptionPlan",
    "UsageLedger",
    "UsageRecord",
    "CostCapManager",
    "SpendAlert",
    "BillingLifecycleManager",
    "AccountStatus",
]
