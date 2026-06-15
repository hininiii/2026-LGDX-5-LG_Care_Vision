# Repository 계층 구현 정리

## 목적

14단계의 목적은 FastAPI 백엔드가 SQLite를 직접 조회하는 구조에서 벗어나, SQLAlchemy 기반 repository 계층을 통해 DB에 접근하도록 분리하는 것이다.

향후 PostgreSQL + pgvector로 전환할 때도 서비스, RAGService, DecisionEngine, AR Guide 생성 로직이 같은 method contract를 사용하도록 구성했다.

## 생성한 산출물

```text
04_백엔드/app/repositories/
  __init__.py
  database.py
  base.py
  utils.py
  interfaces.py
  sqlalchemy_repositories.py
  facade.py
  sqlite.py
  postgres.py

04_백엔드/tests/
  test_repositories_sqlalchemy.py

04_백엔드/requirements.txt
```

## 핵심 구조

```text
FastAPI routers
  -> CareShotBackendService
    -> CareShotRepository facade
      -> UserRepository
      -> DeviceRepository
      -> UsageLogRepository
      -> EnvironmentRepository
      -> ProductModelRepository
      -> StructureTypeRepository
      -> ReferenceImageRepository
      -> PartMapRepository
      -> OfficialAssetRepository
      -> RAGRepository
      -> ConversationRepository
      -> CareHistoryRepository
      -> ARSessionRepository
      -> EvaluationRepository
```

## Repository별 역할

```text
UserRepository
  - get_user_profile(user_id)

DeviceRepository
  - get_device_context(device_id)

UsageLogRepository
  - get_usage_log(device_id)
  - get_smart_diagnosis(device_id)

EnvironmentRepository
  - get_environment_context(region, city)
  - get_current_environment_observation(region, city)
  - list_environment_providers()
  - create_environment_fetch_log(...)

ProductModelRepository
  - get_product_model(model_name, product_type)
  - get_product_model_by_structure(structure_type)
  - resolve_model_structure(model_name, product_type)

StructureTypeRepository
  - list_structure_types(product_type)
  - get_structure_type(structure_type)

ReferenceImageRepository
  - get_reference_image(...)

PartMapRepository
  - get_part_map(structure_type)
  - get_part_map_by_part(structure_type, part_id)
  - get_part_map_version(...)
  - get_ar_overlay_validation_logs(...)

OfficialAssetRepository
  - find_official_assets(model_name, product_type, aliases, series)
  - find_official_contents(...)
  - find_reusable_care_video(...)

RAGRepository
  - search_official_document_chunks(...)
  - search_vector_official_document_chunks(...)
  - get_embedding_stats()
  - create_rag_search_log(...)

ConversationRepository
  - create_chat_session(...)
  - get_chat_session(session_id)
  - add_chat_message(...)
  - get_chat_messages(session_id)
  - create_chatbot_inquiry(...)
  - create_ai_inquiry_analysis(...)
  - get_conversation_state(session_id)
  - upsert_conversation_state(...)

CareHistoryRepository
  - create_care_activity_log(...)
  - get_device_care_summary(user_id, device_id)
  - upsert_device_care_summary(...)
  - get_device_care_history(user_id, device_id, service_flow_type, limit)

ARSessionRepository
  - get_ar_guide_steps(guide_id)
  - find_ar_guides(...)
  - get_ar_guide_template(...)
  - create_ar_session_log(...)
  - get_ar_session_logs(...)
  - get_ar_session_log(session_id)
  - update_ar_session_log(...)
  - create_ar_step_log(...)
  - get_ar_step_logs(session_id)

EvaluationRepository
  - get_intent_risk_test_cases(product_type)
  - save_intent_risk_eval_result(...)
```

## ThinQ model_name exact resolver

`ProductModelRepository.resolve_model_structure(model_name, product_type)`를 추가했다.

동작 흐름:

```text
ThinQ 등록 제품 model_name exact
  -> product_models 조회
  -> structure_type 확인
  -> structure_types 조회
  -> reference_images 조회
  -> part_map_versions 조회
  -> AR overlay에서 사용할 structure/reference/part map 기준 반환
```

검증 결과:

```text
model_name: AS-Q24ENXE
product_type: air_conditioner
structure_type: wall_ac_type_a
reference_image_id: REF_ASQ24_OPEN_FILTER_V1
part_map_version_id: PMV_WALL_AC_A_OPEN_FILTER_V1
part_maps: 5
```

## SQLite와 PostgreSQL method contract

현재 개발 DB는 SQLite를 사용한다.

```text
SQLiteRepositoryRegistry
PostgreSQLRepositoryRegistry
```

두 registry는 같은 `RepositoryRegistry`를 상속하며, 서비스 계층이 같은 method명을 호출하도록 구성했다. PostgreSQL 실제 연결은 15단계 PostgreSQL + pgvector 전환 시 database_url을 주입하는 방식으로 확장한다.

## FastAPI 연결

`CareShotBackendService`의 repository import를 변경했다.

```text
기존:
from ar_db_repository import CareShotRepository

변경:
from .repositories import CareShotRepository
```

따라서 FastAPI API는 새 SQLAlchemy repository facade를 통해 SQLite DB를 조회한다.

## 검증 결과

repository 단위 테스트:

```text
python -m pytest tests/test_repositories_sqlalchemy.py -q
8 passed
```

완료 기준 검증:

```text
official_assets: 791
official_document_chunks: 1,890
official_document_embeddings: 1,890
embedding_status embedded chunk: 1,890
missing_embedding_for_chunk: 0
```

FastAPI live HTTP 검증:

```text
GET http://127.0.0.1:8790/api/v1/health
status: 200

GET http://127.0.0.1:8790/api/v1/demo/context?user_id=U001&device_id=D001
status: 200
device model_name: AS-Q24ENXE

POST http://127.0.0.1:8790/api/v1/rag/search
retrieval_mode: metadata_strict_vector_similarity
first_vector_score: 0.52696998
```

RAG 40 query 검증:

```text
total: 40
passed: 40
failed: 0
all_passed: true
```

legacy AR demo server 검증:

```text
04_AR가이드/backend/server.py도 app.repositories.CareShotRepository를 사용하도록 변경함.
GET http://127.0.0.1:8787/
status: 200
```

## 남은 후속 작업

14단계 자체는 완료되었다.

다음 15단계에서 PostgreSQL + pgvector 최종 DB 전환을 수행해야 한다. 현재 PostgreSQL registry는 method contract 준비 단계이며, 실제 PostgreSQL schema migration, pgvector 컬럼, index 생성, 운영 DB 연결은 아직 수행하지 않았다.

## 추가 보정: legacy server와 parameter binding

완료 감사 중 legacy AR demo server와 일부 AI/RAG 검증 스크립트가 기존 `ar_db_repository` import를 유지하고 있던 부분을 확인했고, 모두 `app.repositories.CareShotRepository` 기준으로 정리했다.

또한 SQLAlchemy repository의 내부 parameter binding을 SQLite `?` placeholder 직접 실행 방식에서 SQLAlchemy named parameter 방식으로 변경했다.

```text
? placeholder
  -> :p0, :p1, :p2 named parameter
```

따라서 SQLite 개발 DB와 PostgreSQL 전환 후보 registry가 같은 method contract와 SQLAlchemy binding 구조를 공유한다.

최종 재검증:

```text
.py 파일 기준 기존 ar_db_repository CareShotRepository import: 없음
repository pytest: 8 passed
FastAPI RAG 40 query: 40 passed / 0 failed
FastAPI health: 200
RAG retrieval_mode: metadata_strict_vector_similarity
AI analyze: low / prepare_ar_guide_session
8787 AR demo server: 200
```

## 2026-06-11 추가 보정: ChatbotEngine 저장 contract

18단계 ChatbotEngine 구현에서 `ConversationRepository`가 최종 21개 테이블 기준의 챗봇 저장 축까지 담당하도록 확장했다.

반영 method:

```text
create_chat_session(...)
add_chat_message(...)
create_chatbot_inquiry(...)
create_ai_inquiry_analysis(...)
upsert_conversation_state(...)
get_chat_messages(...)
get_conversation_state(...)
```

저장 기준:

```text
CHAT_SESSION: 세션 생성 또는 기존 세션 이어받기
CHAT_MESSAGE: 사용자 말풍선과 AI 응답 말풍선 저장
CHATBOT_INQUIRY: 최종 분석 대상 사용자 문의 저장
AI_INQUIRY_ANALYSIS: intent_type, risk_level, recommended_guide_id, safety_reason 저장
CONVERSATION_STATE: 추가 질문 필요 여부, missing_slots, next_question 저장
RAG_SEARCH_LOG: inquiry_id, ai_response_id 연결 저장
```

금지/유지 기준:

```text
decision_logs, service_route_logs, preventive_alerts, content_view_logs, admin_reviews를 다시 생성하지 않는다.
GuideOptionSet은 API 응답으로 제공하고 추천 자체는 별도 테이블에 저장하지 않는다.
Guide 수행 완료 이력은 기존 정책대로 SELF_MANAGEMENT_HISTORY에 저장한다.
```

검증:

```text
python -m pytest -q -rs
-> 28 passed, 1 skipped
```
