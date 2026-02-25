"""Auth repository for MySQL access."""

from __future__ import annotations

from typing import Optional

import pymysql

from agent_project.app.db.mysql import get_conn


class AuthRepository:
    """Data access for auth-related tables."""

    def create_user(self, phone: str, password_hash: str, salt: str) -> int:
        """Create a user and return the new user id.

        Args:
            phone: User phone number.
            password_hash: Password hash.
            salt: Password salt.

        Returns:
            The new user id.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "INSERT INTO users (phone, password_hash, salt) VALUES (%s, %s, %s)",
                    (phone, password_hash, salt),
                )
                return int(cur.lastrowid)

    def get_user_by_phone(self, phone: str) -> Optional[dict]:
        """Fetch a user row by phone.

        Args:
            phone: User phone number.

        Returns:
            User row dict or None.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    "SELECT id, phone, password_hash, salt FROM users WHERE phone = %s",
                    (phone,),
                )
                return cur.fetchone()

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Fetch a user row by id.

        Args:
            user_id: User id.

        Returns:
            User row dict or None.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT id, phone FROM users WHERE id = %s", (user_id,))
                return cur.fetchone()

    def user_exists(self, phone: str) -> bool:
        """Return True if a user with phone exists.

        Args:
            phone: User phone number.

        Returns:
            True if exists.
        """
        with get_conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT 1 FROM users WHERE phone = %s", (phone,))
                return cur.fetchone() is not None
