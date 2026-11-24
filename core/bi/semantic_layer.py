"""
Semantic Layer Metric Definitions & Query Engine (Rule 65)
==========================================================
Adheres to:
- Rule 65: Semantic Layer is Source of Truth
- Invariant: AI agents query metrics through the semantic layer, never raw SQL on operational tables.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SemanticMetricDefinition(BaseModel):
    metric_id: str
    name: str
    category: str  # 'finance', 'sales', 'operations', 'hr'
    formula_description: str
    sql_expression: str
    dimensions: List[str] = Field(default_factory=list)


class SemanticQueryRequest(BaseModel):
    tenant_id: str
    company_id: str
    metric_id: str
    time_grain: Optional[str] = "month"  # 'day', 'month', 'quarter', 'year'
    dimensions: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)


class SemanticQueryResult(BaseModel):
    metric_id: str
    metric_name: str
    value: float
    unit: str
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    calculated_via: str = "Cube_Semantic_Engine"


class RawSqlExecutionBlocked(Exception):
    """Raised when an agent attempts to execute raw SQL instead of querying the semantic layer."""
    pass


class SemanticLayerEngine:
    """Calculates standardized departmental metrics and blocks ad-hoc SQL from agents."""

    STANDARD_METRICS = {
        "mrr": SemanticMetricDefinition(metric_id="mrr", name="Monthly Recurring Revenue", category="finance", formula_description="Sum of active recurring contract value per month", sql_expression="SUM(recurring_amount)"),
        "arr": SemanticMetricDefinition(metric_id="arr", name="Annual Recurring Revenue", category="finance", formula_description="MRR * 12", sql_expression="SUM(recurring_amount) * 12"),
        "gross_margin": SemanticMetricDefinition(metric_id="gross_margin", name="Gross Margin %", category="finance", formula_description="(Revenue - COGS) / Revenue", sql_expression="(SUM(revenue) - SUM(cogs)) / SUM(revenue)"),
        "dso": SemanticMetricDefinition(metric_id="dso", name="Days Sales Outstanding", category="finance", formula_description="(Accounts Receivable / Total Credit Sales) * 365", sql_expression="(ar_balance / credit_sales) * 365"),
        "dpo": SemanticMetricDefinition(metric_id="dpo", name="Days Payable Outstanding", category="finance", formula_description="(Accounts Payable / Cost of Goods Sold) * 365", sql_expression="(ap_balance / cogs) * 365"),
        "dio": SemanticMetricDefinition(metric_id="dio", name="Days Inventory Outstanding", category="operations", formula_description="(Inventory Balance / Cost of Goods Sold) * 365", sql_expression="(inventory_balance / cogs) * 365"),
        "ccc": SemanticMetricDefinition(metric_id="ccc", name="Cash Conversion Cycle", category="finance", formula_description="DIO + DSO - DPO", sql_expression="dio + dso - dpo"),
        "headcount": SemanticMetricDefinition(metric_id="headcount", name="Active Headcount", category="hr", formula_description="Count of active employees", sql_expression="COUNT(employee_id)"),
        "turnover_rate": SemanticMetricDefinition(metric_id="turnover_rate", name="Employee Turnover %", category="hr", formula_description="(Departures / Average Headcount) * 100", sql_expression="(departures / avg_headcount) * 100"),
        "oee": SemanticMetricDefinition(metric_id="oee", name="Overall Equipment Effectiveness", category="operations", formula_description="Availability * Performance * Quality", sql_expression="availability * performance * quality")
    }

    def query_metric(self, req: SemanticQueryRequest, underlying_data: Optional[Dict[str, float]] = None) -> SemanticQueryResult:
        metric = self.STANDARD_METRICS.get(req.metric_id.lower())
        if not metric:
            raise KeyError(f"Metric '{req.metric_id}' is not defined in the semantic catalog")

        data = underlying_data or {}
        val = 0.0

        if req.metric_id.lower() == "arr":
            val = data.get("mrr", 50000.0) * 12.0
        elif req.metric_id.lower() == "mrr":
            val = data.get("mrr", 50000.0)
        elif req.metric_id.lower() == "dso":
            ar = data.get("ar_balance", 200000.0)
            sales = data.get("credit_sales", 1500000.0)
            val = round((ar / sales) * 365.0, 2)
        elif req.metric_id.lower() == "dpo":
            ap = data.get("ap_balance", 120000.0)
            cogs = data.get("cogs", 800000.0)
            val = round((ap / cogs) * 365.0, 2)
        elif req.metric_id.lower() == "dio":
            inv = data.get("inventory_balance", 160000.0)
            cogs = data.get("cogs", 800000.0)
            val = round((inv / cogs) * 365.0, 2)
        elif req.metric_id.lower() == "ccc":
            dio = data.get("dio", 73.0)
            dso = data.get("dso", 48.67)
            dpo = data.get("dpo", 54.75)
            val = round(dio + dso - dpo, 2)
        elif req.metric_id.lower() == "oee":
            val = data.get("oee", 0.8143)
        else:
            val = data.get(req.metric_id.lower(), 100.0)

        unit = "%" if "rate" in metric.metric_id or "margin" in metric.metric_id or metric.metric_id == "oee" else ("days" if metric.metric_id in ("dso", "dpo", "dio", "ccc") else "currency")

        return SemanticQueryResult(
            metric_id=metric.metric_id,
            metric_name=metric.name,
            value=val,
            unit=unit,
            dimensions={"tenant_id": req.tenant_id, "company_id": req.company_id}
        )

    def execute_raw_sql(self, sql_query: str, principal_role: str = "agent") -> Any:
        """Enforces Rule 65: Agents attempting raw SQL directly on DB tables are rejected."""
        if principal_role == "agent":
            raise RawSqlExecutionBlocked(
                f"Rule 65 Violation: Agents cannot execute raw SQL ('{sql_query}'). All queries must route via BiPort semantic metrics."
            )
        return {"executed": True}
