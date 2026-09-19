import math

import pytest

from code_intelligence.providers.embeddings import (
    EmbeddingProviderError,
    LocalHashEmbedding,
    OpenAIEmbeddingProvider,
    get_default_provider,
)


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def test_local_embedding_is_deterministic():
    provider = LocalHashEmbedding(dimensions=64)
    v1 = provider.embed(["authenticate the user"])[0]
    v2 = provider.embed(["authenticate the user"])[0]
    assert v1 == v2


def test_local_embedding_has_configured_dimensions():
    provider = LocalHashEmbedding(dimensions=64)
    vectors = provider.embed(["hello world", "another text"])
    assert all(len(v) == 64 for v in vectors)


def test_local_embedding_similar_texts_score_higher_than_unrelated():
    provider = LocalHashEmbedding(dimensions=128)
    base, related, unrelated = provider.embed([
        "authenticate user with email and password",
        "authenticate user login credentials",
        "render a chart with categorical colors",
    ])
    assert _cosine(base, related) > _cosine(base, unrelated)


def test_openai_provider_without_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIEmbeddingProvider()
    with pytest.raises(EmbeddingProviderError):
        provider.embed(["hello"])


def test_default_provider_falls_back_to_local_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = get_default_provider()
    assert isinstance(provider, LocalHashEmbedding)
