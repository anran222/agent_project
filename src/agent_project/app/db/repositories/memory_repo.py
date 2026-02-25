"""Memory repository for MySQL access."""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

import pymysql

from agent_project.app.db.mysql import get_conn


class MemoryRepository:
    """Data access for memory-related tables."""

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Persist a message for a session.

        Args:
            session_id: Session identifier.
            role: Message role.
            content: Message text.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
                    (session_id, role, content),
                )

    def recent_messages(self, session_id: str, limit: int) -> List[dict]:
        """Fetch recent messages for a session.

        Args:
            session_id: Session identifier.
            limit: Max number of messages.

        Returns:
            List of message rows.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "SELECT role, content FROM messages WHERE session_id = %s ORDER BY id DESC LIMIT %s",
                    (session_id, limit),
                )
                return cur.fetchall()

    def message_count(self, session_id: str) -> int:
        """Count messages for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Message count.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM messages WHERE session_id = %s",
                    (session_id,),
                )
                row = cur.fetchone()
        return int(row["cnt"]) if row else 0

    def insert_memory_item(self, session_id: str, mem_type: str, content: str, importance: float) -> int:
        """Insert a memory item and return its id.

        Args:
            session_id: Session identifier.
            mem_type: Memory type.
            content: Memory content.
            importance: Importance score.

        Returns:
            Memory item id.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "INSERT INTO memory_items (session_id, mem_type, content, importance) VALUES (%s, %s, %s, %s)",
                    (session_id, mem_type, content, importance),
                )
                return int(cur.lastrowid)

    def list_memory_items(self, session_id: str) -> List[dict]:
        """Fetch memory items for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of memory rows.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "SELECT id, mem_type, content, importance, created_at FROM memory_items WHERE session_id = %s",
                    (session_id,),
                )
                return cur.fetchall()

    def add_memory_vector(self, item_id: int, vector: List[float], model: str) -> None:
        """Upsert a vector for a memory item.

        Args:
            item_id: Memory item id.
            vector: Embedding vector.
            model: Embedding model name.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO memory_vectors (item_id, vector, model)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE vector=VALUES(vector), model=VALUES(model)
                    """,
                    (item_id, json.dumps(vector), model),
                )

    def list_memory_with_vectors(self, session_id: str) -> List[dict]:
        """Fetch memory items with vectors for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of memory rows with vectors.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT m.id, m.mem_type, m.content, m.importance, m.created_at, v.vector
                    FROM memory_items m
                    JOIN memory_vectors v ON m.id = v.item_id
                    WHERE m.session_id = %s
                    """,
                    (session_id,),
                )
                return cur.fetchall()

    def set_summary(self, session_id: str, summary: str) -> None:
        """Insert a summary record for a session.

        Args:
            session_id: Session identifier.
            summary: Summary text.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "INSERT INTO memory_summary (session_id, summary) VALUES (%s, %s)",
                    (session_id, summary),
                )

    def latest_summary(self, session_id: str) -> Optional[str]:
        """Fetch latest summary for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Summary text or None.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "SELECT summary FROM memory_summary WHERE session_id = %s ORDER BY id DESC LIMIT 1",
                    (session_id,),
                )
                row = cur.fetchone()
        return str(row["summary"]) if row else None

    def upsert_profile(self, session_id: str, data: Dict[str, str]) -> None:
        """Upsert profile key-values for a session.

        Args:
            session_id: Session identifier.
            data: Profile key-value data.
        """
        if not data:
            return
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                for key, value in data.items():
                    cur.execute(
                        """
                        INSERT INTO user_profile (session_id, `key`, value)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE value=VALUES(value)
                        """,
                        (session_id, key, value),
                    )

    def get_profile(self, session_id: str) -> Dict[str, str]:
        """Fetch profile key-values for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Profile key-values.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "SELECT `key`, value FROM user_profile WHERE session_id = %s",
                    (session_id,),
                )
                rows = cur.fetchall()
        return {row["key"]: row["value"] for row in rows}

    def upsert_task(self, session_id: str, title: str, status: str, notes: str) -> None:
        """Upsert a task for a session.

        Args:
            session_id: Session identifier.
            title: Task title.
            status: Task status.
            notes: Task notes.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO tasks (session_id, title, status, notes)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE status=VALUES(status), notes=VALUES(notes)
                    """,
                    (session_id, title, status, notes),
                )

    def list_open_tasks(self, session_id: str, limit: int) -> List[Tuple[str, str]]:
        """List open tasks for a session.

        Args:
            session_id: Session identifier.
            limit: Max number of tasks.

        Returns:
            List of (title, notes).
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT title, notes FROM tasks
                    WHERE session_id = %s AND status = 'open'
                    ORDER BY id DESC LIMIT %s
                    """,
                    (session_id, limit),
                )
                rows = cur.fetchall()
        return [(row["title"], row["notes"] or "") for row in rows]

    def cleanup(self, session_id: str, max_messages: int, max_memory_age_days: int) -> None:
        """Prune old messages and memory items.

        Args:
            session_id: Session identifier.
            max_messages: Max messages to keep.
            max_memory_age_days: Max age for low-importance memory.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    DELETE FROM messages
                    WHERE session_id = %s
                    AND id NOT IN (
                        SELECT id FROM (
                            SELECT id FROM messages WHERE session_id = %s ORDER BY id DESC LIMIT %s
                        ) t
                    )
                    """,
                    (session_id, session_id, max_messages),
                )
                cur.execute(
                    """
                    DELETE FROM memory_items
                    WHERE session_id = %s
                    AND importance < 0.8
                    AND created_at < (NOW() - INTERVAL %s DAY)
                    """,
                    (session_id, max_memory_age_days),
                )

    def reset_all(self, session_id: str) -> None:
        """Delete all data for a session.

        Args:
            session_id: Session identifier.
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
                cur.execute("DELETE FROM memory_items WHERE session_id = %s", (session_id,))
                cur.execute(
                    "DELETE FROM memory_vectors WHERE item_id NOT IN (SELECT id FROM memory_items)"
                )
                cur.execute("DELETE FROM memory_summary WHERE session_id = %s", (session_id,))
                cur.execute("DELETE FROM user_profile WHERE session_id = %s", (session_id,))
                cur.execute("DELETE FROM tasks WHERE session_id = %s", (session_id,))

    def delete_memory_items_like(self, session_id: str, phrase: str) -> None:
        """Delete memory items matching a phrase.

        Args:
            session_id: Session identifier.
            phrase: Phrase to match.
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM memory_items WHERE session_id = %s AND content LIKE %s",
                    (session_id, f"%{phrase}%"),
                )
