"""Explicit failure types for the governed document backbone.

These errors keep the Truth Rule enforceable at the document boundary: an
operation must never report success (or pretend content was encrypted or
deleted) when the underlying port could not honour it.
"""


class DocumentBackboneError(RuntimeError):
    """Base class for governed document backbone failures."""


class EncryptionUnavailableError(DocumentBackboneError):
    """Raised when envelope encryption cannot be performed by the KMS port."""


class StorageDeletionFailedError(DocumentBackboneError):
    """Raised when a storage backend fails to delete a ciphertext object."""
