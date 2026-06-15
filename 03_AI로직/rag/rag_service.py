from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.embeddings import cosine_similarity, get_embedding_provider


OFFICIAL_SOURCE_PREFIXES = (
    "https://www.lg.com/in/",
    "https://gscs-manual.lge.com/",
    "https://www.youtube.com/watch",
    "https://youtu.be/",
)
OFFICIAL_PDF_SOURCE_TYPES = {
    "owners_manual_pdf",
    "product_spec_pdf",
    "product_spec_dimension",
}
TOKEN_PATTERN = re.compile(r"[a-z0-9\uac00-\ud7a3]{2,}", re.IGNORECASE)
STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "how",
    "please",
    "the",
    "this",
    "with",
    "you",
    "your",
}
BOILERPLATE_PATTERNS = [
    "javascript appears to be disabled",
    "we use cookies",
    "cookie settings",
    "connect with your social channels",
    "share lg technology with friends",
    "add items to your wishlist",
    "the url has been copied",
    "was this information helpful",
    "your email has been successfully registered",
    "accessories all",
    "otp authentication failed",
    "all rights reserved",
    "lg electronics official website",
    "jeong-do management",
]
SOURCE_TYPE_PRIORITY_BONUS = {
    "owners_manual_pdf": 8.0,
    "product_spec_pdf": 5.0,
    "product_spec_dimension": 5.0,
    "online_manual": 7.0,
    "help_library": 6.0,
    "official_youtube": 5.0,
    "product_page": 4.0,
    "search_support_result": 2.0,
}


class RAGService:
    """RAGService v2: official LG India evidence search with vector + strict metadata."""

    def __init__(self, repo: Any) -> None:
        self.repo = repo
        self.embedding_provider = get_embedding_provider()
        self.vector_threshold = 0.045

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = self.require_text(payload.get("query") or payload.get("message"), "query")
        product_type = self.require_text(payload.get("product_type"), "product_type")
        model_name = payload.get("model_name")
        procedure_type = payload.get("procedure_type")
        language = payload.get("language") or "en"
        session_id = payload.get("session_id")
        official_asset_ids = set(payload.get("official_asset_ids") or [])
        limit = max(1, min(int(payload.get("limit") or 5), 10))

        strict_filter = {
            "official_source_prefixes": list(OFFICIAL_SOURCE_PREFIXES),
            "product_type": product_type,
            "model_name": model_name,
            "procedure_type": procedure_type,
            "language": language,
            "official_asset_ids_priority": sorted(official_asset_ids),
            "official_pdf_source_types": sorted(OFFICIAL_PDF_SOURCE_TYPES),
            "allow_common_scope": True,
            "embedding_model": self.embedding_provider.model_name,
            "embedding_dimension": self.embedding_provider.dimension,
            "retrieval_order": [
                "metadata_strict_vector_similarity",
                "metadata_strict_lexical_fallback",
            ],
        }

        retrieval_notes: list[str] = []
        results = self.vector_search(
            query=query,
            product_type=product_type,
            model_name=model_name,
            procedure_type=procedure_type,
            language=language,
            official_asset_ids=official_asset_ids,
            limit=limit,
            require_procedure=True,
        )
        retrieval_mode = "metadata_strict_vector_similarity"

        if not results:
            retrieval_notes.append("Vector search returned no confident result; lexical fallback executed.")
            results = self.lexical_fallback(
                query=query,
                product_type=product_type,
                model_name=model_name,
                procedure_type=procedure_type,
                language=language,
                official_asset_ids=official_asset_ids,
                limit=limit,
            )
            retrieval_mode = "metadata_strict_lexical_fallback"

        no_match_reason = None
        if not results:
            no_match_reason = (
                "No official LG India evidence matched metadata strict filters, "
                "vector similarity threshold, or lexical fallback."
            )
            retrieval_mode = "no_match_ar_guide_blocked"

        search_id = payload.get("search_id") or self.new_search_id()
        score_map = {
            item["chunk_id"]: {
                "score": item["score"],
                "vector_score": item.get("vector_score"),
                "lexical_score": item.get("lexical_score"),
                "retrieval_mode": item.get("retrieval_mode"),
            }
            for item in results
        }
        log_payload = {
            "search_id": search_id,
            "session_id": session_id,
            "inquiry_id": payload.get("inquiry_id"),
            "ai_response_id": payload.get("ai_response_id"),
            "query": query,
            "product_type": product_type,
            "model_name": model_name,
            "procedure_type": procedure_type,
            "strict_filter": strict_filter,
            "matched_chunk_ids": [item["chunk_id"] for item in results],
            "score": score_map,
            "no_match_reason": no_match_reason,
            "raw_json": {
                "request": payload,
                "strict_filter": strict_filter,
                "result_count": len(results),
                "retrieval_mode": retrieval_mode,
                "retrieval_notes": retrieval_notes,
                "ar_guide_blocked": len(results) == 0,
            },
        }
        self.repo.create_rag_search_log(log_payload)

        return {
            "search_id": search_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "product_type": product_type,
            "model_name": model_name,
            "procedure_type": procedure_type,
            "strict_filter": strict_filter,
            "retrieval_mode": retrieval_mode,
            "retrieval_notes": retrieval_notes,
            "embedding_model": self.embedding_provider.model_name,
            "embedding_dimension": self.embedding_provider.dimension,
            "result_count": len(results),
            "results": results,
            "no_match_reason": no_match_reason,
            "ar_guide_allowed": len(results) > 0,
            "ar_guide_blocked": len(results) == 0,
        }

    def vector_search(
        self,
        query: str,
        product_type: str,
        model_name: str | None,
        procedure_type: str | None,
        language: str | None,
        official_asset_ids: set[str],
        limit: int,
        require_procedure: bool,
    ) -> list[dict[str, Any]]:
        query_vector = self.embedding_provider.embed_text(query)
        candidates = self.repo.search_vector_official_document_chunks(
            product_type=product_type,
            model_name=model_name,
            procedure_type=procedure_type,
            language=language,
            embedding_model=self.embedding_provider.model_name,
            require_procedure=require_procedure,
            limit=1000,
        )
        ranked = self.rank_vector_chunks(
            query=query,
            query_vector=query_vector,
            chunks=candidates,
            product_type=product_type,
            model_name=model_name,
            procedure_type=procedure_type,
            official_asset_ids=official_asset_ids,
            require_procedure=require_procedure,
        )
        return self.ensure_official_youtube_evidence(ranked, procedure_type, limit)

    def lexical_fallback(
        self,
        query: str,
        product_type: str,
        model_name: str | None,
        procedure_type: str | None,
        language: str | None,
        official_asset_ids: set[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        candidates = self.repo.search_official_document_chunks(
            query=query,
            product_type=product_type,
            model_name=model_name,
            procedure_type=procedure_type,
            language=language,
            limit=120,
        )
        ranked = self.rank_lexical_chunks(
            query=query,
            chunks=candidates,
            product_type=product_type,
            model_name=model_name,
            procedure_type=procedure_type,
            official_asset_ids=official_asset_ids,
        )
        return ranked[:limit]

    def rank_vector_chunks(
        self,
        query: str,
        query_vector: dict[str, float],
        chunks: list[dict[str, Any]],
        product_type: str,
        model_name: str | None,
        procedure_type: str | None,
        official_asset_ids: set[str],
        require_procedure: bool,
    ) -> list[dict[str, Any]]:
        terms = self.tokenize(query)
        ranked: list[dict[str, Any]] = []
        for chunk in chunks:
            if not self.is_valid_chunk(chunk, product_type):
                continue
            vector = chunk.get("embedding_vector") or {}
            vector_score = cosine_similarity(query_vector, vector)
            lexical_score, matched_terms = self.lexical_score(terms, chunk)
            if vector_score < self.vector_threshold:
                continue

            metadata_bonus = self.metadata_bonus(
                chunk=chunk,
                model_name=model_name,
                procedure_type=procedure_type,
                official_asset_ids=official_asset_ids,
                require_procedure=require_procedure,
            )
            final_score = (vector_score * 100.0) + lexical_score + metadata_bonus
            ranked.append(
                self.result_payload(
                    chunk=chunk,
                    score=round(final_score, 4),
                    vector_score=vector_score,
                    lexical_score=lexical_score,
                    matched_terms=matched_terms,
                    model_name=model_name,
                    procedure_type=procedure_type,
                    official_asset_ids=official_asset_ids,
                    retrieval_mode=(
                        "metadata_strict_vector_similarity"
                        if require_procedure
                        else "metadata_relaxed_procedure_vector_similarity"
                    ),
                )
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index
        return ranked

    @staticmethod
    def ensure_official_youtube_evidence(
        ranked: list[dict[str, Any]],
        procedure_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        selected = ranked[:limit]
        if any(item.get("source_type") == "official_youtube" for item in selected):
            return selected

        youtube = next(
            (
                item
                for item in ranked
                if item.get("source_type") == "official_youtube"
                and (not procedure_type or item.get("procedure_type") == procedure_type)
            ),
            None,
        )
        if not youtube:
            return selected

        if selected:
            selected = selected[:-1] + [youtube]
        else:
            selected = [youtube]
        for index, item in enumerate(selected, start=1):
            item["rank"] = index
        return selected

    def rank_lexical_chunks(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        product_type: str,
        model_name: str | None,
        procedure_type: str | None,
        official_asset_ids: set[str],
    ) -> list[dict[str, Any]]:
        terms = self.tokenize(query)
        ranked: list[dict[str, Any]] = []
        for chunk in chunks:
            if not self.is_valid_chunk(chunk, product_type):
                continue
            lexical_score, matched_terms = self.lexical_score(terms, chunk)
            if lexical_score <= 0:
                continue
            metadata_bonus = self.metadata_bonus(
                chunk=chunk,
                model_name=model_name,
                procedure_type=procedure_type,
                official_asset_ids=official_asset_ids,
                require_procedure=True,
            )
            final_score = lexical_score + metadata_bonus
            ranked.append(
                self.result_payload(
                    chunk=chunk,
                    score=round(final_score, 4),
                    vector_score=None,
                    lexical_score=lexical_score,
                    matched_terms=matched_terms,
                    model_name=model_name,
                    procedure_type=procedure_type,
                    official_asset_ids=official_asset_ids,
                    retrieval_mode="metadata_strict_lexical_fallback",
                )
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index
        return ranked

    def metadata_bonus(
        self,
        chunk: dict[str, Any],
        model_name: str | None,
        procedure_type: str | None,
        official_asset_ids: set[str],
        require_procedure: bool,
    ) -> float:
        score = 5.0
        if chunk.get("procedure_type") == procedure_type:
            score += 10.0
        elif procedure_type and require_procedure:
            score -= 8.0
        if model_name and chunk.get("model_name") == model_name:
            score += 12.0
        if official_asset_ids and chunk.get("asset_id") in official_asset_ids:
            score += 15.0
        score += SOURCE_TYPE_PRIORITY_BONUS.get(chunk.get("source_type") or "", 0.0)
        scope = chunk.get("applicability_scope")
        if scope == "exact_model":
            score += 6.0
        elif scope == "official_alias":
            score += 5.0
        elif scope == "official_series":
            score += 3.0
        elif scope == "product_type_common":
            score += 1.0
        return score

    def result_payload(
        self,
        chunk: dict[str, Any],
        score: float,
        vector_score: float | None,
        lexical_score: float,
        matched_terms: list[str],
        model_name: str | None,
        procedure_type: str | None,
        official_asset_ids: set[str],
        retrieval_mode: str,
    ) -> dict[str, Any]:
        chunk_text = chunk.get("chunk_text") or ""
        pdf_page_match = re.search(r"\[page\s+(\d+)\]", chunk_text, re.IGNORECASE)
        return {
            "rank": 0,
            "chunk_id": chunk["chunk_id"],
            "asset_id": chunk.get("asset_id"),
            "product_type": chunk.get("product_type"),
            "model_name": chunk.get("model_name"),
            "series": chunk.get("series"),
            "procedure_type": chunk.get("procedure_type"),
            "language": chunk.get("language"),
            "chunk_title": chunk.get("chunk_title"),
            "chunk_text": chunk.get("chunk_text"),
            "source_url": chunk.get("source_url") or "",
            "source_section": chunk.get("source_section"),
            "source_type": chunk.get("source_type"),
            "source_raw_file": chunk.get("source_raw_file"),
            "pdf_page_number": int(pdf_page_match.group(1)) if pdf_page_match else None,
            "pdf_page_marker": pdf_page_match.group(0) if pdf_page_match else None,
            "applicability_scope": chunk.get("applicability_scope"),
            "forbidden_actions": chunk.get("forbidden_actions") or [],
            "safety_tags": chunk.get("safety_tags") or [],
            "score": score,
            "vector_score": vector_score,
            "lexical_score": lexical_score,
            "retrieval_mode": retrieval_mode,
            "match_reason": {
                "matched_terms": matched_terms,
                "official_source_verified": True,
                "procedure_matched": chunk.get("procedure_type") == procedure_type,
                "model_matched": bool(model_name and chunk.get("model_name") == model_name),
                "asset_priority_matched": bool(
                    official_asset_ids and chunk.get("asset_id") in official_asset_ids
                ),
                "metadata_scope": chunk.get("applicability_scope"),
            },
        }

    def lexical_score(self, terms: list[str], chunk: dict[str, Any]) -> tuple[float, list[str]]:
        text = " ".join(
            str(value or "")
            for value in [
                chunk.get("chunk_title"),
                chunk.get("chunk_text"),
                chunk.get("source_section"),
                chunk.get("procedure_type"),
                chunk.get("model_name"),
                chunk.get("series"),
            ]
        ).lower()
        matched_terms = sorted(term for term in terms if term in text)
        return len(matched_terms) * 3.0, matched_terms

    def is_valid_chunk(self, chunk: dict[str, Any], product_type: str) -> bool:
        source_url = chunk.get("source_url") or ""
        if not source_url.startswith(OFFICIAL_SOURCE_PREFIXES):
            return False
        if chunk.get("product_type") != product_type:
            return False
        text = " ".join(
            str(value or "")
            for value in [chunk.get("chunk_title"), chunk.get("chunk_text")]
        ).lower()
        return not self.is_boilerplate(text)

    @staticmethod
    def tokenize(text: str) -> list[str]:
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text or "")]
        return [token for token in tokens if token not in STOPWORDS]

    @staticmethod
    def is_boilerplate(text: str) -> bool:
        return any(pattern in text for pattern in BOILERPLATE_PATTERNS)

    @staticmethod
    def require_text(value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} is required.")
        return value.strip()

    @staticmethod
    def new_search_id() -> str:
        return f"RAG_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
