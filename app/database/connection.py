"""Database connection management and initialization using SQLAlchemy."""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings


_engine: Engine = None
_session_factory = None


def get_engine() -> Engine:
    """Get or create singleton SQLAlchemy engine with optimal connection settings."""
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        db_url = settings.DATABASE_URL

        connect_args = {}
        if db_url.startswith("sqlite"):
            # Enable foreign keys and multithreading in SQLite
            connect_args = {"check_same_thread": False}
            _engine = create_engine(
                db_url,
                connect_args=connect_args,
                echo=False
            )
            # Enforce foreign keys in SQLite
            with _engine.connect() as conn:
                conn.execute(text("PRAGMA foreign_keys = ON;"))
        else:
            # PostgreSQL configuration with pooling and statement timeouts
            _engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                connect_args={
                    "options": f"-c statement_timeout={settings.QUERY_TIMEOUT_SECONDS * 1000}"
                } if "psycopg" in db_url else {}
            )

        _session_factory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session scope."""
    get_engine()
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_health() -> dict:
    """Check database connectivity and return diagnostic info."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            dialect = engine.dialect.name
            return {
                "status": "healthy" if result == 1 else "unhealthy",
                "dialect": dialect,
                "url_prefix": engine.url.drivername
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def init_database() -> bool:
    """Initialize database tables using schema definition if not already existing."""
    engine = get_engine()
    schema_sql_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "sql",
        "create_tables.sql"
    )
    
    if os.path.exists(schema_sql_path):
        with open(schema_sql_path, "r", encoding="utf-8") as f:
            sql_statements = f.read()

        # Split statements cleanly for engines that do not execute multi-statements
        with engine.begin() as conn:
            # For SQLite, adjust SERIAL PRIMARY KEY to INTEGER PRIMARY KEY AUTOINCREMENT if needed
            statements = [s.strip() for s in sql_statements.split(";") if s.strip()]
            for stmt in statements:
                # Basic adaptation for SQLite vs Postgres
                if engine.dialect.name == "sqlite":
                    stmt = stmt.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                conn.execute(text(stmt))
        return True
    return False
