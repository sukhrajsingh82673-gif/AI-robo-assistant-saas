"""
Webhooks signing and SSRF protection conforming to Standard Webhooks spec (ADR 0050, Rule 80).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

from .standard_webhooks import StandardWebhooksSigner, SSRFValidator, WebhookSignatureError

_LEGACY_NAME = "core._legacy_webhooks"
if _LEGACY_NAME not in sys.modules:
    _legacy_path = pathlib.Path(__file__).resolve().parent.parent / "webhooks.py"
    _spec = importlib.util.spec_from_file_location(_LEGACY_NAME, _legacy_path)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Unable to load legacy webhooks module at {_legacy_path}")
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
    "StandardWebhooksSigner",
    "SSRFValidator",
    "WebhookSignatureError",
]
