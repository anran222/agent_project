"""Memory store delegates persistence to repositories."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from agent_project.app.db.repositories.memory_repo import MemoryRepository


@dataclass
class Message:
    role: str
    content: str


@dataclass
class MemoryItem:
    item_id: int
    mem_type: str
    content: str
    importance: float
    created_at: str


class MemoryStore:
    """Memory store with session scoping."""

    def __init__(self, session_id: str = "default") -> None:
        self.session_id = session_id
        self.repo = MemoryRepository()

    def add_message(self, role: str, content: str) -> None:
        """Persist a message.

        Args:
            role: Message role.
            content: Message text.
        """
        self.repo.add_message(self.session_id, role, content)

    def recent_messages(self, limit: int = 6) -> List[Message]:
        """Return recent messages.

        Args:
            limit: Max number of messages.

        Returns:
            List of messages.
        """
        rows = list(self.repo.recent_messages(self.session_id, limit))
        rows.reverse()
        return [Message(role=row["role"], content=row["content"]) for row in rows]

    def message_count(self) -> int:
        """Return message count for session.

        Returns:
            Message count.
        """
        return self.repo.message_count(self.session_id)

    def insert_memory_item(self, mem_type: str, content: str, importance: float) -> int:
        """Insert a memory item and return its id.

        Args:
            mem_type: Memory type.
            content: Memory content.
            importance: Importance score.

        Returns:
            Memory item id.
        """
        return self.repo.insert_memory_item(self.session_id, mem_type, content, importance)

    def list_memory_items(self) -> List[MemoryItem]:
        """List memory items for session.

        Returns:
            List of memory items.
        """
        rows = self.repo.list_memory_items(self.session_id)
        return [
            MemoryItem(
                item_id=row["id"],
                mem_type=row["mem_type"],
                content=row["content"],
                importance=float(row["importance"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def add_memory_vector(self, item_id: int, vector: List[float], model: str) -> None:
        """Upsert vector for memory item.

        Args:
            item_id: Memory item id.
            vector: Embedding vector.
            model: Embedding model name.
        """
        self.repo.add_memory_vector(item_id, vector, model)

    def list_memory_with_vectors(self) -> List[Tuple[MemoryItem, List[float]]]:
        """List memory items with vectors.

        Returns:
            List of memory items and vectors.
        """
        rows = self.repo.list_memory_with_vectors(self.session_id)
        items: List[Tuple[MemoryItem, List[float]]] = []
        for row in rows:
            item = MemoryItem(
                item_id=row["id"],
                mem_type=row["mem_type"],
                content=row["content"],
                importance=float(row["importance"]),
                created_at=str(row["created_at"]),
            )
            vector = json.loads(row["vector"])
            items.append((item, vector))
        return items

    def set_summary(self, summary: str) -> None:
        """Store a summary.

        Args:
            summary: Summary text.
        """
        self.repo.set_summary(self.session_id, summary)

    def latest_summary(self) -> Optional[str]:
        """Get latest summary.

        Returns:
            Summary text or None.
        """
        return self.repo.latest_summary(self.session_id)

    def upsert_profile(self, data: Dict[str, str]) -> None:
        """Upsert profile data.

        Args:
            data: Profile key-values.
        """
        self.repo.upsert_profile(self.session_id, data)

    def get_profile(self) -> Dict[str, str]:
        """Get profile data.

        Returns:
            Profile key-values.
        """
        return self.repo.get_profile(self.session_id)

    def upsert_task(self, title: str, status: str = "open", notes: str = "") -> None:
        """Upsert task.

        Args:
            title: Task title.
            status: Task status.
            notes: Task notes.
        """
        self.repo.upsert_task(self.session_id, title, status, notes)

    def list_open_tasks(self, limit: int = 5) -> List[Tuple[str, str]]:
        """List open tasks.

        Args:
            limit: Max number of tasks.

        Returns:
            List of (title, notes).
        """
        return self.repo.list_open_tasks(self.session_id, limit)

    def cleanup(self, max_messages: int = 200, max_memory_age_days: int = 30) -> None:
        """Prune old records.

        Args:
            max_messages: Max messages to keep.
            max_memory_age_days: Max age for low-importance memory.
        """
        self.repo.cleanup(self.session_id, max_messages, max_memory_age_days)

    def reset_all(self) -> None:
        """Delete all data for session."""
        self.repo.reset_all(self.session_id)

    def delete_memory_items_like(self, phrase: str) -> None:
        """Delete items matching phrase.

        Args:
            phrase: Phrase to match.
        """
        self.repo.delete_memory_items_like(self.session_id, phrase)
