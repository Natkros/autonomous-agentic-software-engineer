from code_intelligence.indexing.chunking import CodeChunk
from code_intelligence.indexing.vector_index import InMemoryVectorIndex, build_vector_index
from code_intelligence.providers.embeddings import LocalHashEmbedding


def _make_chunks():
    return [
        CodeChunk(chunk_id="a", text="authenticate user login", file_path="a.py", symbol_name="a", kind="function", lineno=1),
        CodeChunk(chunk_id="b", text="render chart categorical colors", file_path="b.py", symbol_name="b", kind="function", lineno=1),
    ]


def test_in_memory_vector_index_returns_closest_match():
    provider = LocalHashEmbedding(dimensions=64)
    chunks = _make_chunks()
    vectors = provider.embed([c.text for c in chunks])

    index = InMemoryVectorIndex()
    index.upsert(chunks, vectors)

    query_vector = provider.embed(["user authentication credentials"])[0]
    results = index.search(query_vector, top_k=1)

    assert results[0].chunk.chunk_id == "a"


def test_build_vector_index_returns_a_working_index_regardless_of_backend():
    index = build_vector_index(dimensions=64)
    provider = LocalHashEmbedding(dimensions=64)
    chunks = _make_chunks()
    vectors = provider.embed([c.text for c in chunks])
    index.upsert(chunks, vectors)

    query_vector = provider.embed(["chart with colors"])[0]
    results = index.search(query_vector, top_k=1)

    assert results[0].chunk.chunk_id == "b"
