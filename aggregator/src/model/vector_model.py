"""
Lightweight vector model adapter for aggregator fallback mode.

Used only when AGGREGATOR_ALLOW_ZERO_BASE_MODEL=1 is explicitly enabled.
"""

from typing import List, Optional


class VectorModel:
    """
    Minimal model interface compatible with apply_update/evaluate/artifact.
    """

    def __init__(self, weights: List[float], static_accuracy: Optional[float] = None):
        self._weights = [float(w) for w in weights]
        self._static_accuracy = static_accuracy

    def get_weights(self) -> List[float]:
        return list(self._weights)

    def set_weights(self, weights: List[float]):
        self._weights = [float(w) for w in weights]

    def evaluate(self) -> float:
        if self._static_accuracy is None:
            raise RuntimeError(
                "No runtime evaluator available for VectorModel. "
                "Set AGGREGATOR_STATIC_ACCURACY (0.0-1.0) when using "
                "AGGREGATOR_ALLOW_ZERO_BASE_MODEL=1."
            )
        return float(self._static_accuracy)

