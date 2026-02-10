from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agent_project.llm_client import LLMClient


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
    def __init__(self, db_path: Path, session_id: str = "default") -> None:
        self.db_path = db_path
        self.session_id = session_id
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    mem_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_vectors (
                    item_id INTEGER PRIMARY KEY,
                    vector TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(item_id) REFERENCES memory_items(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profile (
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id, key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def add_message(self, role: str, content: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (self.session_id, role, content),
            )
            conn.commit()

    def recent_messages(self, limit: int = 6) -> List[Message]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (self.session_id, limit),
            ).fetchall()
        rows.reverse()
        return [Message(role=row[0], content=row[1]) for row in rows]

    def message_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                (self.session_id,),
            ).fetchone()
        return int(row[0] if row else 0)

    def add_memory_item(self, mem_type: str, content: str, importance: float = 0.5) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memory_items (session_id, mem_type, content, importance) VALUES (?, ?, ?, ?)",
                (self.session_id, mem_type, content, importance),
            )
            conn.commit()

    def list_memory_items(self) -> List[MemoryItem]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, mem_type, content, importance, created_at FROM memory_items WHERE session_id = ?",
                (self.session_id,),
            ).fetchall()
        return [
            MemoryItem(
                item_id=row[0],
                mem_type=row[1],
                content=row[2],
                importance=float(row[3]),
                created_at=row[4],
            )
            for row in rows
        ]

    def add_memory_vector(self, item_id: int, vector: List[float], model: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO memory_vectors (item_id, vector, model)
                VALUES (?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET vector=excluded.vector, model=excluded.model
                """,
                (item_id, json.dumps(vector), model),
            )
            conn.commit()

    def list_memory_with_vectors(self) -> List[Tuple[MemoryItem, List[float]]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT m.id, m.mem_type, m.content, m.importance, m.created_at, v.vector
                FROM memory_items m
                JOIN memory_vectors v ON m.id = v.item_id
                WHERE m.session_id = ?
                """
                ,
                (self.session_id,),
            ).fetchall()
        items: List[Tuple[MemoryItem, List[float]]] = []
        for row in rows:
            item = MemoryItem(
                item_id=row[0],
                mem_type=row[1],
                content=row[2],
                importance=float(row[3]),
                created_at=row[4],
            )
            vector = json.loads(row[5])
            items.append((item, vector))
        return items

    def set_summary(self, summary: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memory_summary (session_id, summary) VALUES (?, ?)",
                (self.session_id, summary),
            )
            conn.commit()

    def latest_summary(self) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT summary FROM memory_summary WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                (self.session_id,),
            ).fetchone()
        return row[0] if row else None

    def upsert_profile(self, data: Dict[str, str]) -> None:
        if not data:
            return
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            for key, value in data.items():
                conn.execute(
                    """
                    INSERT INTO user_profile (session_id, key, value, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(session_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                    """,
                    (self.session_id, key, value, now),
                )
            conn.commit()

    def get_profile(self) -> Dict[str, str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT key, value FROM user_profile WHERE session_id = ?",
                (self.session_id,),
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    def upsert_task(self, title: str, status: str = "open", notes: str = "") -> None:
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id FROM tasks WHERE session_id = ? AND title = ?",
                (self.session_id, title),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE tasks SET status=?, notes=?, updated_at=? WHERE id=?",
                    (status, notes, now, row[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO tasks (session_id, title, status, notes, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (self.session_id, title, status, notes, now),
                )
            conn.commit()

    def list_open_tasks(self, limit: int = 5) -> List[Tuple[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT title, notes FROM tasks WHERE session_id = ? AND status = 'open' ORDER BY id DESC LIMIT ?",
                (self.session_id, limit),
            ).fetchall()
        return [(row[0], row[1] or "") for row in rows]

    def reset_all(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (self.session_id,))
            conn.execute(
                "DELETE FROM memory_items WHERE session_id = ?", (self.session_id,)
            )
            conn.execute(
                "DELETE FROM memory_vectors WHERE item_id NOT IN (SELECT id FROM memory_items)"
            )
            conn.execute(
                "DELETE FROM memory_summary WHERE session_id = ?", (self.session_id,)
            )
            conn.execute(
                "DELETE FROM user_profile WHERE session_id = ?", (self.session_id,)
            )
            conn.execute("DELETE FROM tasks WHERE session_id = ?", (self.session_id,))
            conn.commit()

    def cleanup(self, max_messages: int = 200, max_memory_age_days: int = 30) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM messages
                WHERE id NOT IN (
                    SELECT id FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?
                )
                """,
                (self.session_id, max_messages),
            )
            conn.execute(
                """
                DELETE FROM memory_items
                WHERE id IN (
                    SELECT id FROM memory_items
                    WHERE importance < 0.8
                    AND created_at < datetime('now', ?)
                    AND session_id = ?
                )
                """,
                (f"-{max_memory_age_days} days", self.session_id),
            )
            conn.commit()


def _cosine_vector(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MemoryManager:
    def __init__(
        self,
        store: MemoryStore,
        llm_client: Optional[LLMClient] = None,
        summary_interval: int = 10,
        max_long_term: int = 6,
        max_short_term: int = 8,
    ) -> None:
        self.store = store
        self.llm_client = llm_client
        self.summary_interval = summary_interval
        self.max_long_term = max_long_term
        self.max_short_term = max_short_term

    def write_from_turn(self, user_input: str, assistant_output: str) -> None:
        self.store.add_message("user", user_input)
        self.store.add_message("assistant", assistant_output)

        if self.llm_client:
            extracted = self._llm_extract(user_input, assistant_output)
            self._apply_extracted(extracted)

        if self.store.message_count() % self.summary_interval == 0:
            summary = self._build_summary()
            if summary:
                self.store.set_summary(summary)

        self.store.cleanup()

    def _insert_memory_item(self, mem_type: str, content: str, importance: float) -> int:
        with sqlite3.connect(self.store.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO memory_items (session_id, mem_type, content, importance) VALUES (?, ?, ?, ?)",
                (self.store.session_id, mem_type, content, importance),
            )
            conn.commit()
            return int(cur.lastrowid)

    def _maybe_embed(self, item_id: int, text: str) -> None:
        if not self.llm_client:
            return
        try:
            vector = self.llm_client.embed(text)
        except Exception:
            return
        if not vector:
            return
        model = os.getenv("LLM_EMBED_MODEL", self.llm_client.config.model)
        self.store.add_memory_vector(item_id=item_id, vector=vector, model=model)

    def _build_summary(self) -> str:
        recent = self.store.recent_messages(limit=12)
        if not recent:
            return ""
        if not self.llm_client:
            return ""
        history = "\n".join(f"{m.role}: {m.content}" for m in recent)
        prompt = (
            "Summarize the conversation in Chinese. "
            "Extract user preferences, facts, and ongoing tasks. "
            "Keep it under 120 words.\n\n"
            f"{history}\n\nSummary:"
        )
        return self.llm_client.generate(prompt=prompt, system=None).strip()

    def build_context(self, user_input: str) -> str:
        short_term = self.store.recent_messages(limit=self.max_short_term)
        profile = self.store.get_profile()
        summary = self.store.latest_summary() or ""
        tasks = self.store.list_open_tasks(limit=3)
        long_term = self.retrieve_long_term(user_input)

        sections: List[str] = []
        if profile:
            profile_lines = [f"- {k}: {v}" for k, v in profile.items()]
            sections.append("User Profile:\n" + "\n".join(profile_lines))
        if summary:
            sections.append("Conversation Summary:\n" + summary)
        if tasks:
            task_lines = [f"- {title} {('(' + notes + ')') if notes else ''}" for title, notes in tasks]
            sections.append("Open Tasks:\n" + "\n".join(task_lines))
        if long_term:
            mem_lines = [f"- [{m.mem_type}] {m.content}" for m in long_term]
            sections.append("Long-term Memory:\n" + "\n".join(mem_lines))
        if short_term:
            msg_lines = [f"{m.role}: {m.content}" for m in short_term]
            sections.append("Recent Messages:\n" + "\n".join(msg_lines))

        return "\n\n".join(sections)

    def retrieve_long_term(self, query: str) -> List[MemoryItem]:
        if not self.llm_client:
            return []
        items_with_vecs = self.store.list_memory_with_vectors()
        if not items_with_vecs:
            return []
        q_vec = self.llm_client.embed(query)
        if not q_vec:
            return []
        scored: List[Tuple[MemoryItem, float]] = []
        for item, vec in items_with_vecs:
            sim = _cosine_vector(q_vec, vec)
            score = sim + (item.importance * 0.1)
            scored.append((item, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in scored[: self.max_long_term] if score > 0.2]

    def _llm_extract(self, user_input: str, assistant_output: str) -> Dict[str, object]:
        system = (
            "You extract structured memory from a dialogue turn. "
            "Return ONLY valid JSON with keys: "
            "profile_updates (object), facts (array), preferences (array), "
            "tasks (array of {title, status, notes}), forget (array)."
        )
        prompt = (
            "From the following turn, extract stable user facts, preferences, and tasks.\n"
            "Only include high-confidence items. If nothing, use empty arrays/objects.\n\n"
            f"User: {user_input}\n"
            f"Assistant: {assistant_output}\n\n"
            "JSON only."
        )
        return self.llm_client.generate_json(prompt=prompt, system=system)

    def _apply_extracted(self, extracted: Dict[str, object]) -> None:
        profile_updates = extracted.get("profile_updates", {}) or {}
        if isinstance(profile_updates, dict):
            self.store.upsert_profile(
                {str(k): str(v) for k, v in profile_updates.items() if v}
            )

        facts = extracted.get("facts", []) or []
        if isinstance(facts, list):
            for fact in facts:
                text = str(fact).strip()
                if not text:
                    continue
                item_id = self._insert_memory_item("fact", text, importance=0.7)
                self._maybe_embed(item_id, text)

        prefs = extracted.get("preferences", []) or []
        if isinstance(prefs, list):
            for pref in prefs:
                text = str(pref).strip()
                if not text:
                    continue
                item_id = self._insert_memory_item("preference", text, importance=0.8)
                self._maybe_embed(item_id, text)

        tasks = extracted.get("tasks", []) or []
        if isinstance(tasks, list):
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                title = str(task.get("title", "")).strip()
                status = str(task.get("status", "open")).strip() or "open"
                notes = str(task.get("notes", "")).strip()
                if not title:
                    continue
                self.store.upsert_task(title, status=status, notes=notes)
                item_id = self._insert_memory_item("task", title, importance=0.9)
                self._maybe_embed(item_id, title)

        forget = extracted.get("forget", []) or []
        if isinstance(forget, list) and forget:
            self._forget_items([str(x).strip() for x in forget if str(x).strip()])

    def _forget_items(self, phrases: List[str]) -> None:
        if not phrases:
            return
        with sqlite3.connect(self.store.db_path) as conn:
            for phrase in phrases:
                conn.execute(
                    "DELETE FROM memory_items WHERE content LIKE ?",
                    (f"%{phrase}%",),
                )
            conn.commit()


def build_user_profile_prompt(profile: Dict[str, str]) -> str:
    if not profile:
        return ""
    return json.dumps(profile, ensure_ascii=False)
