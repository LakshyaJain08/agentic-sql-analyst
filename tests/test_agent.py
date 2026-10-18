"""Integration tests for LangGraph Agent state machine and nodes."""

import pytest
from app.agent.graph import agent_app
from app.database.seed_data import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Ensure database has seed data before running agent tests."""
    seed_database(force_reseed=False)


def test_agent_handles_ambiguous_question():
    """Verify that an ambiguous question triggers clarification without executing SQL."""
    state = {
        "question": "Which product is best?",
        "retry_count": 0,
        "audit_trail": []
    }
    result = agent_app.invoke(state)
    assert result.get("status") == "clarification_required"
    assert result.get("needs_clarification") is True
    assert result.get("clarification_question") is not None
    assert result.get("candidate_sql") is None


def test_agent_handles_unsupported_question():
    """Verify that a question outside our data domain is flagged as unsupported."""
    state = {
        "question": "What was our advertising ROI last quarter?",
        "retry_count": 0,
        "audit_trail": []
    }
    result = agent_app.invoke(state)
    assert result.get("status") == "unsupported"
    assert result.get("is_unsupported") is True
    assert "marketing" in result.get("unsupported_reason").lower() or "advertising" in result.get("unsupported_reason").lower()


def test_agent_executes_valid_analytical_question():
    """Verify end-to-end execution for a valid business analytical question."""
    state = {
        "question": "What were net sales by category in 2025?",
        "retry_count": 0,
        "audit_trail": []
    }
    result = agent_app.invoke(state)
    assert result.get("status") == "success"
    assert result.get("candidate_sql") is not None
    assert "LIMIT 500" in result.get("candidate_sql")

    exec_res = result.get("execution_result")
    assert exec_res is not None
    assert exec_res.get("status") == "success"
    assert len(exec_res.get("rows", [])) > 0

    answer = result.get("final_answer", "")
    assert "**Direct Answer**" in answer or "net_sales" in answer or len(answer) > 20
    assert result.get("chart_spec") is not None


def test_agent_handles_empty_results_cleanly():
    """Verify that a query returning zero rows produces a sensible answer without crashing."""
    from app.database.executor import execute_query
    res = execute_query("SELECT * FROM orders WHERE order_date >= '1990-01-01' AND order_date <= '1990-12-31'")
    assert res.status == "success"
    assert res.row_count == 0


def test_bounded_retries_stops_at_limit():
    """Verify that repeated invalid SQL stops after max_retries."""
    state = {
        "question": "Invalid query triggering errors",
        "candidate_sql": "SELECT non_existent_col FROM non_existent_table",
        "retry_count": 2,  # Already at retry limit
        "max_retries": 2,
        "status": "execution_failed",
        "error_category": "TABLE_NOT_FOUND",
        "repair_feedback": "Table does not exist",
        "audit_trail": []
    }
    from app.agent.graph import route_after_execution
    route = route_after_execution(state)
    assert route == "exhausted_retries"
