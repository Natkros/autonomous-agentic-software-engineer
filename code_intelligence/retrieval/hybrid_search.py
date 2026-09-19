"""Hybrid code retrieval: semantic + keyword + symbol + file-path search.

Combines four independent signals into one ranked result list, per the
project's design goal that a query like "find all code responsible for user
authentication" should surface matches a single search mode would miss
(e.g. semantic search alone can miss an exact symbol-name hit if the
deterministic local embedding doesn't weight it heavily enough).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from code_intelligence.indexing.chunking import CodeChunk, build_chunks
from code_intelligence.indexing.models import RepositoryIndex
from code_intelligence.indexing.vector_index import VectorIndex, build_vector_index
from code_intelligence.providers.embeddings import EmbeddingProvider, LocalHashEmbedding

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Relative weight of each signal in the final blended score.
WEIGHTS = {"semantic": 0.4, "keyword": 0.25, "symbol": 0.25, "path": 0.10}


@dataclass
class SearchResult:
    chunk: CodeChunk
    score: float
    matched_signals: list[str]

    def to_dict(self) -> dict:
        return {
            "file_path": self.chunk.file_path,
            "symbol_name": self.chunk.symbol_name,
            "kind": self.chunk.kind,
            "lineno": self.chunk.lineno,
            "score": round(self.score, 4),
            "matched_signals": self.matched_signals,
        }


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _keyword_score(query_tokens: set[str], chunk: CodeChunk) -> float:
    chunk_tokens = _tokenize(chunk.text)
    if not query_tokens or not chunk_tokens:
        return 0.0
    overlap = query_tokens & chunk_tokens
    return len(overlap) / len(query_tokens)


def _symbol_score(query: str, chunk: CodeChunk) -> float:
    q = query.lower()
    name = chunk.symbol_name.lower()
    if q == name:
        return 1.0
    if q in name or name.split(".")[-1] == q:
        return 0.7
    return 0.0


def _path_score(query: str, chunk: CodeChunk) -> float:
    return 1.0 if query.lower() in chunk.file_path.lower() else 0.0


class HybridRetriever:
    def __init__(self, index: RepositoryIndex, embedding_provider: EmbeddingProvider | None = None):
        self.index = index
        self.embedding_provider = embedding_provider or LocalHashEmbedding()
        self.chunks: list[CodeChunk] = build_chunks(index.symbols)
        self.vector_index: VectorIndex = build_vector_index(
            dimensions=getattr(self.embedding_provider, "dimensions", 256)
        )
        if self.chunks:
            vectors = self.embedding_provider.embed([c.text for c in self.chunks])
            self.vector_index.upsert(self.chunks, vectors)

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        if not self.chunks:
            return []

        query_tokens = _tokenize(query)
        query_vector = self.embedding_provider.embed([query])[0]
        semantic_hits = {
            hit.chunk.chunk_id: hit.score
            for hit in self.vector_index.search(query_vector, top_k=len(self.chunks))
        }

        results: list[SearchResult] = []
        for chunk in self.chunks:
            semantic = semantic_hits.get(chunk.chunk_id, 0.0)
            keyword = _keyword_score(query_tokens, chunk)
            symbol = _symbol_score(query, chunk)
            path = _path_score(query, chunk)

            combined = (
                WEIGHTS["semantic"] * semantic
                + WEIGHTS["keyword"] * keyword
                + WEIGHTS["symbol"] * symbol
                + WEIGHTS["path"] * path
            )
            if combined <= 0:
                continue

            signals = []
            if semantic > 0.05:
                signals.append("semantic")
            if keyword > 0:
                signals.append("keyword")
            if symbol > 0:
                signals.append("symbol")
            if path > 0:
                signals.append("path")

            results.append(SearchResult(chunk=chunk, score=combined, matched_signals=signals))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
