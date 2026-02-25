"""Memory manager with retrieval and summarization logic."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from agent_project.app.llm.client import LLMClient
from agent_project.app.memory.store import MemoryStore


@dataclass
class MemoryItem:
    item_id: int
    mem_type: str
    content: str
    importance: float
    created_at: str


def _cosine_vector(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity, or 0.0 when vectors are invalid.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MemoryManager:
    """Memory orchestration: write, summarize, retrieve."""

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
        """Persist a dialogue turn and update memory.

        Args:
            user_input: User message text.
            assistant_output: Assistant reply text.
        """
        self.store.add_message("user", user_input)
        self.store.add_message("assistant", assistant_output)

        if self.llm_client:
            try:
                extracted = self._llm_extract(user_input, assistant_output)
                self._apply_extracted(extracted)
            except Exception:
                # Do not fail chat pipeline when extraction is unstable.
                pass

        if self.store.message_count() % self.summary_interval == 0:
            try:
                summary = self._build_summary()
                if summary:
                    self.store.set_summary(summary)
            except Exception:
                pass

        try:
            self.store.cleanup()
        except Exception:
            pass

    def _insert_memory_item(self, mem_type: str, content: str, importance: float) -> int:
        """Insert a memory item and return its id.

        Args:
            mem_type: Memory type label.
            content: Memory content.
            importance: Importance score.

        Returns:
            Memory item id.
        """
        return self.store.insert_memory_item(mem_type, content, importance)

    def _maybe_embed(self, item_id: int, text: str) -> None:
        """Compute and store embedding for a memory item.

        Args:
            item_id: Memory item id.
            text: Text to embed.
        """
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
        """Create a rolling summary using the LLM.

        Returns:
            Summary string (may be empty).
        """
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
        """Build context from profile, summary, tasks, and memory.

        Args:
            user_input: Current user message.

        Returns:
            Context string for prompting.
        """
        try:
            short_term = self.store.recent_messages(limit=self.max_short_term)
        except Exception:
            short_term = []
        try:
            profile = self.store.get_profile()
        except Exception:
            profile = {}
        try:
            summary = self.store.latest_summary() or ""
        except Exception:
            summary = ""
        try:
            tasks = self.store.list_open_tasks(limit=3)
        except Exception:
            tasks = []
        try:
            long_term = self.retrieve_long_term(user_input)
        except Exception:
            long_term = []

        sections: List[str] = []
        if profile:
            profile_lines = [f"- {k}: {v}" for k, v in profile.items()]
            sections.append("User Profile:\n" + "\n".join(profile_lines))
        if summary:
            sections.append("Conversation Summary:\n" + summary)
        if tasks:
            task_lines = [
                f"- {title} {('(' + notes + ')') if notes else ''}"
                for title, notes in tasks
            ]
            sections.append("Open Tasks:\n" + "\n".join(task_lines))
        if long_term:
            mem_lines = [f"- [{m.mem_type}] {m.content}" for m in long_term]
            sections.append("Long-term Memory:\n" + "\n".join(mem_lines))
        if short_term:
            msg_lines = [f"{m.role}: {m.content}" for m in short_term]
            sections.append("Recent Messages:\n" + "\n".join(msg_lines))

        return "\n\n".join(sections)

    def retrieve_long_term(self, query: str) -> List[MemoryItem]:
        """Retrieve top long-term memories by embedding similarity.

        Args:
            query: Query text.

        Returns:
            List of memory items.
        """
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
        """Extract structured memory from a turn with the LLM.

        Args:
            user_input: User message text.
            assistant_output: Assistant reply text.

        Returns:
            Extracted memory payload.
        """
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
        """Apply extracted memory changes to persistence.

        Args:
            extracted: Structured memory payload.
        """
        profile_updates = extracted.get("profile_updates", {}) or {}
        if isinstance(profile_updates, dict):
            self.store.upsert_profile({str(k): str(v) for k, v in profile_updates.items() if v})

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
            for phrase in [str(x).strip() for x in forget if str(x).strip()]:
                self.store.delete_memory_items_like(phrase)


def build_user_profile_prompt(profile: Dict[str, str]) -> str:
    """Render profile JSON for prompts.

    Args:
        profile: Profile key-values.

    Returns:
        JSON string, or empty when profile is empty.
    """
    if not profile:
        return ""
    return json.dumps(profile, ensure_ascii=False)
