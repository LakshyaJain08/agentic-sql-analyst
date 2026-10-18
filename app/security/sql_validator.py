"""SQL Security and Policy Validator using SQLGlot AST analysis.

Enforces defense-in-depth restrictions:
- Read-only queries (SELECT only, no DDL/DML mutations)
- Single statement enforcement (no stacked queries or semicolons)
- Table allowlisting (only approved domain tables or defined CTEs)
- System catalog and dangerous function blocking
- Result row limit enforcement
"""

import re
from typing import List, Optional, Set
from pydantic import BaseModel
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.database.schema import APPROVED_TABLES


class ValidationResult(BaseModel):
    """Result of SQL security validation."""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_sql: Optional[str] = None
    tables_used: List[str] = []


DISALLOWED_EXPRESSION_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Command,
    exp.Grant,
    exp.Revoke,
    exp.Commit,
    exp.Rollback,
    exp.Transaction,
)

DISALLOWED_SYSTEM_SCHEMAS = {
    "pg_catalog",
    "information_schema",
    "sys",
    "sqlite_master",
    "sqlite_temp_master",
    "sqlite_schema",
    "sqlite_sequence"
}

DISALLOWED_FUNCTIONS = {
    "pg_sleep",
    "dblink",
    "dblink_exec",
    "version",
    "current_setting",
    "set_config",
    "load_extension",
    "read_file",
    "write_file",
    "system",
    "benchmark",
    "sleep"
}


def clean_sql_input(raw_sql: str) -> str:
    """Strip markdown code blocks and extraneous formatting from raw LLM output."""
    cleaned = raw_sql.strip()
    if cleaned.startswith("```"):
        # Remove opening ```sql or ```
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
    if cleaned.endswith("```"):
        cleaned = re.sub(r"\n?```$", "", cleaned)
    cleaned = cleaned.strip()
    # Remove trailing semicolon for AST normalization
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    return cleaned


def validate_and_sanitize_sql(
    raw_sql: str,
    dialect: Optional[str] = None,
    max_rows: int = 500,
    allowed_tables: Optional[Set[str]] = None
) -> ValidationResult:
    """Validate a SQL query against security policies and sanitize/inject limits."""
    if not raw_sql or not raw_sql.strip():
        return ValidationResult(
            is_valid=False,
            error_message="Empty SQL query provided."
        )

    # Determine active dialect
    if dialect is None:
        try:
            from app.database.connection import get_engine
            dialect = get_engine().dialect.name
            if dialect == "postgresql":
                dialect = "postgres"
        except Exception:
            dialect = "postgres"

    allowed = allowed_tables if allowed_tables is not None else APPROVED_TABLES
    cleaned_sql = clean_sql_input(raw_sql)

    # 1. Reject multi-statement queries containing unquoted semicolons
    # A simple check prior to parsing prevents stacked statements
    statements_split = [s.strip() for s in cleaned_sql.split(";") if s.strip()]
    if len(statements_split) > 1:
        return ValidationResult(
            is_valid=False,
            error_message="Multi-statement queries are strictly prohibited."
        )

    # 2. Parse SQL using SQLGlot
    try:
        parsed_statements = sqlglot.parse(cleaned_sql, read=dialect)
    except ParseError as e:
        # Fallback to generic dialect if postgres dialect parser encounters slight variation
        try:
            parsed_statements = sqlglot.parse(cleaned_sql)
        except ParseError as inner_e:
            return ValidationResult(
                is_valid=False,
                error_message=f"SQL Syntax Parse Error: {str(inner_e)}"
            )

    if not parsed_statements or parsed_statements[0] is None:
        return ValidationResult(
            is_valid=False,
            error_message="Could not parse SQL query."
        )

    if len(parsed_statements) > 1:
        return ValidationResult(
            is_valid=False,
            error_message="Multiple SQL statements detected."
        )

    ast = parsed_statements[0]

    # 3. Check for disallowed DDL/DML mutations
    for disallowed_type in DISALLOWED_EXPRESSION_TYPES:
        if ast.find(disallowed_type):
            return ValidationResult(
                is_valid=False,
                error_message=f"Mutating SQL operations ({disallowed_type.__name__}) are forbidden. Only read-only SELECT queries are allowed."
            )

    # Must be a Select or Union expression
    if not isinstance(ast, (exp.Select, exp.Union)):
        return ValidationResult(
            is_valid=False,
            error_message="Query root must be a SELECT or UNION statement."
        )

    # 4. Extract CTE (WITH clause) table aliases so they are not treated as unknown tables
    cte_names: Set[str] = set()
    with_clause = ast.find(exp.With)
    if with_clause:
        for cte in with_clause.find_all(exp.CTE):
            alias = cte.alias
            if alias:
                cte_names.add(alias.lower())

    # 5. Validate Tables & Schemas
    tables_found: Set[str] = set()
    for table_expr in ast.find_all(exp.Table):
        table_name = table_expr.name.lower()
        schema_name = table_expr.db.lower() if table_expr.db else None

        # Check system schema access
        if schema_name and schema_name in DISALLOWED_SYSTEM_SCHEMAS:
            return ValidationResult(
                is_valid=False,
                error_message=f"Access to system schema '{schema_name}' is forbidden."
            )
        if table_name in DISALLOWED_SYSTEM_SCHEMAS:
            return ValidationResult(
                is_valid=False,
                error_message=f"Access to system table '{table_name}' is forbidden."
            )

        # If it's a CTE alias, skip allowlist check
        if table_name in cte_names:
            continue

        # Check against approved domain tables
        if table_name not in allowed:
            return ValidationResult(
                is_valid=False,
                error_message=f"Table '{table_name}' is not in the approved table allowlist: {sorted(list(allowed))}."
            )

        tables_found.add(table_name)

    # 6. Validate Functions against forbidden list
    for func in ast.find_all(exp.Anonymous):
        func_name = func.this.lower() if hasattr(func, "this") else ""
        if func_name in DISALLOWED_FUNCTIONS:
            return ValidationResult(
                is_valid=False,
                error_message=f"Use of restricted function '{func_name}' is prohibited."
            )

    for func in ast.find_all(exp.Func):
        func_name = func.sql_name().lower() if hasattr(func, "sql_name") else ""
        if func_name in DISALLOWED_FUNCTIONS:
            return ValidationResult(
                is_valid=False,
                error_message=f"Use of restricted function '{func_name}' is prohibited."
            )

    # 7. Row Limit Enforcement (Cap or inject LIMIT)
    limit_expr = ast.find(exp.Limit)
    if limit_expr:
        try:
            val_expr = limit_expr.expression
            if isinstance(val_expr, exp.Literal):
                current_limit = int(val_expr.this)
                if current_limit > max_rows:
                    limit_expr.set("expression", exp.Literal.number(max_rows))
        except (ValueError, TypeError):
            limit_expr.set("expression", exp.Literal.number(max_rows))
    else:
        # Append limit to outermost select
        ast.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    sanitized_sql = ast.sql(dialect=dialect)

    return ValidationResult(
        is_valid=True,
        sanitized_sql=sanitized_sql,
        tables_used=sorted(list(tables_found))
    )
