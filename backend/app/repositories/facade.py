from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import quote_table_name
from .database import DEFAULT_SQLITE_DB_PATH, SQLAlchemySessionManager, sqlite_url
from .sqlalchemy_repositories import (
    SQLAlchemyARSessionRepository,
    SQLAlchemyConversationRepository,
    SQLAlchemyDecisionRepository,
    SQLAlchemyDeviceRepository,
    SQLAlchemyEnvironmentRepository,
    SQLAlchemyEvaluationRepository,
    SQLAlchemyOfficialAssetRepository,
    SQLAlchemyPartMapRepository,
    SQLAlchemyCareHistoryRepository,
    SQLAlchemyProductCodeRepository,
    SQLAlchemyProductModelRepository,
    SQLAlchemyRAGRepository,
    SQLAlchemyReferenceImageRepository,
    SQLAlchemyStructureTypeRepository,
    SQLAlchemyUsageLogRepository,
    SQLAlchemyUserRepository,
)


class RepositoryRegistry:
    """Facade used by services while domain repositories stay independently testable."""

    def __init__(self, manager: SQLAlchemySessionManager) -> None:
        self.manager = manager
        self.users = SQLAlchemyUserRepository(manager)
        self.devices = SQLAlchemyDeviceRepository(manager)
        self.usage_logs = SQLAlchemyUsageLogRepository(manager)
        self.environment = SQLAlchemyEnvironmentRepository(manager)
        self.product_models = SQLAlchemyProductModelRepository(manager)
        self.product_codes = SQLAlchemyProductCodeRepository(manager)
        self.structure_types = SQLAlchemyStructureTypeRepository(manager)
        self.reference_images = SQLAlchemyReferenceImageRepository(manager)
        self.part_maps = SQLAlchemyPartMapRepository(manager)
        self.official_assets = SQLAlchemyOfficialAssetRepository(manager)
        self.rag = SQLAlchemyRAGRepository(manager)
        self.conversation = SQLAlchemyConversationRepository(manager)
        self.care_history = SQLAlchemyCareHistoryRepository(manager)
        self.ar_sessions = SQLAlchemyARSessionRepository(manager)
        self.evaluation = SQLAlchemyEvaluationRepository(manager)
        self.decisions = SQLAlchemyDecisionRepository(manager)
        self._components = (
            self.users,
            self.devices,
            self.usage_logs,
            self.environment,
            self.product_models,
            self.product_codes,
            self.structure_types,
            self.reference_images,
            self.part_maps,
            self.official_assets,
            self.rag,
            self.conversation,
            self.care_history,
            self.ar_sessions,
            self.evaluation,
            self.decisions,
        )

    def __getattr__(self, name: str) -> Any:
        for component in self._components:
            if hasattr(component, name):
                return getattr(component, name)
        raise AttributeError(name)

    def count(self, table_name: str) -> int:
        with self.manager.read() as conn:
            return int(conn.exec_driver_sql(f"SELECT COUNT(*) FROM {quote_table_name(table_name)}").scalar_one())


class SQLiteRepositoryRegistry(RepositoryRegistry):
    def __init__(self, db_path: str | Path = DEFAULT_SQLITE_DB_PATH) -> None:
        self.db_path = Path(db_path)
        super().__init__(SQLAlchemySessionManager(sqlite_url(db_path)))


class PostgreSQLRepositoryRegistry(RepositoryRegistry):
    """PostgreSQL-ready registry with the same method contract as SQLite."""

    def __init__(self, database_url: str) -> None:
        super().__init__(SQLAlchemySessionManager(database_url=database_url))


class CareShotRepository(SQLiteRepositoryRegistry):
    """Compatibility name for the existing service layer."""

    pass
