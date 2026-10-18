"""FastAPI REST routes for Agentic AI Data Analyst."""

import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.graph import agent_app
from app.database.schema import SCHEMA_DEFINITION, RELATIONSHIPS, METRIC_DEFINITIONS, BUSINESS_RULES
from app.database.connection import check_db_health, get_engine
from app.config import get_settings


router = APIRouter()


class AskRequest(BaseModel):
    """Payload for natural language analytical inquiry or direct SQL execution with question."""
    question: Optional[str] = Field(None, description="Business question or analysis prompt", json_schema_extra={"example": "What were the top 5 product categories by net revenue in 2025?"})
    sql: Optional[str] = Field(None, description="Optional custom user SQL query to execute, visualize, and analyze")
    session_id: Optional[str] = Field(None, description="Optional conversation session ID")
    provider: Optional[str] = Field(None, description="LLM provider: gemini, openai, anthropic, or mock")
    api_key: Optional[str] = Field(None, description="Optional runtime LLM API key override")


class FollowUpRequest(BaseModel):
    """Payload for asking questions on previously returned query data."""
    question: str = Field(..., description="Follow-up question about returned data")
    sql: Optional[str] = Field(None, description="Underlying SQL query")
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []
    provider: Optional[str] = None
    api_key: Optional[str] = None


class AskResponse(BaseModel):
    """Structured response from the agentic data analyst."""
    status: str
    question: str
    answer: str
    sql: Optional[str] = None
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []
    row_count: int = 0
    execution_ms: float = 0.0
    chart: Optional[Dict[str, Any]] = None
    summary_stats: Optional[Dict[str, Any]] = None
    clarification_question: Optional[str] = None
    unsupported_reason: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = []


@router.post("/ask", response_model=AskResponse)
async def ask_question_endpoint(req: AskRequest):
    """Process a natural language business question or execute & analyze user-provided SQL."""
    if not req.question and not req.sql:
        raise HTTPException(status_code=400, detail="Must provide either a question or a SQL query.")

    # Temporarily set environment key if provided in request
    if req.api_key and req.provider:
        if req.provider.lower() == "gemini":
            os.environ["GEMINI_API_KEY"] = req.api_key
        elif req.provider.lower() == "openai":
            os.environ["OPENAI_API_KEY"] = req.api_key

    # Branch 1: User provided a custom SQL query directly!
    if req.sql and req.sql.strip():
        from app.security.sql_validator import validate_and_sanitize_sql
        from app.database.executor import execute_query
        from app.analytics.chart_builder import build_chart_specification
        from app.analytics.metrics import compute_summary_statistics
        from app.agent.prompts import GROUNDED_ANSWER_PROMPT
        from app.agent.llm_factory import get_llm
        from langchain_core.messages import SystemMessage, HumanMessage
        import json

        val_res = validate_and_sanitize_sql(req.sql)
        if not val_res.is_valid:
            return AskResponse(
                status="validation_failed",
                question=req.question or "Custom SQL Query Execution",
                answer=f"**Security Policy Violation**: {val_res.error_message}",
                sql=req.sql,
                audit_trail=[{"step": "validate_user_sql", "error": val_res.error_message}]
            )

        exec_res = execute_query(val_res.sanitized_sql)
        if exec_res.status != "success":
            return AskResponse(
                status="execution_error",
                question=req.question or "Custom SQL Query Execution",
                answer=f"**Database Error ({exec_res.error_category})**: {exec_res.error_message}",
                sql=val_res.sanitized_sql,
                execution_ms=exec_res.execution_time_ms,
                audit_trail=[{"step": "execute_user_sql", "error": exec_res.error_message}]
            )

        # Build Chart & Stats
        chart_spec = build_chart_specification(exec_res.columns, exec_res.column_types, exec_res.rows)
        stats = compute_summary_statistics(exec_res.columns, exec_res.rows)

        # Synthesize Grounded Answer
        user_prompt_q = req.question if req.question else "Analyze the key insights and findings from this query result."
        prompt = GROUNDED_ANSWER_PROMPT.format(
            question=user_prompt_q,
            sql=val_res.sanitized_sql,
            columns=exec_res.columns,
            row_count=exec_res.row_count,
            rows_json=json.dumps(exec_res.rows[:25], default=str)
        )
        llm = get_llm(provider=req.provider, api_key=req.api_key)
        resp = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=user_prompt_q)])

        return AskResponse(
            status="success",
            question=user_prompt_q,
            answer=resp.content,
            sql=val_res.sanitized_sql,
            columns=exec_res.columns,
            rows=exec_res.rows,
            row_count=exec_res.row_count,
            execution_ms=exec_res.execution_time_ms,
            chart=chart_spec,
            summary_stats=stats,
            audit_trail=[
                {"step": "validate_user_sql", "sanitized": True},
                {"step": "execute_user_sql", "time_ms": exec_res.execution_time_ms},
                {"step": "grounded_synthesis"}
            ]
        )

    # Branch 2: Standard Natural Language to SQL workflow
    try:
        initial_state = {
            "question": req.question.strip(),
            "session_id": req.session_id,
            "conversation_history": [],
            "retry_count": 0,
            "audit_trail": []
        }

        # Run stateful LangGraph agent
        final_state = agent_app.invoke(initial_state)

        exec_res = final_state.get("execution_result") or {}
        columns = exec_res.get("columns", [])
        rows = exec_res.get("rows", [])
        exec_ms = exec_res.get("execution_time_ms", 0.0)

        return AskResponse(
            status=final_state.get("status", "success"),
            question=req.question,
            answer=final_state.get("final_answer", "No answer generated."),
            sql=final_state.get("candidate_sql"),
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_ms=exec_ms,
            chart=final_state.get("chart_spec"),
            summary_stats=final_state.get("summary_stats"),
            clarification_question=final_state.get("clarification_question"),
            unsupported_reason=final_state.get("unsupported_reason"),
            audit_trail=final_state.get("audit_trail", [])
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")


@router.post("/follow-up")
async def follow_up_endpoint(req: FollowUpRequest):
    """Answer a follow-up question strictly grounded in existing query results."""
    import json
    from app.agent.prompts import GROUNDED_ANSWER_PROMPT
    from app.agent.llm_factory import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    if not req.rows:
        return {"answer": "No dataset rows available to analyze."}

    prompt = GROUNDED_ANSWER_PROMPT.format(
        question=req.question,
        sql=req.sql or "N/A",
        columns=req.columns,
        row_count=len(req.rows),
        rows_json=json.dumps(req.rows[:30], default=str)
    )

    llm = get_llm(provider=req.provider, api_key=req.api_key)
    res = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"Answer this specific question regarding the data: {req.question}")
    ])
    return {"answer": res.content, "question": req.question}


@router.get("/schema")
async def get_schema_endpoint():
    """Return approved relational schema metadata, relationships, and business metrics."""
    return {
        "tables": SCHEMA_DEFINITION,
        "relationships": RELATIONSHIPS,
        "metrics": METRIC_DEFINITIONS,
        "rules": BUSINESS_RULES
    }


@router.get("/evaluations/summary")
async def get_evaluations_summary():
    """Return latest benchmark summary metrics."""
    from app.evaluation.reference_queries import verify_reference_queries
    ref_report = verify_reference_queries()
    return {
        "reference_suite": {
            "total_queries": ref_report["total"],
            "passed": ref_report["passed"],
            "accuracy_pct": round(ref_report["passed"] / ref_report["total"] * 100.0, 2)
        },
        "target_metrics": {
            "safety_violation_rate": "0.0%",
            "max_retries_allowed": 2,
            "statement_timeout_seconds": 10,
            "max_row_limit": 500
        }
    }
