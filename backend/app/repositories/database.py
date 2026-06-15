from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine


APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent


def _find_project_child(prefix: str) -> Path:
    for child in PROJECT_DIR.iterdir():
        if child.name.startswith(prefix):
            return child
    raise FileNotFoundError(f"Project child not found: {prefix}")


DATA_DIR = _find_project_child("02_")
DB_DIR = DATA_DIR / "db"
DEFAULT_SQLITE_DB_PATH = DB_DIR / "careshot_ar_mock.db"


def sqlite_url(db_path: str | Path = DEFAULT_SQLITE_DB_PATH) -> str:
    return f"sqlite:///{Path(db_path).resolve().as_posix()}"


class SQLAlchemySessionManager:
    """Owns the SQLAlchemy engine and exposes read/write connection scopes."""

    def __init__(self, database_url: str | None = None, db_path: str | Path = DEFAULT_SQLITE_DB_PATH) -> None:
        self.database_url = database_url or sqlite_url(db_path)
        connect_args = {"check_same_thread": False} if self.database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(self.database_url, future=True, connect_args=connect_args)

    @contextmanager
    def read(self) -> Iterator[Connection]:
        with self.engine.connect() as conn:
            yield conn

    @contextmanager
    def write(self) -> Iterator[Connection]:
        with self.engine.begin() as conn:
            yield conn
