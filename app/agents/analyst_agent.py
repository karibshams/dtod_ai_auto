"""Business Analyst AI Agent for Dress 2 Decor."""

from sqlalchemy.orm import Session

from app.agents.base_agent import BaseAgent
from app.agents.tools import ANALYST_TOOLS

ANALYST_SYSTEM_PROMPT = """You are the Business Analyst AI Agent for Dress 2 Decor.
Your responsibilities:
1. Analyze store-wide KPIs, monthly revenue trends, category performance, top products, low-stock alerts, vendor performance (gross sales, commission earned, cancellation rates), top customers, and payment/delivery bottlenecks using your analytics tools.
2. Present clear, executive-ready insights with tables, numbers, and actionable recommendations grounded strictly in tool results.
3. Transparency rule: The database tracks gross revenue and platform commission, NOT product wholesale cost (COGS) or ad spend. Never invent net profit figures—clearly state if cost data is not tracked."""


class AnalystAgent(BaseAgent):
    """Handles marketplace business intelligence, KPIs, and chart-ready insights."""

    def __init__(self):
        super().__init__(
            name="analyst_agent",
            system_prompt=ANALYST_SYSTEM_PROMPT,
            tools=ANALYST_TOOLS,
        )

    async def process(
        self,
        user_message: str,
        db: Session,
        context: dict | None = None,
    ) -> dict:
        result = await super().process(user_message, db, context=context)
        result["chart"] = self._build_chart_spec(result.get("tool_results") or [])
        return result

    def _mock_tool_execution(
        self, message: str, db: Session, context: dict | None
    ) -> list[dict]:
        """Mock-mode keyword routing for business analyst queries."""
        msg = message.lower()
        calls: list[tuple[str, dict]] = []

        if "category" in msg or "categories" in msg:
            calls.append(("get_revenue_by_category", {}))
        if "stock" in msg or "inventory" in msg or "low" in msg:
            calls.append(("get_low_stock_products", {}))
        if "month" in msg or "trend" in msg or "growth" in msg:
            calls.append(("get_revenue_by_month", {}))
        if "vendor" in msg or "commission" in msg or "cancel" in msg:
            calls.append(("get_vendor_performance", {}))
        if "customer" in msg or "buyer" in msg or "city" in msg:
            calls.append(("get_top_customers", {}))
        if "payment" in msg or "delivery" in msg or "carrier" in msg:
            calls.append(("get_payment_delivery_breakdown", {}))
        if "top product" in msg or "best selling" in msg or "best-selling" in msg:
            calls.append(("get_top_products", {}))

        if not calls:
            calls.append(("get_business_summary", {}))

        results = []
        for tool_name, args in calls:
            res = self._tool_executor.execute(tool_name, args, db)
            results.append({"tool": tool_name, "arguments": args, "result": res})
        return results

    @staticmethod
    def _build_chart_spec(tool_results: list[dict]) -> dict | None:
        """Convert analytics tool output into a Chart.js-friendly spec."""
        for tr in reversed(tool_results):
            res = tr.get("result") or {}
            if not res.get("success"):
                continue
            tool = tr.get("tool", "")
            data = res.get("data")
            if not data:
                continue

            if tool == "get_revenue_by_category" and isinstance(data, list):
                return {
                    "type": "bar",
                    "title": "Gross Revenue by Category ($)",
                    "labels": [d["category"] for d in data],
                    "datasetLabel": "Revenue ($)",
                    "values": [d["revenue"] for d in data],
                }
            if tool == "get_revenue_by_month" and isinstance(data, list):
                return {
                    "type": "line",
                    "title": "Monthly Revenue Trend ($)",
                    "labels": [f"{d['year']}-{str(d['month']).zfill(2)}" for d in data],
                    "datasetLabel": "Revenue ($)",
                    "values": [d["revenue"] for d in data],
                }
            if tool == "get_top_products" and isinstance(data, list):
                return {
                    "type": "bar",
                    "title": "Top Products by Revenue ($)",
                    "labels": [d["name"][:22] for d in data],
                    "datasetLabel": "Revenue ($)",
                    "values": [d["total_revenue"] for d in data],
                }
            if tool == "get_vendor_performance" and isinstance(data, list):
                top = data[:10]
                return {
                    "type": "bar",
                    "title": "Top Vendors by Gross Sales ($)",
                    "labels": [d["company"][:20] for d in top],
                    "datasetLabel": "Gross Sales ($)",
                    "values": [d["gross_sales"] for d in top],
                }
            if tool == "get_low_stock_products" and isinstance(data, list):
                top = data[:12]
                return {
                    "type": "bar",
                    "title": "Low-Stock Products (Units Remaining)",
                    "labels": [d["name"][:22] for d in top],
                    "datasetLabel": "Stock",
                    "values": [d["stock"] for d in top],
                }
            if tool == "get_top_customers" and isinstance(data, list):
                return {
                    "type": "bar",
                    "title": "Top Customers by Total Spend ($)",
                    "labels": [d["name"] for d in data],
                    "datasetLabel": "Total Spent ($)",
                    "values": [d["total_spent"] for d in data],
                }
            if tool == "get_payment_delivery_breakdown" and isinstance(data, dict):
                methods = data.get("payments_by_method") or []
                if methods:
                    return {
                        "type": "doughnut",
                        "title": "Payments by Method ($)",
                        "labels": [m["method"] for m in methods],
                        "datasetLabel": "Amount ($)",
                        "values": [m["amount"] for m in methods],
                    }
        return None
