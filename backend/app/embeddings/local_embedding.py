from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import Iterable, Protocol, Sequence


DEFAULT_HASHING_MODEL_NAME = "careshot_local_hashing_v1"
DEFAULT_LOCAL_MODEL_NAME = "BAAI/bge-m3"
TOKEN_PATTERN = re.compile(r"[a-z0-9\uac00-\ud7a3]{2,}", re.IGNORECASE)

EmbeddingVector = dict[str, float] | list[float]


class EmbeddingProvider(Protocol):
    model_name: str
    dimension: int

    def embed_text(self, text: str) -> EmbeddingVector:
        ...

    def embed_batch(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        ...


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(normalize_text(text))


def iter_hashing_features(text: str) -> Iterable[tuple[str, float]]:
    normalized = normalize_text(text)
    tokens = tokenize(normalized)

    for token in tokens:
        yield f"w:{token}", 1.0

    for left, right in zip(tokens, tokens[1:]):
        yield f"wb:{left}_{right}", 1.25

    compact = f" {normalized} "
    for ngram_size, weight in ((3, 0.35), (4, 0.45), (5, 0.55)):
        if len(compact) < ngram_size:
            continue
        for index in range(0, len(compact) - ngram_size + 1):
            ngram = compact[index : index + ngram_size]
            if ngram.strip():
                yield f"c{ngram_size}:{ngram}", weight


def stable_index(feature: str, dimension: int) -> int:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little") % dimension


@dataclass
class HashingEmbeddingProvider:
    """Deterministic fallback provider used by the existing MVP vector index."""

    model_name: str = DEFAULT_HASHING_MODEL_NAME
    dimension: int = 512
    language_scope: str = "multilingual_keyword_char_ngram"
    cost_profile: str = "local_no_api_cost"

    def embed_text(self, text: str) -> dict[str, float]:
        vector: dict[int, float] = {}
        for feature, weight in iter_hashing_features(text):
            index = stable_index(feature, self.dimension)
            vector[index] = vector.get(index, 0.0) + weight

        norm = math.sqrt(sum(value * value for value in vector.values()))
        if norm <= 0:
            return {}

        return {
            str(index): round(value / norm, 8)
            for index, value in sorted(vector.items())
            if value != 0
        }

    def embed_batch(self, texts: Sequence[str]) -> list[dict[str, float]]:
        return [self.embed_text(text) for text in texts]


class LocalModelEmbeddingProvider:
    """Local open-source embedding provider for BGE/E5 style sentence-transformer models."""

    def __init__(
        self,
        model_name: str = DEFAULT_LOCAL_MODEL_NAME,
        device: str | None = None,
        batch_size: int = 16,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised in runtime env checks.
            raise RuntimeError(
                "sentence-transformers is required for CARESHOT_EMBEDDING_PROVIDER=local_model"
            ) from exc

        self.model_name = model_name
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name, device=device)
        get_dimension = getattr(
            self.model,
            "get_embedding_dimension",
            self.model.get_sentence_embedding_dimension,
        )
        dimension = get_dimension()
        if dimension is None:
            sample = self.embed_text("dimension probe")
            dimension = len(sample) if isinstance(sample, list) else 0
        self.dimension = int(dimension)

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [
            [round(float(value), 8) for value in vector]
            for vector in embeddings.tolist()
        ]


def get_embedding_provider() -> EmbeddingProvider:
    provider_name = os.getenv("CARESHOT_EMBEDDING_PROVIDER", "hashing").strip().lower()
    if provider_name in {"hash", "hashing", "local_hashing"}:
        return HashingEmbeddingProvider()
    if provider_name in {"local_model", "sentence_transformer", "sentence-transformers"}:
        model_name = os.getenv("CARESHOT_EMBEDDING_MODEL", DEFAULT_LOCAL_MODEL_NAME).strip()
        device = os.getenv("CARESHOT_EMBEDDING_DEVICE") or None
        batch_size = int(os.getenv("CARESHOT_EMBEDDING_BATCH_SIZE", "16"))
        try:
            return LocalModelEmbeddingProvider(model_name=model_name, device=device, batch_size=batch_size)
        except Exception:
            if os.getenv("CARESHOT_EMBEDDING_STRICT", "0") == "1":
                raise
            return HashingEmbeddingProvider()
    raise ValueError(f"Unsupported CARESHOT_EMBEDDING_PROVIDER: {provider_name}")


def cosine_similarity(left: EmbeddingVector, right: EmbeddingVector) -> float:
    if isinstance(left, dict) and isinstance(right, dict):
        return cosine_sparse(left, right)
    if isinstance(left, list) and isinstance(right, list):
        return cosine_dense(left, right)
    return 0.0


def cosine_sparse(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    score = sum(value * right.get(index, 0.0) for index, value in left.items())
    return round(float(score), 8)


def cosine_dense(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left))
    right_norm = math.sqrt(sum(float(value) * float(value) for value in right))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return round(float(dot / (left_norm * right_norm)), 8)
