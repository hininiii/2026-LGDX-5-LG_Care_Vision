from __future__ import annotations

import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent


def _find_project_child(prefix: str) -> Path:
    for child in PROJECT_DIR.iterdir():
        if child.name.startswith(prefix):
            return child
    raise FileNotFoundError(f"Project child not found: {prefix}")


def _find_named_child(parent: Path, name: str) -> Path:
    for child in parent.iterdir():
        if child.name == name:
            return child
    raise FileNotFoundError(f"Project child not found: {parent} / {name}")


DATA_DIR = _find_project_child("02_")
AI_DIR = _find_project_child("03_")
DB_DIR = DATA_DIR / "db"
RULES_DIR = _find_named_child(AI_DIR, "rules")
RAG_DIR = _find_named_child(AI_DIR, "rag")


def configure_import_paths() -> None:
    for path in (BACKEND_DIR, DB_DIR, RULES_DIR, RAG_DIR):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
