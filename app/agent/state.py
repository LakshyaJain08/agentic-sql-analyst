"""State definition for LangGraph Natural Language to SQL Agent."""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph state schema for controlled NL-to-SQL data analyst workflow."""
    # Input & Session
    question: str
    session_id: Optional[str]
    conversation_history: List[Dict[str, Any]]

    # Step 1: Interpretation & Ambiguity
    interpretation: Dict[str, Any]
    status: str  # "ready", "clarification_required", "unsupported", "error", "success"
    needs_clarification: bool
    clarification_question: Optional[str]
    is_unsupported: bool
    unsupported_reason: Optional[str]

    # Step 2: Schema Context
    schema_context: str

    # Step 3: SQL Generation & Planning
    candidate_sql: Optional[str]
    assumptions: List[str]
    suggested_chart: Optional[Dict[str, Any]]

    # Step 4: Validation
    validation_result: Optional[Dict[str, Any]]

    # Step 5: Execution
    execution_result: Optional[Dict[str, Any]]

    # Step 6: Diagnosis & Retries
    error_category: Optional[str]
    repair_feedback: Optional[str]
    retry_count: int
    max_retries: int

    # Step 7: Analysis & Visualization
    chart_spec: Optional[Dict[str, Any]]
    summary_stats: Optional[Dict[str, Any]]

    # Step 8: Evidence-Grounded Answer & Audit
    final_answer: str
    audit_trail: List[Dict[str, Any]]
