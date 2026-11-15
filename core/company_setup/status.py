"""Company lifecycle statuses and the server-enforced transition table."""

from __future__ import annotations

from typing import Dict, Iterable, Set


class CompanyStatus:
    DRAFT = "DRAFT"
    CREATING = "CREATING"
    ONBOARDING = "ONBOARDING"
    OPERATIONAL = "OPERATIONAL"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    PENDING_EXPORT = "PENDING_EXPORT"
    PENDING_DELETION = "PENDING_DELETION"
    DELETED = "DELETED"
    # Retained for compatibility with existing records and billing/abuse holds.
    SUSPENDED = "SUSPENDED"

    ALL = (
        DRAFT,
        CREATING,
        ONBOARDING,
        OPERATIONAL,
        NEEDS_ATTENTION,
        PENDING_EXPORT,
        PENDING_DELETION,
        DELETED,
        SUSPENDED,
    )

    # Statuses a company may be submitted into, derived from its type.
    BY_COMPANY_TYPE = {
        "NEW": CREATING,
        "EXISTING": ONBOARDING,
    }

    # Human-readable labels for API/UI. Translated on the client; this is the
    # stable machine key fallback.
    LABELS = {
        DRAFT: "Draft",
        CREATING: "Creating",
        ONBOARDING: "Onboarding",
        OPERATIONAL: "Operational",
        NEEDS_ATTENTION: "Needs attention",
        PENDING_EXPORT: "Pending export",
        PENDING_DELETION: "Pending deletion",
        DELETED: "Deleted",
        SUSPENDED: "Suspended",
    }

    # Legacy value mapping applied on read and by the data migration.
    LEGACY = {"ATTENTION": NEEDS_ATTENTION}


#: Allowed forward transitions. Every mutation of ``companies.status`` must pass
#: through :func:`validate_transition`.
TRANSITIONS: Dict[str, Set[str]] = {
    CompanyStatus.DRAFT: {
        CompanyStatus.CREATING,
        CompanyStatus.ONBOARDING,
        CompanyStatus.PENDING_EXPORT,
        CompanyStatus.DELETED,
    },
    CompanyStatus.CREATING: {
        CompanyStatus.OPERATIONAL,
        CompanyStatus.NEEDS_ATTENTION,
        CompanyStatus.PENDING_EXPORT,
    },
    CompanyStatus.ONBOARDING: {
        CompanyStatus.OPERATIONAL,
        CompanyStatus.NEEDS_ATTENTION,
        CompanyStatus.PENDING_EXPORT,
    },
    CompanyStatus.OPERATIONAL: {
        CompanyStatus.NEEDS_ATTENTION,
        CompanyStatus.SUSPENDED,
        CompanyStatus.PENDING_EXPORT,
    },
    CompanyStatus.NEEDS_ATTENTION: {
        CompanyStatus.OPERATIONAL,
        CompanyStatus.SUSPENDED,
        CompanyStatus.PENDING_EXPORT,
    },
    CompanyStatus.SUSPENDED: {
        CompanyStatus.OPERATIONAL,
        CompanyStatus.NEEDS_ATTENTION,
        CompanyStatus.PENDING_EXPORT,
    },
    CompanyStatus.PENDING_EXPORT: {
        CompanyStatus.PENDING_DELETION,
        CompanyStatus.OPERATIONAL,
        CompanyStatus.NEEDS_ATTENTION,
        CompanyStatus.DRAFT,
        CompanyStatus.CREATING,
        CompanyStatus.ONBOARDING,
        CompanyStatus.SUSPENDED,
    },
    CompanyStatus.PENDING_DELETION: {
        CompanyStatus.DELETED,
        CompanyStatus.OPERATIONAL,
        CompanyStatus.NEEDS_ATTENTION,
        CompanyStatus.DRAFT,
        CompanyStatus.CREATING,
        CompanyStatus.ONBOARDING,
        CompanyStatus.SUSPENDED,
    },
    CompanyStatus.DELETED: set(),
}


class InvalidTransition(Exception):
    """Raised when a status move is not permitted by the transition table."""

    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(f"Transition from {current} to {target} is not allowed")


def normalize_status(status: str) -> str:
    """Map legacy status values onto the canonical vocabulary."""
    value = (status or "").strip().upper()
    return CompanyStatus.LEGACY.get(value, value)


def is_terminal(status: str) -> bool:
    return normalize_status(status) == CompanyStatus.DELETED


def allowed_targets(status: str) -> Set[str]:
    return set(TRANSITIONS.get(normalize_status(status), set()))


def validate_transition(current: str, target: str) -> str:
    """Return the canonical target or raise :class:`InvalidTransition`."""
    current_norm = normalize_status(current)
    target_norm = normalize_status(target)
    if target_norm not in CompanyStatus.ALL:
        raise InvalidTransition(current_norm, target_norm)
    if target_norm == current_norm:
        return current_norm
    if target_norm not in TRANSITIONS.get(current_norm, set()):
        raise InvalidTransition(current_norm, target_norm)
    return target_norm


def statuses_from(values: Iterable[str]) -> Set[str]:
    return {normalize_status(v) for v in values}
