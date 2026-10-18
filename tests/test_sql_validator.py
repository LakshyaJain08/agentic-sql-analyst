"""Unit tests for SQLGlot AST SQL Validator and Security Policies."""

import pytest
from app.security.sql_validator import validate_and_sanitize_sql


def test_valid_select_query_passes():
    """Verify that legitimate SELECT queries pass and have LIMIT injected."""
    sql = "SELECT customer_id, name, city FROM customers WHERE region = 'West'"
    res = validate_and_sanitize_sql(sql, max_rows=500)
    assert res.is_valid is True
    assert res.error_message is None
    assert "LIMIT 500" in res.sanitized_sql.upper()
    assert "customers" in res.tables_used


def test_valid_join_query_passes():
    """Verify that multi-table analytical joins across approved tables pass."""
    sql = """
        SELECT p.category, SUM(oi.quantity * oi.unit_price) AS gross_sales
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.status = 'Completed'
        GROUP BY p.category
    """
    res = validate_and_sanitize_sql(sql)
    assert res.is_valid is True
    assert set(res.tables_used) == {"order_items", "products", "orders"}


def test_mutations_are_strictly_rejected():
    """Verify that all mutating operations (DROP, DELETE, UPDATE, INSERT, ALTER) fail."""
    mutations = [
        "DROP TABLE orders;",
        "DELETE FROM customers WHERE 1=1;",
        "UPDATE products SET cost_price = 0;",
        "INSERT INTO customers (customer_id, name) VALUES (999, 'Hacker');",
        "ALTER TABLE orders DROP COLUMN status;",
        "TRUNCATE TABLE order_items;"
    ]
    for mutation in mutations:
        res = validate_and_sanitize_sql(mutation)
        assert res.is_valid is False
        assert "forbidden" in res.error_message.lower() or "mutating" in res.error_message.lower() or "select" in res.error_message.lower()


def test_multi_statement_queries_rejected():
    """Verify that stacked statements separated by semicolons are rejected."""
    stacked = "SELECT * FROM orders; DROP TABLE customers;"
    res = validate_and_sanitize_sql(stacked)
    assert res.is_valid is False
    assert "multi-statement" in res.error_message.lower() or "multiple" in res.error_message.lower()


def test_unapproved_tables_rejected():
    """Verify that tables outside the allowlist are blocked."""
    unapproved = "SELECT * FROM secret_payroll_data"
    res = validate_and_sanitize_sql(unapproved)
    assert res.is_valid is False
    assert "not in the approved table allowlist" in res.error_message.lower()


def test_system_catalogs_rejected():
    """Verify that access to system tables (pg_catalog, sqlite_master) is blocked."""
    probes = [
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM sqlite_master",
        "SELECT * FROM information_schema.tables"
    ]
    for probe in probes:
        res = validate_and_sanitize_sql(probe)
        assert res.is_valid is False
        assert "forbidden" in res.error_message.lower() or "not in the approved" in res.error_message.lower()


def test_dangerous_functions_rejected():
    """Verify that forbidden built-in functions (pg_sleep, load_extension) are rejected."""
    dangerous = "SELECT pg_sleep(5)"
    res = validate_and_sanitize_sql(dangerous)
    assert res.is_valid is False
    assert "restricted function" in res.error_message.lower()


def test_oversized_limit_is_capped():
    """Verify that a LIMIT higher than max_rows is automatically capped."""
    sql = "SELECT * FROM orders LIMIT 10000"
    res = validate_and_sanitize_sql(sql, max_rows=500)
    assert res.is_valid is True
    assert "LIMIT 500" in res.sanitized_sql.upper()
