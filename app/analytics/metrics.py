"""Statistical summary computation and audit telemetry."""

from typing import List, Dict, Any
import pandas as pd


def compute_summary_statistics(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics for tabular query results."""
    if not rows or not columns:
        return {"row_count": 0, "numeric_summaries": {}}

    df = pd.DataFrame(rows)
    stats = {
        "row_count": len(df),
        "column_count": len(columns),
        "numeric_summaries": {}
    }

    for col in columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            s = df[col].dropna()
            if not s.empty:
                stats["numeric_summaries"][col] = {
                    "total": round(float(s.sum()), 2),
                    "mean": round(float(s.mean()), 2),
                    "min": round(float(s.min()), 2),
                    "max": round(float(s.max()), 2)
                }

    return stats


def estimate_query_cost(prompt_tokens: int, completion_tokens: int, model_name: str = "gemini-1.5-flash") -> float:
    """Estimate approximate LLM cost in USD based on token counts."""
    # Approximate pricing per 1M tokens: Flash ~$0.075 input / $0.30 output
    if "flash" in model_name.lower():
        cost = (prompt_tokens / 1_000_000 * 0.075) + (completion_tokens / 1_000_000 * 0.30)
    elif "gpt-4o" in model_name.lower():
        cost = (prompt_tokens / 1_000_000 * 2.50) + (completion_tokens / 1_000_000 * 10.00)
    else:
        cost = (prompt_tokens / 1_000_000 * 0.15) + (completion_tokens / 1_000_000 * 0.60)
    return round(cost, 6)
