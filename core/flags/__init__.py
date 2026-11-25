"""
Feature flags package with OpenFeature compliant provider.
"""

from .openfeature_provider import OpenFeatureProvider, EvaluationContext

__all__ = ["OpenFeatureProvider", "EvaluationContext"]
