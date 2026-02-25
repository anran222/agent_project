"""MySQL connection pool utilities."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine

from agent_project.app.core.config import settings


engine = create_engine(
    f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
    f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}",
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
)


@contextmanager
def get_conn() -> Generator:
    """Yield a pooled raw connection and always close it.

    Returns:
        Generator yielding a raw connection.
    """
    conn = engine.raw_connection()
    try:
        conn.autocommit(True)
        yield conn
    finally:
        conn.close()
