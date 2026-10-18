"""Safe database query executor with timeouts, row limits, and error categorization."""

import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, DBAPIError

from app.database.connection import get_engine
from app.config import get_settings


class ExecutionResult(BaseModel):
    """Structured result of query execution."""
    status: str  # "success" or "error"
    columns: List[str] = []
    column_types: List[str] = []
    rows: List[Dict[str, Any]] = []
    row_count: int = 0
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    error_category: Optional[str] = None


def categorize_error(error_str: str) -> str:
    """Categorize raw database errors into actionable error categories for the agent."""
    err_lower = error_str.lower()
    if "no such column" in err_lower or "column" in err_lower and "does not exist" in err_lower:
        return "COLUMN_NOT_FOUND"
    if "no such table" in err_lower or "relation" in err_lower and "does not exist" in err_lower:
        return "TABLE_NOT_FOUND"
    if "syntax error" in err_lower or "near" in err_lower or "parse" in err_lower:
        return "SYNTAX_ERROR"
    if "division by zero" in err_lower or "zero division" in err_lower:
        return "ZERO_DIVISION"
    if "canceling statement due to statement timeout" in err_lower or "timed out" in err_lower:
        return "QUERY_TIMEOUT"
    if "ambiguous" in err_lower:
        return "AMBIGUOUS_COLUMN"
    if "group by" in err_lower or "must appear in the group by clause" in err_lower:
        return "AGGREGATION_GROUP_BY_ERROR"
    return "DATABASE_EXECUTION_ERROR"


def execute_query(sql: str, timeout_seconds: Optional[int] = None) -> ExecutionResult:
    """Execute a sanitized SQL query with safety controls and telemetry."""
    settings = get_settings()
    timeout = timeout_seconds or settings.QUERY_TIMEOUT_SECONDS
    max_rows = settings.MAX_RESULT_ROWS
    engine = get_engine()

    start_time = time.perf_counter()

    try:
        with engine.connect() as conn:
            # Set statement timeout for PostgreSQL connection if applicable
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"SET statement_timeout = {int(timeout * 1000)}"))

            cursor_result = conn.execute(text(sql))
            
            # Fetch column metadata
            columns = list(cursor_result.keys()) if cursor_result.returns_rows else []
            column_types = []
            
            # Fetch up to max_rows + 1 to detect truncation
            rows_data = []
            if cursor_result.returns_rows:
                raw_rows = cursor_result.fetchmany(max_rows + 1)
                for row in raw_rows[:max_rows]:
                    row_dict = {}
                    for col in columns:
                        val = row._mapping[col]
                        # Ensure JSON serializable values (e.g. Decimals, Dates)
                        if hasattr(val, "isoformat"):
                            val = val.isoformat()
                        elif hasattr(val, "is_finite") or type(val).__name__ == "Decimal":
                            val = float(val)
                        row_dict[col] = val
                    rows_data.append(row_dict)

                # Infer simple column types from first row or cursor
                if rows_data:
                    for col in columns:
                        first_val = rows_data[0].get(col)
                        if isinstance(first_val, (int, float)):
                            column_types.append("numeric")
                        elif isinstance(first_val, str) and ("-" in first_val and len(first_val) <= 10):
                            column_types.append("date")
                        else:
                            column_types.append("string")
                else:
                    column_types = ["string"] * len(columns)

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return ExecutionResult(
                status="success",
                columns=columns,
                column_types=column_types,
                rows=rows_data,
                row_count=len(rows_data),
                execution_time_ms=duration_ms
            )

    except (OperationalError, ProgrammingError, DBAPIError) as db_err:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        raw_msg = str(db_err)
        # Clean up database error message to remove internal traces
        clean_msg = raw_msg.split("\n")[0]
        cat = categorize_error(clean_msg)
        return ExecutionResult(
            status="error",
            execution_time_ms=duration_ms,
            error_message=clean_msg,
            error_category=cat
        )
    except Exception as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        cat = categorize_error(str(e))
        return ExecutionResult(
            status="error",
            execution_time_ms=duration_ms,
            error_message=str(e),
            error_category=cat
        )
