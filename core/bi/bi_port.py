"""
BiPort and Model Context Protocol (MCP) Analytics Tool Adapter
==============================================================
Exposes semantic metrics via standardized BiPort and MCP tool contracts.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.bi.semantic_layer import SemanticLayerEngine, SemanticQueryRequest, SemanticQueryResult


class BiPort(ABC):
    """Abstract Port for Business Intelligence and Semantic Analytics."""

    @abstractmethod
    def query_metric(self, tenant_id: str, company_id: str, metric_id: str, underlying_data: Optional[Dict[str, float]] = None) -> SemanticQueryResult:
        pass


class CubeSemanticAdapter(BiPort):
    """Cube Core / MetricFlow semantic engine adapter."""

    def __init__(self, engine: Optional[SemanticLayerEngine] = None):
        self.engine = engine or SemanticLayerEngine()

    def query_metric(self, tenant_id: str, company_id: str, metric_id: str, underlying_data: Optional[Dict[str, float]] = None) -> SemanticQueryResult:
        req = SemanticQueryRequest(tenant_id=tenant_id, company_id=company_id, metric_id=metric_id)
        return self.engine.query_metric(req, underlying_data)

    def mcp_cube_analytics(self, tenant_id: str, company_id: str, metric: str, underlying_data: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """MCP Tool interface for AI agents."""
        res = self.query_metric(tenant_id, company_id, metric, underlying_data)
        return {
            "metric": res.metric_name,
            "value": res.value,
            "unit": res.unit,
            "provenance": res.calculated_via
        }
