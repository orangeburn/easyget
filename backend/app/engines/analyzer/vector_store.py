from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from hashlib import md5
from typing import Dict, List, Tuple


class HashingVectorizer:
    """
    轻量向量化：基于哈希桶的词频向量，适合本地/无依赖场景。
    """
    def __init__(self, dim: int = 256):
        self.dim = dim

    def vectorize(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dim
        tokens = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text.lower())
        vec = [0.0] * self.dim
        for t in tokens:
            idx = int(md5(t.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


@dataclass
class SimpleVectorStore:
    """
    轻量向量存储：内存 + 可选 JSON 持久化。
    """
    dim: int = 256
    path: str | None = None
    _store: Dict[str, List[float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.path and os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._store = {k: v for k, v in data.items() if isinstance(v, list)}
            except Exception:
                # Ignore load errors to keep runtime robust
                self._store = {}

    def upsert(self, key: str, vector: List[float]) -> None:
        if not key:
            return
        if not vector or len(vector) != self.dim:
            return
        self._store[key] = vector
        self._persist()

    def get(self, key: str) -> List[float] | None:
        return self._store.get(key)

    def similarity_top_k(self, vector: List[float], k: int = 3) -> List[Tuple[str, float]]:
        if not vector:
            return []
        results = []
        for key, v in self._store.items():
            sim = _cosine_sim(vector, v)
            results.append((key, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def _persist(self) -> None:
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._store, f)


def _cosine_sim(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))
