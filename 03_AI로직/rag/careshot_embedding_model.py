from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path


RAG_DIR = Path(__file__).resolve().parent
PROJECT_DIR = RAG_DIR.parents[1]
BACKEND_DIR = next(
    path for path in PROJECT_DIR.iterdir() if path.name.startswith("04_") and (path / "app").exists()
)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.embeddings.local_embedding import (  # noqa: E402
    DEFAULT_HASHING_MODEL_NAME,
    HashingEmbeddingProvider,
    cosine_sparse,
    normalize_text,
    tokenize,
)


@dataclass(frozen=True)
class EmbeddingModelConfig:
    model_name: str = DEFAULT_HASHING_MODEL_NAME
    dimension: int = 512
    language_scope: str = "multilingual_keyword_char_ngram"
    cost_profile: str = "local_no_api_cost"


DEFAULT_CONFIG = EmbeddingModelConfig()


def embed_text(text: str, config: EmbeddingModelConfig = DEFAULT_CONFIG) -> dict[str, float]:
    provider = HashingEmbeddingProvider(
        model_name=config.model_name,
        dimension=config.dimension,
        language_scope=config.language_scope,
        cost_profile=config.cost_profile,
    )
    return provider.embed_text(text)


def embedding_norm(vector: dict[str, float]) -> float:
    return round(math.sqrt(sum(value * value for value in vector.values())), 8)


__all__ = [
    "DEFAULT_CONFIG",
    "EmbeddingModelConfig",
    "cosine_sparse",
    "embed_text",
    "embedding_norm",
    "normalize_text",
    "tokenize",
]
