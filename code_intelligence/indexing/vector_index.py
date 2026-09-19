"""Vector index over code chunks.

Backed by qdrant-client's embedded mode (no separate Qdrant server process
required — it runs against a local file or in-memory storage engine), with
a pure-Python brute-force cosine-similarity fallback if qdrant-client is
unavailable in a given environment. Both implement the same small interface
so callers (the hybrid retriever) don't need to know which one is active.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from code_intelligence.indexing.chunking import CodeChunk


@dataclass
class ScoredChunk:
    chunk: CodeChunk
    score: float


class VectorIndex(ABC):
    @abstractmethod
    def upsert(self, chunks: list[CodeChunk], vectors: list[list[float]]) -> None: ...

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredChunk]: ...


class InMemoryVectorIndex(VectorIndex):
    """Pure-Python fallback: exact brute-force cosine similarity.

    Fine for the scale a single repository's symbols produce (hundreds to
    low thousands of chunks); not intended to scale to a multi-repository
    production index, which is what the Qdrant-backed implementation below
    is for.
    """

    def __init__(self) -> None:
        self._entries: list[tuple[CodeChunk, list[float]]] = []

    def upsert(self, chunks: list[CodeChunk], vectors: list[list[float]]) -> None:
        self._entries.extend(zip(chunks, vectors))

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredChunk]:
        scored = [ScoredChunk(chunk=c, score=self._cosine(query_vector, v)) for c, v in self._entries]
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_k]


class QdrantVectorIndex(VectorIndex):
    """qdrant-client in embedded mode: ``path=None`` -> in-memory,
    ``path="/some/dir"`` -> persisted to disk. No Qdrant server needed.
    """

    def __init__(self, dimensions: int, collection_name: str = "code_chunks", path: str | None = None):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        self._PointStruct = PointStruct
        self.collection_name = collection_name
        self.client = QdrantClient(path=path or ":memory:")
        if self.client.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
        )
        self._chunks_by_id: dict[int, CodeChunk] = {}
        self._next_id = 0

    def upsert(self, chunks: list[CodeChunk], vectors: list[list[float]]) -> None:
        points = []
        for chunk, vector in zip(chunks, vectors):
            point_id = self._next_id
            self._next_id += 1
            self._chunks_by_id[point_id] = chunk
            points.append(self._PointStruct(id=point_id, vector=vector, payload={"chunk_id": chunk.chunk_id}))
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredChunk]:
        results = self.client.search(
            collection_name=self.collection_name, query_vector=query_vector, limit=top_k
        )
        return [ScoredChunk(chunk=self._chunks_by_id[hit.id], score=hit.score) for hit in results]


def build_vector_index(dimensions: int, prefer_qdrant: bool = True) -> VectorIndex:
    """Try Qdrant's embedded mode first; fall back to the in-memory index if
    the library import or client construction fails for any reason, so
    indexing never hard-fails just because of a missing/broken dependency.
    """
    if prefer_qdrant:
        try:
            return QdrantVectorIndex(dimensions=dimensions)
        except Exception:
            pass
    return InMemoryVectorIndex()
