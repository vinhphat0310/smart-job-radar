"""Minimal PostgreSQL connectivity check."""

from sqlalchemy import create_engine, text
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
