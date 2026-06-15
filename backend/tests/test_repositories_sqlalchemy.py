from __future__ import annotations

from app.repositories import (
    CareShotRepository,
    PostgreSQLRepositoryRegistry,
    RepositoryRegistry,
    SQLiteRepositoryRegistry,
)


def test_repository_registry_has_required_domain_repositories() -> None:
    repo = CareShotRepository()

    for component_name in [
        "users",
        "devices",
        "usage_logs",
        "environment",
        "product_models",
        "product_codes",
        "structure_types",
        "reference_images",
        "part_maps",
        "official_assets",
        "rag",
        "conversation",
        "care_history",
        "ar_sessions",
        "evaluation",
    ]:
        assert hasattr(repo, component_name), component_name


def test_sqlite_seed_counts_are_visible_through_repository() -> None:
    repo = CareShotRepository()

    assert repo.count("official_assets") >= 792
    assert repo.count("official_document_chunks") >= 1891
    assert repo.count("official_document_embeddings") >= 1891
    assert repo.count("product_code_registry") == 155

    stats = repo.get_embedding_stats()
    assert stats["table_exists"] is True
    assert stats["embedding_count"] >= 1891
    assert stats["chunk_status_counts"]["embedded"] >= 1891
    assert stats["model_counts"]["careshot_local_hashing_v1::embedded"] >= 1891


def test_basic_context_repositories_read_seed_data() -> None:
    repo = CareShotRepository()

    assert repo.get_user_profile("U001")["user_id"] == "U001"
    assert repo.get_device_context("D001")["model_name"] == "AS-Q24ENXE"
    usage_log = repo.get_usage_log("D001")
    assert usage_log["device_id"] == "D001"
    assert usage_log["recent_used_hours"] == 42
    assert usage_log["usage_period_days"] == 7
    assert repo.get_smart_diagnosis("D001")["device_id"] == "D001"
    assert repo.get_current_environment_observation("Gujarat")["region"] == "Gujarat"


def test_thinq_exact_model_resolver_returns_structure_reference_and_part_map() -> None:
    repo = CareShotRepository()

    resolved = repo.resolve_model_structure("AS-Q24ENXE", "air_conditioner")

    assert resolved is not None
    assert resolved["match_type"] == "exact_model"
    assert resolved["model_name"] == "AS-Q24ENXE"
    assert resolved["structure_type"] == "wall_ac_type_a"
    assert resolved["product_model"]["model_name"] == "AS-Q24ENXE"
    assert resolved["reference_image"]["reference_image_id"] == "AR_TARGET_2"
    assert resolved["part_map_version"]["part_map_version_id"] == "PMV_WALL_AC_TYPE_A_FROM_AR_GUIDE"
    assert len(repo.get_part_map(resolved["structure_type"])) == 5


def test_product_code_registry_blocks_unverified_codes() -> None:
    repo = CareShotRepository()

    wall_ac = repo.find_product_code("AS-Q24ENXE")
    assert wall_ac is not None
    assert wall_ac["verification_status"] == "verified"
    assert wall_ac["registration_supported"] == 1
    assert wall_ac["product_model_id"] == "AS-Q24ENXE"

    window_ac = repo.find_product_code("AWQ24WWXA")
    assert window_ac is not None
    assert window_ac["product_code"] == "AW-Q24WWXA"
    assert window_ac["structure_type"] == "window_ac_type_a"

    blocked = repo.find_product_code("LGIN-STANDING-AC-CATEGORY-ONLY")
    assert blocked is not None
    assert blocked["verification_status"] == "unverified"
    assert blocked["registration_supported"] == 0


def test_rag_repository_returns_vector_candidates_from_embeddings() -> None:
    repo = CareShotRepository()

    candidates = repo.search_vector_official_document_chunks(
        product_type="air_conditioner",
        model_name="AS-Q24ENXE",
        procedure_type="filter_cleaning",
        embedding_model="careshot_local_hashing_v1",
        limit=10,
    )

    assert candidates
    assert all(candidate["embedding_dimension"] == 512 for candidate in candidates)
    assert all(candidate["embedding_vector"] for candidate in candidates)
    assert all(
        candidate["source_url"].startswith(
            ("https://www.lg.com/in/", "https://gscs-manual.lge.com/", "https://www.youtube.com/watch")
        )
        for candidate in candidates
    )
    assert any(candidate["source_url"].startswith("https://www.youtube.com/watch") for candidate in candidates)


def test_official_asset_and_care_history_repositories_are_accessible() -> None:
    repo = CareShotRepository()

    official_match = repo.find_official_assets("AS-Q24ENXE", "air_conditioner")
    assert official_match["match_status"] == "verified"
    assert official_match["official_assets"]

    summary = repo.get_device_care_summary(user_id="U001", device_id="D001")
    assert summary is not None
    assert "self_care_count" in summary
    care_history = repo.get_device_care_history(user_id="U001", device_id="D001", limit=5)
    assert isinstance(care_history, list)
    assert len(care_history) <= 5


def test_evaluation_repository_handles_empty_current_test_set() -> None:
    repo = CareShotRepository()

    assert repo.get_intent_risk_test_cases() == []


def test_sqlite_and_postgresql_registries_share_repository_contract() -> None:
    assert issubclass(SQLiteRepositoryRegistry, RepositoryRegistry)
    assert issubclass(PostgreSQLRepositoryRegistry, RepositoryRegistry)

    sqlite_public = {name for name in dir(SQLiteRepositoryRegistry) if not name.startswith("_")}
    postgres_public = {name for name in dir(PostgreSQLRepositoryRegistry) if not name.startswith("_")}

    assert sqlite_public == postgres_public
