from __future__ import annotations

from typing import Any, Protocol


class UserRepository(Protocol):
    def get_user_profile(self, user_id: str) -> dict[str, Any] | None: ...


class DeviceRepository(Protocol):
    def get_device_context(self, device_id: str) -> dict[str, Any] | None: ...


class UsageLogRepository(Protocol):
    def get_usage_log(self, device_id: str) -> dict[str, Any] | None: ...
    def get_smart_diagnosis(self, device_id: str, include_high_risk_sample: bool = False) -> dict[str, Any] | None: ...


class EnvironmentRepository(Protocol):
    def get_environment_context(self, region: str, city: str | None = None) -> dict[str, Any] | None: ...
    def get_current_environment_observation(self, region: str, city: str | None = None) -> dict[str, Any] | None: ...
    def create_environment_observation(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class ProductModelRepository(Protocol):
    def get_product_model(self, model_name: str, product_type: str | None = None) -> dict[str, Any] | None: ...
    def resolve_model_structure(self, model_name: str, product_type: str | None = None) -> dict[str, Any] | None: ...


class ProductCodeRepository(Protocol):
    def find_product_code(self, input_code: str) -> dict[str, Any] | None: ...
    def create_product_registration_attempt(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class StructureTypeRepository(Protocol):
    def list_structure_types(self, product_type: str | None = None) -> list[dict[str, Any]]: ...
    def get_structure_type(self, structure_type: str) -> dict[str, Any] | None: ...


class ReferenceImageRepository(Protocol):
    def get_reference_image(
        self,
        reference_image_id: str | None = None,
        model_name: str | None = None,
        structure_type: str | None = None,
        image_role: str | None = None,
    ) -> dict[str, Any] | None: ...


class PartMapRepository(Protocol):
    def get_part_map(self, structure_type: str) -> list[dict[str, Any]]: ...
    def get_part_map_by_part(self, structure_type: str, part_id: str) -> dict[str, Any] | None: ...


class OfficialAssetRepository(Protocol):
    def find_official_assets(
        self,
        model_name: str,
        product_type: str,
        aliases: list[str] | None = None,
        series: str | None = None,
    ) -> dict[str, Any]: ...


class RAGRepository(Protocol):
    def search_vector_official_document_chunks(
        self,
        product_type: str,
        model_name: str | None = None,
        procedure_type: str | None = None,
        language: str | None = None,
        embedding_model: str | None = None,
        require_procedure: bool = True,
        limit: int = 500,
    ) -> list[dict[str, Any]]: ...
    def get_embedding_stats(self) -> dict[str, Any]: ...


class ConversationRepository(Protocol):
    def get_chat_session(self, session_id: str) -> dict[str, Any] | None: ...
    def create_chat_session(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def add_chat_message(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def get_chat_messages(self, session_id: str) -> list[dict[str, Any]]: ...
    def create_chatbot_inquiry(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def create_ai_inquiry_analysis(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def get_conversation_state(self, session_id: str) -> dict[str, Any] | None: ...
    def upsert_conversation_state(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class CareHistoryRepository(Protocol):
    def get_device_care_history(
        self,
        user_id: str,
        device_id: str,
        service_flow_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...


class ARSessionRepository(Protocol):
    def get_ar_session_log(self, session_id: str) -> dict[str, Any] | None: ...
    def get_ar_guide_steps(self, guide_id: str) -> list[dict[str, Any]]: ...


class EvaluationRepository(Protocol):
    def get_intent_risk_test_cases(self, product_type: str | None = None) -> list[dict[str, Any]]: ...
