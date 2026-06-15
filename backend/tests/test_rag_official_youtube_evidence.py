from __future__ import annotations

from app.path_setup import configure_import_paths
from app.repositories import CareShotRepository


configure_import_paths()
from rag_service import RAGService  # noqa: E402


def test_rag_returns_manual_evidence_with_official_youtube_video() -> None:
    result = RAGService(CareShotRepository()).search(
        {
            "query": "How do I clean my LG air conditioner filter?",
            "product_type": "air_conditioner",
            "model_name": "AS-Q24ENXE",
            "procedure_type": "filter_cleaning",
            "language": "en",
            "limit": 8,
        }
    )

    urls = [item["source_url"] for item in result["results"]]
    source_types = {item["source_type"] for item in result["results"]}

    assert "help_library" in source_types
    assert any(url.startswith("https://www.youtube.com/watch") for url in urls)


def test_power_troubleshooting_rag_does_not_fall_back_to_filter_cleaning() -> None:
    result = RAGService(CareShotRepository()).search(
        {
            "query": "My LG AC has no power and suddenly turns off.",
            "product_type": "air_conditioner",
            "model_name": "AS-Q24ENXE",
            "procedure_type": "power_troubleshooting",
            "language": "en",
            "limit": 8,
        }
    )

    assert result["result_count"] >= 1
    assert {item["procedure_type"] for item in result["results"]} == {"power_troubleshooting"}
    assert all(item["procedure_type"] != "filter_cleaning" for item in result["results"])
    assert any(item["source_type"] == "official_youtube" for item in result["results"])
