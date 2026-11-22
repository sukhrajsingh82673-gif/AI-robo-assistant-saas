"""
ZONATA Deterministic Spot Check Sampler
OpenCode Step 2H: Deterministic spot-check sampling on task ID hash.
"""

from __future__ import annotations

import hashlib
from typing import Union
from core.verification.types import VerificationLayer


class SpotCheckSampler:
    """
    Evaluates spot check sampling deterministically on task ID hash.
    Ensures identical sampling results across restarts, processes, and test runs.
    """

    @staticmethod
    def is_sampled(task_id: str, layer: Union[VerificationLayer, str], sample_rate: float) -> bool:
        """
        Determines whether a task is sampled for higher verification layer review.
        Deterministic on SHA-256(task_id:spot_check:layer).
        sample_rate: float in range [0.0, 1.0].
        """
        if sample_rate <= 0.0:
            return False
        if sample_rate >= 1.0:
            return True

        layer_str = layer.value if isinstance(layer, VerificationLayer) else str(layer)
        salt = f"{task_id}:spot_check:{layer_str}"
        hash_hex = hashlib.sha256(salt.encode("utf-8")).hexdigest()[:8]
        hash_int = int(hash_hex, 16)
        
        # Scale to 0.0 - 0.9999
        ratio = (hash_int % 10000) / 10000.0
        return ratio < sample_rate
