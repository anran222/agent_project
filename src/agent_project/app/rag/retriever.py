from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass
class Doc:
    doc_id: str
    text: str


def _tokenize(text: str) -> List[str]:
    tokens = []
    for raw in text.lower().split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if token:
            tokens.append(token)
    return tokens


def _tf(tokens: List[str]) -> Dict[str, float]:
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = float(len(tokens)) or 1.0
    return {t: c / total for t, c in counts.items()}


def _idf(docs: Iterable[List[str]]) -> Dict[str, float]:
    docs_list = list(docs)
    n = len(docs_list) or 1
    df: Dict[str, int] = {}
    for tokens in docs_list:
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (df_t + 1)) + 1.0 for t, df_t in df.items()}


def _tfidf(tokens: List[str], idf_map: Dict[str, float]) -> Dict[str, float]:
    tf_map = _tf(tokens)
    return {t: tf_map[t] * idf_map.get(t, 0.0) for t in tf_map}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
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
    if not docs:
        return []
    doc_tokens = [_tokenize(d.text) for d in docs]
    idf_map = _idf(doc_tokens)
    doc_vecs = [_tfidf(toks, idf_map) for toks in doc_tokens]

    q_vec = _tfidf(_tokenize(query), idf_map)
    scored = [(doc, _cosine(q_vec, vec)) for doc, vec in zip(docs, doc_vecs)]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
