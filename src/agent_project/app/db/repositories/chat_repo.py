"""Chat repository for session and message persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import pymysql

from agent_project.app.db.mysql import get_conn


class ChatRepository:
    """Data access for chat sessions and messages."""

    def create_session(self, user_id: int, title: str) -> int:
        """Create a chat session.

        Args:
            user_id: User id.
            title: Session title.

        Returns:
            New session id.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO chat_sessions (user_id, title, last_message_preview)
                    VALUES (%s, %s, '')
                    """,
                    (user_id, title),
                )
                return int(cur.lastrowid)

    def list_sessions(self, user_id: int) -> List[dict]:
        """List sessions for a user.

        Args:
            user_id: User id.

        Returns:
            Session rows sorted by update time.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, title, last_message_preview, created_at, updated_at
                    FROM chat_sessions
                    WHERE user_id = %s
                    ORDER BY updated_at DESC, id DESC
                    """,
                    (user_id,),
                )
                return cur.fetchall()

    def get_session(self, user_id: int, session_id: int) -> Optional[dict]:
        """Get a session owned by user.

        Args:
            user_id: User id.
            session_id: Session id.

        Returns:
            Session row or None.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, title, last_message_preview, created_at, updated_at
                    FROM chat_sessions
                    WHERE id = %s AND user_id = %s
                    """,
                    (session_id, user_id),
                )
                return cur.fetchone()

    def rename_session(self, user_id: int, session_id: int, title: str) -> bool:
        """Rename a session.

        Args:
            user_id: User id.
            session_id: Session id.
            title: New title.

        Returns:
            True when session exists and updated.
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                affected = cur.execute(
                    """
                    UPDATE chat_sessions
                    SET title = %s
                    WHERE id = %s AND user_id = %s
                    """,
                    (title, session_id, user_id),
                )
                return affected > 0

    def add_message(self, user_id: int, session_id: int, role: str, content: str) -> int:
        """Insert a chat message.

        Args:
            user_id: User id.
            session_id: Session id.
            role: Message role.
            content: Message content.

        Returns:
            New message id.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO chat_messages (session_id, user_id, role, content)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session_id, user_id, role, content),
                )
                return int(cur.lastrowid)

    def latest_message(self, user_id: int, session_id: int) -> Optional[dict]:
        """Fetch latest message in a session.

        Args:
            user_id: User id.
            session_id: Session id.

        Returns:
            Latest message row or None.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT m.id, m.role, m.content, m.created_at
                    FROM chat_messages m
                    JOIN chat_sessions s ON s.id = m.session_id
                    WHERE m.session_id = %s AND s.user_id = %s
                    ORDER BY m.id DESC
                    LIMIT 1
                    """,
                    (session_id, user_id),
                )
                return cur.fetchone()

    def list_messages(self, user_id: int, session_id: int, limit: int = 200) -> List[dict]:
        """List messages in a session.

        Args:
            user_id: User id.
            session_id: Session id.
            limit: Max messages.

        Returns:
            Message rows in ascending order.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT m.id, m.session_id, m.role, m.content, m.created_at
                    FROM chat_messages m
                    JOIN chat_sessions s ON s.id = m.session_id
                    WHERE m.session_id = %s AND s.user_id = %s
                    ORDER BY m.id DESC
                    LIMIT %s
                    """,
                    (session_id, user_id, limit),
                )
                rows = list(cur.fetchall())
        rows.reverse()
        return rows

    def touch_session(self, user_id: int, session_id: int, preview: str) -> None:
        """Update session last preview and timestamp.

        Args:
            user_id: User id.
            session_id: Session id.
            preview: Latest preview text.
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE chat_sessions
                    SET last_message_preview = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                    """,
                    (preview, session_id, user_id),
                )

    def should_dedupe_user_message(
        self,
        user_id: int,
        session_id: int,
        content: str,
        within_seconds: int = 15,
    ) -> bool:
        """Return whether message should be deduplicated.

        Args:
            user_id: User id.
            session_id: Session id.
            content: Message content.
            within_seconds: Dedup time window.

        Returns:
            True if latest message is same user content within window.
        """
        latest = self.latest_message(user_id, session_id)
        if not latest:
            return False
        if str(latest.get("role")) != "user":
            return False
        if str(latest.get("content") or "") != content:
            return False
        created_at = latest.get("created_at")
        if not created_at:
            return False
        if isinstance(created_at, datetime):
            latest_dt = created_at
        else:
            return False
        if latest_dt.tzinfo is None:
            latest_dt = latest_dt.replace(tzinfo=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        delta = (now_dt - latest_dt).total_seconds()
        return delta <= float(within_seconds)
