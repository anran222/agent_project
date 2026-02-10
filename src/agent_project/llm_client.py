from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import urllib.request


@dataclass
class LLMConfig:
    provider: str
    model: str
    base_url: str


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @staticmethod
    def from_env() -> "LLMClient":
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        model = os.getenv("LLM_MODEL", "llama3.1")
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        return LLMClient(LLMConfig(provider=provider, model=model, base_url=base_url))

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        if self.config.provider == "ollama":
            return self._ollama_generate(prompt=prompt, system=system)
        if self.config.provider == "mock":
            return self._mock_generate(prompt=prompt, system=system)

        raise ValueError(
            f"Unsupported provider: {self.config.provider}. "
            "Set LLM_PROVIDER=ollama or LLM_PROVIDER=mock."
        )

    def generate_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        raw = self.generate(prompt=prompt, system=system)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Best-effort fallback: extract JSON-like object
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(raw[start : end + 1])
        raise

    def embed(self, text: str) -> List[float]:
        if self.config.provider == "ollama":
            return self._ollama_embed(text=text)
        if self.config.provider == "mock":
            return self._mock_embed(text=text)
        raise ValueError(
            f"Unsupported provider: {self.config.provider}. "
            "Set LLM_PROVIDER=ollama or LLM_PROVIDER=mock."
        )

    def _ollama_generate(self, prompt: str, system: Optional[str]) -> str:
        url = f"{self.config.base_url}/api/generate"
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")

    def _ollama_embed(self, text: str) -> List[float]:
        url = f"{self.config.base_url}/api/embeddings"
        model = os.getenv("LLM_EMBED_MODEL", self.config.model)
        payload = {"model": model, "prompt": text}
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("embedding", [])

    def _mock_generate(self, prompt: str, system: Optional[str]) -> str:
        # Deterministic mock response for learning/testing without a real LLM.
        prefix = "[MOCK]"
        if "{" in prompt and "}" in prompt and "JSON" in prompt.upper():
            return json.dumps({"tool": "none", "args": {}, "reason": "mock"})
        return f"{prefix} {prompt.strip()}"

    def _mock_embed(self, text: str) -> List[float]:
        # Simple stable embedding for tests.
        total = sum(ord(ch) for ch in text) or 1
        return [float((total % 97) + 1), float((total % 53) + 1)]
