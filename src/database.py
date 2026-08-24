"""Minimal PostgreSQL connectivity check."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError


class DatabaseConnectionError(RuntimeError):
    """Raised when PostgreSQL cannot be reached safely."""


def check_connection(database_url: str) -> None:
    """Connect to PostgreSQL and execute a harmless query."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    try:
        with create_engine(database_url).connect() as connection:
            connection.execute(text("SELECT 1"))
    except (ModuleNotFoundError, SQLAlchemyError, ValueError) as error:
        raise DatabaseConnectionError("Could not connect to PostgreSQL. Check DATABASE_URL and Neon access.") from error


def check_schema(database_url: str) -> None:
    """Verify initial Alembic schema exists without changing the database."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    required_tables = {
        "sources", "jobs", "job_occurrences", "search_profiles", "scores",
        "notifications", "runs", "source_runs", "job_status_history",
    }
    try:
        with create_engine(database_url).connect() as connection:
            missing_tables = required_tables - set(inspect(connection).get_table_names())
        if missing_tables:
            raise DatabaseConnectionError("Schema incomplete. Run Alembic migrations before retrying.")
    except DatabaseConnectionError:
        raise
    except (ModuleNotFoundError, SQLAlchemyError, ValueError) as error:
        raise DatabaseConnectionError("Could not verify PostgreSQL schema. Check DATABASE_URL and Neon access.") from error
