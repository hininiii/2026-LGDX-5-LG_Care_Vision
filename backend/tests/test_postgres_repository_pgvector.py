from __future__ import annotations

import os

import pytest

from app.repositories import PostgreSQLRepositoryRegistry


POSTGRES_DSN = os.environ.get("CARESHOT_POSTGRES_TEST_DSN")


@pytest.mark.skipif(not POSTGRES_DSN, reason="CARESHOT_POSTGRES_TEST_DSN is not set")
def test_postgres_repository_reads_seeded_pgvector_database() -> None:
    repo = PostgreSQLRepositoryRegistry(POSTGRES_DSN)

    assert repo.count("official_assets") == 792
    assert repo.count("official_document_chunks") == 1891
    assert repo.count("official_document_embeddings") == 1891
    assert repo.count("product_code_registry") == 155

    stats = repo.get_embedding_stats()
    assert stats["table_exists"] is True
    assert stats["embedding_count"] == 1891
    assert stats["chunk_status_counts"]["embedded"] == 1891

    resolved = repo.resolve_model_structure("AS-Q24ENXE", "air_conditioner")
    assert resolved is not None
    assert resolved["structure_type"] == "wall_ac_type_a"

    canonical = {
        item["structure_type"]
        for item in repo.list_structure_types("air_conditioner")
        if item["structure_type"] in {"wall_ac_type_a", "standing_ac_type_a", "window_ac_type_a"}
    }
    assert canonical == {"wall_ac_type_a", "standing_ac_type_a", "window_ac_type_a"}

    candidates = repo.search_vector_official_document_chunks(
        "air_conditioner",
        "AS-Q24ENXE",
        "filter_cleaning",
        limit=5,
    )
    assert len(candidates) == 5
    assert all(candidate["embedding_vector"] for candidate in candidates)
