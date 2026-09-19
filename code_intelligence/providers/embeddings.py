"""Embedding provider abstraction.

Per the project's own engineering rule ("if a dependency or API is
unavailable, implement a provider abstraction and a local/mock fallback"):
this defines a small interface plus two implementations.

``LocalHashEmbedding`` is a real, deterministic, offline embedding using the
classic hashing trick (bag-of-tokens hashed into a fixed-size vector, then
L2-normalized). It is not a learned embedding and will not capture semantic
meaning the way a trained model would, but it is genuinely functional: texts
sharing vocabulary score higher on cosine similarity than unrelated texts,
which is what the hybrid retriever in this phase needs, and it requires no
network access or API key, so it is what is actually exercised by this
project's test suite.

``OpenAIEmbeddingProvider`` is a real implementation of the interface against
OpenAI's embeddings API, included for production use once an API key is
configured. It has NOT been exercised in this environment (no network/API
key available here) — do not treat it as verified until it's actually run.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.request
from abc import ABC, abstractmethod

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    dimensions: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""


class LocalHashEmbedding(EmbeddingProvider):
    """Deterministic offline embedding via the hashing trick. No network."""

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Real OpenAI embeddings API client. Requires OPENAI_API_KEY.

    NOT exercised in this project's test suite (no network/API key in this
    environment) — verify manually before relying on it in production.
    """

    def __init__(self, model: str = "text-embedding-3-small", dimensions: int = 1536):
        self.model = model
        self.dimensions = dimensions
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingProviderError(
                "OPENAI_API_KEY is not set; cannot call the OpenAI embeddings API. "
                "Use LocalHashEmbedding for offline/local development instead."
            )
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        request = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read())
        except Exception as exc:  # network error, HTTP error, etc.
            raise EmbeddingProviderError(f"OpenAI embeddings request failed: {exc}") from exc
        return [item["embedding"] for item in body["data"]]


def get_default_provider() -> EmbeddingProvider:
    """Use OpenAI if a key is configured, otherwise fall back to the local
    deterministic embedding so the system always works offline.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIEmbeddingProvider()
    return LocalHashEmbedding()
