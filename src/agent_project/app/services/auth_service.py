"""Auth service with MySQL for users and Redis for sessions."""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

import redis

from agent_project.app.core.config import settings
from agent_project.app.db.repositories.auth_repo import AuthRepository


@dataclass
class User:
    user_id: int
    phone: str


def validate_phone(phone: str) -> bool:
    """Return True if phone is 10-15 digits.

    Args:
        phone: Phone number string.

    Returns:
        True if valid.
    """
    return bool(re.fullmatch(r"\d{10,15}", phone))


def validate_password(password: str) -> bool:
    """Return True for a strong password (>=8, letters+digits).

    Args:
        password: Password string.

    Returns:
        True if strong enough.
    """
    if len(password) < 8:
        return False
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return has_letter and has_digit


class AuthStore:
    """Auth logic backed by MySQL and Redis."""

    def __init__(self) -> None:
        self.redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            decode_responses=True,
        )
        self.repo = AuthRepository()

    def _hash_password(self, password: str, salt: str) -> str:
        """Hash a password with PBKDF2.

        Args:
            password: Raw password.
            salt: Per-user salt.

        Returns:
            Hex digest.
        """
        data = (salt + password).encode("utf-8")
        return hashlib.pbkdf2_hmac("sha256", data, salt.encode("utf-8"), 100_000).hex()

    def create_user(self, phone: str, password: str) -> User:
        """Create a user and return User.

        Args:
            phone: Phone number.
            password: Raw password.

        Returns:
            User object.
        """
        salt = secrets.token_hex(16)
        pwd_hash = self._hash_password(password, salt)
        user_id = self.repo.create_user(phone, pwd_hash, salt)
        return User(user_id=int(user_id), phone=phone)

    def verify_user(self, phone: str, password: str) -> Optional[User]:
        """Verify credentials and return User if valid.

        Args:
            phone: Phone number.
            password: Raw password.

        Returns:
            User if valid; otherwise None.
        """
        row = self.repo.get_user_by_phone(phone)
        if not row:
            return None
        if self._hash_password(password, row["salt"]) != row["password_hash"]:
            return None
        return User(user_id=int(row["id"]), phone=str(row["phone"]))

    def user_exists(self, phone: str) -> bool:
        """Return True if user exists.

        Args:
            phone: Phone number.

        Returns:
            True if exists.
        """
        return self.repo.user_exists(phone)

    def _session_key(self, token: str) -> str:
        """Build Redis session key.

        Args:
            token: Session token.

        Returns:
            Redis key.
        """
        return f"sess:{token}"

    def _user_sessions_key(self, user_id: int) -> str:
        """Build Redis key for a user's sessions.

        Args:
            user_id: User id.

        Returns:
            Redis key.
        """
        return f"user_sessions:{user_id}"

    def create_session(self, user_id: int, user_agent: str = "", ip: str = "") -> str:
        """Create a session token and store it in Redis.

        Args:
            user_id: User id.
            user_agent: Client user-agent.
            ip: Client IP.

        Returns:
            Session token.
        """
        token = secrets.token_urlsafe(32)
        ttl_seconds = settings.session_ttl_hours * 3600
        session_value = f"{user_id}|{user_agent}|{ip}"
        self.redis.setex(self._session_key(token), ttl_seconds, session_value)
        self.redis.zadd(self._user_sessions_key(user_id), {token: datetime.utcnow().timestamp()})
        max_sessions = settings.max_sessions
        if max_sessions > 0:
            tokens = self.redis.zrange(self._user_sessions_key(user_id), 0, -max_sessions - 1)
            for t in tokens:
                self.delete_session(t)
        return token

    def get_user_by_token(self, token: str) -> Optional[User]:
        """Resolve session token to User.

        Args:
            token: Session token.

        Returns:
            User if valid; otherwise None.
        """
        if not token:
            return None
        val = self.redis.get(self._session_key(token))
        if not val:
            return None
        user_id = int(val.split("|", 1)[0])
        row = self.repo.get_user_by_id(user_id)
        if not row:
            return None
        return User(user_id=int(row["id"]), phone=str(row["phone"]))

    def delete_session(self, token: str) -> None:
        """Delete a session by token.

        Args:
            token: Session token.
        """
        val = self.redis.get(self._session_key(token))
        if val:
            user_id = int(val.split("|", 1)[0])
            self.redis.zrem(self._user_sessions_key(user_id), token)
        self.redis.delete(self._session_key(token))

    def delete_all_sessions(self, user_id: int) -> None:
        """Delete all sessions for a user.

        Args:
            user_id: User id.
        """
        tokens = self.redis.zrange(self._user_sessions_key(user_id), 0, -1)
        for t in tokens:
            self.redis.delete(self._session_key(t))
        self.redis.delete(self._user_sessions_key(user_id))

    def extend_session(self, token: str) -> None:
        """Extend session TTL.

        Args:
            token: Session token.
        """
        val = self.redis.get(self._session_key(token))
        if not val:
            return
        ttl_seconds = settings.session_ttl_hours * 3600
        self.redis.expire(self._session_key(token), ttl_seconds)

    def can_attempt_login(self, phone: str) -> Tuple[bool, int]:
        """Return whether login is allowed and retry_after seconds.

        Args:
            phone: Phone number.

        Returns:
            Tuple of (allowed, retry_after_seconds).
        """
        key = f"login_fail:{phone}"
        count = self.redis.get(key)
        if not count:
            return True, 0
        count = int(count)
        if count < 5:
            return True, 0
        ttl = self.redis.ttl(key)
        return False, max(ttl, 0)

    def record_failed_login(self, phone: str) -> None:
        """Increment failure counter in Redis.

        Args:
            phone: Phone number.
        """
        key = f"login_fail:{phone}"
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 600)

    def reset_failed_logins(self, phone: str) -> None:
        """Reset failure counter for a phone.

        Args:
            phone: Phone number.
        """
        self.redis.delete(f"login_fail:{phone}")
