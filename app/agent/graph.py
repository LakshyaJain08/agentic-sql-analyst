"""LangGraph Workflow definition with state machine, conditional routing, and bounded retries."""

from typing import Literal
from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes import (
    interpret_question_node,
    retrieve_schema_node,
    generate_sql_node,
    validate_sql_node,
    execute_sql_node,
    diagnose_error_node,
    analyze_result_node,
    generate_answer_node,
    handle_exhausted_retries_node
)
from app.config import get_settings


def route_after_interpretation(state: AgentState) -> Literal["retrieve_schema", "end"]:
    """Conditional edge: Branch based on clarification or unsupported status."""
    if state.get("needs_clarification") or state.get("is_unsupported"):
        return "end"
    return "retrieve_schema"


def route_after_validation(state: AgentState) -> Literal["execute_sql", "diagnose_error", "exhausted_retries"]:
    """Conditional edge: Check if SQL validation passed or route to repair."""
    val_status = state.get("status")
    if val_status == "validation_passed":
        return "execute_sql"

    # Validation failed
    retry_count = state.get("retry_count", 0)
    settings = get_settings()
    max_retries = state.get("max_retries", settings.MAX_SQL_RETRIES)

    if retry_count < max_retries:
        return "diagnose_error"
    return "exhausted_retries"


def route_after_execution(state: AgentState) -> Literal["analyze_result", "diagnose_error", "exhausted_retries"]:
    """Conditional edge: Check if query execution succeeded or route to repair."""
    exec_status = state.get("status")
    if exec_status == "execution_success":
        return "analyze_result"

    # Execution failed
    retry_count = state.get("retry_count", 0)
    settings = get_settings()
    max_retries = state.get("max_retries", settings.MAX_SQL_RETRIES)

    if retry_count < max_retries:
        return "diagnose_error"
    return "exhausted_retries"


def build_agent_graph() -> StateGraph:
    """Construct and compile the LangGraph agent state machine."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("interpret_question", interpret_question_node)
    workflow.add_node("retrieve_schema", retrieve_schema_node)
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("validate_sql", validate_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("diagnose_error", diagnose_error_node)
    workflow.add_node("analyze_result", analyze_result_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("exhausted_retries", handle_exhausted_retries_node)

    # Define Graph Entry Point
    workflow.set_entry_point("interpret_question")

    # Edge: interpret_question -> conditional
    workflow.add_conditional_edges(
        "interpret_question",
        route_after_interpretation,
        {
            "retrieve_schema": "retrieve_schema",
            "end": END
        }
    )

    # Edge: retrieve_schema -> generate_sql
    workflow.add_edge("retrieve_schema", "generate_sql")

    # Edge: generate_sql -> validate_sql
    workflow.add_edge("generate_sql", "validate_sql")

    # Edge: validate_sql -> conditional
    workflow.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "execute_sql": "execute_sql",
            "diagnose_error": "diagnose_error",
            "exhausted_retries": "exhausted_retries"
        }
    )

    # Edge: execute_sql -> conditional
    workflow.add_conditional_edges(
        "execute_sql",
        route_after_execution,
        {
            "analyze_result": "analyze_result",
            "diagnose_error": "diagnose_error",
            "exhausted_retries": "exhausted_retries"
        }
    )

    # Edge: diagnose_error -> generate_sql (Retry loop!)
    workflow.add_edge("diagnose_error", "generate_sql")

    # Edge: analyze_result -> generate_answer
    workflow.add_edge("analyze_result", "generate_answer")

    # Edge: generate_answer -> END
    workflow.add_edge("generate_answer", END)

    # Edge: exhausted_retries -> END
    workflow.add_edge("exhausted_retries", END)

    return workflow.compile()


# Singleton compiled graph
agent_app = build_agent_graph()
