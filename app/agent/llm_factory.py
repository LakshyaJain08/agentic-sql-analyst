"""Multi-provider LLM Factory with support for Gemini, OpenAI, and Mock deterministic fallback."""

import json
import os
import re
from typing import Optional, Any, List
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage

from app.config import get_settings


class MockDataAnalystLLM(BaseChatModel):
    """Deterministic Mock LLM for offline testing, CI/CD, and zero-cost local evaluation."""

    model_name: str = "mock-analyst-v1"

    @property
    def _llm_type(self) -> str:
        return "mock-data-analyst"

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> Any:
        prompt_text = "\n".join([m.content for m in messages if isinstance(m.content, str)])
        response_text = self._simulate_response(prompt_text)
        from langchain_core.outputs import ChatResult, ChatGeneration
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response_text))])

    def _simulate_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # Extract specific question from prompt
        user_q = ""
        for line in prompt.split("\n"):
            if line.lower().startswith("user question:") or line.lower().startswith("business question:"):
                user_q = line.split(":", 1)[1].strip().lower()
                break
        if not user_q:
            user_q = prompt_lower

        # 1. Ambiguity Detection (Check user's actual question)
        has_metric_or_rank = any(m in user_q for m in ["revenue", "sales", "spend", "margin", "volume", "order count", "cost", "price", "top 10", "top 5", "top 3", "by "])
        is_ambiguous = (
            ("best" in user_q and not has_metric_or_rank)
            or ("top" in user_q and not has_metric_or_rank)
            or "top product performance" in user_q
        )
        if is_ambiguous:
            if "interpretation" in prompt_lower or "analyze whether" in prompt_lower:
                return json.dumps({
                    "status": "clarification_required",
                    "clarification_question": "Should performance be measured by total net sales revenue, total units sold, or highest profit margin? Also, which time period would you like to analyze?",
                    "unsupported_reason": None,
                    "intent": "Identify performance without specified metric",
                    "metrics": ["unspecified"],
                    "filters": []
                })

        # 2. Unsupported Request Detection
        is_unsupported = any(term in user_q for term in ["advertising", "ad spend", "roi", "marketing campaign", "salary", "payroll", "nps", "ticket"])
        if is_unsupported:
            if "interpretation" in prompt_lower or "analyze whether" in prompt_lower:
                return json.dumps({
                    "status": "unsupported",
                    "clarification_question": None,
                    "unsupported_reason": "The database contains customer orders, order items, and product catalog data. Marketing spend, advertising ROI, and customer support tickets are not tracked in this system.",
                    "intent": "Query marketing/ad spend",
                    "metrics": [],
                    "filters": []
                })

        # 3. Interpretation Ready
        if "interpretation" in prompt_lower or "analyze whether" in prompt_lower:
            return json.dumps({
                "status": "ready",
                "clarification_question": None,
                "unsupported_reason": None,
                "intent": "Standard analytical question",
                "metrics": ["net_sales"],
                "filters": []
            })

        # 4. Grounded Answer Synthesis
        if "executive ai data analyst" in prompt_lower or "synthesize an evidence-backed answer" in prompt_lower:
            # Extract returned rows from prompt
            rows_match = re.search(r"Returned Data Rows \(\d+ rows\):\s*(\[.*?\])", prompt, re.DOTALL)
            if rows_match:
                try:
                    rows = json.loads(rows_match.group(1))
                    if not rows:
                        return "**Direct Answer**: No matching records were found in the database for the specified criteria.\n\n**Key Findings**:\n- 0 records met the filter conditions.\n\n**Data Evidence**: The query executed successfully and returned 0 rows."
                    
                    first_row = rows[0]
                    # Check if asking specifically about total / average
                    if "total" in prompt_lower or "average" in prompt_lower or "sum" in prompt_lower:
                        numeric_keys = [k for k, v in first_row.items() if isinstance(v, (int, float))]
                        if numeric_keys:
                            k = numeric_keys[0]
                            vals = [r[k] for r in rows if r.get(k) is not None]
                            total_val = sum(vals)
                            avg_val = total_val / max(1, len(vals))
                            return f"**Direct Answer**: The total sum for `{k}` across all {len(rows)} records is **${total_val:,.2f}**, with an average of **${avg_val:,.2f}** per record.\n\n**Data Evidence**: Calculated across {len(rows)} verified database rows."

                    # Check if asking about lowest / anomalies
                    if "lowest" in prompt_lower or "anomal" in prompt_lower or "bottom" in prompt_lower:
                        numeric_keys = [k for k, v in first_row.items() if isinstance(v, (int, float))]
                        if numeric_keys:
                            k = numeric_keys[0]
                            sorted_rows = sorted(rows, key=lambda r: r.get(k, 0))
                            lowest_row = sorted_rows[0]
                            items_str = ", ".join([f"{k2}: {v2}" for k2, v2 in lowest_row.items()])
                            return f"**Direct Answer**: The lowest performing record in this data set is:\n- {items_str}\n\n**Data Evidence**: Identified from the minimum observed `{k}` value in the query results."

                    lines = [f"**Direct Answer**: Analysis completed across {len(rows)} record(s). Key figure: {list(first_row.items())[0][0]} is {list(first_row.items())[0][1]}."]
                    lines.append("\n**Key Findings**:")
                    for idx, r in enumerate(rows[:5], 1):
                        items_str = ", ".join([f"{k}: {v}" for k, v in r.items()])
                        lines.append(f"- Rank {idx}: {items_str}")
                    lines.append(f"\n**Data Evidence**: Verified across {len(rows)} rows from completed transactions.")
                    return "\n".join(lines)
                except Exception:
                    pass
            return "**Direct Answer**: The query executed successfully against the database.\n\n**Data Evidence**: Findings grounded in transactional records."

        # 5. SQL Generation / Repair
        # Check for Month-over-Month growth
        if "month-over-month" in prompt_lower or "mom" in prompt_lower or "growth" in prompt_lower:
            return json.dumps({
                "status": "ready",
                "sql": """WITH monthly_sales AS (
    SELECT SUBSTR(o.order_date, 1, 7) AS month, SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)) AS net_sales
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'Completed' AND o.order_date >= '2025-01-01' AND o.order_date <= '2025-12-31'
    GROUP BY SUBSTR(o.order_date, 1, 7)
)
SELECT month, ROUND(net_sales, 2) AS current_sales,
       ROUND(LAG(net_sales, 1) OVER (ORDER BY month), 2) AS previous_month_sales,
       ROUND(((net_sales - LAG(net_sales, 1) OVER (ORDER BY month)) / LAG(net_sales, 1) OVER (ORDER BY month)) * 100.0, 2) AS mom_growth_pct
FROM monthly_sales
ORDER BY month ASC;""",
                "assumptions": ["Filtered for Completed orders in 2025", "Computed percentage change from prior calendar month"],
                "clarification_question": None,
                "chart_type": "line",
                "chart_x": "month",
                "chart_y": "mom_growth_pct"
            })

        # Category sales
        if "category" in prompt_lower:
            return json.dumps({
                "status": "ready",
                "sql": """SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.status = 'Completed'
GROUP BY p.category
ORDER BY net_sales DESC;""",
                "assumptions": ["Aggregated completed orders across product categories"],
                "clarification_question": None,
                "chart_type": "bar",
                "chart_x": "category",
                "chart_y": "net_sales"
            })

        # Regional sales
        if "region" in prompt_lower:
            return json.dumps({
                "status": "ready",
                "sql": """SELECT c.region, COUNT(DISTINCT o.order_id) AS order_count, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'Completed'
GROUP BY c.region
ORDER BY net_sales DESC;""",
                "assumptions": ["Grouped by customer region for completed orders"],
                "clarification_question": None,
                "chart_type": "bar",
                "chart_x": "region",
                "chart_y": "net_sales"
            })

        # Top products
        if "product" in prompt_lower:
            return json.dumps({
                "status": "ready",
                "sql": """SELECT p.product_name, p.category, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.status = 'Completed'
GROUP BY p.product_name, p.category
ORDER BY net_sales DESC
LIMIT 10;""",
                "assumptions": ["Ranked top products by net sales"],
                "clarification_question": None,
                "chart_type": "bar",
                "chart_x": "product_name",
                "chart_y": "net_sales"
            })

        # Monthly trend
        if "monthly" in prompt_lower or "trend" in prompt_lower:
            return json.dumps({
                "status": "ready",
                "sql": """SELECT SUBSTR(o.order_date, 1, 7) AS month, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'Completed'
GROUP BY SUBSTR(o.order_date, 1, 7)
ORDER BY month ASC;""",
                "assumptions": ["Aggregated monthly completed order revenue"],
                "clarification_question": None,
                "chart_type": "line",
                "chart_x": "month",
                "chart_y": "net_sales"
            })

        # Default: Net sales overview
        return json.dumps({
            "status": "ready",
            "sql": """SELECT ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales,
       COUNT(DISTINCT o.order_id) AS total_orders,
       COUNT(DISTINCT o.customer_id) AS active_customers
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'Completed';""",
            "assumptions": ["Aggregated overall completed orders revenue, count, and customers"],
            "clarification_question": None,
            "chart_type": "metric",
            "chart_x": None,
            "chart_y": "net_sales"
        })


def get_llm(provider: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None) -> BaseChatModel:
    """Instantiate and return the requested LLM client or fallback to MockLLM if no key."""
    settings = get_settings()
    active_provider = (provider or settings.LLM_PROVIDER).lower()
    active_model = model or settings.LLM_MODEL

    if active_provider == "gemini":
        key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if key and key.strip() and key != "your_gemini_api_key_here":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=active_model,
                    google_api_key=key,
                    temperature=settings.LLM_TEMPERATURE
                )
            except Exception as e:
                print(f"[Warning] Failed to initialize Gemini LLM ({e}), falling back to MockDataAnalystLLM")
        return MockDataAnalystLLM()

    elif active_provider == "openai":
        key = api_key or settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        if key and key.strip() and key != "your_openai_api_key_here":
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=active_model or "gpt-4o-mini",
                    api_key=key,
                    temperature=settings.LLM_TEMPERATURE
                )
            except Exception as e:
                print(f"[Warning] Failed to initialize OpenAI LLM ({e}), falling back to MockDataAnalystLLM")
        return MockDataAnalystLLM()

    return MockDataAnalystLLM()
