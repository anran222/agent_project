"""init tables

Revision ID: 0001_init_tables
Revises:
Create Date: 2026-02-10
"""

from alembic import op

revision = "0001_init_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with open("/Users/a147735/agent_study/agent_project/sql/schema_mysql.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    for stmt in sql.split(";\n"):
        stmt = stmt.strip()
        if stmt:
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks")
    op.execute("DROP TABLE IF EXISTS user_profile")
    op.execute("DROP TABLE IF EXISTS memory_summary")
    op.execute("DROP TABLE IF EXISTS memory_vectors")
    op.execute("DROP TABLE IF EXISTS memory_items")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS users")
