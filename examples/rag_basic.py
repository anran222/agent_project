from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from agent_project.llm_client import LLMClient


@dataclass
class Doc:
    doc_id: str
    text: str


def tokenize(text: str) -> List[str]:
    tokens = []
    for raw in text.lower().split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if token:
            tokens.append(token)
    return tokens


def tf(tokens: List[str]) -> Dict[str, float]:
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = float(len(tokens)) or 1.0
    return {t: c / total for t, c in counts.items()}


def idf(docs: Iterable[List[str]]) -> Dict[str, float]:
    docs_list = list(docs)
    n = len(docs_list) or 1
    df: Dict[str, int] = {}
    for tokens in docs_list:
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (df_t + 1)) + 1.0 for t, df_t in df.items()}


def tfidf_vector(tokens: List[str], idf_map: Dict[str, float]) -> Dict[str, float]:
    tf_map = tf(tokens)
    return {t: tf_map[t] * idf_map.get(t, 0.0) for t in tf_map}


def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    dot = 0.0
    for k, v in a.items():
        dot += v * b.get(k, 0.0)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_docs(kb_dir: Path) -> List[Doc]:
    docs: List[Doc] = []
    for path in sorted(kb_dir.glob("*.md")):
        docs.append(Doc(doc_id=path.stem, text=path.read_text()))
    return docs


def retrieve(query: str, docs: List[Doc], top_k: int = 2) -> List[Tuple[Doc, float]]:
    doc_tokens = [tokenize(d.text) for d in docs]
    idf_map = idf(doc_tokens)
    doc_vecs = [tfidf_vector(toks, idf_map) for toks in doc_tokens]

    q_vec = tfidf_vector(tokenize(query), idf_map)
    scored = [(doc, cosine(q_vec, vec)) for doc, vec in zip(docs, doc_vecs)]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def main() -> int:
    kb_dir = Path(__file__).resolve().parents[1] / "docs" / "kb"
    if not kb_dir.exists():
        raise FileNotFoundError(f"KB not found: {kb_dir}")

    query = input("Question: ").strip()
    docs = load_docs(kb_dir)
    top = retrieve(query, docs, top_k=2)

    context = "\n\n".join(f"[{doc.doc_id}]\n{doc.text}" for doc, _ in top)
    system = "You answer questions using the provided context only."
    prompt = (
        "Context:\n"
        f"{context}\n\n"
        "Question:\n"
        f"{query}\n\n"
        "Answer in Chinese."
    )

    client = LLMClient.from_env()
    answer = client.generate(prompt=prompt, system=system)
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
