from __future__ import annotations

import pytest

from app.embeddings import HashingEmbeddingProvider, cosine_similarity, get_embedding_provider
from app.path_setup import configure_import_paths
from app.repositories import CareShotRepository


configure_import_paths()
from rag_service import RAGService  # noqa: E402


def test_hashing_embedding_provider_is_stable_sparse_fallback(monkeypatch) -> None:
    monkeypatch.setenv("CARESHOT_EMBEDDING_PROVIDER", "hashing")

    provider = get_embedding_provider()
    vector = provider.embed_text("My AC smells bad")

    assert isinstance(provider, HashingEmbeddingProvider)
    assert provider.model_name == "careshot_local_hashing_v1"
    assert provider.dimension == 512
    assert isinstance(vector, dict)
    assert vector
    assert cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_rag_service_uses_configured_embedding_model_for_query_and_db_filter(monkeypatch) -> None:
    monkeypatch.setenv("CARESHOT_EMBEDDING_PROVIDER", "hashing")

    result = RAGService(CareShotRepository()).search(
        {
            "query": "My AC smells bad",
            "product_type": "air_conditioner",
            "model_name": "AS-Q24ENXE",
            "procedure_type": "filter_cleaning",
            "language": "en",
            "limit": 3,
        }
    )

    assert result["embedding_model"] == "careshot_local_hashing_v1"
    assert result["embedding_dimension"] == 512
    assert result["strict_filter"]["embedding_model"] == "careshot_local_hashing_v1"
    assert result["result_count"] >= 1
