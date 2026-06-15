from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
APP_DIR = BACKEND_DIR / "app"
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = next(path for path in PROJECT_DIR.iterdir() if path.name.startswith("02_"))
DB_PATH = DATA_DIR / "db" / "careshot_ar_mock.db"
VECTOR_DIR = DATA_DIR / "vector_index"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.embeddings import HashingEmbeddingProvider, get_embedding_provider  # noqa: E402


OFFICIAL_SOURCE_PREFIXES = (
    "https://www.lg.com/in/",
    "https://gscs-manual.lge.com/",
    "https://www.youtube.com/watch",
    "https://youtu.be/",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_embedding_text(row: sqlite3.Row) -> str:
    parts = [
        row["product_type"],
        row["model_name"],
        row["source_type"],
        row["product_code"],
        row["procedure_type"],
        row["source_section"],
        row["language_code"],
        row["chunk_text"],
    ]
    return " ".join(str(part) for part in parts if part)


def load_chunks(conn: sqlite3.Connection, model_name: str, skip_existing: bool) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    existing_filter = ""
    if skip_existing:
        existing_filter = """
          AND NOT EXISTS (
            SELECT 1
            FROM "OFFICIAL_DOCUMENT_EMBEDDING" e
            WHERE e.chunk_id = c.chunk_id
              AND e.embedding_model = ?
              AND e.embedding_status = 'embedded'
          )
        """
    params = (model_name,) if skip_existing else ()
    return conn.execute(
        f"""
        SELECT
          c.chunk_id,
          c.asset_id,
          c.product_code,
          c.procedure_type,
          c.chunk_text,
          c.source_url,
          c.source_section,
          c.language_code,
          a.product_type,
          a.model_name,
          a.source_type
        FROM "OFFICIAL_DOCUMENT_CHUNK" c
        JOIN "OFFICIAL_ASSET" a ON a.asset_id = c.asset_id
        WHERE c.chunk_text IS NOT NULL
          AND TRIM(c.chunk_text) != ''
          AND (
            c.source_url LIKE 'https://www.lg.com/in/%'
            OR c.source_url LIKE 'https://gscs-manual.lge.com/%'
            OR c.source_url LIKE 'https://www.youtube.com/watch%'
            OR c.source_url LIKE 'https://youtu.be/%'
          )
          {existing_filter}
        ORDER BY c.chunk_id ASC
        """,
        params,
    ).fetchall()


def backup_existing_embeddings(conn: sqlite3.Connection, backup_path: Path, model_name: str) -> int:
    rows = conn.execute(
        """
        SELECT embedding_id, chunk_id, embedding_model, embedding_vector, embedding_status, created_at
        FROM "OFFICIAL_DOCUMENT_EMBEDDING"
        WHERE embedding_model = ?
        ORDER BY chunk_id ASC
        """,
        (model_name,),
    ).fetchall()
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with backup_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def next_embedding_id(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        'SELECT COALESCE(MAX(embedding_id), 0) + 1 AS next_id FROM "OFFICIAL_DOCUMENT_EMBEDDING"'
    ).fetchone()
    return int(row["next_id"])


def vector_dimension(vector: Any) -> int:
    if isinstance(vector, list):
        return len(vector)
    if isinstance(vector, dict) and vector:
        return max(int(index) for index in vector) + 1
    return 0


def reembed(db_path: Path, dry_run: bool = False, skip_existing: bool = True) -> dict[str, Any]:
    provider = get_embedding_provider()
    now = utc_now()
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        chunks = load_chunks(conn, provider.model_name, skip_existing=skip_existing)
        if not chunks:
            raise RuntimeError("No official document chunks found to embed.")

        backup_path = VECTOR_DIR / (
            f"official_document_embeddings_backup_{provider.model_name.replace('/', '_')}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        backup_count = backup_existing_embeddings(conn, backup_path, provider.model_name)

        records: list[dict[str, Any]] = []
        inserted = 0
        updated = 0
        failed = 0
        embedding_id = next_embedding_id(conn)

        for batch_start in range(0, len(chunks), provider.batch_size if hasattr(provider, "batch_size") else 16):
            batch = chunks[batch_start : batch_start + (provider.batch_size if hasattr(provider, "batch_size") else 16)]
            vectors = provider.embed_batch([build_embedding_text(row) for row in batch])
            if len(vectors) != len(batch):
                raise RuntimeError(f"Embedding count mismatch: chunks={len(batch)} vectors={len(vectors)}")

            for row, vector in zip(batch, vectors):
                status = "embedded" if vector else "failed"
                if status != "embedded":
                    failed += 1
                    continue
                record = {
                    "chunk_id": row["chunk_id"],
                    "asset_id": row["asset_id"],
                    "embedding_model": provider.model_name,
                    "embedding_dimension": vector_dimension(vector),
                    "embedding_vector": vector,
                    "embedding_status": status,
                    "indexed_at": now,
                    "product_type": row["product_type"],
                    "model_name": row["model_name"],
                    "procedure_type": row["procedure_type"],
                    "source_type": row["source_type"],
                    "source_url": row["source_url"],
                }
                records.append(record)

                existing = conn.execute(
                    """
                    SELECT embedding_id
                    FROM "OFFICIAL_DOCUMENT_EMBEDDING"
                    WHERE chunk_id = ? AND embedding_model = ?
                    """,
                    (row["chunk_id"], provider.model_name),
                ).fetchone()
                if dry_run:
                    continue
                if existing:
                    updated += 1
                    conn.execute(
                        """
                        UPDATE "OFFICIAL_DOCUMENT_EMBEDDING"
                        SET embedding_vector = ?, embedding_status = 'embedded', created_at = ?
                        WHERE embedding_id = ?
                        """,
                        (
                            json.dumps(vector, ensure_ascii=True, sort_keys=not isinstance(vector, list)),
                            now,
                            existing["embedding_id"],
                        ),
                    )
                else:
                    inserted += 1
                    conn.execute(
                        """
                        INSERT INTO "OFFICIAL_DOCUMENT_EMBEDDING"
                          (embedding_id, chunk_id, embedding_model, embedding_vector, embedding_status, created_at)
                        VALUES (?, ?, ?, ?, 'embedded', ?)
                        """,
                        (
                            embedding_id,
                            row["chunk_id"],
                            provider.model_name,
                            json.dumps(vector, ensure_ascii=True, sort_keys=not isinstance(vector, list)),
                            now,
                        ),
                    )
                    embedding_id += 1

            if not dry_run:
                conn.commit()
            print(
                json.dumps(
                    {
                        "progress": min(batch_start + len(batch), len(chunks)),
                        "total": len(chunks),
                        "inserted": inserted,
                        "updated": updated,
                        "failed": failed,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

        if not dry_run:
            conn.execute(
                """
                UPDATE "OFFICIAL_DOCUMENT_CHUNK"
                SET embedding_status = 'embedded'
                WHERE chunk_id IN (
                  SELECT chunk_id
                  FROM "OFFICIAL_DOCUMENT_EMBEDDING"
                  WHERE embedding_model = ?
                    AND embedding_status = 'embedded'
                )
                """,
                (provider.model_name,),
            )
            conn.commit()

    suffix = provider.model_name.replace("/", "_").replace(":", "_")
    index_path = VECTOR_DIR / f"official_document_embeddings_{suffix}.jsonl"
    manifest_path = VECTOR_DIR / f"official_document_embeddings_{suffix}_manifest.json"
    with index_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    summary = {
        "created_at": now,
        "dry_run": dry_run,
        "skip_existing": skip_existing,
        "embedding_provider": provider.__class__.__name__,
        "embedding_model": provider.model_name,
        "embedding_dimension": provider.dimension,
        "db_path": str(db_path),
        "source_table": "OFFICIAL_DOCUMENT_CHUNK",
        "embedding_table": "OFFICIAL_DOCUMENT_EMBEDDING",
        "total_candidate_chunks": len(chunks),
        "embedded_chunks": len(records),
        "failed_chunks": failed,
        "inserted_embeddings": inserted,
        "updated_embeddings": updated,
        "backup_model_row_count": backup_count,
        "backup_path": str(backup_path),
        "vector_index_path": str(index_path),
        "manifest_path": str(manifest_path),
        "fallback_embedding_model": HashingEmbeddingProvider().model_name,
        "official_source_prefixes": OFFICIAL_SOURCE_PREFIXES,
    }
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-embed official document chunks.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-existing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = reembed(args.db_path, dry_run=args.dry_run, skip_existing=not args.include_existing)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
