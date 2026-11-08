"""Typed errors for the Settings V2 service and API.

The HTTP layer maps these to stable status codes.  Error messages never include
secret values.
"""

from __future__ import annotations


class SettingsError(Exception):
    """Base class for settings-domain failures."""

    status_code = 400
    code = "SETTINGS_ERROR"


class NotFoundError(SettingsError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationError(SettingsError):
    status_code = 400
    code = "VALIDATION_ERROR"


class ScopeError(SettingsError):
    status_code = 400
    code = "INVALID_SCOPE"


class PermissionDenied(SettingsError):
    status_code = 403
    code = "PERMISSION_DENIED"


class ConflictError(SettingsError):
    status_code = 409
    code = "VERSION_CONFLICT"


class ApprovalRequired(SettingsError):
    status_code = 202
    code = "APPROVAL_REQUIRED"

    def __init__(self, message: str, approval_id: str):
        super().__init__(message)
        self.approval_id = approval_id


class SecretsUnavailable(SettingsError):
    status_code = 503
    code = "SECRETS_UNAVAILABLE"


class UnsupportedOperation(SettingsError):
    status_code = 400
    code = "UNSUPPORTED_OPERATION"

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint
