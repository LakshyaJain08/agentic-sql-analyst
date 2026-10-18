"""LangGraph agent node implementations for the NL-to-SQL data analyst workflow."""

import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.state import AgentState
from app.agent.prompts import (
    INTERPRETATION_PROMPT,
    SQL_GENERATION_PROMPT,
    SQL_REPAIR_PROMPT,
    GROUNDED_ANSWER_PROMPT
)
from app.agent.llm_factory import get_llm
from app.database.schema import get_formatted_schema_context
from app.security.sql_validator import validate_and_sanitize_sql
from app.database.executor import execute_query, categorize_error
from app.analytics.chart_builder import build_chart_specification
from app.analytics.metrics import compute_summary_statistics
from app.config import get_settings


def parse_json_from_llm(text: str) -> Dict[str, Any]:
    """Extract and parse JSON object from LLM response cleanly."""
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        # Remove first and last line if markdown fence
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean = "\n".join(lines).strip()

    try:
        return json.loads(clean)
    except Exception:
        # Fallback regex search for JSON block
        import re
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {}


def interpret_question_node(state: AgentState) -> Dict[str, Any]:
    """Node: Interpret user intent, metrics, filters, and check for ambiguity or unsupported requests."""
    question = state.get("question", "")
    llm = get_llm()

    messages = [
        SystemMessage(content=INTERPRETATION_PROMPT),
        HumanMessage(content=f"User Question: {question}")
    ]

    response = llm.invoke(messages)
    parsed = parse_json_from_llm(response.content)

    status = parsed.get("status", "ready")
    clarification_q = parsed.get("clarification_question")
    unsupported_reason = parsed.get("unsupported_reason")

    audit_entry = {
        "step": "interpret_question",
        "status": status,
        "intent": parsed.get("intent", "Analysis request")
    }

    if status == "clarification_required":
        return {
            "status": "clarification_required",
            "needs_clarification": True,
            "clarification_question": clarification_q or "Could you clarify which metric or date range you would like to examine?",
            "final_answer": f"**Clarification Needed**: {clarification_q}",
            "audit_trail": state.get("audit_trail", []) + [audit_entry]
        }
    elif status == "unsupported":
        return {
            "status": "unsupported",
            "is_unsupported": True,
            "unsupported_reason": unsupported_reason or "This request requires data outside our e-commerce order system.",
            "final_answer": f"**Unsupported Request**: {unsupported_reason}",
            "audit_trail": state.get("audit_trail", []) + [audit_entry]
        }

    return {
        "status": "ready",
        "interpretation": parsed,
        "needs_clarification": False,
        "is_unsupported": False,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


def retrieve_schema_node(state: AgentState) -> Dict[str, Any]:
    """Node: Fetch relevant schema, relationships, metrics, and business rules."""
    context = get_formatted_schema_context()
    audit_entry = {
        "step": "retrieve_schema",
        "tables_provided": ["customers", "orders", "order_items", "products"]
    }
    return {
        "schema_context": context,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


def generate_sql_node(state: AgentState) -> Dict[str, Any]:
    """Node: Generate or repair candidate SQL query."""
    question = state.get("question", "")
    schema_context = state.get("schema_context", "")
    repair_feedback = state.get("repair_feedback")
    failed_sql = state.get("candidate_sql")
    error_cat = state.get("error_category")
    llm = get_llm()

    if repair_feedback and failed_sql:
        # We are in a repair cycle!
        prompt = SQL_REPAIR_PROMPT.format(
            question=question,
            failed_sql=failed_sql,
            error_category=error_cat or "EXECUTION_ERROR",
            error_message=repair_feedback,
            schema_context=schema_context
        )
    else:
        # Initial generation
        prompt = SQL_GENERATION_PROMPT.format(
            schema_context=schema_context
        )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Business Question: {question}")
    ]

    response = llm.invoke(messages)
    parsed = parse_json_from_llm(response.content)

    sql = parsed.get("sql")
    assumptions = parsed.get("assumptions", [])
    suggested_chart = {
        "type": parsed.get("chart_type", "bar"),
        "x": parsed.get("chart_x"),
        "y": parsed.get("chart_y")
    }

    audit_entry = {
        "step": "generate_sql",
        "is_repair": bool(repair_feedback),
        "generated_sql": sql
    }

    return {
        "candidate_sql": sql,
        "assumptions": assumptions,
        "suggested_chart": suggested_chart,
        # Reset repair feedback once new SQL is generated
        "repair_feedback": None,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


def validate_sql_node(state: AgentState) -> Dict[str, Any]:
    """Node: Strictly validate SQL against AST rules, table allowlist, and inject row limits."""
    candidate_sql = state.get("candidate_sql", "")
    settings = get_settings()

    val_result = validate_and_sanitize_sql(
        raw_sql=candidate_sql,
        max_rows=settings.MAX_RESULT_ROWS
    )

    audit_entry = {
        "step": "validate_sql",
        "is_valid": val_result.is_valid,
        "error": val_result.error_message
    }

    if not val_result.is_valid:
        return {
            "validation_result": val_result.model_dump(),
            "status": "validation_failed",
            "error_category": "POLICY_VALIDATION_ERROR",
            "repair_feedback": f"Query rejected by security validator: {val_result.error_message}",
            "audit_trail": state.get("audit_trail", []) + [audit_entry]
        }

    return {
        "candidate_sql": val_result.sanitized_sql,
        "validation_result": val_result.model_dump(),
        "status": "validation_passed",
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


def execute_sql_node(state: AgentState) -> Dict[str, Any]:
    """Node: Safely execute validated query against database with timeout and row limit."""
    candidate_sql = state.get("candidate_sql", "")
    exec_result = execute_query(candidate_sql)

    audit_entry = {
        "step": "execute_sql",
        "status": exec_result.status,
        "execution_time_ms": exec_result.execution_time_ms,
        "row_count": exec_result.row_count,
        "error": exec_result.error_message
    }

    if exec_result.status != "success":
        return {
            "execution_result": exec_result.model_dump(),
            "status": "execution_failed",
            "error_category": exec_result.error_category,
            "repair_feedback": f"Database error: {exec_result.error_message}",
            "audit_trail": state.get("audit_trail", []) + [audit_entry]
        }

    return {
        "execution_result": exec_result.model_dump(),
        "status": "execution_success",
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


def diagnose_error_node(state: AgentState) -> Dict[str, Any]:
    """Node: Categorize failure and increment retry counter."""
    retry_count = state.get("retry_count", 0) + 1
    feedback = state.get("repair_feedback", "Previous query failed.")
    error_cat = state.get("error_category", "UNKNOWN_ERROR")

    audit_entry = {
        "step": "diagnose_error",
        "retry_attempt": retry_count,
        "category": error_cat,
        "feedback": feedback
    }

    return {
        "retry_count": retry_count,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


def analyze_result_node(state: AgentState) -> Dict[str, Any]:
    """Node: Evaluate result structure, validate chart columns, and compute statistics."""
    exec_data = state.get("execution_result", {})
    columns = exec_data.get("columns", [])
    column_types = exec_data.get("column_types", [])
    rows = exec_data.get("rows", [])
    suggested = state.get("suggested_chart", {})

    chart_spec = build_chart_specification(
        columns=columns,
        column_types=column_types,
        rows=rows,
        suggested_type=suggested.get("type"),
        suggested_x=suggested.get("x"),
        suggested_y=suggested.get("y")
    )

    stats = compute_summary_statistics(columns, rows)

    audit_entry = {
        "step": "analyze_result",
        "chart_type": chart_spec.get("type"),
        "row_count": len(rows)
    }

    return {
        "chart_spec": chart_spec,
        "summary_stats": stats,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


def generate_answer_node(state: AgentState) -> Dict[str, Any]:
    """Node: Synthesize an evidence-grounded executive answer based strictly on returned rows."""
    question = state.get("question", "")
    sql = state.get("candidate_sql", "")
    exec_data = state.get("execution_result", {})
    columns = exec_data.get("columns", [])
    rows = exec_data.get("rows", [])
    llm = get_llm()

    prompt = GROUNDED_ANSWER_PROMPT.format(
        question=question,
        sql=sql,
        columns=columns,
        row_count=len(rows),
        rows_json=json.dumps(rows[:25], default=str)  # Send up to 25 sample rows
    )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Explain findings for: {question}")
    ]

    response = llm.invoke(messages)
    answer = response.content

    audit_entry = {
        "step": "generate_answer",
        "grounded": True
    }

    return {
        "final_answer": answer,
        "status": "success",
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


def handle_exhausted_retries_node(state: AgentState) -> Dict[str, Any]:
    """Node: Handle case when all retry attempts fail."""
    err_cat = state.get("error_category", "EXECUTION_ERROR")
    feedback = state.get("repair_feedback", "Unknown error")
    retry_count = state.get("retry_count", 0)

    answer = (
        f"**Query Resolution Unsuccessful**: After {retry_count} attempts, the agent could not safely execute a query for this question.\n\n"
        f"**Reason**: {err_cat} - {feedback}\n\n"
        f"**Recommendation**: Please check your question phrasing or specify more concrete column/category criteria."
    )

    return {
        "status": "error",
        "final_answer": answer,
        "audit_trail": state.get("audit_trail", []) + [{"step": "exhausted_retries", "error": feedback}]
    }
