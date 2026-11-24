"""
ZONATA Evolution Layer Package.
Governed self-improvement, failure intelligence, knowledge store, and intake.

Preserves backward compatibility with legacy core/evolution.py without mutating it (Rule 49).
"""

import os
import importlib.util

# Seamless backward compatibility with legacy core/evolution.py (Step 1-5)
_legacy_path = os.path.join(os.path.dirname(__file__), "..", "evolution.py")
if os.path.exists(_legacy_path):
    _spec = importlib.util.spec_from_file_location("_legacy_evolution", _legacy_path)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        for _attr in dir(_mod):
            if not _attr.startswith("_"):
                globals()[_attr] = getattr(_mod, _attr)
