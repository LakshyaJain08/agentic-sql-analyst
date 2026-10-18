"""Chart generator and validator using Plotly with strict column validation."""

from typing import List, Dict, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


CHART_PALETTE = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4", "#6366F1"]


def build_chart_specification(
    columns: List[str],
    column_types: List[str],
    rows: List[Dict[str, Any]],
    suggested_type: Optional[str] = None,
    suggested_x: Optional[str] = None,
    suggested_y: Optional[str] = None
) -> Dict[str, Any]:
    """Validate columns and construct an executive-ready chart specification."""
    if not rows or not columns:
        return {
            "type": "empty",
            "message": "No data returned to plot a visualization.",
            "plotly_json": None
        }

    df = pd.DataFrame(rows)

    # Identify numeric and categorical columns
    numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    date_cols = [c for c in columns if any(kw in c.lower() for kw in ["date", "month", "year", "quarter", "day"])]
    cat_cols = [c for c in columns if c not in numeric_cols and c not in date_cols]

    # Rule 1: Single row with single or few aggregate numbers -> KPI Metric
    if len(df) == 1 and numeric_cols:
        primary_metric = numeric_cols[0]
        val = df[primary_metric].iloc[0]
        formatted_val = f"${val:,.2f}" if any(m in primary_metric.lower() for m in ["sales", "revenue", "price", "spend", "cost", "aov", "total", "profit"]) else f"{val:,}"
        return {
            "type": "metric",
            "title": primary_metric.replace("_", " ").title(),
            "value": formatted_val,
            "raw_value": val,
            "plotly_json": None
        }

    # Validate suggested X and Y
    x_col = suggested_x if suggested_x in columns else None
    y_col = suggested_y if suggested_y in columns else None
    chart_type = (suggested_type or "auto").lower()

    # Auto-detection if not provided or invalid
    if not x_col or not y_col:
        if date_cols and numeric_cols:
            x_col = date_cols[0]
            y_col = numeric_cols[0]
            chart_type = "line"
        elif cat_cols and numeric_cols:
            x_col = cat_cols[0]
            y_col = numeric_cols[0]
            chart_type = "bar"
        elif len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            chart_type = "scatter"
        elif numeric_cols:
            x_col = columns[0]
            y_col = numeric_cols[0]
            chart_type = "bar"
        else:
            return {
                "type": "table",
                "message": "Data does not contain numeric fields suitable for charts.",
                "plotly_json": None
            }

    # Ensure y_col is numeric
    if y_col not in numeric_cols:
        if numeric_cols:
            y_col = numeric_cols[0]
        else:
            return {
                "type": "table",
                "message": f"Column '{y_col}' is not numeric and cannot be plotted.",
                "plotly_json": None
            }

    # Cap categories for readability if too many rows
    is_truncated_chart = False
    original_row_count = len(df)
    if chart_type == "bar" and len(df) > 15:
        df = df.sort_values(by=y_col, ascending=False).head(15)
        is_truncated_chart = True

    # Build Plotly Figure
    try:
        title = f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}"
        
        if chart_type == "line" or (date_cols and x_col in date_cols):
            fig = px.line(
                df,
                x=x_col,
                y=y_col,
                markers=True,
                title=title,
                template="plotly_dark",
                color_discrete_sequence=CHART_PALETTE
            )
            chart_type = "line"
        elif chart_type == "scatter":
            fig = px.scatter(
                df,
                x=x_col,
                y=y_col,
                title=title,
                template="plotly_dark",
                color_discrete_sequence=CHART_PALETTE
            )
        else:
            fig = px.bar(
                df,
                x=x_col,
                y=y_col,
                title=title,
                template="plotly_dark",
                color_discrete_sequence=CHART_PALETTE
            )
            chart_type = "bar"

        # Apply executive layout touches
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, -apple-system, sans-serif", size=12, color="#E2E8F0"),
            margin=dict(l=40, r=40, t=50, b=40),
            hovermode="x unified" if chart_type == "line" else "closest"
        )
        fig.update_xaxes(showgrid=True, gridcolor="#334155", zeroline=False)
        fig.update_yaxes(showgrid=True, gridcolor="#334155", zeroline=False)

        note = f"Displaying top 15 of {original_row_count} categories" if is_truncated_chart else None

        return {
            "type": chart_type,
            "x": x_col,
            "y": y_col,
            "title": title,
            "truncation_note": note,
            "plotly_json": fig.to_json()
        }

    except Exception as e:
        return {
            "type": "table",
            "message": f"Could not render chart: {str(e)}",
            "plotly_json": None
        }
