"""
ZONATA Organization Model Enums, Types, and Exceptions (OpenCode Step 2D)
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional


class OrgLevel(str, Enum):
    """Supported hierarchical levels in corporate governance."""
    OWNER = "OWNER"
    CHAIRMAN = "CHAIRMAN"
    BOARD_MEMBER = "BOARD_MEMBER"
    CEO = "CEO"
    C_SUITE = "C_SUITE"
    DIRECTOR = "DIRECTOR"
    MANAGER = "MANAGER"
    SUPERVISOR = "SUPERVISOR"
    TEAM_LEAD = "TEAM_LEAD"
    EMPLOYEE = "EMPLOYEE"
    AGENT = "AGENT"  # Note: agents are tools owned by a position, not positions themselves


class OccupantType(str, Enum):
    """Types of occupants that can fill a position seat."""
    HUMAN = "HUMAN"
    AI_EMPLOYEE = "AI_EMPLOYEE"


class AssignmentStatus(str, Enum):
    """Status lifecycle of a position assignment."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class HandoverStatus(str, Enum):
    """Status of an empirical handover pack."""
    GENERATED = "GENERATED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ARCHIVED = "ARCHIVED"


# -----------------------------------------------------------------------------
# Domain Exceptions
# -----------------------------------------------------------------------------

class OrganizationError(Exception):
    """Base exception for all organization model failures."""
    pass


class SingleCEOViolationError(OrganizationError):
    """Raised when an attempt is made to create a second CEO position or seat."""
    pass


class ReportingCycleError(OrganizationError):
    """Raised when a proposed reporting line introduces a directed cycle in the hierarchy."""
    pass


class AgentHierarchyViolationError(OrganizationError):
    """Raised when an agent attempts to command, manage, or assign an employee."""
    pass


class AIOrganizationSelfEditError(OrganizationError):
    """Raised when an AI occupant attempts to edit its own position, authority, or reporting line (Rule 15)."""
    pass


class VacantPositionError(OrganizationError):
    """Raised when an operation requires an active occupant but the position seat is vacant."""
    pass


class PositionNotFoundError(OrganizationError):
    """Raised when a requested position is not found within the tenant and company scope."""
    pass


class DepartmentNotFoundError(OrganizationError):
    """Raised when a requested department is not found within the tenant and company scope."""
    pass
