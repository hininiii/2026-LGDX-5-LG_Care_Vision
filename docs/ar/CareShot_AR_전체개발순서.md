# CareShot AR 가전케어 AI 전체 개발 순서

## 1. 개발 원칙

CareShot AR 가전케어 AI는 단순 AR 화면이 아니라, 고객 문의를 이해하고 공식자료 근거와 안전 판단을 거친 뒤 AR Guide Session을 제공하는 서비스다.

따라서 개발 순서는 다음 원칙을 따른다.

```text
DB/데이터 기반
→ 챗봇 입력/대화
→ LLM/RAG
→ AI 판단엔진
→ ARGuidePlan
→ AR 화면
→ 세션 저장/검증
→ 발표 polish
```

### 26.7 복합 증상 primary/secondary procedure 분리 - 완료

배경:

```text
weak airflow + smell처럼 고객 문장에 복수 증상이 들어오면
기존 MVP의 첫 번째 매칭 procedure_type 하나만으로는 후속 가이드가 부족해질 수 있다.
```

결정:

```text
기존 procedure_type은 primary procedure로 유지한다.
복합 증상은 secondary_procedures를 함께 반환한다.

weak airflow + smell
-> procedure_type: odor_self_check
-> primary_procedure: odor_self_check
-> secondary_procedures: [no_cooling_self_check]
```

구현:

```text
03_AI로직/rules/ai_decision_engine.py
- resolve_secondary_procedures() 추가
- analyze().procedure에 primary_procedure, secondary_procedures 추가
- high_risk_troubleshooting은 secondary_procedures를 비워 expert_as 흐름을 명확히 유지
```

검증:

```text
POST /api/v1/chat/messages
message: The AC has weak airflow and smells bad.

procedure:
  procedure_type: odor_self_check
  primary_procedure: odor_self_check
  secondary_procedures:
    - no_cooling_self_check

python -m pytest tests -q
-> 52 passed, 1 skipped
```

AR 화면을 먼저 완성하는 것보다, 챗봇과 판단엔진이 어떤 근거로 AR을 열어주는지가 더 중요하다. AR은 최종 사용자 경험이고, 챗봇/AI/RAG/DB는 그 앞단의 의사결정 구조다.

## 2. 전체 아키텍처 흐름

```text
사용자
  ↓
프론트엔드 챗봇 UI
  ↓
백엔드 Chat API
  ↓
챗봇 대화 엔진
  ↓
LLM 응답 생성 + RAG 공식자료 검색
  ↓
AI 판단엔진
  ↓
위험도 판단 / 공식자료 strict matching / AR 허용 여부 판단
  ↓
ARGuidePlan 생성
  ↓
프론트엔드 AR Guide Session
  ↓
AR Session Log 저장
```

High Risk 문의는 다음 흐름으로 분기한다.

```text
사용자 문의
→ High Risk 감지
→ RAG/공식자료와 관계없이 AR Guide 차단
→ A/S 연결 또는 상담원 연결
→ 차단 사유 로그 저장
```

## 3. 개발 단계 요약

| 단계 | 중심 영역 | 목표 | 현재 상태 |
|---|---|---|---|
| 1 | DB | 실제 근거 기반 mock 데이터와 SQLite 기반 구축 | 데이터 수량/coverage 기준 충족 / intent 평가·RAG 품질 검증 필요 |
| 2 | Backend | 기본 API 서버 구축 | FastAPI/repository/service 분리 구현됨 / 21개 테이블 기준 전체 API 스모크 통과 |
| 3 | Rule/AI 판단 | 학습 모델이 아닌 rule 기반 판단엔진 1차 구현 | 구현됨 / 고도화 필요 |
| 4 | AR | ARGuidePlan + reference overlay 1차 구현 | 구현됨 / 검증·좌표 보정 필요 |
| 5 | Frontend | 챗봇 + AR 화면 1차 구현 | 구현됨 / multi-turn UX 필요 |
| 6 | Chatbot | 대화 상태/추가 질문 엔진 구현 | ChatbotEngine 구현됨 / 21개 테이블 저장 연동 및 multi-turn 검증 통과 |
| 7 | LLM | 자연어 응답 생성 연결 | LLMServiceMock 구현됨 / 외부 LLM API는 후속 |
| 8 | RAG | 공식문서 검색/근거 반환 | 구현됨 / chunk 정제·검색 품질 고도화 필요 |
| 9 | Integration | LLM/RAG 결과를 판단엔진과 연결 | RAG/Decision/GuideOptionSet/ChatbotEngine/LLMServiceMock 결합 완료 / LLM은 최종 판단 권한 없음 |
| 10 | QA | 안전/좌표/근거 검증 | 일부 구현 |
| 11 | Demo | 발표용 시나리오 polish | 미구현 |

## 4. 1단계: DB/데이터 기반

### 4.1 목표

ThinQ 실제 데이터에 접근하지 못하는 개발 환경에서, 최종 서비스와 같은 형태의 데이터를 mock DB로 구성한다.

### 4.2 필요한 데이터

| 데이터 | 목적 |
|---|---|
| 고객 프로필 | 언어, 지역, 선호 방식 |
| ThinQ 등록 제품 | 제품군, 모델명, alias, series |
| 사용 로그 | 필터 청소 경과일, 사용 시간, 관리 trigger |
| 스마트 진단 | 에러 코드, severity, 감지 신호 |
| 인도 환경 데이터 | 습도, AQI, 경수, 지역 기후 |
| 공식자료 DB | 매뉴얼, FAQ, 제품 이미지, 지원 페이지 |
| 공식 콘텐츠 DB | LG 공식 매뉴얼/FAQ/Help Library/지원 페이지 매칭 |
| Product Model | 모델명, structure_type, reference image 연결 |
| Part Map | 제품 구조별 부품 좌표 |
| AR Guide Step | 단계별 AR 안내 |
| AR Session Log | 사용자의 AR 진행 이력 |

### 4.2-A ARGuidePlan/overlay 생성을 위한 선행 수집 데이터

`ARGuidePlan`과 `ar_overlay_data`는 AI가 즉석에서 부품 위치나 이미지를 상상해 만드는 것이 아니라, 사전에 수집·정리된 제품 정보, 공식자료, reference image, AR target, AR guide step을 현재 고객 문의의 `product_type`, `procedure_type`, `structure_type`에 맞게 조합해서 만든다.

따라서 AR 기능 개발 전에 아래 데이터가 먼저 준비되어야 한다.

| 선행 데이터 | 최종 21테이블 기준 | 수집/정리 내용 | 사용 위치 |
|---|---|---|---|
| 제품 정보 | `PRODUCT`, `USER_PRODUCT` | `product_type`, `product_code`, `model_name`, `structure_type`, 사용자 등록 제품 연결 | 고객 `device_id`에서 제품군/구조 타입을 확정 |
| 공식자료 근거 | `OFFICIAL_ASSET`, `OFFICIAL_DOCUMENT_CHUNK`, `OFFICIAL_DOCUMENT_EMBEDDING` | LG 공식 매뉴얼, Help Library, FAQ, 제품 페이지, 공식 YouTube 근거와 chunk/vector index | RAG 근거 검색, official match 검증, no-match 차단 |
| AR 대상/부품 기준 | `AR_TARGET` | 구조별 `target_part`, 사용자 접근 가능 여부, 위험도, 좌표/크기, overlay label | 프론트가 reference image 위에 하이라이트 박스를 렌더링 |
| AR 가이드 템플릿 | `AR_GUIDE` | `procedure_type`, `guide_type`, `structure_type`, `step_order`, `action_type`, `target_part`, `safety_message` | `guide_steps` 생성, 단계별 안내 문구/안전문구 제공 |
| reference image | `PRODUCT.image_path`, `OFFICIAL_ASSET`, `AR_TARGET`와 연결되는 로컬 asset 경로 | 제품 또는 구조별 기준 이미지. 예: `open_cover_filter_visible`, `closed_front` | 프론트 AR 화면의 기준 이미지, part map 좌표 투영 대상 |
| 프론트 overlay 매핑 | API 응답 조립 결과 | `reference_image`, `part_maps`, `guide_steps`, `target_part_map`, `display_title`, `display_instruction`, `display_safety` | `/chat/messages` 또는 `/ar/plans` 응답의 `ar_overlay_data` |

수집/정리 순서:

```text
1. LG 공식 제품/모델 정보 수집
   -> PRODUCT.product_code, model_name, product_type, structure_type 확정

2. 제품별 공식자료 수집 및 chunk/embedding 구축
   -> OFFICIAL_ASSET, OFFICIAL_DOCUMENT_CHUNK, OFFICIAL_DOCUMENT_EMBEDDING 적재

3. 제품 구조별 reference image 확보
   -> 실제 제품 이미지 또는 발표용 기준 이미지 경로 확정

4. reference image 기준 AR_TARGET 좌표 작성
   -> target_part, x/y/w/h, user_accessible, risk_level, label 정리

5. procedure_type별 AR_GUIDE 단계 작성
   -> filter_cleaning, odor_self_check, power_troubleshooting 등 절차별 step 구성

6. ARGuidePlan/API 응답 검증
   -> product_type + procedure_type + structure_type 조합으로 template/guide/target/image가 모두 매칭되는지 확인

7. 프론트 overlay 검수
   -> reference image 위 target_part 하이라이트 위치, step 문구, safety 문구를 화면 기준으로 확인
```

완료 기준:

```text
고객 문의 -> service_flow_type/procedure_type 결정
-> 제품 structure_type 조회
-> 공식자료/RAG 근거 verified
-> AR_GUIDE step 조회
-> AR_TARGET 좌표 조회
-> reference image 조회
-> ar_overlay_data 생성
-> 프론트에서 reference image + part_maps + guide_steps 렌더링
```

주의:

- reference image와 AR_TARGET 좌표가 없으면 `ARGuidePlan`은 만들 수 있어도 실제 AR overlay 화면은 정확하게 렌더링할 수 없다.
- 공식자료 근거가 없거나 High Risk로 분류되면 ARGuidePlan 생성은 차단한다.
- 현재 MVP는 AS-Q24ENXE 중심의 에어컨 데이터와 일부 `procedure_type`에 대해 검증된 상태이며, 전체 LG 가전군/전체 procedure로 확장하려면 위 수집 작업을 제품군별로 반복해야 한다.

### 4.3 현재 상태

현재 산출 파일:

최종 산출물 기준으로는 RAG DB, 대화 세션 DB, 공식문서 chunk DB, mock ThinQ 데이터 확장, intent/risk 평가 데이터셋 고도화가 필요하다.

```text
02_데이터연동/mock_data/*.json
02_데이터연동/db/schema.sql
02_데이터연동/db/seed_ar_mock_db.py
02_데이터연동/db/ar_db_repository.py
```

현재 SQLite DB:

```text
02_데이터연동/db/careshot_ar_mock.db
```

### 4.4 최종 산출물 기준 점검

현재 1단계 DB는 기존 임의 mock을 폐기하고 실제 근거 기반 데이터로 재구축했다.
폐기 폴더(`99_폐기_*`, `discard`, `deprecated`)에 있는 예전 JSON/HTML/PDF는 공식자료 DB 구축, seed, RAG chunk 생성, 평가셋 생성의 입력으로 다시 사용하지 않는다. 공식자료 seed 스크립트는 폐기 경로가 `raw_file`, `source_raw_file`, `source_url`, `download_url`, `online_url`에 들어오면 즉시 실패하도록 검증한다.

단, DB에 데이터가 들어간 것과 AI 판단 정확도가 검증된 것은 다르다. 현재 `intent_risk_eval_results`는 0건이며, 분류 정확도는 아직 측정되지 않았다.

현재 확인된 mock 데이터 수량:

| 파일 | 현재 건수 | 최종 기준 판단 |
|---|---:|---|
| `user_profiles.json` | 120 | 수량 기준 충족 |
| `thinq_registered_devices.json` | 240 | 4개 제품군 60개씩 coverage 충족 |
| `usage_logs.json` | 720 | 4개 제품군 180건씩 coverage 충족 |
| `smart_diagnosis_results.json` | 480 | none/low/medium/high 각 120건 coverage 충족 |
| `india_environment_contexts.json` | 50 | Open-Meteo API 기반 50개 도시 기준 충족 |
| `intent_risk_test_cases.json` | 147 | 2026-06-12 26번 작업에서 실제 VOC 500건 원천 풀 기반으로 선별/라벨링 완료. `remote_operation` 2건 포함 |
| `official_assets_db.json` | 791 | LG India 공식 URL 기준 충족. 공식 PDF(Owner's Manual/Spec/Dimension 포함), Online Manual, Help Library, 검색 support 목록 포함 |
| `official_document_chunks.json` | 1,890 | LG India 공식자료 chunk 구축됨. embedding/Vector DB도 1,890건 연결됨. AS-Q24ENXE support/FAQ 누락 후보 510건 중 484건을 asset화하고 762 chunk를 추가함 |
| `care_video_db.json` | 4 | 최종 기준 폐기 대상. 영상 생성/관리 영상 재사용 DB는 사용하지 않고 `official_contents`로 대체 |
| `product_models.json` | 2 | 기초 샘플, 모델별 reference asset 확장 필요 |
| `part_maps.json` | 5 | 기초 샘플, 에어컨 3개 구조 타입과 전체 제품군 확장을 위한 part map versioning 필요 |
| `ar_guide_steps.json` | 11 | 기초 샘플, 에어컨 3개 구조 타입 및 제품군/절차별 AR guide step 확장 필요 |
| `ar_session_logs.json` | 2 | 기초 샘플, step별 상세 로그와 safety audit 분리 필요 |

현재 SQLite schema에 존재하는 테이블:

```text
users
devices
usage_logs
smart_diagnosis_results
environment_contexts
official_assets
care_videos  # 최종 기준 폐기 대상. 다음 DB 정리 단계에서 제거 필요
product_models
part_maps
ar_guide_steps
ar_session_logs
```

15-1 DB schema 확장으로 추가된 DB 구조:

```text
chat_sessions
chat_messages
conversation_state
official_document_chunks
rag_search_logs
safety_audit_logs
intent_risk_test_cases
intent_risk_eval_results
official_contents
part_map_versions
reference_images
```

이번 15-1 작업으로 위 구조는 `schema.sql`, mock JSON, seed script, repository 조회 함수에 반영되었다. 2026-06-03 실제 근거 기반 재구축으로 아래 데이터도 SQLite에 적재했다.

```text
users: 120
devices: 240
usage_logs: 720
smart_diagnosis_results: 480
environment_contexts: 50
official_assets: 791
official_document_chunks: 1,890
intent_risk_test_cases: 147
intent_risk_eval_results: 0
```

남은 후속 고도화:

```text
intent/risk 평가 실행 및 accuracy/precision/recall/confusion matrix 산출
RAGService 실제 검색 로직 구현
AI 판단엔진 v2 연결
평가 리포트 생성
```

따라서 1단계 상태는 아래처럼 관리한다.

```text
1 | DB | 실제 근거 기반 mock 데이터와 SQLite 기반 구축 | 15-2-B 데이터 재구축 수행됨 / 15-3 평가셋 구축·평가 실행은 다음 단계
```

## 5. 2단계: 백엔드 API

### 5.1 목표

프론트엔드, 챗봇, AI 판단엔진, ARGuidePlan, AR 세션 저장을 연결하는 API 서버를 만든다.

### 5.2 현재 API

| Method | Path | 역할 |
|---|---|---|
| `GET` | `/api/health` | 서버 상태 확인 |
| `GET` | `/api/demo/context` | mock 사용자/제품/로그 조회 |
| `POST` | `/chat/messages` | 챗봇 메시지 → 판단 → ARGuidePlan → overlay data |
| `POST` | `/ai/analyze` | AI 판단 결과만 반환 |
| `POST` | `/ar/guides/plan` | ARGuidePlan 생성 |
| `POST` | `/ar/sessions` | AR 세션 시작 |
| `GET` | `/ar/sessions/{session_id}` | AR 세션 조회 |
| `PATCH` | `/ar/sessions/{session_id}` | AR 세션 진행 상태 저장 |

### 5.3 현재 상태

현재 산출 파일:

최종 산출물 기준으로는 Chatbot/RAG/LLM 서비스 계층 분리와 API 스키마 고정이 필요하다.

```text
04_AR가이드/backend/server.py
```

### 5.4 다음 백엔드 작업

1. API request/response schema 문서화
2. `ChatbotEngine` 클래스 분리
3. `RAGService` 클래스 추가
4. `LLMService` 클래스 추가
5. `ThinQMockAdapter` 클래스 분리
6. 오류 응답 표준화
7. API 테스트 스크립트 작성

## 6. 3단계: 프론트엔드

### 6.1 목표

최종 ThinQ 앱 내 챗봇 경험을 가정해, 로컬 개발 환경에서는 자체 챗봇 화면과 AR Guide Session 화면을 구현한다.

### 6.2 현재 화면

현재 프론트는 다음 구조다.

```text
왼쪽: 챗봇 입력/메시지 패널
오른쪽: AR Guide Session 패널
```

현재 구현:

| 기능 | 상태 |
|---|---|
| 챗봇 입력창 | 구현 |
| 샘플 문의 버튼 | 구현 |
| API 연결 상태 표시 | 구현 |
| 등록 제품 표시 | 구현 |
| Low Risk AR 화면 | 구현 |
| High Risk A/S 연결 화면 | 구현 |
| 실제 reference image 표시 | 구현 |
| Part Map overlay | 구현 |
| 이전/다음 단계 이동 | 구현 |

### 6.3 현재 파일

```text
05_프론트엔드/index.html
05_프론트엔드/static/app.js
05_프론트엔드/static/styles.css
05_프론트엔드/static/assets/reference/*.jpeg
05_프론트엔드/static/assets/reference/*.png
```

### 6.4 다음 프론트 작업

1. 화면 상태 타입 분리
   - `idle`
   - `analyzing`
   - `clarifying`
   - `ar_ready`
   - `ar_running`
   - `completed`
   - `high_risk_service_route`

2. 챗봇 UI 고도화
   - 대화 상태 표시
   - 추가 질문 카드
   - 공식자료 근거 카드
   - AR 시작 버튼
   - A/S 연결 버튼

3. AR UI 고도화
   - 단계 진행률
   - 완료 화면
   - 해결됨/해결 안 됨 버튼
   - 좌표 보정 모드

## 7. 4단계: 챗봇 대화 엔진

### 7.1 목표

현재는 챗봇이 학습된 상태가 아니라 rule 기반 API mock이다. 다음 단계에서는 챗봇이 대화 상태를 유지하고, 모호한 문의에 추가 질문을 던질 수 있어야 한다.

### 7.2 챗봇 엔진 역할

| 역할 | 설명 |
|---|---|
| intent 후보 분류 | 관리 문의 / 자가점검 / High Risk / 범위 외 |
| slot 추출 | 증상, 냄새 종류, 발생 시점, 제품 상태 |
| 추가 질문 | 정보가 부족하면 안전 질문 우선 |
| 대화 상태 저장 | multi-turn 문의 처리 |
| 판단엔진 호출 준비 | 정리된 context를 AI 판단엔진에 전달 |

### 7.3 다음 구현 파일

예상 파일:

```text
03_AI로직/chatbot/chatbot_engine.py
03_AI로직/chatbot/conversation_state.py
03_AI로직/chatbot/dialogue_rules.json
```

### 7.4 우선 구현해야 할 대화 예시

```text
사용자: 냄새가 나요.
챗봇: 타는 냄새인가요, 곰팡이 냄새인가요?

사용자: 곰팡이 냄새 같아요.
챗봇: 필터 청소와 송풍구 표면 점검을 안내할 수 있습니다.

사용자: 타는 냄새예요.
챗봇: 안전을 위해 AR 안내를 중단하고 A/S 연결을 도와드릴게요.
```

## 8. 5단계: LLM 기반 대화 응답

### 8.1 목표

LLM은 고객에게 자연스럽게 답변하고, 문의 내용을 요약하며, 필요한 추가 질문을 생성한다.

단, LLM은 최종 안전 판단을 하지 않는다. 최종 판단은 rule 기반 safety layer와 공식자료 matching 결과가 결정한다.

### 8.2 LLM 역할

| 역할 | 허용 여부 |
|---|---|
| 고객 문장 요약 | 허용 |
| 추가 질문 생성 | 허용 |
| 고객 안내 문장 생성 | 허용 |
| 다국어 번역 | 허용 |
| 공식자료 없는 절차 생성 | 금지 |
| High Risk를 Low Risk로 낮추기 | 금지 |
| 임의 수리 절차 생성 | 금지 |

### 8.3 구현 방향

1. 개발 단계
   - API 비용 절약을 위해 `LLMService`를 mock 모드로 먼저 구현
   - 나중에 OpenAI API 또는 사내 LLM API 연결

2. 최종 구조
   - LLM 응답은 `safety_guard`를 통과해야 고객에게 표시
   - 공식자료 근거 없는 안내는 차단

예상 파일:

```text
03_AI로직/llm/llm_service.py
03_AI로직/llm/prompts/chatbot_system_prompt.md
03_AI로직/llm/safety_guard.py
```

## 9. 6단계: RAG 기반 공식문서 검색

### 9.1 목표

고객 모델명과 문의 내용을 기준으로 공식 매뉴얼/FAQ/지원 페이지/제품 이미지를 검색하고, AR 제공 근거를 확보한다.

### 9.2 RAG가 필요한 이유

순수 LLM만 사용하면 공식 매뉴얼에 없는 절차를 만들어낼 수 있다. 따라서 AR 안내는 반드시 공식자료 검색 결과에 근거해야 한다.

### 9.2-A LLM API와 embedding model/API 역할 분리

LLM과 embedding model은 같은 역할이 아니다.

```text
LLM API
-> 고객 문의 이해
-> 증상/제품/위험 신호 slot 추출
-> 추가 질문 생성
-> 고객 응답 문장 생성
-> 다국어 응답 보조

Embedding model/API
-> 공식자료 chunk와 고객 문의를 검색용 숫자 벡터로 변환
-> RAG vector search 품질을 결정
```

초기 RAG는 학습된 semantic embedding model을 사용하지 않고 `careshot_local_hashing_v1` 계열의 로컬 해싱 기반 embedding function으로 512차원 vector를 생성했다. 2026-06-11 기준으로는 선택지 B를 채택해 로컬 오픈소스 embedding model `BAAI/bge-m3`를 추가 적용했다.

최신 기준:

```text
공식자료 chunk
-> LocalModelEmbeddingProvider(BAAI/bge-m3)
-> OFFICIAL_DOCUMENT_EMBEDDING에 1024차원 dense vector 저장
-> query도 같은 BGE-M3 provider로 벡터화
-> embedding_model='BAAI/bge-m3' row만 vector similarity 비교
-> metadata strict filter + vector similarity + lexical fallback 유지
```

기존 `careshot_local_hashing_v1` embedding row는 삭제하지 않고 fallback/backup으로 유지한다. 운영 실행 시에는 아래 env를 사용한다.

```text
CARESHOT_EMBEDDING_PROVIDER=local_model
CARESHOT_EMBEDDING_MODEL=BAAI/bge-m3
```

LLM API와 embedding model은 여전히 분리한다. LLM API는 고객 문장 이해, slot 추출, 추가 질문, 응답 문장 생성을 보조하고, RAG 검색 벡터는 BGE-M3 또는 향후 선택한 별도 embedding model/API가 담당한다.

고도화 선택지는 아래처럼 정리한다.

```text
선택지 A: LLM API + embedding API
- 자연어 이해/응답은 LLM API 사용
- RAG vector는 embedding API로 재생성
- 품질은 좋지만 외부 API 비용/키 관리 필요

선택지 B: LLM API + 로컬 오픈소스 embedding model
- 자연어 이해/응답은 LLM API 사용
- RAG vector는 BGE/E5 계열 로컬 embedding model로 생성
- API 비용은 줄지만 로컬 실행 환경/모델 관리 필요

선택지 C: LLM API + 현재 로컬 해싱 embedding function 유지
- 가장 빠르고 비용 없음
- MVP는 가능하지만 semantic RAG 품질 주장은 제한적으로 해야 함
```

중요 원칙:

```text
LLM API를 붙인다고 embedding vector가 자동으로 좋아지는 것은 아니다.
RAG vector search를 고도화하려면 별도의 embedding model/API를 선택하고,
기존 OFFICIAL_DOCUMENT_CHUNK를 같은 embedding model로 재임베딩해야 한다.
```

따라서 현 단계 결정은 아래와 같다.

```text
현재 MVP:
- 외부 LLM API는 아직 미구현
- 비용 없는 `LLMServiceMock`과 provider 교체 경계는 20단계에서 구현
- RAG는 로컬 오픈소스 embedding model `BAAI/bge-m3` 기반 vector search로 동작
- 기존 로컬 해싱 embedding은 fallback/backup으로 유지
- 발표에서는 "LLM API + 로컬 오픈소스 embedding model 기반 RAG"로 설명

후속 고도화:
- LLM API를 slot 추출/응답 생성 보조에 붙인다.
- RAG 품질이 부족하면 OpenAI embeddings 등 embedding API 또는 다른 BGE/E5 계열 모델로 OFFICIAL_DOCUMENT_EMBEDDING을 재생성한다.
```

2026-06-11 선택지 B 구현 결과:

```text
EmbeddingProvider interface 추가
- HashingEmbeddingProvider: careshot_local_hashing_v1, 512차원 sparse vector, fallback/backup
- LocalModelEmbeddingProvider: BAAI/bge-m3, 1024차원 dense vector

재임베딩 대상
- 현재 DB 기준 OFFICIAL_DOCUMENT_CHUNK: 1,997건
- 기존 문서의 1,890건은 공식 YouTube/추가 공식자료 확장 전 수치

재임베딩 결과
- OFFICIAL_DOCUMENT_EMBEDDING / BAAI/bge-m3 / embedded: 1,997건
- OFFICIAL_DOCUMENT_EMBEDDING / careshot_local_hashing_v1 / embedded: 1,997건 유지
- BGE-M3 누락 official chunk: 0건
- sample vector dimension: 1024

RAG 품질 재검증
- scripts/validate_rag_quality.py
- BGE-M3 40 query 검증: 40/40 통과
- top1 procedure accuracy: 1.0
- official URL only: 통과
- safe flow에 high-risk 근거 혼입 없음
- power_troubleshooting에 filter_cleaning 혼입 없음
- 결과 파일: 06_산출물/RAG_BGE_M3_40쿼리_검증결과_2026-06-11.json
```

### 9.3 RAG 처리 순서

```text
제품 모델명 확인
→ 공식자료 DB strict filter
→ procedure 후보 검색
→ 관련 문서 chunk 검색
→ 근거 asset_id / chunk_id 반환
→ 판단엔진에 전달
```

### 9.4 검색 기준

| 기준 | 설명 |
|---|---|
| exact model | 모델명 완전 일치 |
| official alias | 공식 alias 일치 |
| series | 공식 series 일치 |
| product_type_common | 제품군 공통 절차 |

금지 범위:

```text
전기 수리
냉매
PCB
배선
컴프레서
내부 분해
가스 누출
화재/연기/스파크
```

### 9.5 다음 구현 파일

```text
03_AI로직/rag/rag_indexer.py
03_AI로직/rag/rag_search.py
03_AI로직/rag/rag_sources_manifest.json
02_데이터연동/mock_data/official_document_chunks.json
```

## 10. 7단계: AI 판단엔진

### 10.1 목표

챗봇, LLM, RAG, ThinQ mock, 환경 데이터, 사용 로그, 스마트 진단 결과를 종합해 최종 action을 결정한다.

### 10.1-A 현재 "AI 판단엔진" 명칭의 의미와 한계

현재 구현된 판단엔진은 학습 기반 AI 모델이 아니다. 고객 문의를 이해해 스스로 학습·추론하는 모델이 아니라, 사람이 정의한 키워드, 조건문, threshold, 공식자료 검증 규칙으로 동작하는 `rule-based decision engine`이다.

현재 동작 방식:

```text
1. 고객 문의 문장에 특정 키워드가 있는지 확인
2. DB에서 제품, 사용로그, 스마트진단, 환경, 공식자료 context 조회
3. 정해둔 rule로 self_care / self_as / expert_as 결정
4. procedure_type 결정
5. risk_level 결정
6. AR template 후보 조회
7. High Risk 또는 공식자료 근거 없음이면 AR 생성 차단
```

따라서 현재 단계에서는 아래 표현을 사용한다.

```text
정확한 표현: rule 기반 판단엔진, DecisionEngine rule version, AI 판단엔진 1차 mock/rule version
부정확한 표현: 학습된 AI 모델, 자동 학습 모델, AI가 AR을 생성
```

현재 "AI"라는 명칭은 최종 서비스 아키텍처에서 LLM/분류 모델/RAG/safety policy가 연결될 수 있는 위치를 의미한다. 하지만 현재 코드 구현체는 학습 모델이 아니라 deterministic rule engine이다.

학습 기반 모델은 현 단계 필수 구현물이 아니다. 학습 기반 intent/risk classifier를 만들려면 먼저 26단계의 VOC intent/risk 평가셋 라벨링과 27단계의 EvaluationService/정확도 리포트가 필요하다. 그 전에는 학습 모델을 새로 만들지 않고, rule 기반 판단엔진 + RAG 공식근거 + safety rule + LLM adapter/mock 조합으로 개발한다.

LLM API를 도입하더라도 LLM은 AR 허용 여부를 최종 결정하지 않는다.

```text
LLM이 담당하는 일
- 고객 문장 이해
- 증상/제품/위험 신호 slot 추출
- 추가 질문 생성
- 고객 응답 문장 생성
- 다국어 응답 보조

LLM이 담당하지 않는 일
- High Risk 최종 차단 여부 결정
- AR Guide 허용 여부 최종 결정
- 공식자료 없는 절차 생성
- 부품 위치/좌표 생성
- 내부 분해/전기/냉매/PCB 등 안전 민감 절차 임의 생성
```

최종 AR 허용 여부는 아래 조합으로 결정한다.

```text
Rule/Safety Guard
+ RAG 공식자료 근거
+ High Risk 차단 규칙
+ 공식자료 match 여부
+ AR_TARGET/AR_GUIDE/reference image 준비 여부
```

따라서 LLM은 후보/보조 정보를 제공하고, `DecisionEngine`과 safety layer가 최종 action을 확정한다.

### 10.2 판단엔진 입력

```text
사용자 문의
대화 상태
제품 정보
사용 로그
스마트 진단
환경 데이터
RAG 검색 결과
공식자료 match 결과
```

### 10.3 판단 결과

| 결과 | 설명 |
|---|---|
| `prepare_ar_guide_session` | AR Guide 제공 가능 |
| `provide_official_content` | 공식 콘텐츠만 제공 |
| `ask_clarifying_question` | 추가 질문 필요 |
| `route_to_service` | High Risk A/S 연결 |
| `blocked_official_match_failed` | 공식자료 근거 부족 |

### 10.4 현재 상태

현재 파일:

```text
03_AI로직/rules/ai_decision_engine.py
```

현재는 rule 기반 1차 판단엔진이다. 다음에는 챗봇/RAG 결과를 입력으로 받도록 확장한다.

## 11. 8단계: ARGuidePlan 생성

### 11.1 목표

판단엔진이 AR 제공 가능하다고 결정하면, 제품 구조와 절차에 맞는 AR Guide Plan을 생성한다.

### 11.2 처리 순서

```text
decision_result 확인
→ High Risk 차단 여부 확인
→ 공식자료 match 확인
→ product_type + procedure_type 기반 guide 선택
→ product_model reference image 확인
→ part_maps 연결
→ ar_guide_steps 연결
→ AROverlayData 반환
```

### 11.3 현재 파일

```text
03_AI로직/rules/ar_guide_template_selector.py
02_데이터연동/mock_data/product_models.json
02_데이터연동/mock_data/part_maps.json
02_데이터연동/mock_data/ar_guide_steps.json
```

## 12. 9단계: AR 화면/오버레이

### 12.1 목표

Reference Image 기반으로 고객에게 어느 부품을 누르고, 열고, 빼고, 닦아야 하는지 시각적으로 안내한다.

### 12.2 현재 AR 방식

```text
실제 또는 데모용 reference image
→ Part Map 좌표
→ 현재 step target_part
→ overlay box / arrow / label 표시
```

### 12.3 현재 구현 상태

현재는 AS-Q24ENXE 에어컨 필터 청소 시나리오를 기준으로 구현되어 있다.

현재 reference:

```text
05_프론트엔드/static/assets/reference/as_q24enxe_reference_cover_open_filter_visible.png
```

### 12.4 다음 AR 작업

1. Part Map 좌표 보정 UI
2. overlay type 다양화
3. 실제 카메라처럼 보이는 UI
4. 완료/중단/해결 여부 흐름
5. 다른 제품군으로 확장

## 13. 10단계: 안전 검증/품질 검증

### 13.1 목표

AR 안내가 공식자료와 일치하고, 위험 행동을 유도하지 않으며, overlay 좌표가 정확한지 검증한다.

### 13.2 검증 항목

| 검증 | 내용 |
|---|---|
| 공식자료 검증 | 근거 asset_id가 있는지 |
| 위험도 검증 | High Risk 차단 여부 |
| 좌표 검증 | Part Map이 실제 부품 위치와 맞는지 |
| 금지 행동 검증 | 내부 분해/전기/냉매 안내가 없는지 |
| 대화 검증 | 모호한 문의에 추가 질문을 하는지 |
| 다국어 검증 | 안전 문구가 잘못 번역되지 않는지 |

## 14. 11단계: 발표용 시연 구성

### 14.1 정상 관리 시나리오

```text
사용자: Please help me clean the AC filter.
→ 관리 문의 분류
→ Low Risk
→ AS-Q24ENXE exact model 공식자료 match
→ AR Guide Session 준비
→ 커버 열린 reference image 표시
→ 내부 필터 하이라이트
→ 단계별 안내
```

### 14.2 High Risk 시나리오

```text
사용자: There is smoke and a burning smell from the AC.
→ High Risk 감지
→ AR 차단
→ expert A/S 연결 카드 표시
```

### 14.3 모호한 문의 시나리오

```text
사용자: 냄새가 나요.
→ 챗봇 추가 질문
→ 타는 냄새면 A/S
→ 곰팡이 냄새면 필터 청소/송풍구 표면 점검 AR
```

이 시나리오는 19. ConversationState 기반 multi-turn 추가 질문 구현에서 5개 모호 문의 테스트로 추가 검증했다.

## 15. 지금부터의 실제 개발 순서

현재는 실제 데이터 수집 파이프라인, SQLite/PostgreSQL 적재, LG India 공식자료 기반 RAG 데이터 구축 고도화, AS-Q24ENXE support/FAQ 누락분 추가 수집, 공식 YouTube 근거 확장, BGE-M3 로컬 embedding 전환, RAGService v2 품질 재검증, FastAPI/repository/PostgreSQL 전환, EnvironmentDataAdapter, CareRiskScoreEngine, GuideOptionSet, Device Care History, ChatbotEngine 1차 구현, ConversationState 기반 multi-turn 추가 질문 구현, LLMServiceMock/adapter 경계 구현, DecisionEngineV2 및 ARGuidePlan 연결까지 수행된 상태다.

AS-Q24ENXE support/FAQ 간극 검증 결과 544개 공식 support 후보 중 510개가 누락되어 있었고, 누락분 추가 수집에서 484개 asset과 762개 chunk를 추가했다. 이후 공식 YouTube 근거까지 포함되면서 현재 SQLite 기준 공식자료 chunk는 1,997건이다. RAGService v2 검색 품질은 BGE-M3 기준 동일 40개 query set 재검증에서 40개 모두 통과했다. 현재 기준 22. React + TypeScript 프론트 전환은 FastAPI 실제 호출과 회원가입 DB 연동까지 부분 수행되었고, 남은 작업은 제품 코드 등록 시연 흐름, AR asset 보강, 23~24번 화면 QA다.

여기서 용어를 분리한다.

| 용어 | 의미 | 현재 상태 |
|---|---|---|
| RAG 데이터 구축 고도화 | LG India 공식 PDF(Owner's Manual/Spec/Dimension 포함), Online Manual, FAQ, Help Library, 지원 페이지를 추가 수집하고 본문을 chunk화하는 작업 | 수행됨 / AS-Q24ENXE support/FAQ 누락분 484 asset, 762 chunk 추가 |
| Embedding/Vector DB 구축 | 정제된 chunk를 embedding 모델로 벡터화하고 Vector DB 또는 vector index에 저장하는 작업 | 수행됨 / BAAI/bge-m3 1,997건 embedded, 기존 careshot_local_hashing_v1 1,997건 fallback 유지 |
| RAGService 고도화 | Vector DB와 metadata strict filter를 이용해 검색하고 evidence bundle을 반환하는 서비스 고도화 | v2 구현됨 / BGE-M3 기준 검색 품질 재검증 40/40 통과 |
| ChatbotEngine | 고객 문의를 받아 slot 추출, 추가 질문, RAG 검색 호출, DecisionEngine 호출, 고객 응답 생성을 조율하는 대화 엔진 | 구현됨 / CHAT_SESSION, CHATBOT_INQUIRY, AI_INQUIRY_ANALYSIS, CHAT_MESSAGE, CONVERSATION_STATE, RAG_SEARCH_LOG 연동 및 5개 multi-turn 시나리오 검증 |
| LLM/챗봇 모델 | 자연어 이해, 요약, 답변 문장 생성, 다국어 출력에 쓰이는 모델 또는 model adapter | `LLMServiceMock` 구현됨 / 외부 LLM API는 후속, embedding은 로컬 BGE-M3 구현됨 |

Embedding/Vector DB 구축과 RAGService v2 구현은 수행되었다. 현재는 공식자료 chunk 1,997건이 `OFFICIAL_DOCUMENT_EMBEDDING` 테이블에 `BAAI/bge-m3` 1,997건과 `careshot_local_hashing_v1` 1,997건으로 연결되어 있고, RAGService v2가 metadata strict filter, BGE-M3 vector similarity search, lexical fallback을 사용한다.

현재 완료된 데이터 기준:

```text
VOC 원천 풀: 500건
환경 context: 50개 도시 / 350 row
LG India 공식자료: 791건
LG India 공식문서 chunk: 1,997건
BGE-M3 embedding: 1,997건
hashing fallback embedding: 1,997건
ThinQ 근거 기반 synthetic mock: users 120, devices 240, usage_logs 720, smart_diagnosis_results 480
intent/risk 평가셋: 0건, 현 단계 미수행
```

따라서 지금부터의 실제 개발 순서는 아래 최신 목록을 기준으로 한다. 아래 목록은 2026-06-12 현재 수행/검증 상태를 반영한 운영용 진행표다.

```text
1. 수집 파이프라인 검증 리포트 생성 - 수행됨
2. LG India 공식자료 chunk 재정제 - 수행됨
3. RAGService 1차 구현 - 수행됨
4. RAG 데이터 구축 고도화 - 수행됨 / 공식 PDF, Online Manual, FAQ, Help Library, 제품 페이지 수집
5. RAG chunk 검수 및 evidence set 구축 - 수행됨 / 확대 검증 실패 케이스 보정 완료
6. Embedding/Vector DB 구축 - 수행됨 / 초기 careshot_local_hashing_v1 1,890건 구축
7. RAGService v2 구현 - 수행됨 / metadata strict filter + vector similarity + lexical fallback
8. AS-Q24ENXE support/FAQ 전체 수집 간극 검증 - 수행됨 / 544 후보 중 누락 510건 확인
9. 공식 FAQ/Help Library 누락분 추가 수집 - 수행됨 / 484 asset, 762 chunk 추가
10. 신규 chunk embedding 재생성 - 수행됨 / 초기 1,890 chunk, 1,890 embedding 확인
11. RAGService v2 검색 품질 검증 - 수행됨 / 40개 query 통과
12. RAGService v2 실패 케이스 보정 - 수행됨 / 재검증 40/40 통과
13. FastAPI 백엔드 구조 전환 - 수행됨 / OpenAPI, live HTTP RAG 40/40 통과
14. SQLAlchemy repository 계층 작성 - 수행됨 / SQLite/PostgreSQL registry 검증 완료
15. PostgreSQL + pgvector 최종 DB 전환 - 수행됨 / seed, HNSW index, RAG top-k, SQLite 비교 검증 완료
15.2 PostgreSQL 운영 안정화 및 Alembic migration 관리 전환 - named volume 적용 완료 / Alembic baseline 후속 관리 필요
15.3 PostgreSQL FK migration 적용 - 수행됨 / FK 후보 103개 중 101개 적용, reference image asset 미연결 2개 보류
16. EnvironmentDataAdapter 구현 - 수행됨 / cache hit, external refresh, fallback, fetch log, Care Risk 전달 검증
16.2 EnvironmentDataAdapter 운영 보완 실행 - 수행됨 / provider adapter, API key manager, hard water source, fallback live 검증
17. CareRiskScoreEngine 및 Guide 옵션 API 구현 - 수행됨 / usage log + 환경 데이터 기반 self care 추천 조건 계산 검증, AQI 가중치 보정 완료
17.1 서비스 명칭/제공 방식/이력 저장 정책 변경 반영 - 수행됨 / self_care, self_as, expert_as 용어 통일
17.1-A GuideOptionSet 및 Guide 완료 API 재정리 - 수행됨 / options API, 완료 이력 저장 API 검증
17.2 Product Code Registry 및 제품 등록 흐름 설계/DB 반영 - 수행됨 / 검증 완료
17.3 Device Care History 조회 View/API 구현 - 수행됨 / 검증 완료
17.4 최종 21개 테이블 구조 기준 전체 검증 - 수행됨 / SQLite, schema, API, pytest 기준 검증
17.5 공식 YouTube RAG 근거 확장 - 수행됨 / official_youtube asset, chunk, embedding, manual guide 연결
17.6 power_troubleshooting 제한 AR/동적 매뉴얼 보강 - 수행됨 / filter_cleaning 혼입 차단 검증
18. ChatbotEngine 구현 - 수행됨 / /api/v1/chat/messages 통합, session/message/inquiry/analysis/state/log 저장
18.1 ChatbotEngine 최종 21개 테이블 정합 보정 - 수행됨 / decision_logs 미사용, AI_INQUIRY_ANALYSIS.intent_type 기준 저장
18.2 service_flow_type 보정 - 수행됨 / self_care, self_as, expert_as 분기 및 응답 필드 검증
18.3 AR 선행 수집 데이터 정의 - 수행됨 / 제품 정보, 공식자료, AR_TARGET, AR_GUIDE, reference image, overlay mapping 수집 항목 문서화
18.4 LLM과 embedding 역할 분리 문서화 - 수행됨 / LLM은 AR 허용 최종 결정 불가, Rule/Safety/RAG가 최종 gate
18.5 로컬 BGE-M3 embedding 전환 - 수행됨 / BAAI/bge-m3 1,997건 embedded, hashing fallback 1,997건 유지
18.6 BGE-M3 RAG 품질 재검증 - 수행됨 / 40/40 통과, top1 accuracy 1.0, official URL only, high-risk 혼입 없음
19. ConversationState 기반 multi-turn 추가 질문 구현 - 수행됨 / 5개 모호 문의 추가 질문 후 최종 intent/risk/procedure 확정 검증
20. LLMServiceMock 또는 LLM API adapter 구현 - 수행됨 / mock provider, prompt/output schema, ChatbotEngine 연동 검증
21. DecisionEngineV2 구현 및 판단엔진 v2 -> ARGuidePlan 연결 - 수행됨 / v1 fallback, v2 input/output schema, RAG/LLM/slot/context 결합, ARGuidePlan 연결 검증
22. React + TypeScript 프론트 전환 - 수행 중 / FastAPI 실제 호출, Home/Chat/ARGuide/API client/회원가입 DB 연동 검증 완료
22.1 프론트 원본 도입 및 백업 - 수행됨 / GitHub frontend 원본 보존, 로컬 React/Vite 앱 구성
22.2 백엔드 프론트 호환 API 추가 - 수행됨 / `/api/users/*`, `/api/devices`, `/api/chat-messages`, `/api/ai/chat`
22.3 프론트 fetch 전환 - 수행됨 / user, device, chat, care risk, environment, AR guide API 호출
22.4 회원가입/로그인/프로필 DB 연동 - 수행됨 / `USER` 저장, `USER_PRODUCT` 및 demo ThinQ log seed 생성
22.5 프론트 원본 UI 보호 및 데이터 주입 정리 - 수행됨 / UI 구조 변경 금지, 승인된 데이터 치환만 유지
22.6 제품 코드 등록 시연 흐름 - 후속 필요 / `PRODUCT` master 조회 -> `USER_PRODUCT` 연결 흐름 미구현
22.7 AR reference image 정적 서빙 및 part map 좌표 seed - 후속 필요
23. 프론트 챗봇 UI를 multi-turn + 공식근거 카드 구조로 변경 - 수행 중 / 자유입력 추가 질문, 저정보 문의 추가질문 guard, API 기반 YouTube+단계 가이드 표시, 전원 문의 risk/detail 분리 검증
23-1. self care 예방 알림 UI 구현 - 부분 수행 / Care Risk API 연결, 문구/근거 정합성 보강 중
24. 안전 차단 카드 / expert A/S 연결 카드 / AR 시작 카드 정리 - 수행됨 / High Risk, no-match, Low/Medium 화면 분기 검증 완료
25. RAG 연결 후 intent/risk 평가 기준 확정 - 수행됨 / 2026-06-12 검증 완료
26. VOC 원천 풀에서 intent/risk 평가셋 별도 라벨링 - 수행됨 / 2026-06-12 검증 완료
27. EvaluationService 구현 및 정확도 리포트 생성 - 수행됨 / 147건 평가 실행, 정확도 리포트 저장, 실패 케이스 분류 완료
28. 정상/모호/Medium/High Risk/매칭 실패/self care 알림/expert A/S 시나리오 검증 - 수행됨 / 7개 시나리오 자동검증, QA 리포트, 화면 캡처 생성 완료
29. AR 오버레이 정확도 검수 - 다음 작업
30. 발표용 UI와 산출물 정리 - 후속
```

### 26.6 전원 꺼짐 UI 검증 및 동적 매뉴얼 범위 확장 - 완료

작업 내용:

```text
1. 전원 꺼짐 영어/한국어 문의 UI 검증
2. 동적 매뉴얼 생성 범위 확장
3. static 검증 프론트 GuideOptionSet 표시 보강
4. 개발 완료 MD 생성
5. 완성 React/Vite 프론트 연동은 후속 작업으로 명시
```

전원 꺼짐 검증:

```text
The AC power suddenly turns off.
에어컨 전원이 갑자기 꺼져요.

procedure_type: power_troubleshooting
service_flow_type: self_as
ar_scope: external_safe_check_only
manual_count: 1
youtube_count: 2
ar_count: 1
filter_cleaning 표시: False
```

동적 매뉴얼 생성 범위:

```text
power_troubleshooting
no_cooling_self_check
odor_self_check
water_leak_monsoon
noise_self_check
remote_operation
auto_clean
```

프론트 정책:

```text
현재 React/Vite 프론트는 `05_프론트엔드/react-vite/` 기준으로 도입되어 FastAPI 실제 호출까지 부분 연결됨.
이 항목의 static HTML/JS 검증 데모 기록은 2026-06-12 이전 상태의 이력으로 보존한다.
GuideOptionSet 기반 실제 프론트 연동은 22단계에서 진행되었고, 세부 화면 QA는 23~24번에서 계속 검증한다.
MindAR 모바일 카메라 MVP는 web-ar-mvp 같은 별도 폴더로 진행.
```

검증:

```text
python -m pytest tests -q
-> 34 passed, 1 skipped
```

산출물:

```text
06_산출물/2026-06-11_CareShot_AR_개발완료_정리.md
06_산출물/power_troubleshooting_static_ui_verify.png
```

### 15.1 13~30 단계 상세 개발 정의

13번부터는 단순 기능 추가가 아니라 백엔드, DB, AI 판단, 챗봇, 프론트, AR 검증을 하나의 제품 흐름으로 묶는 단계다. 현재 13~21단계와 25~26단계는 수행 및 검증 완료되었고, 22단계는 React/Vite 프론트와 FastAPI 연결, 회원가입 DB 저장, Care Risk/환경/ARGuide API 연결까지 부분 수행되었다. 남은 핵심 작업은 제품 코드 등록 시연 흐름, AR reference image 정적 서빙, part map 좌표 seed, 23~24번 화면 QA와 카드 분기 정리다.

13. FastAPI 백엔드 구조 전환 - 수행됨 / FastAPI 서버 기동, OpenAPI 생성, live HTTP 기준 RAG 40/40 통과
   - 기존 Python 기본 HTTP 서버를 FastAPI app 구조로 전환
   - `/api/v1/chat/messages`, `/api/v1/ai/analyze`, `/api/v1/rag/search`, `/api/v1/ar/plans`, `/api/v1/ar/sessions`, `/api/v1/guides/options`, `/api/v1/guides/{guide_id}/complete` 라우터 분리
   - Pydantic request/response schema를 공통 스키마와 맞춤
   - RAGService v2, DecisionEngine, ARGuide selector를 dependency로 주입할 수 있게 구성
   - 산출물: `04_백엔드/app/main.py`, `routers/`, `schemas/`, `services/`, FastAPI 실행 로그
   - 완료 기준: FastAPI 서버 기동, OpenAPI 문서 생성, 기존 RAG 검색 40개 query가 API 호출 기준으로도 통과
   - 검증 결과: `http://127.0.0.1:8790` live HTTP 서버 기준 `/api/v1/rag/search` 40개 query 전부 통과

14. SQLAlchemy 또는 SQLModel repository 계층 작성 - 수행됨 / 검증 완료
   - SQLite 직접 조회 코드를 repository interface로 분리
   - `UserRepository`, `DeviceRepository`, `UsageLogRepository`, `EnvironmentRepository`, `ProductModelRepository`, `StructureTypeRepository`, `ReferenceImageRepository`, `PartMapRepository`, `OfficialAssetRepository`, `RAGRepository`, `ConversationRepository`, `CareHistoryRepository`, `ARSessionRepository`, `EvaluationRepository` 작성
   - SQLite와 PostgreSQL 구현체가 같은 메서드명을 쓰도록 구성
   - ThinQ 등록 제품에서 들어오는 `model_name`을 exact 기준으로 조회하고 `structure_type`을 반환하는 resolver repository 포함
   - 산출물: `repositories/`, DB session 관리 코드, repository 단위 테스트
   - 완료 기준: SQLite seed 데이터 791 asset, 1,890 chunk, 1,890 embedding을 repository로 조회 가능
   - 검증 결과: repository/postgres 관련 테스트 통과, SQLite seed 데이터 791 asset / 1,890 chunk / 1,890 embedding repository 조회 가능

15. PostgreSQL + pgvector 최종 DB 전환 - 수행됨 / 검증 완료
   - 개발 검증용 SQLite는 유지하고 최종 설계 DB를 PostgreSQL + pgvector로 전환
   - `official_document_embeddings`에 pgvector 컬럼 추가
   - HNSW 또는 IVFFLAT index 구성
   - 기존 seed JSON을 PostgreSQL에 적재하는 migration/seed script 작성
   - self care 추천형을 위해 환경 관측값, 사용 로그, Guide, SELF_MANAGEMENT_HISTORY 기반 계산 흐름을 포함
   - AR 확장을 위해 `structure_types`, `reference_images`, `part_map_versions`, `part_maps`, `ar_guide_templates`, `ar_guide_steps` 테이블을 모델/구조 타입 중심으로 재정의
   - 에어컨 구조 타입은 최소 `wall_mounted_ac`, `standing_ac`, `window_ac`를 포함
   - 산출물: `05_DB/postgres/schema.sql`, migration, seed script, pgvector 검증 리포트
   - 완료 기준: PostgreSQL에서 RAG top-k 검색 동작, SQLite 주요 query 결과와 비교 검증
   - 검증 결과: pgvector 0.8.2, HNSW index 존재, `official_document_embeddings` 1,890건, canonical AC 구조 타입 3건, SQLite 주요 count 비교 통과, RAG top-k `all_query_top1_matches: true`

15.2 PostgreSQL 운영 안정화 및 Alembic migration 관리 전환 - named volume 적용 완료 / Alembic baseline은 18단계 시작 전 수행
   - Docker compose에 `careshot_pgdata` named volume을 추가해 컨테이너 삭제 시에도 PostgreSQL data directory가 유지되도록 구성
   - 기존 실행 컨테이너가 anonymous volume을 쓰고 있었으므로 `pg_dump` 백업 후 compose 기반 named volume 컨테이너로 재생성하고 복원
   - 산출물: `05_DB/postgres/docker/docker-compose.yml`, `05_DB/postgres/backups/careshot_ar_before_named_volume_2026-06-05.sql`
   - 검증 결과: 현재 컨테이너 mount가 `docker_careshot_pgdata -> /var/lib/postgresql/data`로 전환됨, pgvector 0.8.2, `official_document_embeddings` 1,890건, RAG top-k `all_query_top1_matches: true`
   - Alembic 전환 시점: 지금의 `schema.sql`은 초기 구축/reset migration 성격이므로, 18단계 ChatbotEngine 구현 전에 Alembic baseline을 생성한다. 이후 chat/conversation/decision/evaluation 관련 DB 변경은 `DROP TABLE` 방식이 아니라 Alembic revision으로 누적 관리한다.
   - Alembic 전환 산출물 예정: `05_DB/postgres/alembic.ini`, `05_DB/postgres/alembic/env.py`, `05_DB/postgres/alembic/versions/0001_baseline_pgvector.py`, migration 실행/rollback 검증 리포트

15.3 PostgreSQL FK migration 적용 - 수행됨 / 검증 완료
   - FK 적용 전에 `verify_fk_integrity.py`로 실제 PostgreSQL seed 데이터 기준 참조 무결성을 검사했다.
   - 검사 결과: 후보 FK 103개 중 101개 통과, 2개 실패, 컬럼 부재 0개.
   - 실패 2개는 `product_models.product_image_asset_id -> official_assets.asset_id`, `reference_images.source_asset_id -> official_assets.asset_id`다. 현재 값 `OA_AC_ASQ24ENXE_IMAGE_001`은 AR reference image용 asset id이지만 `official_assets`에는 없으므로 FK 적용을 보류했다.
   - `004_add_fk_constraints.sql`에는 seed 위반 0건인 FK 101개만 반영했다.
   - PostgreSQL 적용 결과: `pg_constraint` 기준 FK 101개 생성.
   - migration idempotency 확인: 동일 migration 재실행 시 오류 없이 COMMIT.
   - repository/API 재검증: `test_environment_data_adapter.py`, `test_care_risk_engine.py`, `test_repositories_sqlalchemy.py`, `test_postgres_repository_pgvector.py` 총 18개 테스트 통과.
   - FastAPI RAG API 재검증: 40개 query 중 40개 통과.
   - 산출물: `05_DB/postgres/migrations/004_add_fk_constraints.sql`, `05_DB/postgres/scripts/verify_fk_integrity.py`, `05_DB/postgres/scripts/generate_fk_migration.py`, `05_DB/postgres/reports/fk_integrity_result_2026-06-05.json`, `05_DB/postgres/reports/fk_integrity_report_2026-06-05.md`.
   - 다음 보완 필요: reference image asset을 `official_assets`에 넣을지, 별도 `reference_image_assets` 또는 `product_code_official_assets` 매핑 테이블로 분리할지 결정 후 보류 FK 2개를 재검토한다.

16. EnvironmentDataAdapter 구현 - 수행됨 / 검증 완료
   - 환경 데이터는 최종 구조에서 외부 API를 실시간 또는 준실시간으로 조회한다.
   - 단, 매 요청마다 외부 API를 호출하지 않고 DB cache freshness를 먼저 확인한다.
   - 2026-06-15 보정: 기본 cache TTL을 180분에서 60분으로 낮췄다. `/environment/current` 또는 Care Risk 호출 시 TTL이 만료되었으면 외부 API를 호출해 DB에 저장한 뒤 응답한다.
   - 2026-06-15 보정: 서버 자동갱신을 추가했다. FastAPI lifespan background task가 서버 시작 후 `CARESHOT_ENV_AUTO_REFRESH_INITIAL_DELAY_SECONDS` 뒤 1회 실행되고, 이후 `CARESHOT_ENV_AUTO_REFRESH_INTERVAL_MINUTES` 기본 60분마다 환경 refresh target을 외부 API로 갱신해 DB에 저장한다.
   - 2026-06-15 보정: 자동갱신 target은 `Delhi/Delhi`, `Gujarat/Ahmedabad`를 우선 포함하고, 이후 USER/ENVIRONMENT_OBSERVATION 기반 지역을 이어 붙인다. 기본 provider는 key 없이 검증 가능한 `ENV_PROVIDER_OPENMETEO`다.
   - 역할 구분: lazy refresh는 사용자가 호출했을 때 만료 여부를 보고 갱신하는 흐름, server auto refresh는 사용자가 앱을 켜지 않아도 DB를 미리 최신화하는 흐름, frontend polling은 이미 켜진 화면이 최신 DB/API 값을 다시 받아 UI를 갱신하는 흐름이다.
   - 설정: `CARESHOT_ENV_AUTO_REFRESH_ENABLED=0`이면 서버 자동갱신을 끈다. `CARESHOT_ENV_AUTO_REFRESH_INTERVAL_MINUTES`, `CARESHOT_ENV_AUTO_REFRESH_PROVIDER`, `CARESHOT_ENV_AUTO_REFRESH_TARGET_LIMIT`로 주기/provider/target 수를 조정한다.
   - 2026-06-15 보정: `New Delhi`, `뉴델리` 입력은 `REGION.city = Delhi`로 정규화해 환경 API 조회, DB cache 조회, DB observation 저장이 같은 지역 기준으로 동작하도록 했다.
   - 입력: user_id, region, city, product_type, requested_metrics
   - 처리: provider 선택, API key 관리, cache TTL 확인, 외부 API 호출, 응답 정규화, fetch log 저장
   - 출력: temperature, humidity, AQI, PM2.5, PM10, rain/monsoon intensity, water hardness, observed_at, provider
   - 개발 단계에서는 기존 `environment_contexts`와 수집 데이터를 fallback cache로 사용한다.
   - 산출물: `EnvironmentDataAdapter`, `EnvironmentProvider` interface, `environment_observations`, `environment_api_fetch_logs`, `/environment/current`, `/environment/refresh`
   - 완료 기준: DB cache가 유효하면 cache를 쓰고, 만료 시 외부 API 호출 결과를 저장한 뒤 Care Risk 계산에 전달
   - 검증 결과: cache hit, 외부 API refresh, fallback cache, fetch log 저장, Care Risk 전달 검증 완료
   - 2026-06-15 검증: `/api/v1/environment/current?region=Delhi&city=New%20Delhi`가 `normalized_location.requested_city=New Delhi`, `normalized_location.city=Delhi`, `cache_ttl_minutes=60`, observation `city=Delhi`로 응답함을 TestClient smoke로 확인했다.
   - 2026-06-15 검증: `refresh_scheduled_environment_targets(provider_id="ENV_PROVIDER_OPENMETEO", limit=2)` smoke 결과 Delhi/Delhi, Gujarat/Ahmedabad 2건이 `failed_count=0`으로 refresh되었다.

16.1 EnvironmentDataAdapter 현재 검증 감사 및 보완 필요사항 - 2026-06-05 재검증
   - 실제 검증 결과: `/environment/current`는 fresh cache에서 `cache_hit` 반환, `/environment/refresh`는 외부 API 호출 후 `environment_observations`와 `environment_api_fetch_logs`에 저장, `/care/risk/evaluate`는 최신 observation을 받아 Care Risk 계산에 사용
   - PostgreSQL 확인 결과: `environment_observations` 4건, `environment_api_fetch_logs` 3건, 최신 observation `ENVOBS_E9D442A28271` 저장됨
   - 단위 테스트 결과: `test_environment_data_adapter.py` 포함 관련 테스트 `13 passed, 1 skipped`
   - 부족 1: provider table에는 `ENV_PROVIDER_OPENWEATHER`, `ENV_PROVIDER_WAQI`가 있으나, 현재 개발용 runtime provider는 API key 없이 검증 가능한 `OpenMeteoEnvironmentProvider`다. 요청 provider는 `ENV_PROVIDER_OPENWEATHER`로 기록되고 runtime provider는 response_summary에 남지만, 운영형 provider 연동은 아직 아님
   - 부족 2: API key 관리는 `OPENMETEO_API_KEY` 환경변수 읽기 수준이며, provider별 secret 관리/검증/회전 구조는 아직 없음
   - 부족 3: `water_hardness_level`은 외부 API에서 직접 받은 값이 아니라 `environment_contexts` fallback cache에서 보강한다. 운영형 경수 데이터 provider 또는 지역별 공식/통계 source 연동이 필요함
   - 부족 4: fallback cache 동작은 단위 테스트로 검증했지만, live API에서 외부 provider 장애를 강제로 발생시키는 통합 테스트는 아직 없음
   - 부족 5: `requested_metrics`는 요청/로그에 반영되지만 Open-Meteo adapter는 현재 고정 metric set을 조회한다. provider별 metric mapping을 더 엄격히 분리해야 함
   - 판단: 16단계의 개발 검증 완료 기준은 충족했지만, 최종 운영 안정화 기준에서는 provider별 실제 API adapter, API key 관리, 경수 데이터 source, 장애 통합 테스트가 추가로 필요하다

16.2 EnvironmentDataAdapter 운영 보완 실행 - 수행됨 / 2026-06-05 검증 완료
   - 보완 1: `OpenWeatherEnvironmentProvider`와 `WAQIEnvironmentProvider`를 실제 provider adapter class로 추가했다. 이제 `ENV_PROVIDER_OPENWEATHER`는 Open-Meteo alias가 아니라 OpenWeather API key 기반 adapter로 동작한다
   - 보완 2: `APIKeyManager`를 추가해 provider별 API key 환경변수(`OPENWEATHER_API_KEY`, `WAQI_API_KEY`, `OPENMETEO_API_KEY`)를 분리했다. OpenWeather/WAQI key가 없으면 가짜 성공 처리하지 않고 `failed_external_api_used_fallback_cache`로 기록한다
   - 보완 2-1: `04_백엔드/.env`와 `app/env.py`를 추가해 발급받은 API key를 파일에 입력하면 FastAPI 실행 시 자동 로드되도록 했다. 이미 OS 환경변수에 값이 있으면 `.env`가 덮어쓰지 않는다
   - 보완 3: `ENV_PROVIDER_OPENMETEO`를 개발용 no-key 외부 API provider로 DB/mock data에 추가했다. 실제 외부 API refresh 검증은 Open-Meteo로 수행한다
   - 보완 4: `ENV_PROVIDER_WATER_HARDNESS_CONTEXT`를 추가하고, 경수 데이터가 외부 API에서 직접 오지 않을 경우 `environment_contexts` fallback source를 payload에 `water_hardness_provider_id`로 기록한다
   - 보완 5: `ENV_PROVIDER_FORCE_FAIL` 강제 실패 provider를 추가해 live API에서도 fallback cache 경로를 검증할 수 있게 했다
   - 보완 6: `requested_metrics`에 따라 Open-Meteo/OpenWeather/WAQI adapter가 필요한 metric group만 조회하도록 mapping을 분리했다
   - DB 반영: `environment_providers`는 PostgreSQL/SQLite 모두 4건으로 갱신됨 (`OPENWEATHER`, `WAQI`, `OPENMETEO`, `WATER_HARDNESS_CONTEXT`)
   - 단위 테스트 결과: `test_environment_data_adapter.py` 6 passed, 전체 관련 테스트 16 passed / 1 skipped
   - 실제 API 검증 결과: `ENV_PROVIDER_OPENMETEO` refresh는 `external_api_refresh`, `ENV_PROVIDER_OPENWEATHER`와 `ENV_PROVIDER_WAQI`는 `.env` key 입력 후 실제 `success_external_api`, `ENV_PROVIDER_FORCE_FAIL`은 fallback, `/care/risk/evaluate`는 최신 observation을 Care Risk에 전달
   - PostgreSQL 검증 결과: `environment_observations` 5건, `environment_api_fetch_logs` 6건, 최신 observation `ENVOBS_0034234BEFAA`, RAG top-k `all_query_top1_matches: true`
   - 운영 검증 업데이트: 2026-06-08 기준 `OPENWEATHER_API_KEY`, `WAQI_API_KEY`를 `04_백엔드/.env`에 입력한 뒤 실 API 성공 케이스 검증 완료

17. CareRiskScoreEngine 및 Guide 옵션 API 구현 - 수행됨 / 검증 완료
   - 고객 문의가 없어도 가전 사용 로그와 최신 환경 데이터를 기준으로 Care Risk Score를 계산한다.
   - 입력: user_id, device_id, product_type, usage_log, smart_diagnosis, latest_environment_context
   - score 산정 요소: 사용 시간, 마지막 관리일, 청소 이력, 습도/AQI/경수/몬순, 제품군 민감도, 스마트 진단 보정
   - 예: 에어컨 필터 청소 주기 초과 + 고습도/몬순 -> filter_cleaning score 상승
   - 출력: care_risk_score, risk_band, trigger_reason, procedure_type, urgency, recommended_options
   - score가 기준 이상이면 별도 알림 테이블에 저장하지 않고, 응답에 `guide_options`를 포함한다.
   - Guide 옵션에는 Manual Guide와 AR Guide가 함께 제공된다. 고객은 둘 중 하나만 선택하는 것이 아니라 둘 다 자유롭게 사용할 수 있다.
   - 산출물: `CareRiskScoreEngine`, `PreventiveCareRecommendationEngine`, `/care/risk/evaluate`, `/guides/options`, `/guides/{guide_id}/complete`
   - 완료 기준: 사용자 문의 없이도 usage log + 환경 API/cache 데이터만으로 self care 추천 조건이 계산되고, Manual Guide와 AR Guide가 함께 제공됨
   - 검증 결과: `/care/risk/evaluate` Guide 옵션 반환, `/guides/options` 옵션 세트 조회, `/guides/{guide_id}/complete` 완료 이력 저장 검증 완료
   - 2026-06-15 보정: 에어컨/공기청정기 AQI 가중치를 공식 AQI health category 기반 CRS 내부 가중치로 조정했다. AQI 100~149는 +10, 150~199는 +20, 200~299는 +30, 300 이상은 +35를 부여한다.
   - 2026-06-15 검증: AQI 223/일평균 6시간/습도 40% 에어컨 케이스가 `20 + 15 + 30 = 65`, `risk_band=medium`으로 산출됨을 확인했다. live 환경 API smoke에서는 AQI 227 기준 score 65, risk_level medium, factor_scores `[daily_runtime_hours +15, aqi +30]` 확인.

17.1 서비스 명칭/제공 방식/이력 저장 정책 변경 반영 - 문서/DB 설계 반영 및 API endpoint 재정리 완료
   - 서비스 명칭을 `self_care`, `self_as`, `expert_as`로 통일했다.
   - `self_care`: 고객 문의 없이 주소 기반 환경 API + ThinQ 사용 로그 + 관리 이력으로 생성되는 예방 관리 흐름
   - `self_as`: 고객 자연어 문의/스마트 진단을 기반으로 Low/Medium Risk에서 고객이 직접 수행 가능한 자가 A/S 흐름
   - `expert_as`: High Risk, 공식 근거 부재, 고객 자가 조치 불가 시 공식 A/S/상담원/서비스센터로 연결되는 흐름
   - 공식 콘텐츠와 AR Guide는 하나를 고르는 옵션이 아니라, 기본 응답에서 함께 제공되는 `GuideOptionSet` 구조로 재정의했다.
   - `self_care`와 `self_as` 진행 횟수를 각각 저장하고, 두 값을 합산한 `device_care_summary`를 가전 탭에 표시하도록 DB 구조를 확장했다.
   - 회원가입 주소는 `user_addresses`에 저장하고, 환경 API 조회와 `expert_as` 연결 주소의 기준으로 사용한다.
   - 고객 선택 언어는 `supported_languages`, `user_language_preferences`, `translation_templates`, `translation_jobs`, `content_localizations`로 관리한다.
   - 산출물: `01_정의서/최종_DB_테이블_전체정리.md`, `01_정의서/예방알림형_CareRiskScore_환경API_설계서.md`, `01_정의서/다국어정책_정의서.md`, `05_프론트엔드/프론트엔드_고려사항_ReactVite_AROverlay_정리.md`, `05_프론트엔드/types/careshot.ts`, `05_DB/postgres/migrations/002_service_taxonomy_content_history_i18n.sql`
   - 완료된 범위: 최종 DB 테이블 목록에 신규 테이블과 변경 컬럼 반영, SQLite/PostgreSQL migration 적용 가능, 문서/프론트 타입 반영
   - API endpoint 재정리 최종 범위: `GET /guides/options`, `POST /guides/{guide_id}/complete`
   - 기존 `/care/alerts/*`, `/contents/*/view/*`, `/admin/reviews/*` API는 최종 21개 테이블 구조와 맞지 않아 API 표면에서 제거했다.

17.1-A GuideOptionSet 및 Guide 완료 API 재정리 - 수행됨 / 검증 완료
   - `GET /guides/options`를 구현해 Manual Guide와 AR Guide를 함께 내려주는 `GuideOptionSet` 응답을 제공한다.
   - `POST /guides/{guide_id}/complete`를 구현해 Manual/AR 수행 방식 구분 없이 완료 이력을 `SELF_MANAGEMENT_HISTORY`에 저장한다.
   - `ContentViewLog`, `PREVENTIVE_ALERT`, `ADMIN_REVIEW` 기반 API는 최종 API 표면에서 제거했다.
   - 검증 결과: FastAPI `TestClient` 기준 OpenAPI old path 0건, `GET /guides/options` 200, `POST /guides/GUIDE_1/complete` 200, 전체 테스트 25 passed / 1 skipped 확인.

17.2 Product Code Registry 및 제품 등록 흐름 설계/DB 반영 - 수행됨 / 검증 완료
   - LG India 공식 출처 기반 registry로 exact code를 검증하고 검증된 제품만 등록 가능하게 만드는 단계다.
   - 산출물과 검증 상세는 아래 `17.2단계` 섹션에 기록되어 있다.

17.3 Device Care History 조회 View/API 구현 - 수행됨 / 검증 완료
   - 가전 탭의 “관리/A/S 내역”을 프론트가 여러 로그 테이블에서 직접 조합하지 않도록 백엔드 통합 조회 View/API를 구현한다.
   - 17.1-A에서 생성되는 `content_view_logs`, `care_activity_logs`, `device_care_summary`가 17.3의 주요 source가 된다.
   - `GET /api/v1/devices/{device_id}/care-history` API와 `get_device_care_history(user_id, device_id, service_flow_type, limit)` repository 조회를 구현했다.
   - AR Guide 이력은 `ar_session_logs`를 대표 이력으로 내려주고 `ar_step_logs` 집계(`step_log_count`, 최신 step 시각)를 함께 반영한다.
   - 검증 결과: `tests/test_device_care_history.py`, `tests/test_content_option_flow.py`, 관련 회귀 테스트, PostgreSQL repository contract 테스트 통과.
   - 2026-06-11 최종 DB 보정: 현재 기본 SQLite DB는 21개 최종 테이블 구조이며 `content_view_logs`, `care_activity_logs`, `device_care_summary`, `ar_session_logs`, `ar_step_logs`, `preventive_alerts`를 포함하지 않는다. 따라서 repository는 구버전 로그 테이블을 새로 만들지 않고 `SELF_MANAGEMENT_HISTORY` 기준의 계산형 summary/history를 반환하도록 보정했다.
   - 2026-06-11 repository 재검증: 최종 테이블 기준으로 `USER`, `PRODUCT`, `USER_PRODUCT`, `OFFICIAL_ASSET`, `GUIDE`, `AR_GUIDE`, `AR_TARGET`, `OFFICIAL_DOCUMENT_CHUNK`, `OFFICIAL_DOCUMENT_EMBEDDING` 조회를 정렬했고 `python -m pytest tests -q` 결과 `23 passed, 1 skipped`를 확인했다.
   - 2026-06-11 방향 확정: 21개 테이블을 유지하고, 콘텐츠 완료/AR 완료/자가점검 완료 같은 발표용 이력은 `SELF_MANAGEMENT_HISTORY`에 축약 저장한다. 구버전 세부 로그 테이블은 재도입하지 않는다.
   - 2026-06-11 추가 검증: 콘텐츠 완료와 AR 세션 완료가 `SELF_MANAGEMENT_HISTORY` 기반 care-history에 반영되는 테스트를 추가했고 `python -m pytest tests -q` 결과 `25 passed, 1 skipped`를 확인했다.

18. ChatbotEngine 구현 - 수행됨 / 2026-06-11 검증 완료
   - 고객 자연어 문의를 받아 chat session 생성
   - 사용자/제품/언어/ThinQ mock device/log/diagnosis context 조회
   - 문의를 관리 문의 / 자가점검 문의 / High Risk / 추가 질문 필요 후보로 1차 분기
   - 필요 시 RAGService, DecisionEngineV2, ARGuidePlan 생성 흐름 호출
   - 산출물: `ChatbotEngine`, `/chat/messages` 통합 응답, 챗봇 처리 로그
   - 완료 기준: 단일 문의 입력 시 관리 안내, 자가점검, High Risk A/S 연결, 추가 질문 중 하나로 정상 분기
   - 2026-06-11 사전 보정: 기존 `/api/v1/chat/messages` decision 흐름에 `service_flow_type` 산출을 추가했다.
     - 예방/관리/청소/주기 문의 -> `self_care`
     - 현재 증상/고장/약한 바람/냄새/자가점검 문의 -> `self_as`
     - 연기/타는 냄새/전기/냉매/내부 분해 등 위험 문의 -> `expert_as`
   - 2026-06-11 사전 보정: `analysis.decision_result.service_flow_type` 응답 필드를 추가했다.
   - 주의: 현재 최종 21개 테이블 구조에서는 `decision_logs`를 사용하지 않는다. 챗봇 문의 분석 저장은 `AI_INQUIRY_ANALYSIS.intent_type`에 `self_care`, `self_as`, `expert_as` 기준으로 저장하도록 ChatbotEngine/DB 연동을 맞췄다.
   - 검증: `tests/test_chat_service_flow_type.py`에서 필터 청소/self_care, 바람 약함+냄새/self_as, 연기+타는 냄새/expert_as 및 expert_as AR 차단을 확인했다.
   - 2026-06-15 보정: `이상해요`, `문제가 있어요`, `고장난 것 같아요`, `작동이 이상해요`, `상태가 이상해요` 같은 저정보 초기 문의는 어떤 증상으로도 억지 분류하지 않고 `missing_slots=["symptom_type"]`, `needs_clarification=true`, `guide_options=null`로 응답한다.
   - 2026-06-15 보정 질문: "어떤 문제가 있나요? 냉방/바람, 소음/진동, 냄새, 물샘, 전원 문제, 필터 관리 중 가까운 증상을 알려주세요."
   - 저장 주의: 최종 21개 테이블의 `AI_INQUIRY_ANALYSIS.intent_type` CHECK 제약은 `self_care/self_as/expert_as`만 허용하므로, 저정보 문의의 DB 저장용 intent는 보수적으로 `self_as`로 기록하되 응답 decision/procedure/guide는 비워 추가 질문 상태를 유지한다.

18.1 ChatbotEngine 최종 21개 테이블 정합 보정 - 수행됨 / 2026-06-11 검증 완료
   - `decision_logs` 사용을 제거하고 최종 21개 테이블 구조에 없는 테이블 호출이 남지 않도록 보정했다.
   - 챗봇 문의 분석 저장 기준을 `AI_INQUIRY_ANALYSIS.intent_type`으로 맞췄다.
   - `/api/v1/chat/messages` 응답과 DB 저장 흐름이 `self_care`, `self_as`, `expert_as` 기준으로 맞는지 검증했다.
   - 검증 결과: `python -m pytest -q` 기준 36 passed, 1 skipped.

18.2 service_flow_type 보정 - 수행됨 / 2026-06-11 검증 완료
   - 예방/관리/청소/주기 문의는 `self_care`로 분기한다.
   - 현재 증상/고장/약한 바람/냄새/자가점검 문의는 `self_as`로 분기한다.
   - 연기/타는 냄새/전기/냉매/내부 분해 등 위험 문의는 `expert_as`로 분기한다.
   - 응답 필드 `analysis.decision_result.service_flow_type`을 추가했다.

18.3 AR 선행 수집 데이터 정의 - 수행됨 / 문서 반영 완료
   - AR 생성을 위해 제품 정보, 공식자료 근거, AR 대상/부품 기준, AR 가이드 템플릿, reference image, frontend overlay mapping을 사전 수집해야 함을 명시했다.
   - `PRODUCT`, `OFFICIAL_ASSET`, `OFFICIAL_DOCUMENT_CHUNK`, `OFFICIAL_DOCUMENT_EMBEDDING`, `AR_TARGET`, `AR_GUIDE`, reference image, part maps, guide steps의 역할을 정리했다.

18.4 LLM과 embedding 역할 분리 - 수행됨 / 문서 반영 완료
   - LLM은 고객 문장 이해, slot 추출, 추가 질문, 응답 문장 생성을 보조한다.
   - LLM은 AR 허용 여부를 최종 결정하지 않는다.
   - 최종 AR 허용/차단은 Rule/Safety Guard, RAG 공식자료 근거, High Risk 차단 규칙, 공식자료 match 여부가 결정한다.

18.5 로컬 BGE-M3 embedding 전환 - 수행됨 / 2026-06-11 검증 완료
   - `EmbeddingProvider`, `HashingEmbeddingProvider`, `LocalModelEmbeddingProvider`를 추가했다.
   - `CARESHOT_EMBEDDING_PROVIDER=local_model`, `CARESHOT_EMBEDDING_MODEL=BAAI/bge-m3` 기준으로 로컬 오픈소스 embedding model을 사용한다.
   - 현재 DB 기준 `OFFICIAL_DOCUMENT_CHUNK` 1,997건을 BGE-M3로 재임베딩했다.
   - `OFFICIAL_DOCUMENT_EMBEDDING`에는 `BAAI/bge-m3` 1,997건과 기존 `careshot_local_hashing_v1` 1,997건이 함께 존재한다.
   - 기존 해싱 embedding은 삭제하지 않고 fallback/backup으로 유지한다.

18.6 BGE-M3 RAG 품질 재검증 - 수행됨 / 2026-06-11 검증 완료
   - RAGService가 query도 같은 provider로 embedding하고 DB에서도 같은 `embedding_model` row만 검색하도록 보정했다.
   - query `My AC smells bad`는 `BAAI/bge-m3` 1024차원 vector로 변환되고, DB 후보도 `BAAI/bge-m3` row만 조회됨을 확인했다.
   - RAG 40 query 검증 결과: 40 passed, 0 failed.
   - top1 accuracy: 1.0.
   - official URL only: 통과.
   - safe flow에 high-risk 근거 혼입 없음.
   - `power_troubleshooting`에 `filter_cleaning` 혼입 없음.
   - 산출물: `06_산출물/RAG_BGE_M3_40쿼리_검증결과_2026-06-11.json`, `06_산출물/RAG_BGE_M3_40쿼리_검증리포트_2026-06-11.md`.

19. ConversationState 기반 multi-turn 추가 질문 구현 - 수행됨 / 2026-06-11 검증 완료
   - “냄새가 나요”, “물이 새요” 같은 모호 문의의 누락 slot 관리
   - 제품군, 증상 위치, 위험 신호, 최근 진단 결과, 사용 환경 slot 정의
   - 누락 slot이 있으면 추가 질문 생성
   - 충분한 slot이 채워지면 최종 판단 단계로 이동
   - 산출물: `ChatbotEngine.SLOT_SCHEMA`, `CONVERSATION_STATE` DB upsert, `/api/v1/chat/messages` multi-turn 응답, `tests/test_conversation_state_multiturn.py`
   - 구현 slot: `product_family`, `symptom_type`, `symptom_location`, `risk_signal`, `recent_diagnosis`, `environment_context`
   - 검증 시나리오: 냄새, 물샘, 바람 약함, 소음, 전원 꺼짐
   - 완료 기준: 5개 모호 문의에서 1턴 추가 질문 후 2턴 답변으로 최종 `service_flow_type`, `risk_level`, `procedure_type` 확정
   - 검증: `python -m pytest -q tests/test_conversation_state_multiturn.py` -> 5 passed
   - 회귀 검증: `python -m pytest -q tests/test_conversation_state_multiturn.py tests/test_chatbot_engine_persistence.py tests/test_chat_service_flow_type.py` -> 10 passed
   - 전체 검증: `python -m pytest -q` -> 41 passed, 1 skipped

20. LLMServiceMock 또는 LLM adapter 구현 - 수행됨 / 2026-06-11 검증 완료
   - 개발 단계에서는 비용 없는 mock/로컬 rule adapter 우선 사용
   - 최종 구조에서는 OpenAI 등 외부 LLM API로 교체 가능한 interface 작성
   - LLM 역할은 고객 문의 요약, slot 추출 보조, 다국어 응답 문장 생성, 안전 문구 템플릿 변환으로 제한
   - 공식근거 판단 자체는 RAGService/DecisionEngineV2가 담당
   - 산출물: `app/llm_service.py`, `LLMService` protocol, `LLMServiceMock`, `ExternalLLMAdapter` placeholder, `LLM_PROMPT_SCHEMA`, `LLM_OUTPUT_SCHEMA`, `tests/test_llm_service_mock.py`
   - ChatbotEngine 연동: `/api/v1/chat/messages` 응답에 `chatbot_engine.llm_assist`, `chatbot_engine.llm_policy`, `analysis.llm_assist` 추가
   - 완료 기준: LLM 없이도 mock으로 동작하고, provider 교체 시 ChatbotEngine은 `assist_chat_turn()` contract만 유지하면 됨
   - 권한 제한: LLM은 최종 AR 허용, 공식근거 검증, High Risk override를 수행하지 않음
   - 검증: `python -m pytest -q tests/test_llm_service_mock.py tests/test_chatbot_engine_persistence.py tests/test_conversation_state_multiturn.py tests/test_chat_service_flow_type.py -vv` -> 13 passed
   - 전체 검증: `python -m pytest -q` -> 44 passed, 1 skipped

21. DecisionEngineV2 구현 및 판단엔진 v2 -> ARGuidePlan 연결 - 수행됨 / 2026-06-12 검증 완료
   - rule 기반 판단엔진을 RAG/진단로그/환경 context 결합 구조로 고도화
   - v2도 기본 전제는 학습 모델이 아니라 설명 가능한 rule/safety/RAG 결합 판단엔진이다.
   - 학습 기반 intent/risk classifier는 26~27단계에서 라벨링/평가 결과가 확보된 뒤 별도 도입 여부를 결정한다.
   - 입력 schema: `customer_message`, `collected_slots`, `llm_assist`, `rag_evidence`, `smart_diagnosis`, `usage_log`, `environment`, `official_asset_match`
   - 출력 schema: `service_flow_type`, `intent_type`, `risk_level`, `decision_action`, `ar_guide_allowed`, `blocked_reason`, `allowed_actions`, `forbidden_actions`, `evidence_refs`, `procedure_type`
   - 기존 v1 rule engine 결과를 `v1_decision_result`, `v1_intent`, `v1_procedure`로 입력에 포함하고, v2 미구성 시 v1 fallback을 유지한다.
   - ChatbotEngine은 추가 질문이 끝난 뒤 `RAG -> LLMServiceMock assist -> DecisionEngineV2 -> GuideOptionSet/ARGuidePlan` 순서로 호출한다.
   - Low/Medium은 ARGuidePlan 후보로 연결
   - `model_name exact -> structure_type -> reference_image -> part_map_version -> ar_guide_template` 순서로 ARGuidePlan 후보를 생성
   - High Risk와 공식근거 no-match는 ARGuidePlan 생성 차단
   - 산출물: `app/engines/decision_v2.py`, `DecisionEngineV2`, `DECISION_ENGINE_V2_INPUT_SCHEMA`, `DECISION_ENGINE_V2_OUTPUT_SCHEMA`, ChatbotEngine v2 호출 연결, `tests/test_decision_engine_v2.py`
   - 테스트: self_care, self_as, expert_as, 추가 질문 후 최종 판단, 공식자료 없음 차단, RAG 근거 없음 차단, power_troubleshooting external_safe_check_only 유지
   - 실패/수정: 전체 테스트 중 환경 관측 test가 고정 과거 시각 때문에 최신 row 조회에 실패해, 테스트 관측시각을 현재 시각+5분으로 바꾸고 repository 최신 조회 tie-breaker에 `observation_id DESC`를 추가했다.
   - 검증: `python -m pytest -q tests/test_decision_engine_v2.py -vv` -> 8 passed
   - 회귀 검증: `python -m pytest -q tests/test_decision_engine_v2.py tests/test_llm_service_mock.py tests/test_chatbot_engine_persistence.py tests/test_conversation_state_multiturn.py tests/test_chat_service_flow_type.py -vv` -> 21 passed
   - 전체 검증: `python -m pytest -q` -> 52 passed, 1 skipped

> 22. React + TypeScript 프론트 전환 - 수행 중 / 핵심 API 연결 완료

목표:

```text
정적/간이 화면을 React + TypeScript + Vite 앱으로 전환하고,
FastAPI 응답으로 Home, Chat, AR Guide Session, 회원가입/프로필 흐름을 렌더링한다.
프론트 UI 구조는 원본 디자인을 최대한 유지하고, 승인된 데이터 주입부만 수정한다.
```

수행 현황:

| 세부 항목 | 상태 | 핵심 내용 |
|---|---|---|
| 22.1 프론트 원본 도입 | 수행됨 | GitHub `frontend/`를 `05_프론트엔드/react-vite/`로 가져오고 원본 백업 |
| 22.2 백엔드 프론트 호환 API | 수행됨 | `/api/users/*`, `/api/devices`, `/api/chat-messages`, `/api/ai/chat` 추가 |
| 22.3 기본 fetch 전환 | 수행됨 | user, device, chat API client가 FastAPI 호출 |
| 22.4 Home/Chat/ARGuide API 연결 | 수행됨 | Care Risk, 환경, guide options, AR plan/session 호출 연결 |
| 22.5 챗봇 응답 분기 | 부분 수행 | `service_flow_type`, `risk_level`, `needs_clarification`, `guide_options` 기반 카드 분기 연결 |
| 22.6 회원가입/로그인/프로필 DB 연동 | 수행됨 | `USER` 저장/조회/수정, 로그인, `currentUserEmail` 세션 저장, FastAPI 8791 실제 연결 및 DB row 검증 |
| 22.7 가입 후 demo ThinQ seed | 수행됨 | `USER_PRODUCT`, `APPLIANCE_USAGE_LOG`, `SMART_DIAGNOSIS_RESULT`, `SELF_MANAGEMENT_HISTORY` 자동 생성 |
| 22.8 환경/Care Risk 주소 연동 | 수행됨 | 회원가입/프로필의 region/city 기준 환경 API와 Care Risk 계산 연결 |
| 22.9 프론트 원본 UI 보호 | 수행 중 | 임의 버튼/문구 추가 제거, 원본 카드 구조 유지, 데이터 주입부만 제한 수정 |
| 22.9-1 홈 환경/Care Risk polling | 수행됨 | Home 화면이 켜져 있으면 60분마다 환경 API와 Care Risk API를 재호출해 최신 DB/API 값을 반영 |
| 22.9-2 DeviceDetail 관리 요약 DB 응답 보강 | 수행됨 | 프론트 소스 미수정 상태에서 `/api/devices`, `/api/devices/{device_id}`가 `SELF_MANAGEMENT_HISTORY` 기반 `care_summary`, `recent_history`를 반환하도록 백엔드 호환 API 확장 |
| 22.9-3 SelfCare 추천관리 화면 매뉴얼/AR 연동 | 수행됨 | 홈 최상단 “AI 추천 관리” 진입 화면(`/self-care`)에서 `/api/v1/guides/options` 기반 공식 YouTube, 단계 카드, ARGuide 이동, 완료 저장 API 연결 |
| 22.10 제품 코드 등록 시연 흐름 | 후속 필요 | `PRODUCT` master 조회 -> `USER_PRODUCT` 연결 API/UI 미구현 |
| 22.11 AR asset 정확도 보강 | 후속 필요 | reference image 정적 서빙, part map 좌표 seed, overlay 정확도 검수 필요 |

현재 연결된 주요 API:

```text
POST /api/users/register
POST /api/users/login
GET  /api/users/me
PUT  /api/users/me
GET  /api/devices
GET  /api/devices/{device_id}
GET  /api/v1/guides/options
POST /api/v1/guides/{guide_id}/complete
POST /api/chat-messages
POST /api/ai/chat
GET  /api/v1/environment/current
POST /api/v1/care/risk/evaluate
POST /api/v1/ar/plans
POST /api/v1/ar/sessions
PATCH /api/v1/ar/sessions/{session_id}
```

검증 기록:

```text
프론트 빌드: npm run build -> success
프론트 라우트 smoke: /, /chat, /ar-guide -> 200
백엔드 API smoke: users/devices/chat/care risk/environment/ar plan/session 응답 확인
회귀 테스트: tests/test_frontend_compat_api.py, tests/test_care_risk_engine.py,
tests/test_repositories_sqlalchemy.py 등 관련 범위 통과
프론트 원본 보호 확인: 임의 추가 버튼/문구 제거 후 build 성공
2026-06-15 추가 검증: 프론트 5173은 200, 초기 백엔드 8791 미기동으로 회원가입 API 실패 재현
2026-06-15 보강: FastAPI 8791 기동 후 `POST /api/users/register`, `POST /api/users/login`, `GET /api/users/me` 실제 성공 확인
2026-06-15 DB 검증: `USER`, `USER_PRODUCT`, `APPLIANCE_USAGE_LOG`, `SMART_DIAGNOSIS_RESULT`, `SELF_MANAGEMENT_HISTORY`에 신규 user_email 기준 row 1건씩 생성 확인
2026-06-15 프론트 검증: `npm run build` -> success, Vite chunk size warning만 있음
2026-06-16 SelfCare 추천관리 화면 보강: `/self-care`가 `/api/v1/guides/options`를 호출해 공식 YouTube embed, 필터 청소 단계 카드, ARGuide route state를 구성하도록 연결했다.
검증: `npm run build` -> success, `npm run smoke:ar-guide` -> ok=true, Chrome headless `/self-care` 렌더링에서 YouTube iframe `https://www.youtube.com/embed/tR91lFD0yIo`, 필터 단계, AR 탭/버튼 확인, AR 시작 클릭 후 `/ar-guide` 이동 및 STEP 1/5 표시 확인.
```

남은 작업:

```text
1. 제품 코드 등록 시연 흐름 구현 - 추후 필요시 구현
   - 현재는 회원가입 시 AS-Q24ENXE demo 제품이 자동 연결된다.
   - 최종 시연에서 제품 코드를 직접 등록하는 장면을 보여주려면
     PRODUCT master 조회, PRODUCT_REGISTRATION_ATTEMPT 기록,
     USER_PRODUCT 연결 흐름을 별도 구현해야 한다.

2. AR reference image와 part map 보강
   - 현재 ARGuide API 연결은 되어 있으나 reference image 정적 경로와 part map 좌표 seed가 부족하다.
   - `/static/assets/reference/*` 서빙 또는 DB image_path 정규화가 필요하다.
   - AR_TARGET/AR_GUIDE overlay config에 normalized 좌표를 넣어야 임시 overlay box를 제거할 수 있다.

3. 23~24번 화면 QA
   - multi-turn 추가 질문 카드, 공식근거 카드, expert_as 차단 카드,
     AR 시작 카드가 원본 UI 안에서 자연스럽게 표시되는지 검증한다.
```

23. 프론트 챗봇 UI를 multi-turn + 공식근거 카드 구조로 변경 - 수행 중
   - 원본 Chat 화면의 말풍선, 빨간 선택 버튼, 영상 카드, 단계 카드 형태를 유지한다.
   - 문제 선택 후 `/api/ai/chat`을 호출해 `needs_clarification`, `missing_slots`, `service_flow_type`, `risk_level`, `procedure_type`, `guide_options`를 받는다.
   - 추가 질문이 필요한 경우 빨간 선택 버튼을 새로 늘리지 않고, 챗봇 질문 말풍선 뒤 하단 입력창으로 고객이 자유 답변한다.
   - 같은 `session_id`로 고객 답변을 다시 보내 multi-turn context를 이어간다.
   - `guide_options.youtube_recommendations` 또는 manual `video_url`이 있으면 매칭 영상이 먼저 표시된다.
   - `guide_options.manual_guides.guide_text`와 procedure별 공식 가이드 step을 기반으로 영상 아래에 단계별 가이드 카드를 표시한다.
   - `guide_options`가 있으면 기존 `AR 가이드` 버튼을 함께 표시하고, `ar_guides`가 비어 있으면 클릭 시 AR 제공 불가 안내를 표시한다. high/expert_as이면 AR 버튼 대신 서비스센터 연결 버튼을 표시한다.
   - 메시지 내부 상태는 `sent`, `analyzing`, `needs_clarification`, `evidence_found`, `blocked`, `ar_ready`로 매핑하되, 상태값 문자열 자체는 사용자에게 노출하지 않는다.
   - 2026-06-15 보정: 사용자가 위험 신호 질문에 `아뇨`라고 짧게 답하면 `risk_signal=none`으로 처리하고, 같은 질문 반복 대신 남은 `symptom_location` 질문으로 넘어가도록 루프를 차단했다.
   - 2026-06-15 보정: 추가 질문 문구를 procedure별로 분리했다. 냉방/기능 문제는 `no_cooling_self_check/self_as`로 보정하고 바람/냉방 상황을 묻는다. 소음/진동 문구가 냉방 문의에 섞이지 않도록 테스트로 고정했다.
   - 2026-06-15 보정: 냉방 문의에서 고객이 `바람이 약하고 안시원해요`처럼 위험 여부 없이 증상만 답하면 `symptom_location=outlet`, `environment_context=unknown`으로 수집하고, 같은 통합 질문 반복 대신 남은 `risk_signal`만 묻도록 수정했다.
   - 2026-06-15 보정: 새 문제 선택 시 이전 multi-turn `session_id`를 끊도록 프론트를 수정했다. 이전 소음/진동 세션에 필터 청소 문의가 이어 붙어 YouTube/AR 버튼이 사라지는 문제를 차단했다.
   - 2026-06-15 보정: `/api/ai/chat`의 `guide_options`가 내려온 경우에도 처음부터 기본 매뉴얼 가이드를 제공한다. 표시 순서는 기존 버튼 영역의 `매뉴얼 가이드`/`AR 가이드`, 매칭 영상, 단계 카드, `관리를 완료하셨나요?` 확인 버튼이다.
   - 2026-06-15 보정: 추가 질문 순서를 `위험 신호 확인`과 `증상 상황 설명`으로 분리했다. `risk_signal`이 남아 있으면 연기/스파크/타는 냄새/감전/냉매 냄새 여부만 먼저 묻고, 부정 답변 후 procedure별 위치/상황 질문으로 넘어간다.
   - 2026-06-15 보정: `guide_options`가 있으면 `ar_guides`가 비어 있어도 `AR 가이드` 버튼을 함께 표시한다. 사용자가 AR 버튼을 눌렀을 때 해당 procedure의 AR 템플릿이 없으면 화면 이동 대신 AR 제공 불가 안내 말풍선을 표시한다.
   - 2026-06-15 보정: 공식근거 영상/단계 카드와 기존 비디오/매뉴얼 카드 폭을 대화 말풍선 및 완료 확인 카드 기준인 `max-w-[290px]`로 맞췄다. 영상은 고정 높이 대신 `aspect-video`로 렌더링해 카드 폭 변경 시 비율이 유지되도록 했다.
   - 2026-06-15 보정: `매뉴얼 가이드`/`AR 가이드` 버튼 묶음도 가이드 카드 기준 폭 `max-w-[290px]`에 맞추고 각 버튼을 균등 폭으로 정렬했다. AR 미지원 안내가 마지막 메시지로 추가되어도 `관리를 완료하셨나요?` 확인 버튼이 유지되도록 `showDoneAsk`를 함께 내려준다.
   - 2026-06-15 보정: 전원 문의(`전원이 불안정하고 자주 꺼져요`)는 첫 턴에서 위험 신호만 묻고, 사용자가 `아니요`라고 답한 뒤에 플러그/콘센트/차단기/표시장/리모컨 상태를 묻도록 `/api/ai/chat` 실제 호출 smoke로 검증했다.
   - 2026-06-15 보정: `/chat`에서 `AR 가이드`를 누를 때 `guide_options.procedure_type`과 procedure별 step title/desc를 `/ar-guide` route state로 전달한다. `ARGuide.tsx`는 더 이상 모든 챗봇 진입을 필터청소 하드코딩 단계로 렌더링하지 않고, 전달된 `guideSteps`를 우선 표시한다.
   - 2026-06-15 보정: `noise_self_check` 공식 YouTube seed의 `OFFICIAL_ASSET.procedure_type`과 `OFFICIAL_DOCUMENT_CHUNK.procedure_type`을 `air_conditioner_support`에서 `noise_self_check`로 맞췄다. `/api/v1/guides/options`는 이제 소음/진동 자가점검에서 LG India 공식 영상 `LG Split Air Conditioner: Silent Function`을 반환한다.
   - 2026-06-15 보정: `/api/ai/chat` 호환 응답도 `missing_slots=["symptom_type"]`일 때 ChatbotEngine의 `next_question`을 그대로 노출하도록 맞췄다. 따라서 초기 `이상해요` 입력은 필터청소 카드가 아니라 추가 질문 말풍선으로 표시된다.
   - 검증: `npm run build` -> success, `python -m pytest -q tests/test_frontend_compat_api.py tests/test_conversation_state_multiturn.py -vv` -> 20 passed, `/api/ai/chat` TestClient smoke -> 전원 문의 1턴 risk-only / 2턴 power detail 응답 확인.
   - 2026-06-15 추가 검증: `python -m pytest -q tests/test_environment_data_adapter.py tests/test_conversation_state_multiturn.py tests/test_content_option_flow.py tests/test_frontend_compat_api.py` -> 40 passed. TestClient smoke에서 `이상해요`는 `needs_clarification=true`, `procedure_type=null`, `guide_options=null`, 지정 추가 질문 문구로 응답했고, `noise_self_check`는 YouTube 1건(`I-06GlrB_pY`)과 manual `video_url`을 반환했다.
   - 산출물: `src/app/api/chat.ts`, `src/app/types/chat.ts`, `src/app/pages/Chat.tsx`
   - 구현 확정: 기존 UI 보호와 시연 안정성을 우선해 `ChatPanel`, `EvidenceCard`, `ClarificationPrompt` 별도 파일 분리는 진행하지 않는다. 챗봇 말풍선, 추가 질문, 공식근거 영상/단계 카드, 매뉴얼/AR 버튼, 완료 확인 버튼은 `Chat.tsx` 내부 렌더링으로 유지한다.
   - 완료 기준: 모호 문의에서 추가 질문이 나오고, 고객 자유입력 답변 후 공식 근거 기반 영상/단계 카드 또는 차단/서비스센터 분기가 표시됨

23-1. 예방 관리 알림 UI 구현
   - 앱 홈 또는 ThinQ 기기 상세 화면에 `관리 필요 알림` 카드 표시
   - 알림 카드에는 트리거 사유, 관련 사용 로그, 환경 근거, 공식 콘텐츠 보기, AR Guide 시작 CTA 포함
   - 예: “최근 습도가 높고 필터 청소 후 92일이 지나 에어컨 필터 관리가 필요합니다.”
   - 산출물: `CareRiskRecommendationPanel`, `CareReasonBadge`, `OfficialCareContentCard`, `StartARGuideButton`
   - 완료 기준: 예방 알림형 흐름과 사용자 문의형 챗봇 흐름이 프론트에서 명확히 구분됨

24. 안전 차단 카드 / expert A/S 연결 카드 / AR 시작 카드 정리
   - High Risk는 AR 시작 버튼을 숨기고 expert A/S 연결 카드만 표시
   - 공식근거 no-match는 “공식자료 확인 불가” 차단 카드로 표시
   - Low/Medium은 기존 원본 UI의 `매뉴얼 가이드` / `AR 가이드` 버튼과 영상+단계 카드 표시를 AR 시작 카드 역할로 인정
   - 산출물: `SafetyBlockCard`, `ServiceRouteCard`, `ARStartCard`
   - 2026-06-15 백엔드 계약 보강:
     - `/api/ai/chat` 응답에 `card_policy`를 추가한다.
     - `card_policy.card_type=service_route`: High Risk 또는 `expert_as`, AR 버튼 숨김, 서비스센터 연결만 허용.
     - `card_policy.card_type=safety_block`: `official_match_review_needed` 또는 `official_evidence_required`, 공식자료 확인 불가 카드 대상.
     - `card_policy.card_type=ar_start`: Low/Medium + 공식 guide options 존재, 매뉴얼/AR 버튼 허용.
     - `card_policy.card_type=clarification`: 추가 질문 수집 중, 가이드/서비스 버튼 숨김.
   - 2026-06-15 검증:
     - `pytest tests/test_frontend_compat_api.py tests/test_decision_engine_v2.py tests/test_chat_service_flow_type.py` -> 23 passed
     - UTF-8 live smoke: 한국어 High Risk 입력 -> `service_route`, `show_ar_button=false`, `show_service_button=true`
     - UTF-8 live smoke: 필터 청소 입력 -> `ar_start`, `show_manual_button=true`, `show_ar_button=true`
   - 2026-06-15 프론트 no-match 최소 반영:
     - `Chat.tsx`에서 `card_policy.card_type=safety_block`일 때만 “공식자료 확인 불가” 차단 안내를 렌더링한다.
     - Low/Medium 화면에는 별도 설명 카드를 추가하지 않고 기존 매뉴얼/AR 버튼과 영상+단계 카드 구조를 유지한다.
     - High Risk는 기존처럼 AR/매뉴얼 버튼 없이 서비스센터 연결 버튼만 표시한다.
   - 2026-06-15 화면 검증:
     - no-match 저장소 주입 렌더링 -> “공식자료 확인 불가” 표시, 서비스센터 버튼 표시, AR/매뉴얼 버튼 미표시
     - High Risk 렌더링 -> 서비스센터 버튼 표시, AR/매뉴얼 버튼 미표시
     - Low/Medium 렌더링 -> 매뉴얼/AR 버튼 및 단계 카드 표시, 서비스센터/no-match 카드 미표시
   - 완료 기준: High Risk, no-match, Low/Medium 케이스가 화면에서 명확히 다르게 표시

25. RAG 연결 후 intent/risk 평가 기준 확정 - 수행됨 / 2026-06-12 검증 완료
   - RAG evidence가 들어간 상태의 intent/risk 평가 기준을 확정
   - `self_care`, `self_as`, `expert_as` 분류 기준 문서화
   - `low`, `medium`, `high`, `unknown` risk 라벨 기준 문서화
   - 공식근거 없음 정책 확정: official asset match 실패 또는 RAG 0건이면 AR 차단
   - 공식 YouTube 추천 정책 확정: official_youtube + exact procedure_type + service_flow/risk_policy 호환 조건
   - AR 허용/제한/차단 기준 확정: low self_care 허용, medium self_as 제한 허용, power_troubleshooting은 `external_safe_check_only`, high/expert_as는 차단
   - 추가 질문 기준 확정: symptom_type, risk_signal, symptom_location, environment_context, recent_diagnosis slot 부족 시 collecting
   - 복합 증상 기준 확정: `procedure_type = primary_procedure`, 보조 증상은 `secondary_procedures`, high risk는 secondary 비움
   - 산출물:
     - `06_산출물/2026-06-12_intent_risk_evaluation_criteria.md`
     - `06_산출물/2026-06-12_intent_risk_label_guide.md`
   - 검증:
     - `python -m pytest -q tests/test_decision_engine_v2.py tests/test_chat_service_flow_type.py tests/test_rag_official_youtube_evidence.py tests/test_content_option_flow.py` -> 16 passed
     - `python -m pytest -q` -> 52 passed, 1 skipped
   - 완료 기준: 평가셋 생성자가 같은 기준으로 라벨링 가능하도록 기준서와 label guide 작성 완료
   - 미완료/후속:
     - 실제 VOC 500건 라벨링은 26번에서 수행
     - 정확도/recall/precision 산출은 27번 EvaluationService에서 수행
     - React/Vite 프론트 라벨별 카드 검증은 프론트 도착 후 22~24번에서 수행
     - `remote_operation` 사용법 문의는 `self_care`/`usage_help`/`low`/AR false/YouTube true로 정책 확정

26. VOC 원천 풀에서 intent/risk 평가셋 별도 라벨링 - 수행됨 / 2026-06-12 검증 완료
   - LLM API + RAG + rule 기반 판단엔진의 정확도와 안전성을 검증하기 위한 필수 기준 데이터다.
   향후 별도 학습 기반 classifier나 fine-tuning을 도입할 경우에는 그때 학습/검증 데이터의 기반으로도 활용할 수 있다.
   - 실제 VOC 500건 원천 풀에서 프로젝트에 맞는 문의 147건 선별
   - 제품군/intent/risk/action/procedure/AR/YouTube/followup 정답 라벨 부여
   - 임의 생성 문장을 정답데이터로 사용하지 않음
   - 언어가 섞인 문장은 `raw_message`, `normalized_message`, `translated_message`, `language_hint`로 분리
   - 구매/가격/보증/추천/일반 리뷰성 문장은 정답 평가셋에서 제외하고 라벨링 로그에 제외 사유 기록
   - 제품군 추정과 본문 제품군이 충돌하는 행은 `product_text_mismatch`로 제외
   - `remote_operation`은 `self_care`/`usage_help`/`low`/`manual_or_service_guidance_only`/AR false/YouTube true로 정답 평가셋에 포함
   - 산출물:
     - `02_데이터연동/mock_data/intent_risk_test_cases.json` -> 147건
     - `02_데이터연동/eval_sets/intent_risk_labeling_log_2026-06-12.json` -> 500건 전체 선택/제외 로그
     - `02_데이터연동/eval_sets/intent_risk_coverage_report_2026-06-12.json`
     - `06_산출물/2026-06-12_intent_risk_labeling_log.md`
     - `06_산출물/2026-06-12_intent_risk_coverage_report.md`
     - `04_백엔드/scripts/build_intent_risk_eval_set_from_voc.py`
     - `04_백엔드/tests/test_intent_risk_eval_dataset.py`
   - coverage:
     - 원천 VOC 500건
     - 평가셋 선별 147건
     - 제외 353건
     - 제품군: air_conditioner 28, washing_machine 40, air_purifier 40, water_purifier 39
     - service_flow_type: self_care 63, self_as 56, expert_as 28
     - risk_level: low 63, medium 56, high 28
     - procedure_type: remote_operation 2건 포함
     - expected_action: ask_clarification 28, manual_or_service_guidance_only 2, prepare_ar_guide_session 74, prepare_limited_ar_safe_check 15, route_to_service 28
   - 실패/수정:
     - 초기 키워드 점검에서 `electricity bill`, `PCB warranty` 같은 비증상 문장이 high risk로 과분류될 수 있음을 확인
     - 구매/가격/보증/추천 문맥 out-of-scope 제외 규칙 추가
     - high risk는 위험 신호 또는 위험 행동 조합에서만 선택되도록 보정
     - 제품군 본문 충돌 제외 규칙 추가
   - 검증:
     - `python scripts/build_intent_risk_eval_set_from_voc.py` -> coverage_passed true
     - `python -m pytest -q tests/test_intent_risk_eval_dataset.py` -> 2 passed
     - `python -m pytest -q` -> 57 passed, 1 skipped
   - 완료 기준: 제품군별, risk별, intent별 최소 기준을 충족하는 평가셋 생성 완료

27. EvaluationService 구현 및 정확도 리포트 생성 - 수행됨 / 2026-06-15 검증 완료
   - ChatbotEngine/DecisionEngineV2를 평가셋에 일괄 실행
   - intent accuracy, risk accuracy, action accuracy, High Risk recall, no-match precision 계산
   - clarification 필요 여부와 실패 케이스 error_type 분류
   - 정확도 리포트 결과를 본 뒤 rule 보정, LLM adapter 보강, 또는 별도 학습 기반 classifier 도입 여부를 결정한다.
   - 산출물:
     - `04_백엔드/app/evaluation_service.py`
     - `04_백엔드/app/routers/evaluation.py`
     - `04_백엔드/scripts/run_intent_risk_evaluation.py`
     - `02_데이터연동/eval_sets/intent_risk_eval_results_20260615.json`
     - `02_데이터연동/eval_sets/intent_risk_accuracy_report_20260615.json`
     - `06_산출물/2026-06-15_intent_risk_accuracy_report.md`
   - 2026-06-15 구현/보강:
     - `report_date`, `cases_path`, `results_path`, `report_json_path`, `report_md_path` 옵션을 EvaluationService/API/CLI에 연결했다.
     - 기본 출력은 `report_date` 기준 날짜별 JSON/MD 산출물로 저장하고, 호환용 `mock_data/intent_risk_eval_results.json`도 함께 갱신한다.
     - no-match 해석을 위해 `expected_no_match_count`, `no_match_true_positive_count`, `failed_case_count`를 metrics에 추가했다.
   - 2026-06-15 평가 결과:
     - 평가 케이스: 147건
     - intent_accuracy: 0.5782
     - risk_accuracy: 0.4830
     - action_accuracy: 0.4286
     - procedure_accuracy: 0.4626
     - ar_allowed_accuracy: 0.5102
     - clarification_accuracy: 0.5986
     - high_risk_recall: 1.0
     - no_match_precision: 0.0
     - 실패 케이스: 107건
     - error_type_counts: correct 40, clarification_error 58, intent_mismatch 23, risk_mismatch 13, no_match_false_positive 7, procedure_mismatch 6
   - 검증:
     - `pytest tests/test_evaluation_service.py tests/test_intent_risk_eval_dataset.py` -> 5 passed
     - `pytest` -> 89 passed, 1 skipped
     - `python scripts/run_intent_risk_evaluation.py --run-id EVAL_27_FULL_20260615 --report-date 2026-06-15` -> 147건 리포트 생성
     - `POST /api/v1/evaluation/intent-risk/run` limit=2 smoke -> 2026-06-15 날짜 경로 응답 확인
   - 실패/해석:
     - 현재 정확도는 데모 가능 여부 판단용 baseline이며, 바로 제품 품질 기준으로 보기에는 낮다.
     - 가장 큰 실패 유형은 clarification_error 58건이다. 긴 VOC 문장인데도 추가 질문으로 보내는 경향이 있어 28번 시나리오 검증/룰 보정 대상이다.
     - no_match_precision 0.0은 평가셋에 expected no-match가 0건인데 7건을 no-match로 예측했기 때문이다.
   - 완료 기준: 정확도 수치와 실패 케이스 목록이 산출물로 저장

28. 정상/모호/Medium/High Risk/매칭 실패/예방 알림 시나리오 검증 - 수행됨 / 2026-06-15 검증 완료
   - API와 프론트 기준 통합 시나리오 검증
   - 예방 알림, 정상 관리, 자가점검 가능, 추가 질문 필요, High Risk A/S 연결, 공식근거 없음, 저장/재시청 케이스 포함
   - 산출물: 시나리오 테스트 스크립트, QA 리포트, 화면 캡처
   - 완료 기준: 핵심 사용자 흐름이 API와 화면에서 모두 재현
   - 2026-06-15 수행 내용:
     - `04_백엔드/scripts/run_scenario_validation.py`를 추가해 핵심 흐름 7개를 일괄 검증한다.
     - 검증 대상: 예방 관리 알림, 필터 청소 정상 관리, 모호 문의 추가 질문, Medium 냉방/바람 약함 self_as, High Risk expert A/S, 공식근거 no-match 카드 정책, 가이드 완료 저장/AR session 재시청.
     - 검증 결과: 7개 시나리오 모두 passed, failed 0.
     - 산출물:
       - `02_데이터연동/eval_sets/scenario_validation_results_20260615.json`
       - `06_산출물/2026-06-15_scenario_validation_report.md`
       - `06_산출물/scenario_screenshots_20260615/01_home_authenticated.png`
       - `06_산출물/scenario_screenshots_20260615/02_chat_authenticated.png`
       - `06_산출물/scenario_screenshots_20260615/03_ar_guide_authenticated.png`
     - 검증:
       - `python -X utf8 scripts/run_scenario_validation.py --run-id SCENARIO_28_FULL_20260615 --report-date 2026-06-15` -> 7 passed / 0 failed
       - `pytest tests/test_frontend_compat_api.py tests/test_conversation_state_multiturn.py tests/test_self_management_history_lifecycle.py` -> 31 passed
       - `pytest` -> 89 passed, 1 skipped
       - `npm run build` -> Vite build 성공, chunk size warning 발생
       - Playwright CLI screenshot -> Home/Chat/ARGuide authenticated 화면 캡처 생성
     - 실패/수정 사항:
       - 1차 스크립트 실행 실패: 임시 DB 초기화에서 실제 DB에 없는 `AR_STEP_LOG`, `AR_SESSION_LOG` 삭제를 시도했다. AR session/step은 repository 내부 ephemeral 저장소라 해당 삭제를 제거했다.
       - 2차 스크립트 실행 실패: JSON 리포트 detail에 `dict_keys`가 들어가 직렬화가 실패했다. `list(guide_options.keys())`로 보정했다.
       - 1차 화면 캡처는 로그인 화면으로 저장되었다. `storage_state_20260615.json`으로 `isLoggedIn/currentUserEmail/appLanguage`를 주입해 인증된 Home/Chat/ARGuide 화면을 다시 캡처했다.
       - Playwright 브라우저 바이너리가 없어 최초 캡처가 실패했다. `npx playwright install chromium` 후 재검증했다.
       - no-match는 현재 seed 평가셋에 expected no-match row가 없으므로 실제 corpus no-match가 아니라 frontend card_policy mapping 단위로 검증했다.
       - 프론트 빌드는 성공했지만 `index` JS chunk가 500kB를 초과한다는 Vite 경고가 남아 있다. 기능 실패는 아니며 발표 전 성능 최적화 후보로만 기록한다.

29. AR 오버레이 정확도 검수
   - AR 방식은 객체인식이 아니라 image-based reference overlay로 고정
   - ThinQ 등록 제품의 `model_name` exact 값을 기준으로 모델을 식별
   - model_name이 다양해도 `product_type`과 `structure_type`으로 AR resource를 매핑
   - 4.2-A의 ARGuidePlan/overlay 선행 수집 데이터가 제품군/구조 타입/procedure_type별로 준비되었는지 먼저 확인
   - 최종 발표 시연은 에어컨 3개 구조 타입을 대상으로 구성
     - `wall_mounted_ac`: 벽걸이형
     - `standing_ac`: 스탠드형
     - `window_ac`: 창문형
   - 각 구조 타입별 reference_images 추가 확장
   - 각 구조 타입별 part_map_versions 추가 확장
   - 각 구조 타입별 AR guide template과 step instruction 확장
   - 전체 개발 구조는 에어컨 외 세탁기, 공기청정기, 정수기 제품군도 같은 resolver/template 구조로 확장 가능하게 유지
   - reference image와 part map 기준으로 부품 하이라이트 위치 검수
   - 커버/필터 이동 방향, step overlay, 금지 action 표시 검수
   - clean reference와 annotated overlay 분리
   - 좌표 오차와 보정 이력 기록
   - 산출물: 에어컨 3구조 reference image set, AR_TARGET 좌표표, procedure별 AR_GUIDE step set, part_map/target approval log, AR 오버레이 검수 리포트
   - 완료 기준: 발표용 에어컨 벽걸이형/스탠드형/창문형 AR 시연에서 하이라이트가 실제 부위와 어긋나지 않음

30. 발표용 UI와 산출물 정리
   - 시연 시나리오, 시스템 아키텍처, DB/RAG 검증 리포트, API 문서, 프론트 화면, AR 화면 정리
   - “ThinQ 앱 내 제공, 개발에서는 자체 챗봇/API” 전제 명확화
   - 개발로그와 검증 리포트 요약 정리
   - 산출물: 최종 발표 산출물 폴더, 시연 체크리스트, 개발로그 요약
   - 완료 기준: 예방 알림형과 사용자 문의형 모두에서 에어컨 3구조 AR 안내 또는 A/S 연결 흐름을 발표자가 끊김 없이 시연 가능

## 16. 현재 위치

```text
데이터 수집 파이프라인          수행됨 / 검증 리포트 생성됨
SQLite DB 적재                  수행됨 / 실제 근거 기반 synthetic mock 반영
LG India 공식자료 수집          수행됨 / 공식자료 791건, chunk 1,890건
백엔드 API 뼈대                 구현됨 / FastAPI-router-service-repository 분리 및 21테이블 API 스모크 통과
rule 기반 판단엔진              구현됨 / RAG·진단로그·환경데이터 결합, LLMServiceMock은 보조 응답으로만 연결
ARGuidePlan 생성                구현됨 / 공식근거 기반 guide/overlay 생성 및 session 저장 검증
AR reference overlay            구현됨 / 오버레이 정확도 검수 필요
정적 프론트 프로토타입          구현됨 / API base 연결 및 AR session 문자열 step id sync 검증
React + TypeScript 전환         미구현 / 22단계 이후 작업
RAG 공식문서 검색               v2 구현됨 / vector search + strict metadata filter 적용
RAG 데이터 구축 고도화          수행됨 / 공식자료 791건, chunk 1,890건, 검증 리포트 생성됨
Embedding/Vector DB             수행됨 / 공식자료 chunk 1,890건 embedded
RAGService v2                   구현됨 / 실패 케이스 보정 후 검색 품질 재검증 40/40 통과
AS-Q24ENXE support/FAQ 간극 검증 수행됨 / 누락 510건 확인
AS-Q24ENXE support/FAQ 누락분 추가 수집 수행됨 / 484 asset, 762 chunk 추가
FastAPI 백엔드                 수행됨 / 서버 기동, OpenAPI 생성, live HTTP RAG 40/40 통과
챗봇 대화 엔진                  구현됨 / 21개 테이블 저장 연동 및 API 스모크 통과
LLM 기반 응답                   LLMServiceMock 구현됨 / 외부 LLM API adapter는 후속
multi-turn 대화                 구현됨 / CONVERSATION_STATE 저장, 5개 slot filling 시나리오 검증 완료
intent/risk 평가셋              미수행 / 현 단계 보류
발표 polish                     미구현 / 검증 이후 진행
```

## 17. 다음 작업 - 과거 기준 기록

AS-Q24ENXE support/FAQ 전체 수집 간극 검증과 누락분 추가 수집은 수행되었다.

검증 결과, LG India search support tab의 Coveo Support totalCount는 544건이고, 이번 검증에서 544개 공식 LG India support URL 후보를 모두 내려받았다. 기존 DB에 반영된 후보 URL은 34개였으며, 누락 후보 URL은 510개였다. 누락분 수집 결과 510개 URL을 처리했고, 484개를 asset으로 추가했으며, 762개 chunk를 생성했다.

주의할 점은 544건을 순수 FAQ 문서 544건으로 확정하지 않는다는 것이다. 544건은 Support tab 전체 후보 수이며, Help Library/FAQ 성격의 공식 지원 문서가 섞여 있다. 현재 DB 기준 `official_faq` asset은 1건뿐이다.

FastAPI 백엔드 구조 전환은 수행되었다. 이 섹션 작성 당시 다음 작업은 **SQLAlchemy 또는 SQLModel repository 계층 작성**이었다. 현재 기준으로 14~17단계 일부가 이후 수행되었으므로 최신 작업 순서는 `15. 지금부터의 실제 개발 순서`와 `15.1 13~30 단계 상세 개발 정의`를 우선한다.

따라서 다음 작업은 아래 순서로 고정한다.

우선순위:

1. `Embedding/Vector DB 구축` - 수행됨
   - 산출물: `06_산출물/Embedding_VectorDB_검증리포트_2026-06-04.md`
   - 결과: `official_document_embeddings` 1,890건, JSONL vector index 1,890 line

2. `RAGService v2` 구현 - 수행됨
   - metadata strict filter, vector similarity, lexical fallback 적용
   - no-match 시 ARGuidePlan 차단

3. `AS-Q24ENXE support/FAQ 전체 수집 간극 검증` - 수행됨
   - 결과: totalCount 544건, 공식 URL 후보 544건, DB 반영 34건, 누락 510건
   - 산출물: `06_산출물/AS-Q24ENXE_support_FAQ_수집간극_검증리포트_2026-06-04.md`

4. `공식 FAQ/Help Library 누락분 추가 수집` - 수행됨
   - 결과: 510개 URL 처리, 484 asset 추가, 762 chunk 추가
   - 산출물: `06_산출물/AS-Q24ENXE_support_FAQ_누락분_수집리포트_2026-06-04.md`

5. `RAGService v2 검색 품질 검증 확대` - 수행됨
   - 최초 40개 query 중 37개 통과, 3개 실패 케이스 확인

6. `RAGService v2 실패 케이스 보정` - 수행됨
   - 정수기 공식 PDF/Help Library fallback 명확화
   - 세탁기 `limescale_care` 근거 chunk 추가
   - 공기청정기 `filter_replacement` 근거 chunk 추가
   - 보정 후 동일 40개 query set 재검증 40/40 통과

7. `FastAPI 백엔드 구조 전환` - 수행됨
   - `/api/v1/chat/messages`, `/api/v1/ai/analyze`, `/api/v1/rag/search`, `/api/v1/ar/plans`, `/api/v1/ar/sessions`, `/api/v1/guides/options`, `/api/v1/guides/{guide_id}/complete` 라우터 분리
   - RAGService v2, DecisionEngine, ARGuide selector를 FastAPI dependency 구조로 연결
   - `http://127.0.0.1:8790/openapi.json` 생성 확인
   - live HTTP 기준 `/api/v1/rag/search` 40개 query 재검증 40/40 통과
   - 이후 13~30 단계는 `15.1 13~30 단계 상세 개발 정의`를 기준으로 진행한다.

8. `SQLAlchemy 또는 SQLModel repository 계층 작성` - 수행됨
   - SQLite 직접 조회 repository를 interface 중심으로 정리
   - PostgreSQL + pgvector 전환 전에 DB 접근 계층을 분리한다.

10. `ChatbotEngine` 구현 - 17.3 완료 후 진행
    - RAG corpus와 evidence 반환 구조가 안정된 뒤 진행
    - 입력: 고객 메시지, session_id, user_id, device_id
    - 출력: 추가 질문 필요 여부, slot 추출 결과, 대화 상태
    - RAGService 검색 전 필요한 정보가 부족하면 바로 ARGuidePlan을 만들지 않고 추가 질문으로 전환

11. `DecisionEngineV2` 입력 구조 확장
    - 입력에 `rag_evidence`, `conversation_state`, `llm_summary`를 포함
    - `rag_evidence.result_count = 0`이면 Low Risk라도 공식근거 부족 상태로 판단
    - High Risk는 RAG 결과와 무관하게 ARGuidePlan 생성 차단

12. 프론트 공식근거 카드 연결

## 18. 최종 산출물 기준 문서

이 문서는 전체 개발 순서를 설명한다. 최종 제출/발표 산출물 기준의 완료 조건은 아래 문서를 기준으로 한다.

```text
00_계획수립/CareShot_AR_최종산출물_개발계획.md
```

특히 `AI / rule 기반 판단엔진 1차 구현 / 구현됨 / 고도화 필요`로 기록하며, 최종 기준 충족 상태로 넘기지 않는다. 최종 개발에서는 챗봇 대화 엔진, LLMService, RAGService 결과를 입력으로 받는 `AI 판단엔진 v2`가 필요하다.

## 19. 고도화 필요 추적 기준

앞으로 개발 상태는 아래 추적표 기준으로 기록한다.

```text
00_계획수립/CareShot_AR_고도화필요_추적표.md
```

현재까지 만들어진 DB, 백엔드, rule 기반 AI, ARGuidePlan, 프론트, reference overlay는 모두 `구현됨 / 고도화 필요` 상태로 관리한다. 최종 기준 검수가 끝나기 전까지 단순히 `완료`로 넘기지 않는다.

## 20. 최종 산출물 기준 상세 개발 항목

이 섹션은 앞으로 실제 개발할 항목을 최종 산출물 기준으로 상세히 정리한 것이다.

중요 전제:

```text
현재 ThinQ mock 데이터는 실제 VOC/환경 근거 기반 synthetic mock으로 재구축되었다.
현재 intent 분류는 학습 모델이 아니다.
현재 Low/Medium/High 판단은 rule 판단이다.
현재 분류 정확도는 측정되지 않았다.
현재 intent/risk 평가셋은 현 단계 미수행이다.
최종 AI 판단엔진 v2에서는 LLM/RAG/진단로그/공식근거를 결합해야 한다.
```

따라서 앞으로의 개발 목표는 단순히 화면이 돌아가게 하는 것이 아니라, “어떤 공식자료를 근거로 AR을 열었는지”, “왜 이 문의가 관리/자가점검/High Risk로 분류되었는지”, “분류 정확도를 어떻게 검증할 것인지”까지 설명 가능한 산출물을 만드는 것이다.

### 20.1 1단계 DB/데이터 최종 개발 항목

현재 상태:

```text
15-1 DB schema 확장 수행됨
15-2 실제 근거 기반 데이터 재구축 수행됨
수집 파이프라인 검증 리포트 생성됨
15-3 intent/risk 평가셋 구축은 현 단계 미수행
15-4 RAGService 1차 구현 및 검색 품질 1차 검증 수행됨
15-5 RAG 데이터 구축 고도화 수행됨 / 검증 리포트 생성됨
15-6 Embedding/Vector DB 구축 수행됨
15-7 RAGService v2 구현 수행됨
```

현재 한계:

| 항목 | 한계 |
|---|---|
| ThinQ mock 데이터 | 실제 ThinQ API 접근 데이터가 아니라, 실제 VOC/환경 근거 기반 synthetic mock이다. |
| 공식자료 DB | LG India 공식자료 기반 corpus가 구축되었고 RAGService v2도 구현되었다. 현재 SQLite 기준 chunk 1,997건, `BAAI/bge-m3` embedding 1,997건, `careshot_local_hashing_v1` fallback embedding 1,997건이 존재한다. BGE-M3 기준 RAG 품질 재검증은 40/40 통과이며, SQLAlchemy repository 계층과 FastAPI 연결까지 완료되었다. |
| 대화 DB | 최종 21개 테이블 기준으로 ChatbotEngine이 CHAT_SESSION, CHATBOT_INQUIRY, AI_INQUIRY_ANALYSIS, CHAT_MESSAGE, CONVERSATION_STATE, RAG_SEARCH_LOG에 연결됨. |
| 평가 DB | 구조는 있으나 현 단계에서는 intent/risk 평가셋을 만들지 않았다. 테스트셋/평가결과는 0건이다. |
| 안전 로그 | 15-1에서 기본 구조 추가됨. AI 판단엔진 v2 연동은 필요 |
| Part Map 관리 | 15-1에서 version 구조 추가됨. 좌표 검수 UI/승인 플로우는 필요 |

개발할 DB schema:

15-1에서 아래 schema는 추가되었다. 앞으로는 데이터 확장과 서비스 연결을 진행한다.

| 테이블 | 목적 | 주요 필드 |
|---|---|---|
| `chat_sessions` | 사용자별 챗봇 대화 세션 저장 | `session_id`, `user_id`, `device_id`, `status`, `language`, `created_at`, `updated_at` |
| `chat_messages` | multi-turn 메시지 저장 | `message_id`, `session_id`, `role`, `message_text`, `message_state`, `created_at` |
| `conversation_state` | slot/intent/risk 후보 상태 저장 | `session_id`, `slots_json`, `intent_candidates_json`, `risk_candidates_json`, `missing_slots_json` |
| `official_document_chunks` | RAG 검색용 공식자료 chunk 저장 | `chunk_id`, `asset_id`, `product_type`, `model_name`, `procedure_type`, `chunk_text`, `language`, `source_url` |
| `rag_search_logs` | RAG 검색 결과와 근거 로그 저장 | `search_id`, `session_id`, `query`, `matched_chunk_ids_json`, `score_json`, `created_at` |
| `safety_audit_logs` | 위험도/금지 action 판단 근거 저장 | `audit_id`, `session_id`, `risk_level`, `blocked`, `reasons_json`, `forbidden_actions_json` |
| `intent_risk_test_cases` | 분류 정확도 평가용 정답 데이터셋 | `case_id`, `message_text`, `expected_intent`, `expected_risk`, `product_type`, `expected_action` |
| `intent_risk_eval_results` | 분류 평가 실행 결과 저장 | `run_id`, `case_id`, `predicted_intent`, `predicted_risk`, `is_correct`, `error_type` |
| `official_contents` | 영상/문서/FAQ/유튜브/매뉴얼 콘텐츠 통합 | `content_id`, `content_type`, `product_type`, `procedure_type`, `language`, `source_asset_ids_json` |
| `reference_images` | 제품/구조별 reference image 관리 | `reference_image_id`, `model_name`, `structure_type`, `image_path`, `image_role`, `version` |
| `part_map_versions` | 좌표 버전/검수 이력 관리 | `part_map_version_id`, `reference_image_id`, `structure_type`, `calibrated_by`, `approved_status` |

개발할 mock JSON:

| 파일 | 개발 내용 |
|---|---|
| `chat_sessions.json` | 발표용 사용자별 대화 세션 샘플 |
| `chat_messages.json` | 관리/자가점검/High Risk/multi-turn 대화 샘플 |
| `conversation_state.json` | slot 누락, 추가 질문, 확정 상태 샘플 |
| `official_document_chunks.json` | 공식 매뉴얼/FAQ 절차 chunk |
| `rag_search_logs.json` | 검색 결과 근거 샘플 |
| `safety_audit_logs.json` | 위험 차단 및 허용 근거 샘플 |
| `intent_risk_test_cases.json` | 2026-06-12 26번 작업에서 실제 VOC 500건 중 147건 선별 라벨링 완료. `remote_operation` 2건 포함 |
| `intent_risk_eval_results.json` | 현 단계 0건. 평가 실행 후 생성 |
| `official_contents.json` | 기존 LG 관리 영상/FAQ/매뉴얼 통합 콘텐츠 |
| `reference_images.json` | clean reference, open-cover reference, annotated reference 분리 |
| `part_map_versions.json` | 좌표 버전과 검수 상태 |

ThinQ mock 데이터 최종 발표/제출 안정권 기준:

| 데이터 | 최소 확장 기준 |
|---|---|
| 고객 | 120명 이상, 영어/힌디어/지역어, 숙련도/선호 방식/거주 지역/서비스 접근성 다양화 |
| 제품 | 240개 이상, 4개 제품군별 60개 이상, exact model/alias/series/common 매칭 케이스 포함 |
| 사용 로그 | 720건 이상, 제품별 정상/관리필요/과사용/장기미사용/습도연동/경수연동/AQI연동 케이스 포함 |
| 스마트 진단 | 480건 이상, none/low/medium/high severity 균형, result_code와 detected_signals 포함 |
| 환경 | 50지역 이상 + 관측 row 300건 이상, 인도 주요 지역별 고온다습, 건조, 경수, AQI 악화, 몬순, 해안/내륙 조합 케이스 포함 |
| 공식자료 | 실제 LG India 공식자료 기반. 현재 SQLite 기준 1,997 chunk, BGE-M3 embedding 1,997건, hashing fallback embedding 1,997건이 구축되었다. AS-Q24ENXE support 검색 후보 544건 중 기존 반영 34건, 누락 510건을 검증했고, 누락분 중 484 asset/762 chunk를 추가했다. 공식 YouTube 근거 확장과 BGE-M3 전환 후 RAG 품질 재검증은 40/40 통과 상태다. |
| 사용자 고충 근거 | 각 케이스에 `scenario_basis`, `pain_tags`, `evidence_level`을 남겨 실제 인도 사용자 문제와 연결 |

현재 실제 근거 기반 데이터 재구축 결과:

| 데이터 | 현재 건수 | 검증 결과 |
|---|---:|---|
| raw VOC 원천 풀 | 500 | 제품군별 125건 균형 |
| 환경 context | 50 | Open-Meteo 기반 50개 도시 |
| 환경 관측 row | 350 | Open-Meteo 기반 관측 row |
| 고객 프로필 | 120 | 실제 VOC/환경 근거 기반 synthetic mock |
| ThinQ 등록 제품 | 240 | 제품군별 60개 |
| 사용 로그 | 720 | 제품군별 180건 |
| 스마트 진단 | 480 | 제품군별 120건, none/low/medium/high 균형 |
| LG India 공식자료 asset | 791 | LG India 공식자료 기반. `https://www.lg.com/in/`, `https://gscs-manual.lge.com/` 공식 원본 포함 |
| LG India 공식문서 chunk | 1,997 | PDF 기반 chunk, AS-Q24ENXE support/FAQ 누락분 추가 chunk, 공식 YouTube 근거 chunk 포함 |
| 공식문서 embedding | 3,994 | `BAAI/bge-m3` 1,997건 + `careshot_local_hashing_v1` fallback 1,997건 |
| intent/risk 테스트셋 | 0 | 현 단계 미수행 |
| intent/risk 평가결과 | 0 | 현 단계 미수행 |

수집 파이프라인 검증 리포트:

```text
06_산출물/수집파이프라인_검증리포트_2026-06-03.md
```

현재 남은 DB/데이터 고도화:

```text
AS-Q24ENXE support/FAQ 전체 수집 간극 검증 - 수행됨
공식 FAQ/Help Library 누락분 추가 수집 - 수행됨
신규 PDF/HTML/FAQ 본문 추출 및 official_document_chunks 확장 - 수행됨
신규 chunk embedding 재생성 - 수행됨
RAGService v2 검색 품질 검증 확대 - 수행됨 / 최초 37개 통과, 3개 실패 확인
RAGService v2 실패 케이스 보정 - 수행됨 / 재검증 40개 query 통과
official_document_embeddings 또는 vector index 구축 - 수행됨 / BGE-M3 1,997건 + hashing fallback 1,997건
RAGService v2: BGE-M3 vector similarity + metadata strict filter 구현 - 수행됨 / 40개 query 재검증 통과
AI 판단엔진 v2와 safety policy 연결 - 미수행 / 21단계에서 실행
intent/risk 평가 기준 확정 - 미수행 / 25단계에서 실행
VOC 원천 풀에서 평가셋 별도 라벨링 - 미수행 / 26단계에서 실행
제품군별 reference_images/part_map_versions 추가 확장 - 미수행 / 29단계에서 실행
```

중요:

```text
intent/risk 평가셋 확대와 official_document_chunks 확대는 같은 작업이 아니다.

intent/risk 평가셋:
  사용자 문의 문장과 정답 intent/risk/action label을 저장하는 정확도 평가용 데이터

official_document_chunks:
  LG 공식 매뉴얼/FAQ/지원문서를 절차 단위로 쪼개 RAG 검색 근거로 쓰는 데이터

현재 순서는 RAG 데이터 구축 고도화, AS-Q24ENXE support/FAQ 간극 검증, 누락분 추가 수집, Embedding/Vector DB 재생성, RAGService v2 구현까지 수행된 상태다. 다음은 RAGService v2 검색 품질 확대 검증이며, intent/risk 평가셋은 RAG/판단엔진 입력 구조가 안정된 뒤 별도 단계에서 생성한다.
```

최종 검증 기준:

```text
seed script 실행 시 모든 mock JSON이 SQLite에 적재된다.
Repository에서 chat/session/RAG/safety/eval 데이터를 조회할 수 있다.
공식자료 chunk가 asset_id와 연결된다.
RAGService가 공식자료 chunk에서 근거 passage를 반환한다.
공식 PDF(Owner's Manual/Spec/Dimension 포함)/FAQ/Help Library가 source manifest와 원본 파일로 검증된다.
Embedding/Vector DB에서 chunk_id와 vector가 1,890건 연결되어 있다.
High Risk 차단 로그가 safety_audit_logs에 저장된다.
intent/risk 평가셋은 별도 단계에서 라벨링 후 DB에 들어간다.
```

### 20.2 2단계 Backend 최종 개발 항목

현재 상태:

```text
구현됨 / 서비스 분리 필요
```

현재 한계:

```text
/chat/messages가 한 번에 rule 판단과 ARGuidePlan을 생성한다.
ChatbotEngine, LLMService, RAGService, ThinQAdapter가 분리되어 있지 않다.
API request/response schema가 고정되어 있지 않다.
테스트 코드와 오류 응답 표준이 부족하다.
```

개발할 서비스 계층:

| 서비스 | 역할 |
|---|---|
| `ThinQMockAdapter` | mock DB에서 사용자/제품/로그/진단/환경 context 조회 |
| `ChatbotEngine` | message를 받아 대화 상태와 추가 질문 여부 결정 |
| `LLMServiceMock` | 문의 요약, 고객 응답 문구, 번역 mock 생성 |
| `RAGService` | official_document_chunks 검색 및 근거 반환 |
| `DecisionEngineV2` | 대화 상태, RAG, ThinQ context, safety rule을 종합 판단 |
| `ARGuidePlanService` | decision_result를 ARGuidePlan으로 변환 |
| `SafetyAuditService` | High Risk/forbidden action 판단 로그 저장 |
| `EvaluationService` | intent/risk test case 실행 및 결과 저장 |

최종 API:

| Method | Path | 개발 내용 |
|---|---|---|
| `POST` | `/chat/sessions` | 대화 세션 생성 |
| `GET` | `/chat/sessions/{id}` | 대화 세션/상태 조회 |
| `POST` | `/chat/messages` | multi-turn 메시지 처리 |
| `POST` | `/ai/analyze` | DecisionEngineV2 분석 |
| `POST` | `/rag/search` | 공식문서 chunk 검색 |
| `POST` | `/safety/check` | 위험도/금지 action 검증 |
| `POST` | `/ar/guides/plan` | ARGuidePlan 생성 |
| `POST` | `/ar/sessions` | AR 세션 시작 |
| `PATCH` | `/ar/sessions/{id}` | AR 세션 진행 저장 |
| `POST` | `/eval/intent-risk/run` | intent/risk 평가 실행 |

최종 검증 기준:

```text
/chat/messages가 추가 질문 상태와 최종 판단 상태를 구분한다.
High Risk는 RAG 결과가 있어도 ARGuidePlan 생성이 차단된다.
RAG 검색 결과가 decision_result.evidence에 포함된다.
모든 decision은 safety_audit_logs에 기록된다.
API 테스트 스크립트로 정상/모호/Medium/High/매칭 실패 케이스를 검증한다.
```

### 20.3 3단계 ChatbotEngine 최종 개발 항목

현재 상태:

```text
미구현 / 개발 필요
```

개발할 기능:

| 기능 | 상세 |
|---|---|
| message normalization | 영어/한국어/힌디어/오타/짧은 문장 정규화 |
| intent 후보 추출 | care, self_check, high_risk, ambiguous, out_of_scope |
| slot 추출 | symptom, odor_type, noise_type, leak_type, duration, product_area |
| safety-first 질문 | 냄새/연기/스파크/누전 의심이면 안전 질문 우선 |
| 추가 질문 생성 | 정보가 부족하면 AR을 바로 열지 않고 추가 질문 |
| conversation_state 저장 | 세션별 누락 slot과 확정 slot 저장 |
| final handoff | 충분한 정보가 모이면 DecisionEngineV2 호출 |

중요한 한계 기록:

```text
현재 intent 분류는 학습 모델이 아니다.
현재는 keyword 기반 intent 분류이므로 정확도를 알 수 없다.
최종 기준에서는 intent/risk test case로 정확도를 측정해야 한다.
```

intent 분류 고도화 방식:

| 단계 | 방식 |
|---|---|
| v1 | keyword/rule 기반 |
| v2 | LLMServiceMock으로 증상 요약과 slot 추출 보조 |
| v3 | 평가셋 기반으로 rule 보정 |
| 최종 발표 | 학습 모델이 아니라 LLM+rule+RAG safety 구조로 설명 |

### 20.4 4단계 LLMServiceMock 최종 개발 항목

현재 상태:

```text
미구현 / 개발 필요
```

개발 원칙:

```text
LLM은 고객 응답과 요약을 돕는다.
LLM은 최종 안전 판단자가 아니다.
LLM은 공식자료에 없는 절차를 만들어내면 안 된다.
```

개발할 기능:

| 기능 | 상세 |
|---|---|
| inquiry summary | 고객 문의를 구조화된 증상 요약으로 변환 |
| slot extraction assist | 냄새/소음/누수/냉방불량 등 slot 후보 추출 |
| clarifying question | 모호한 문의에 추가 질문 문구 생성 |
| customer response | 고객 표시용 자연어 응답 생성 |
| translation | 사용자 선호 언어로 출력 문구 변환 |
| safety wording | High Risk 차단 문구를 고정 템플릿 기반으로 생성 |

금지:

```text
공식자료 없는 수리 절차 생성 금지
High Risk를 임의로 Low Risk로 낮추기 금지
전기/냉매/PCB/내부 분해 안내 생성 금지
RAG 근거 없는 AR step 생성 금지
```

최종 검증 기준:

```text
LLM mock 결과가 DecisionEngineV2 입력에 포함된다.
LLM 응답은 safety_guard를 통과해야 프론트에 표시된다.
High Risk 문구는 고정 안전 템플릿을 사용한다.
```

### 20.5 5단계 RAG 데이터 구축 및 RAGService 최종 개발 항목

현재 상태:

```text
RAGService v2 구현됨 / 공식 FAQ coverage 검증과 검색 품질 평가 필요
```

현재 구현된 것:

| 항목 | 상태 |
|---|---|
| official_document_chunks | 1,890개 공식자료 chunk 구축 |
| /rag/search API | 구현됨 |
| /chat/messages rag_evidence 연결 | 구현됨 |
| 공식 URL 검증 | 구현됨 |
| boilerplate chunk 제외 | 구현됨 |
| 검색 방식 | metadata strict filter + vector similarity + lexical fallback |
| embedding model | `careshot_local_hashing_v1` 개발용 embedding 구현됨 |
| Vector DB | SQLite embedding table + JSONL vector index 구현 후, PostgreSQL + pgvector 최종 DB 전환 수행됨. `official_document_embeddings.embedding_vector vector(512)`와 HNSW index 검증 완료 |
| 공식 PDF RAG | Owner's Manual/Spec/Dimension 등 공식 PDF 기반 chunk와 embedding 포함 |
| 충분한 FAQ/Help Library corpus | AS-Q24ENXE support/FAQ 간극 검증 및 누락분 추가 수집 수행됨. 다른 제품군 FAQ coverage는 별도 확장 필요 |

개발 순서:

| 순서 | 작업 | 완료 조건 |
|---:|---|---|
| 1 | LG India 공식자료 수집 범위 확장 | 공식 PDF(Owner's Manual/Spec/Dimension 포함), Online Manual, FAQ, Help Library, Support Page 수집 대상 정의 |
| 2 | 공식자료 원본 수집 | PDF/HTML 원본 파일 저장, source manifest 기록, 비공식 URL 제외 |
| 3 | PDF/HTML 본문 추출 | PDF 텍스트, JSON-LD articleBody, FAQ Q/A를 추출하고 boilerplate 제거 |
| 4 | official_document_chunks 확장 | product_type, model_name, series, procedure_type, source_type, page_number, source_url metadata 포함 |
| 5 | chunk 검수 리포트 생성 | 제품군/절차/source_type별 coverage, 공식 URL only, boilerplate 0건 검증 |
| 6 | Embedding/Vector DB 구축 | embedding model 선정, vector index 또는 embeddings table 생성, chunk_id-vector 연결 |
| 7 | RAGService v2 구현 | metadata strict filter + vector similarity + lexical fallback 적용 |
| 8 | RAGService v2 품질 검증 | top-k 근거 정확도, no-match 차단, PDF page/section 반환 확인 |

RAGService v2 개발할 기능:

| 기능 | 상세 |
|---|---|
| strict filter | model_name, alias, series, product_type_common 기준 필터 |
| vector search | embedding vector 기반 semantic similarity 검색 |
| lexical fallback | vector 검색 실패 또는 낮은 점수일 때 keyword/procedure 기반 fallback |
| chunk search | official_document_chunks에서 procedure 관련 passage 검색 |
| evidence bundle | `asset_id`, `chunk_id`, `source_url`, `source_type`, `page_number`, `procedure_type`, `forbidden_actions` 반환 |
| no-match handling | 공식자료 근거가 없으면 ARGuidePlan 차단 |
| log storage | 검색 query와 결과를 `rag_search_logs`에 저장 |

RAG 검색 순서:

```text
1. ThinQ 등록 제품의 model_name 확인
2. official_assets strict match
3. metadata filter 생성: exact model / alias / series / product_type_common
4. Vector DB에서 semantic search 수행
5. 낮은 점수 또는 no-match면 lexical fallback 수행
6. forbidden_actions 확인
7. evidence bundle 생성
8. DecisionEngineV2로 전달
```

최종 검증 기준:

```text
공식 PDF(Owner's Manual/Spec/Dimension 포함)/FAQ/Help Library 원본 파일이 저장되어 있다.
source manifest에 공식 URL과 asset_type이 기록되어 있다.
official_document_chunks가 PDF page/HTML section/source_type metadata를 가진다.
embedding_status가 embedded로 갱신된 chunk가 존재한다.
Vector DB 또는 vector index에서 semantic search가 수행된다.
exact model 근거가 있으면 exact_model evidence 반환
alias 근거는 official_alias로 반환
series 근거는 official_series로 반환
제품군 공통 근거는 product_type_common으로 반환
전기/냉매/PCB/내부 분해 chunk는 ARGuidePlan에서 차단
RAG 근거가 없으면 ARGuidePlan을 생성하지 않는다.
```

### 20.6 6단계 AI 판단엔진 v2 최종 개발 항목

현재 상태:

```text
rule 기반 판단엔진 1차 구현 / 구현됨 / 고도화 필요
```

현재 판단 방식:

```text
High:
  - High Risk keyword 포함
  - 또는 smart_diagnosis.severity == high

Medium:
  - Medium Risk keyword 포함
  - 또는 smart_diagnosis.severity == medium

Unknown:
  - 공식자료 strict matching 실패

Low:
  - High/Medium/Unknown이 아니고 공식자료 match_status == verified
```

현재 한계:

```text
학습 모델이 아니다.
키워드 누락에 취약하다.
분류 정확도가 측정되지 않았다.
Medium Risk 정책이 세분화되지 않았다.
LLM 요약/RAG 근거/진단로그/환경 데이터가 충분히 결합되어 있지 않다.
```

AI 판단엔진 v2 입력:

| 입력 | 내용 |
|---|---|
| `chatbot_context` | intent 후보, slot, 추가 질문 결과 |
| `llm_summary` | 증상 요약, 고객 표현 정규화 |
| `rag_result` | 공식자료 chunk, asset_id, forbidden_actions |
| `thinq_context` | 등록 제품, 모델명, alias, series |
| `usage_log` | 사용 시간, 마지막 관리일, care trigger |
| `smart_diagnosis` | severity, result_code, detected_signals |
| `environment_context` | 지역, 습도, AQI, 경수, 기후 trigger |

AI 판단엔진 v2 출력:

| 출력 | 내용 |
|---|---|
| `intent_type` | care/self_check/high_risk/ambiguous/out_of_scope |
| `risk_level` | low/medium/high/unknown |
| `risk_reasons` | 고객 표시용/내부 로그용 분리 |
| `evidence` | official asset/chunk 근거 |
| `decision_action` | ask_clarifying_question/provide_official_content/prepare_ar_guide_session/route_to_service |
| `ar_guide_allowed` | AR Guide 허용 여부 |
| `blocked_reason` | 차단 시 사유 |
| `confidence` | 평가셋 기반 보정 전에는 rule confidence로 명시 |

최종 검증 기준:

```text
정상 관리 문의는 Low + AR 허용
모호한 문의는 바로 AR을 열지 않고 추가 질문
Medium Risk는 제한된 안내 또는 공식 콘텐츠 우선
High Risk는 무조건 AR 차단
공식자료 근거 실패 시 AR 차단
판단 결과가 safety_audit_logs에 저장
intent/risk 평가셋 기준 정확도 리포트 생성
```

### 20.7 7단계 Intent/Risk 평가 체계 최종 개발 항목

현재 상태:

```text
미구현 / 개발 필요
```

필요 이유:

```text
키워드 기반 intent 분류가 어느 정도 정확한지 현재 알 수 없다.
Low/Medium/High rule 판단도 실제 문의 문장에 대해 검증되지 않았다.
따라서 최종 산출물에는 평가 데이터셋과 평가 결과가 포함되어야 한다.
```

개발할 평가 데이터:

| 케이스 | 예시 |
|---|---|
| 관리 문의 | 필터 청소, 통세척, 필터 교체, 석회질 관리 |
| 자가점검 문의 | 냄새, 약한 바람, 물 흐름 약함, 소음 |
| 모호한 문의 | 냄새나요, 이상해요, 잘 안 돼요 |
| Medium Risk | 누수, 냉방 약함, 반복 에러, 내부 소음 |
| High Risk | 연기, 스파크, 타는 냄새, 누전, 냉매, PCB |
| 매칭 실패 | 등록되지 않은 모델, 공식자료 없는 모델 |
| 다국어 | 영어, 한국어, 힌디어/지역어 샘플 |

평가 지표:

```text
intent accuracy
risk accuracy
High Risk recall
High Risk false negative count
Medium Risk confusion
official match failure detection rate
```

최종 산출 파일:

```text
06_산출물/evaluation/intent_risk_eval_report.json
06_산출물/evaluation/intent_risk_confusion_matrix.csv
06_산출물/evaluation/high_risk_false_negative_cases.json
```

### 20.8 8단계 ARGuidePlan 최종 개발 항목

현재 상태:

```text
구현됨 / 고도화 필요
```

개발할 기능:

| 기능 | 상세 |
|---|---|
| evidence 연결 | 각 AR step에 공식자료 chunk_id 연결 |
| forbidden action 검증 | step action이 forbidden_actions와 충돌하는지 검사 |
| part map version 연결 | 어떤 reference image와 좌표 버전을 썼는지 기록 |
| language output | 고객 선호 언어 instruction/voice text 생성 |
| Medium Risk 제한 | Medium에서는 위험 step 제거 또는 공식 콘텐츠 우선 |
| blocked plan | High Risk/근거 실패 시 plan 대신 차단 결과 반환 |

최종 검증 기준:

```text
ARGuidePlan의 모든 step이 공식자료 근거를 가진다.
전기/냉매/PCB/내부 분해 관련 step은 생성되지 않는다.
Part Map 좌표 version이 plan에 포함된다.
High Risk에서는 ARGuidePlan이 생성되지 않는다.
```

### 20.9 9단계 Frontend/AR 최종 개발 항목

현재 상태:

```text
구현됨 / multi-turn UX 및 AR 검증 필요
```

프론트 개발할 상태:

| 상태 | 화면 |
|---|---|
| `idle` | 첫 챗봇 입력 |
| `analyzing` | 문의 분석 중 |
| `clarifying` | 추가 질문 표시 |
| `rag_searching` | 공식자료 검색 중 |
| `official_content_ready` | 공식 콘텐츠 카드 제공 |
| `ar_ready` | AR Guide 시작 가능 |
| `ar_running` | 단계별 AR overlay |
| `ar_completed` | 완료/해결 여부 선택 |
| `high_risk_service_route` | expert A/S 연결 카드 |
| `blocked_official_match_failed` | 공식자료 검토 필요 안내 |

개발할 UI:

| UI | 상세 |
|---|---|
| multi-turn chat | 추가 질문/답변 누적 |
| evidence card | 공식자료명, FAQ/Manual 근거 표시 |
| safety card | High Risk 차단 이유 표시 |
| AR start card | AR Guide 시작 버튼 |
| camera alignment frame | 카메라 화면에서 실물을 맞출 기준 영역 |
| reference ghost layer | 구조 타입별 기준 외형/반투명 정렬 실루엣 |
| AR overlay | reference image + part map + step instruction |
| completion flow | 해결됨/해결 안 됨/A/S 연결 |
| save history | 고객이 저장한 AR 세션 재시청 |

최종 검증 기준:

```text
모호한 문의는 추가 질문 UI가 나온다.
High Risk는 AR 화면이 열리지 않는다.
Low Risk는 공식근거 카드 후 AR 시작이 가능하다.
사용자가 실물을 정렬 가이드에 맞춘 상태에서 AR overlay가 실제 부품 위치에 맞는다.
모바일 시연 화면에서 텍스트/버튼이 겹치지 않는다.
```

### 20.10 10단계 안전/품질 검수 최종 개발 항목

현재 상태:

```text
일부 수동 검증 / 체계적 QA 필요
```

검수 항목:

| 검수 | 기준 |
|---|---|
| 안전 차단 | High Risk recall을 최우선으로 검증 |
| 공식자료 근거 | AR step마다 asset_id/chunk_id 존재 |
| 오버레이 정확도 | reference image 기준 target part와 overlay 일치 |
| 금지 action | 전기/냉매/PCB/내부 분해 안내 없음 |
| 다국어 안전 문구 | 안전 문구는 고정 템플릿 번역 사용 |
| 로그 저장 | 판단/RAG/safety/AR session 로그 저장 |

최종 산출물:

```text
06_산출물/qa/api_test_results.json
06_산출물/qa/safety_audit_sample.json
06_산출물/qa/ar_overlay_checklist.md
06_산출물/qa/rag_evidence_checklist.md
06_산출물/qa/demo_scenario_test_log.md
```

### 20.11 11단계 발표/제출 산출물 최종 개발 항목

최종 발표에서 보여줘야 할 것:

| 산출물 | 내용 |
|---|---|
| 서비스 아키텍처 | ThinQ 앱 챗봇, mock adapter, LLM/RAG, 판단엔진, ARGuidePlan 흐름 |
| DB 구조 | mock ThinQ, 공식자료, RAG chunk, 대화, safety log, AR session |
| 정상 관리 시연 | 환경/로그 기반 필터 청소 AR |
| 모호한 문의 시연 | 추가 질문 후 분기 |
| High Risk 시연 | AR 차단 후 A/S 연결 |
| 공식근거 시연 | RAG evidence card와 AR step 연결 |
| 한계/향후 확장 | 실제 ThinQ API, 자동 객체/부품 인식 AR, 더 큰 평가셋, 운영 검수 |

최종 완료로 볼 수 있는 기준:

```text
1. DB에 대화/RAG/평가/안전 로그 구조가 있다.
2. ThinQ mock 데이터가 제품군/지역/진단/환경별로 충분히 확장되어 있다.
3. intent/risk 평가셋과 평가 결과가 있다.
4. ChatbotEngine이 추가 질문을 수행한다.
5. RAGService가 공식자료 근거를 반환한다.
6. AI 판단엔진 v2가 LLM/RAG/진단로그/공식근거를 결합한다.
7. High Risk는 항상 AR을 차단한다.
8. Low Risk는 공식근거가 있을 때만 AR을 연다.
9. ARGuidePlan이 reference image, part map version, evidence를 포함한다.
10. 프론트가 multi-turn 챗봇, 예방 알림 카드, 카메라 정렬 기반 AR Guide Session을 시연할 수 있다.
```

이 기준을 만족하기 전까지는 각 항목을 `구현됨 / 고도화 필요` 또는 `미구현 / 개발 필요`로 유지한다.

## 21. 2026-06-04 기준 개발 순서 재정렬

### 21.1 RAG corpus 수량 재점검

현재 DB 기준 공식자료 corpus는 아래와 같다.

| 항목 | 현재 수량 | 판단 |
|---|---:|---|
| `official_assets` | 791 | 공식자료 asset 저장됨 |
| `official_document_chunks` | 1,997 | 공식자료 chunk 저장됨. 공식 YouTube/추가 공식자료 확장분 포함 |
| `official_document_embeddings` | 3,994 | `BAAI/bge-m3` 1,997건 + `careshot_local_hashing_v1` fallback 1,997건 |
| `owners_manual_pdf` chunk | 702 | PDF 기반 chunk 포함됨 |
| `search_support_result` chunk | 45 | AS-Q24ENXE support 검색 결과 일부만 포함됨 |
| `help_library` chunk | 773 | Help Library/support 후보 chunk 확장됨 |
| `official_faq` asset | 1 | 별도 FAQ landing page asset. 검색 support 후보는 대부분 help_library로 분류됨 |

중요한 정정:

```text
AS-Q24ENXE LG India support 검색 화면의 support 후보 544건 중 기존 DB에는 34개 URL만 반영되어 있었다.
간극 검증 후 누락 510개 URL을 처리했고, 그중 484개 URL을 asset으로 추가했다.

초기 RAG chunk 1,890건은 PDF 기반 chunk, 기존 정제 chunk,
제품 spec/dimension 116건, support search result 45건,
online manual 36건, help library 773건 기준이었다.
2026-06-11 현재 SQLite 기준 corpus는 공식 YouTube/추가 공식자료 확장분까지 포함해
`OFFICIAL_DOCUMENT_CHUNK` 1,997건이며, BGE-M3 embedding 1,997건과 hashing fallback 1,997건을 함께 유지한다.

단, 544건은 순수 FAQ 544건이 아니라 LG India search support tab의 Support 후보 수다.
따라서 현재 완료 범위는 AS-Q24ENXE support/Help Library 후보 확장으로 기록하고,
별도 FAQ landing page 전체 coverage는 다른 수집 범위로 분리한다.
```

### 21.2 다음 작업 우선순위

기존 문서에서 FastAPI, React 프론트, 최종 DB 전환 시점이 분산되어 있어 아래 순서로 재정렬한다.

1. AS-Q24ENXE support/FAQ 전체 수집 간극 검증 - 수행됨 / 후보 544건, 기존 반영 34건, 누락 510건 확인
2. 공식 FAQ/Help Library 원본 HTML 추가 수집 - 수행됨 / 누락 510 URL 처리, 484 asset 추가
3. FAQ/Help Library 본문 추출 및 chunk 확장 - 수행됨 / 신규 762 chunk 생성
4. 신규 chunk embedding 재생성 - 수행됨 / 초기 `official_document_embeddings` 1,890건과 vector index 1,890 line 일치
5. RAGService v2 검색 품질 검증 확대 - 수행됨 / 최초 40개 query 중 37개 통과, 3개 실패 케이스 확인
6. RAGService v2 실패 케이스 보정 - 수행됨 / 재검증 40/40 통과
13. FastAPI 백엔드 구조 전환 - 수행됨 / FastAPI 서버 기동, OpenAPI 생성, live HTTP 기준 RAG 40/40 통과
14. SQLAlchemy 또는 SQLModel repository 계층 작성 - 수행됨 / SQLAlchemy repository 계층 및 SQLite/PostgreSQL registry 검증 완료
15. PostgreSQL + pgvector 최종 DB 전환 - 수행됨 / 2026-06-05 현재 상태 재검증 완료
15.2 PostgreSQL 운영 안정화 및 Alembic migration 관리 전환 - named volume 적용 완료 / Alembic baseline은 18단계 시작 전 수행
16. EnvironmentDataAdapter 구현 - 수행됨 / cache hit, 외부 API refresh, fallback cache, fetch log, Care Risk 전달 검증 완료
16.2 EnvironmentDataAdapter 운영 보완 실행 - 수행됨 / provider adapter, API key manager, 실제 OpenWeather/WAQI key 연결 검증 완료
17. CareRiskScoreEngine 및 Guide 옵션 API 구현 - 수행됨 / Care Risk 계산 및 Guide 옵션 반환 검증 완료, AQI 가중치 보정 완료
17.1 서비스 명칭/제공 방식/이력 저장 정책 변경 반영 - 문서/DB 설계 반영 및 API endpoint 재정리 완료
17.1-A GuideOptionSet 및 Guide 완료 API 재정리 - 수행됨 / 검증 완료
17.2 Product Code Registry 및 제품 등록 흐름 설계/DB 반영 - 수행됨 / 검증 완료
17.3 Device Care History 조회 View/API 구현 - 수행됨 / 검증 완료
17.4 최종 21개 테이블 구조 기준 전체 검증 - 수행됨 / 검증 완료
17.5 공식 YouTube RAG 근거 확장 - 수행됨 / 검증 완료
17.6 power_troubleshooting 제한 AR/동적 매뉴얼 보강 - 수행됨 / 검증 완료
18. ChatbotEngine 구현 - 수행됨 / 검증 완료
18.1 ChatbotEngine 최종 21개 테이블 정합 보정 - 수행됨 / `decision_logs` 미사용, `AI_INQUIRY_ANALYSIS.intent_type` 저장
18.2 service_flow_type 보정 - 수행됨 / self_care, self_as, expert_as 분기 검증
18.3 AR 선행 수집 데이터 정의 - 수행됨 / 문서 반영 완료
18.4 LLM과 embedding 역할 분리 - 수행됨 / 문서 반영 완료
18.5 로컬 BGE-M3 embedding 전환 - 수행됨 / `BAAI/bge-m3` 1,997건 embedded, hashing fallback 유지
18.6 BGE-M3 RAG 품질 재검증 - 수행됨 / 40/40 통과, top1 accuracy 1.0
19. ConversationState 기반 multi-turn 추가 질문 구현 - 수행됨 / 5개 모호 문의 multi-turn 검증 완료
20. LLMServiceMock 또는 LLM adapter 구현 - 수행됨 / mock provider 및 ChatbotEngine 연동 검증 완료
21. DecisionEngineV2 구현 및 판단엔진 v2 -> ARGuidePlan 연결 - 수행됨 / 검증 완료
22. React + TypeScript 프론트 전환 - 수행 중 / FastAPI 실제 호출, Home/Chat/ARGuide/API client/회원가입 DB 연동 검증 완료
22.1 프론트 원본 도입 및 백업 - 수행됨
22.2 백엔드 프론트 호환 API 추가 - 수행됨
22.3 프론트 fetch 전환 - 수행됨
22.4 회원가입/로그인/프로필 DB 연동 - 수행됨
22.5 제품 코드 등록 시연 흐름 - 후속 필요
22.6 AR reference image 정적 서빙 및 part map 좌표 seed - 후속 필요
23. 프론트 챗봇 UI를 multi-turn + 공식근거 카드 구조로 변경 - 수행 중 / 자유입력 추가 질문, 저정보 문의 추가질문 guard, API 기반 YouTube+단계 가이드 표시, 전원 문의 risk/detail 분리 검증
23-1. self care 추천 UI 구현 - 부분 수행 / Care Risk API 연결, 화면 문구 QA 후속
24. 안전 차단 카드 / expert A/S 연결 카드 / AR 시작 카드 정리 - 수행됨 / High Risk, no-match, Low/Medium 화면 분기 검증 완료
25. RAG 연결 후 intent/risk 평가 기준 확정 - 수행됨 / 2026-06-12 검증 완료
26. VOC 원천 풀에서 intent/risk 평가셋 별도 라벨링 - 수행됨 / 2026-06-12 검증 완료
27. EvaluationService 구현 및 정확도 리포트 생성 - 수행됨 / 147건 평가 실행, 정확도 리포트 저장, 실패 케이스 분류 완료
28. 정상/모호/Medium/High Risk/매칭 실패/self care 추천 시나리오 검증 - 수행됨 / 7개 시나리오 자동검증, QA 리포트, 화면 캡처 생성 완료
29. AR 오버레이 정확도 검수 - 다음 작업
30. 발표용 UI와 산출물 정리

### 21.3 FastAPI 전환 시점

FastAPI 전환은 ChatbotEngine이나 React 프론트보다 먼저 진행한다.

이유:

```text
현재 Python 기본 HTTP 서버는 데모 연결용이다.
최종 개발에서는 FastAPI가 API schema, OpenAPI 문서, Pydantic validation,
AI/RAG service dependency injection, DB repository 계층을 묶는 중심이어야 한다.
```

FastAPI 전환 후 API 구조:

| API | 역할 |
|---|---|
| `POST /api/v1/chat/messages` | 고객 문의 입력, 챗봇 응답, 추가 질문 또는 AR 분기 |
| `POST /api/v1/ai/analyze` | intent/risk/context 분석 |
| `POST /api/v1/rag/search` | 공식자료 evidence 검색 |
| `POST /api/v1/ar/plans` | ARGuidePlan 생성 |
| `POST /api/v1/ar/sessions` | AR Guide Session 시작/저장 |
| `GET /api/v1/guides/options` | Manual Guide와 AR Guide 옵션 세트 조회 |
| `POST /api/v1/guides/{guide_id}/complete` | Guide 완료 이력 저장 |

### 21.4 최종 설계 DB 전환 시점

SQLite는 개발 검증용으로 유지하지만 최종 설계 DB는 PostgreSQL + pgvector로 전환한다.

전환 시점:

```text
FastAPI 백엔드 구조 전환 직후,
React 프론트 고도화와 ChatbotEngine/DecisionEngine v2 본격 통합 전에 전환한다.
```

이유:

```text
ChatbotEngine, DecisionEngine v2, RAGService, ARGuidePlan 저장 로직이
SQLite 전용 구조에 깊게 묶인 뒤 전환하면 재작업이 커진다.

따라서 FastAPI + repository 계층을 먼저 만들고,
그 repository 계층이 PostgreSQL + pgvector를 바라보게 바꾼 뒤,
프론트와 AI 엔진을 최종 DB 기준 API에 연결한다.
```

최종 DB 전환 범위:

| 현재 | 최종 |
|---|---|
| SQLite `official_document_chunks` | PostgreSQL `official_document_chunks` |
| SQLite `official_document_embeddings` | PostgreSQL `official_document_embeddings` + pgvector |
| JSONL vector index | pgvector HNSW/IVFFLAT index |
| mock users/devices/logs | PostgreSQL seed data |
| Python 직접 sqlite query | SQLAlchemy/SQLModel repository |

### 21.5 프론트/백 연결 개발 기준

프론트는 단순 정적 화면이 아니라 FastAPI API 응답을 기준으로 상태가 바뀌어야 한다.

연결 기준:

| 프론트 상태 | 호출 API | 백엔드 결과 |
|---|---|---|
| 고객 문의 입력 | `POST /api/v1/chat/messages` | intent/risk 분석 시작 |
| 공식근거 검색 중 | `POST /api/v1/rag/search` | evidence card 반환 |
| 추가 질문 필요 | `POST /api/v1/chat/messages` | clarification message 반환 |
| Low Risk AR 가능 | `POST /api/v1/ar/plans` | ARGuidePlan 반환 |
| High Risk 차단 | `POST /api/v1/ai/analyze` | A/S 연결 상태 반환 |
| AR 시작 | `POST /api/v1/ar/sessions` | ar_guide_session 생성 |
| 저장 | `POST /api/v1/ar/sessions/{id}/save` | 고객별 저장 이력 생성 |

이 연결 기준이 문서와 코드에 반영되기 전까지 프론트/백 통합은 완료로 보지 않는다.

## 22. 13-보정: SQLite official_document_embeddings 재적재

### 22.1 보정 사유

14단계 SQLAlchemy 또는 SQLModel repository 계층 작성으로 넘어가기 전, 완료 기준에 포함된 아래 조건을 재검증했다.

```text
SQLite seed 데이터 791 asset, 1,890 chunk, 1,890 embedding을 repository로 조회 가능
```

재검증 결과 `official_assets` 791건, `official_document_chunks` 1,890건은 유지되고 있었지만, `official_document_embeddings`는 0건이었다.

원인:

```text
vector_index/official_document_embeddings.jsonl 파일에는 1,890건이 존재했으나,
seed_ar_mock_db.py가 SQLite DB reset 후 official_document_embeddings 테이블에 JSONL을 재적재하지 않았음.
```

### 22.2 수행 내용

```text
1. seed_ar_mock_db.py에 vector_index/official_document_embeddings.jsonl 로딩 로직 추가
2. JSONL 1,890건을 SQLite official_document_embeddings에 INSERT/UPSERT
3. official_document_chunks.embedding_status를 embedded로 재갱신
4. seed_ar_mock_db.py 재실행
5. RAG 검색이 lexical fallback이 아니라 metadata_strict_vector_similarity로 동작하는지 확인
```

### 22.3 검증 결과

SQLite 검증:

```text
official_assets: 791
official_document_chunks: 1,890
official_document_embeddings: 1,890
embedded_chunks: 1,890
embedding_model: careshot_local_hashing_v1
embedding_status: embedded
```

RAG 검색 검증:

```text
POST /api/v1/rag/search
query: how to clean AC filter
product_type: air_conditioner
model_name: AS-Q24ENXE
procedure_type: filter_cleaning

status_code: 200
retrieval_mode: metadata_strict_vector_similarity
result_count: 3
first_vector_score: 0.52696998
```

### 22.4 현재 상태

```text
13-보정 수행됨.
Embedding/Vector DB의 SQLite table과 JSONL vector index가 다시 1,890건으로 일치함.
RAGService v2가 vector similarity 경로로 동작함.
이제 14단계 repository 계층 작성으로 넘어갈 수 있음.
```


## 23. 13-보정 재검증: seed reset 후 embedding 재적재 확인

14단계 repository 계층 작성으로 넘어가기 전, `official_document_embeddings SQLite 재적재`가 실제 reset 이후에도 동작하는지 재검증했다.

검증 과정:

```text
1. JSONL vector index 1,890건 존재 확인
2. SQLite official_document_embeddings 1,890건 존재 확인
3. JSONL chunk_id set과 DB chunk_id set 일치 확인
4. embedding_dimension 512 확인
5. embedding_vector_json 비어있는 row 0건 확인
6. CareShot FastAPI/AR 서버가 DB file lock을 잡고 있어 seed reset 1차 실패 확인
7. CareShot 관련 서버만 중지
8. seed_ar_mock_db.py 실제 재실행
9. reset 후 791 asset / 1,890 chunk / 1,890 embedding 유지 확인
10. FastAPI/AR 서버 재기동
11. live HTTP RAG 검색이 metadata_strict_vector_similarity로 동작하는지 확인
```

재검증 결과:

```text
official_assets: 791
official_document_chunks: 1,890
official_document_embeddings: 1,890
embedded_chunks: 1,890
missing_embedding_for_chunk: 0
orphan_embeddings: 0
jsonl_db_id_sets_match: True
db_dimension_counts: [(512, 1890)]
db_nonempty_vectors: 1,890
retrieval_mode: metadata_strict_vector_similarity
FastAPI health: http://127.0.0.1:8790/api/v1/health 200
AR/frontend server: http://127.0.0.1:8787/ 200
```

결론:

```text
13-보정은 실제 seed reset 재실행 기준으로 검증 완료.
14단계 SQLAlchemy repository 계층은 이후 수행 및 검증 완료되었다.
당시 완료 흐름 기준 다음 번호 단계는 18. ChatbotEngine 구현이었다. 현재 기준으로는 21. DecisionEngineV2 구현 및 판단엔진 v2 -> ARGuidePlan 연결과 25~26단계까지 완료되었다. 22번 React/Vite 프론트 전환은 FastAPI 실제 호출, 회원가입 DB 연동, Home/Chat/ARGuide 연결까지 부분 수행되었다. 남은 작업은 제품 코드 등록 시연 흐름, AR reference image/part map 보강, 23~24번 화면 QA다.
```

## 24. 14단계: SQLAlchemy repository 계층 작성 - 수행됨 / 검증 완료

14단계에서는 FastAPI 백엔드가 SQLite DB를 직접 조회하는 구조를 repository interface와 SQLAlchemy session manager 기반 구조로 분리했다.

수행 내용:

```text
1. SQLAlchemy, pytest 의존성 설치
2. 04_백엔드/app/repositories/ 생성
3. SQLAlchemySessionManager 작성
4. UserRepository, DeviceRepository, UsageLogRepository, EnvironmentRepository 작성
5. ProductModelRepository, StructureTypeRepository, ReferenceImageRepository, PartMapRepository 작성
6. OfficialAssetRepository, RAGRepository 작성
7. ConversationRepository, CareHistoryRepository, ARSessionRepository, EvaluationRepository 작성
8. SQLiteRepositoryRegistry와 PostgreSQLRepositoryRegistry를 같은 RepositoryRegistry contract로 구성
9. ThinQ model_name exact 기준 resolver resolve_model_structure(...) 구현
10. FastAPI CareShotBackendService가 새 CareShotRepository facade를 사용하도록 변경
11. repository 단위 테스트 작성 및 실행
12. FastAPI live HTTP와 RAG 40 query 재검증
```

산출물:

```text
04_백엔드/app/repositories/
04_백엔드/tests/test_repositories_sqlalchemy.py
04_백엔드/requirements.txt
04_백엔드/Repository_계층_구현_정리.md
```

완료 기준 검증:

```text
official_assets: 791
official_document_chunks: 1,890
official_document_embeddings: 1,890
embedding_status embedded: 1,890
```

ThinQ exact model resolver 검증:

```text
resolve_model_structure('AS-Q24ENXE', 'air_conditioner')
match_type: exact_model
structure_type: wall_ac_type_a
reference_image_id: REF_ASQ24_OPEN_FILTER_V1
part_map_version_id: PMV_WALL_AC_A_OPEN_FILTER_V1
part_maps: 5
```

테스트 결과:

```text
python -m pytest tests/test_repositories_sqlalchemy.py -q
8 passed
```

FastAPI/RAG 검증:

```text
GET /api/v1/health: 200
GET /api/v1/demo/context: 200
POST /api/v1/rag/search: metadata_strict_vector_similarity
FastAPI RAG 40 query: 40 passed / 0 failed
8787 AR demo server: app.repositories.CareShotRepository 사용, GET / 200
```

주의사항:

```text
PostgreSQLRepositoryRegistry는 같은 method contract를 쓰도록 준비되었고,
15단계에서 실제 PostgreSQL + pgvector schema, migration, vector index, seed, top-k 검증까지 수행했다.
이 기록은 15단계 완료 직후의 과거 기준이며, 당시 다음 작업은 16단계 EnvironmentDataAdapter 구현이었다.
```

당시 다음 작업:

```text
16. EnvironmentDataAdapter 구현
```

## 2026-06-11 최신 기준: 18. ChatbotEngine 구현 반영

18단계 ChatbotEngine은 FastAPI `POST /api/v1/chat/messages`에 연결되었다.

구현 범위:

```text
1. 사용자 메시지 입력
2. CHAT_SESSION 생성 또는 기존 session_id 이어받기
3. CHAT_MESSAGE에 사용자 메시지 저장
4. DecisionEngine/RAGService 기반 context, intent, risk, official evidence 분석
5. self_care / self_as / expert_as 분류
6. Low / Medium / High risk 판단
7. 공식근거 RAG 검색 및 RAG_SEARCH_LOG 연결 저장
8. Low/Medium + 공식근거 검증 시 GuideOptionSet 반환
9. High Risk 또는 expert_as는 AR Guide 차단 및 safety_card 반환
10. 모호한 문의는 CONVERSATION_STATE에 missing_slots, next_question 저장
11. CHATBOT_INQUIRY와 AI_INQUIRY_ANALYSIS 저장
12. AI 응답 말풍선을 CHAT_MESSAGE에 저장
```

저장 테이블:

```text
CHAT_SESSION
CHATBOT_INQUIRY
AI_INQUIRY_ANALYSIS
CHAT_MESSAGE
CONVERSATION_STATE
RAG_SEARCH_LOG
```

유지한 금지 기준:

```text
old API는 재생성하지 않음
PREVENTIVE_ALERT, ContentViewLog, ADMIN_REVIEW 테이블 재도입 없음
ContentOptionSet 명칭 재도입 없음
GuideOptionSet 기준 유지
Guide 완료 이력은 SELF_MANAGEMENT_HISTORY 기준 유지
```

검증:

```text
python -m pytest -q -rs
-> 28 passed, 1 skipped
```

당시 다음 작업:

```text
19. LLMServiceMock 또는 응답 문장 adapter 분리
20. multi-turn slot filling 시나리오 확대 검증
```

2026-06-15 최신 기준으로는 위 작업에 더해 21단계 DecisionEngineV2 구현 및 ARGuidePlan 연결, 25단계 RAG 연결 후 intent/risk 평가 기준 확정, 26단계 VOC 원천 풀 기반 intent/risk 평가셋 별도 라벨링까지 수행 및 검증 완료되었다. 22단계 React/Vite 프론트 전환은 FastAPI 실제 호출, 회원가입 DB 저장, 주소 기반 환경/Care Risk 연결, ARGuide API 연결까지 부분 수행되었다. 23~24단계는 카드별 화면 QA와 원본 UI 안에서의 분기 표시 검증이 남아 있다.

## 26.2 공식 YouTube RAG 에어컨 영상 최종 확장 - LG DIY Service 포함

사용자 피드백에 따라 `AC` 키워드만으로는 수집 범위가 부족하다고 판단하고, `Air Conditioner` 키워드와 `LG DIY Service - Air Conditioner` 재생목록/채널 검색 결과를 추가 수집 범위로 확장했다.

수행 내용:

```text
1. LG DIY Service 공식 채널 whitelist 추가
2. LG India의 LG DIY Service - Air Conditioner 재생목록 후보 55건 확인
3. LG DIY Service 채널의 Air Conditioner / AC 검색 후보 포함
4. YouTube oEmbed author_name/author_url 검증
5. watch URL 접근 검증
6. 제품군은 air_conditioner만 유지
7. OFFICIAL_ASSET / OFFICIAL_DOCUMENT_CHUNK / OFFICIAL_DOCUMENT_EMBEDDING 반영
8. 타는 냄새, CH38/error code 영상은 expert_as_only 근거로 분류
9. No Power / turning off 영상은 power_troubleshooting self-AS 근거로 분류하고 AR 안내 차단
```

최종 반영 결과:

```text
attempted: 107
stored: 106
skipped: 1
official_youtube_total: 106
official_youtube_aircon: 106
official_youtube_non_aircon: 0
youtube_aircon_chunks: 106
youtube_aircon_embeddings: 106

LG India: 67
LG DIY Service: 36
LG Global: 3
```

검증 결과:

```text
python -m pytest tests -q
-> 26 passed, 1 skipped

반복 재실행 주의:
YouTube watch 페이지는 대량 재확인 시 429 Too Many Requests가 발생할 수 있음.
oEmbed author_name/author_url 공식 채널 검증이 성공하면 저장 후보는 유효로 보고,
429 발생 건수는 direct_access_rate_limited로 별도 기록함.
```

## 26.3 전원 꺼짐 / No Power self-AS 보강

`에어컨 전원이 갑자기 꺼졌어요`, `no power`, `power off`, `turning off` 계열 문의가 에어컨 기본값인 `filter_cleaning`으로 fallback되는 위험을 차단했다.

수행 내용:

```text
1. POWER_ISSUE_KEYWORDS 추가
2. 전원 꺼짐/No Power 계열 intent를 self_as로 분류
3. procedure_type을 power_troubleshooting으로 고정
4. risk_level medium + ar_guide_allowed False 처리
5. decision_action을 manual_or_service_guidance_only로 분리
6. No Power / turning off YouTube chunk를 power_troubleshooting으로 재분류
7. RAG 검색 시 filter_cleaning 근거가 섞이지 않도록 테스트 추가
```

검증 결과:

```text
power_troubleshooting official_youtube chunk: 3
RAG power_troubleshooting query -> 전원 문제 YouTube 3건만 반환
filter_cleaning 반환 없음

python -m pytest tests -q
-> 29 passed, 1 skipped
```

## 26.4 Manual / YouTube 매칭 정책 및 추천 selector 구현

공식 매뉴얼과 공식 YouTube를 고객 문의에 붙일 때 제목 일치가 아니라 `product_type + procedure_type + risk_policy + 공식 채널 검증` 기준으로 추천하도록 정리했다.

수행 내용:

```text
1. Manual Guide 매칭 정책 확정
   - product_type + procedure_type + language + exact/common model
   - cross-procedure fallback 금지

2. YouTube 추천 정책 확정
   - RAG official_youtube evidence 우선
   - 부족하면 DB catalog fallback
   - exact procedure_type만 허용
   - self_care/self_as 추천 카드에서 expert_as_only 제외

3. procedure_type 후보 정리
   - filter_cleaning
   - auto_clean
   - remote_operation
   - no_cooling_self_check
   - odor_self_check
   - noise_self_check
   - water_leak_monsoon
   - power_troubleshooting
   - high_risk_troubleshooting

4. GuideOptionSet 응답 확장
   - youtube_recommendations
   - matching_policy
```

검증 결과:

```text
GET /api/v1/guides/options filter_cleaning
-> manual_count 1, ar_count 1, youtube_count 3

POST /api/v1/chat/messages "The AC power suddenly turns off."
-> procedure_type power_troubleshooting
-> ar_guide_allowed False
-> youtube_count 2
-> filter_cleaning 추천 없음

python -m pytest tests -q
-> 33 passed, 1 skipped
```

산출물:

```text
06_산출물/2026-06-11_manual_youtube_matching_policy_정리.md
```

## 26. 공식 YouTube 링크 RAG 저장 및 Manual Guide 동시 제공 - 수행됨 / SQLite 검증 완료

목표:

```text
Manual Guide를 공식 LG/LG India 문서 기반으로 생성할 때,
고객 문의와 procedure_type이 일치하는 공식 YouTube 영상도 함께 제공한다.
```

설계 결론:

```text
1. DB 테이블은 현재 21개 최종 구조를 유지한다.
2. YouTube 원본은 OFFICIAL_ASSET(source_type=official_youtube)에 저장한다.
3. RAG 검색용 영상 metadata/요약 chunk는 OFFICIAL_DOCUMENT_CHUNK에 저장한다.
4. 해당 chunk embedding은 OFFICIAL_DOCUMENT_EMBEDDING에 저장한다.
5. 실제 Manual Guide 응답에서 바로 노출할 대표 영상은 GUIDE.video_url에 연결한다.
6. AR Guide overlay 자체는 video_url을 쓰지 않고, 공식 문서 기반 단계 텍스트만 사용한다.
```

구현 파일:

```text
02_데이터연동/scripts/collect_official_youtube_guides.py
04_백엔드/app/repositories/sqlalchemy_repositories.py
04_백엔드/app/services.py
04_백엔드/app/schemas.py
04_백엔드/app/main.py
04_백엔드/app/routers/contents.py
04_백엔드/tests/test_content_option_flow.py
04_백엔드/tests/test_repositories_sqlalchemy.py
```

수집 방식:

```text
1. 발표/MVP 기준 공식 영상 후보를 LG India, LG Global 공식 채널에서 선별한다.
2. YouTube oEmbed로 author_name/author_url이 whitelist와 일치하는지 확인한다.
3. watch URL에 직접 접속해 200 응답을 확인한다.
4. title, channel, product_type, procedure_type, customer query phrases를 chunk_text로 구성한다.
5. careshot_local_hashing_v1 embedding을 생성해 RAG 후보로 편입한다.
```

향후 운영형 수집 권장 방식:

```text
1. YouTube Data API search.list 사용
   - channelId: LG India / LG Global / 필요한 지역 공식 채널 ID
   - q: product_type + procedure_type + customer query keyword
   - type=video
   - maxResults=50
   - regionCode=IN
   - relevanceLanguage=en 또는 hi
   - videoEmbeddable=true
2. YouTube Data API videos.list로 2차 검증
   - snippet.channelId/channelTitle/title/description
   - contentDetails.duration/caption
   - status.embeddable/privacyStatus
3. 사내 whitelist 통과 영상만 OFFICIAL_ASSET에 저장
4. title/description/caption/운영자가 작성한 요약을 OFFICIAL_DOCUMENT_CHUNK로 저장
5. 위험 키워드(연기, 타는 냄새, 전기, 냉매, 내부 분해 등)는 영상 추천 대상에서 제외하고 expert_as로 라우팅
```

현재 SQLite 적재 결과:

```text
OFFICIAL_ASSET official_youtube: 8건
OFFICIAL_DOCUMENT_CHUNK official_youtube chunk: 8건
OFFICIAL_DOCUMENT_EMBEDDING official_youtube embedding: 8건
GUIDE_1.video_url: https://www.youtube.com/watch?v=tR91lFD0yIo
```

검증 결과:

```text
1차 검증:
- collect_official_youtube_guides.py 실행
- attempted 8 / stored 8 / skipped 0
- 8개 모두 공식 채널 oEmbed 확인 및 watch URL 200 확인

2차 검증:
- DB 재조회 결과 official_youtube 8건 확인
- vector 후보 10건 중 YouTube URL 3건 포함
- RAGService 검색 결과에 LG Split AC Filter Cleaning URL 포함
- 8개 URL 모두 oEmbed 200, watch URL 200 재확인
- python -m pytest tests -q -> 25 passed, 1 skipped
```

주의:

```text
PostgreSQL live seed --no-reset은 기존 PostgreSQL varchar 길이 제한에 걸려 중단됨.
SQLite 기본 DB, FastAPI repository, RAGService, API 테스트 기준 구현은 완료.
PostgreSQL 재적재까지 최신 YouTube 8건을 반영하려면 PG seed/스키마 길이 보정을 별도 수행해야 함.
2026-06-11 추가 보강: YOUTUBE_API_KEY가 없는 현재 실행에서는 공식 description/caption 원문은 미수집이나, 각 YouTube chunk에 Official video summary 운영 요약을 저장하고 API metadata 미수집 상태를 명시함.
운영 환경에서는 YOUTUBE_API_KEY를 설정해 videos.list 기반 description/caption/duration/caption availability/embeddable/privacy/region restriction metadata까지 채우는 것을 권장함.
```

### 26.1 브라우저 기반 에어컨 공식 YouTube 확장 수집 - 수행됨 / 검증 완료

사용자 요청에 따라 API key 없이 브라우저/검색 기반으로 LG India / LG Global 공식 YouTube의 에어컨 관련 영상만 확장 수집했다.

변경된 기준:

```text
1. 세탁기/냉장고 official_youtube 후보는 제거
2. 에어컨 product_type만 유지
3. LG India, LG Global whitelist만 통과
4. YouTube oEmbed author_name/author_url 검증
5. watch URL 200 접속 검증
6. RAG 결과에서 manual/help_library chunk와 official_youtube chunk가 함께 내려오도록 보정
```

현재 결과:

```text
official_youtube_total: 31
air_conditioner official_youtube: 31
non-air_conditioner official_youtube: 0
official_youtube chunk: 31
official_youtube embedding: 31
skipped: 1건, LG Malaysia 채널이라 whitelist 제외
```

검증 결과:

```text
31개 URL 모두 oEmbed 200 / watch URL 200
RAG vector 후보에 YouTube URL 포함
RAGService top 8 결과에 help_library + official_youtube 동시 포함
GET /api/v1/guides/options -> GUIDE_1 video_url 반환
python -m pytest tests -q -> 26 passed, 1 skipped
```

추가 산출물:

```text
02_데이터연동/scripts/collect_official_youtube_guides.py
06_산출물/official_youtube/official_youtube_aircon_collection_report.json
04_백엔드/tests/test_rag_official_youtube_evidence.py
```

### 25.1 15단계 현재 상태 재검증 - 2026-06-05 수행됨

사용자 지적에 따라 16단계로 넘어가기 전에 15단계가 현재 상태에서도 실제 수행/구현/동작하는지 다시 확인했다.

재검증 명령:

```text
docker ps --filter name=careshot-pgvector
python 05_DB/postgres/scripts/verify_pgvector_topk.py
```

재검증 결과:

```text
careshot-pgvector container: Up
pgvector_extension_version: 0.8.2
HNSW index exists: true
official_assets PostgreSQL count: 791
official_document_chunks PostgreSQL count: 1,890
official_document_embeddings PostgreSQL count: 1,890
environment_providers PostgreSQL count: 2
environment_observations PostgreSQL count: 2
care_risk_rules PostgreSQL count: 2
preventive_alerts PostgreSQL count: 과거 확장안 기준 기록. 현재 최종 21개 테이블 구조에서는 사용하지 않음
structure_types PostgreSQL count: 7
canonical_aircon_structure_types: 3
SQLite 주요 table count 비교: 모두 match true
pgvector top-k 검증 case: PGV_AC_FILTER_001 / PGV_AC_ODOR_001 / PGV_WM_TUB_001
all_query_top1_matches: true
```

재검증 판단:

```text
15단계 PostgreSQL + pgvector 최종 DB 전환은 현재 상태 기준으로도 완료로 판단한다.
이 기록은 15단계 재검증 시점의 과거 기준이며, 당시 다음 번호 단계는 16. EnvironmentDataAdapter 구현이었다.
```

## 26. 16단계: EnvironmentDataAdapter 구현 - 수행됨 / 검증 완료

16단계는 기존 `environment_observations` 직접 조회 방식에서 벗어나, 환경 데이터 조회를 `EnvironmentDataAdapter`로 통합하는 작업이다.

구현 목표:

```text
1. DB cache freshness 우선 확인
2. cache 만료 또는 강제 refresh 시 외부 API adapter 호출
3. 외부 API 응답을 temperature, humidity, AQI, PM2.5, PM10, rain/monsoon intensity, water hardness 형태로 정규화
4. 정규화 결과를 environment_observations에 저장
5. environment_api_fetch_logs에 성공/실패 로그 저장
6. 외부 API 실패 시 environment_contexts fallback cache 사용
7. Care Risk 계산에 최신 환경 관측값 전달
```

구현 파일:

```text
04_백엔드/app/adapters/environment.py
04_백엔드/app/adapters/__init__.py
04_백엔드/app/repositories/interfaces.py
04_백엔드/app/repositories/sqlalchemy_repositories.py
04_백엔드/app/schemas.py
04_백엔드/app/services.py
04_백엔드/app/routers/environment.py
04_백엔드/tests/test_environment_data_adapter.py
```

구현 내용:

```text
EnvironmentProvider interface 추가
OpenMeteoEnvironmentProvider 추가
EnvironmentDataAdapter 추가
provider registry와 select_provider() 추가
create_environment_observation repository method 추가
/environment/current query에 user_id, product_type, provider_id, requested_metrics, cache_ttl_minutes, force_refresh 반영
/environment/refresh request schema 확장
/care/risk/evaluate가 환경 데이터를 직접 조회하지 않고 EnvironmentDataAdapter를 통해 조회하도록 변경
```

개발용 외부 API 처리 기준:

```text
최종 구조에서는 provider/API key 기반 외부 환경 API를 사용한다.
현재 검증 가능한 개발 adapter는 API key 없이 호출 가능한 Open-Meteo weather/air-quality API를 사용한다.
요청 provider_id는 fetch log에 남기고, 실제 runtime provider는 response_summary에 runtime_provider_id로 기록한다.
```

검증 명령:

```text
python -m py_compile app/adapters/environment.py app/services.py app/schemas.py app/routers/environment.py app/repositories/sqlalchemy_repositories.py app/repositories/interfaces.py
python -m pytest tests/test_environment_data_adapter.py -q
python -m pytest tests/test_environment_data_adapter.py tests/test_repositories_sqlalchemy.py tests/test_postgres_repository_pgvector.py -q
FastAPI PostgreSQL mode port 8791 실행 후 실제 HTTP API 호출
```

검증 결과:

```text
py_compile: 통과
EnvironmentDataAdapter unit test: 3 passed
repository/postgres 관련 테스트 포함: 11 passed, 1 skipped
GET /api/v1/health: health_ok true
GET /api/v1/environment/current: current_mode cache_hit
POST /api/v1/environment/refresh: refresh_mode external_api_refresh
POST /api/v1/environment/refresh: refresh_log_status success_external_api
POST /api/v1/care/risk/evaluate: care_environment_mode cache_hit
POST /api/v1/care/risk/evaluate: care_environment_observation_id ENVOBS_63443062A196
POST /api/v1/care/risk/evaluate: guide_options 반환, 별도 alert 저장 없음
```

PostgreSQL 적재 검증:

```text
environment_observations: 3
environment_api_fetch_logs: 2
care_risk_scores: 2
preventive_alerts: 과거 확장안 기준 기록. 현재 최종 21개 테이블 구조에서는 사용하지 않음
```

중간 실패와 보정:

```text
1. 최초 16단계 진행 전에 15단계 현재 상태 재검증을 생략하고 넘어가려는 절차 오류가 있었음
   -> 16단계 작업을 중단하고 15단계 재검증 및 문서/로그 보정 후 재개
2. EnvironmentDataAdapter 파일은 있었지만 service/router가 아직 기존 직접 조회 방식을 사용하고 있었음
   -> services.py, routers/environment.py를 adapter 경유 방식으로 보정
3. create_environment_observation repository method가 없어서 외부 API 결과 저장 경로가 빠져 있었음
   -> interface와 SQLAlchemy repository에 insert method 추가
4. provider_id는 입력받지만 실제 provider 객체 선택 구조가 약했음
   -> EnvironmentDataAdapter에 provider registry와 select_provider()를 추가하고 재검증
```

당시 다음 작업:

```text
17. CareRiskScoreEngine 및 예방 알림 API 구현
```

## 27. 17단계: CareRiskScoreEngine 및 Guide 옵션 API 구현 - 수행됨 / 검증 완료

17단계는 고객 문의가 없어도 ThinQ 사용 로그, 스마트 진단, 최신 환경 데이터를 기준으로 self care 필요도를 계산하고, 기준 이상이면 API 응답에 Manual Guide와 AR Guide 옵션을 함께 제공하는 단계다. 최종 21개 테이블 기준에서는 예방 알림을 별도 테이블에 저장하지 않는다.

구현 목표:

```text
1. CareRiskScoreEngine 구현
2. PreventiveCareRecommendationEngine 구현
3. 사용 시간, 마지막 관리일, 청소 이력, 습도, AQI, PM2.5, PM10, 경수, 몬순, 제품군 민감도, 스마트 진단 보정 반영
4. care_risk_score, risk_band, trigger_reason, procedure_type, urgency, recommended_options 반환
5. score가 threshold 이상이면 응답에 guide_options 포함
6. Manual Guide와 AR Guide를 함께 제공
7. 사용자가 Guide 완료 시 SELF_MANAGEMENT_HISTORY에 완료 이력을 저장하는 API 동작 검증
```

구현 파일:

```text
04_백엔드/app/engines/__init__.py
04_백엔드/app/engines/care_risk.py
04_백엔드/app/services.py
04_백엔드/tests/test_care_risk_engine.py
```

구현 내용:

```text
CareRiskScoreEngine.evaluate()
- device, usage_log, smart_diagnosis, environment, rules, procedure_type 입력
- usage factor: days_since_last_care, daily_runtime_hours
- environment factor: humidity, AQI, PM2.5, PM10, water_hardness, rain_monsoon_intensity
- smart diagnosis factor: low/medium/high severity 보정
- product_type별 민감도 반영
- threshold는 care_risk_rules.threshold_json 우선 사용

PreventiveCareRecommendationEngine.build()
- self care 추천 title/message 생성
- recommended_options에 manual과 ar_guide 동시 제공

CareShotBackendService.evaluate_care_risk()
- EnvironmentDataAdapter로 최신 환경 데이터 조회
- CareRiskScoreEngine으로 score 계산
- score는 stored: false로 응답
- threshold 이상이면 guide_options 포함
- PREVENTIVE_ALERT, ContentViewLog, ADMIN_REVIEW 기반 저장 흐름은 사용하지 않음
```

검증 명령:

```text
python -m py_compile app/engines/care_risk.py app/engines/__init__.py app/services.py
python -m pytest tests/test_care_risk_engine.py tests/test_environment_data_adapter.py -q
python -m pytest tests/test_care_risk_engine.py tests/test_environment_data_adapter.py tests/test_repositories_sqlalchemy.py tests/test_postgres_repository_pgvector.py -q
FastAPI PostgreSQL mode port 8792 실행 후 실제 HTTP API 호출
```

검증 결과:

```text
py_compile: 통과
CareRiskScoreEngine + EnvironmentDataAdapter tests: 5 passed
repository/postgres 관련 테스트 포함: 13 passed, 1 skipped

POST /api/v1/care/risk/evaluate
score: 54.5
risk_band: low
urgency: recommended
trigger_reason_count: 3
recommended_options: manual, ar_guide
alert_created: false
notification_status: not_stored
content_match_count: not_stored
stored: false
guide_options: manual + ar_guide

GET /api/v1/guides/options
manual_guide: included
ar_guide: included

POST /api/v1/guides/{guide_id}/complete
history_table: SELF_MANAGEMENT_HISTORY
manual_ar_method_saved: false
```

PostgreSQL 적재 검증:

```text
SELF_MANAGEMENT_HISTORY: Guide 완료 이력 저장
OFFICIAL_ASSET/GUIDE/AR_GUIDE: Guide 옵션 조회 기준
PREVENTIVE_ALERT/ContentViewLog/ADMIN_REVIEW: 최종 구조에서 사용하지 않음
```

중간 실패와 보정:

```text
1. 기존 services.py에는 compute_care_risk_score 함수가 있었지만, 독립 CareRiskScoreEngine 산출물이 아니었음
   -> app/engines/care_risk.py로 점수 엔진과 추천 엔진을 분리
2. 기존 API 응답은 trigger_reason, urgency, recommended_options를 명확히 제공하지 않았음
   -> evaluate_care_risk 응답에 care_risk_decision과 recommended_options 추가
3. 기존 점수 계산은 smart_diagnosis 보정이 빠져 있었음
   -> CareRiskScoreEngine에 smart_diagnosis severity 보정 추가
```

당시 다음 작업:

```text
17.1-A GuideOptionSet 및 Guide 완료 API 재정리
```

## 28. 17.2단계: Product Code Registry 및 제품 등록 흐름 설계/DB 반영 - 수행됨 / 검증 완료

17.2단계는 사용자가 CareShot 웹에서 제품 코드를 입력해 제품을 등록할 때, LG India 공식 출처 기반 registry로 exact code를 검증하고 검증된 제품만 등록 가능하게 만드는 단계다.

수행 내용:

```text
1. LG India 공식 제품 페이지 기준 제품 코드 seed 생성
2. LG India Support/Manual/API 계열 근거와 기존 official_assets, official_document_chunks 연결
3. product_code_registry, product_code_aliases, product_registration_attempts 테이블 추가
4. devices에 product_code_id, registered_product_code, product_code_verification_status 컬럼 추가
5. product_models와 연결해 structure_type을 반환하는 구조 확립
6. 최종 시연용 에어컨 구조 타입 seed 정리
7. 공식 출처가 없거나 exact code가 없는 코드는 unverified로 두고 등록 차단
8. ProductCodeRepository를 repository 계층에 추가
```

공식 수집/연결 결과:

```text
AS-Q24ENXE
- LG India split AC product page 확인
- product_code_registry: verified / registration_supported=1
- product_model_id: PM_AC_ASQ24ENXE_001
- official_asset_links: 80
- official_chunk_links: 80

AW-Q24WWXA
- LG India window AC product page 신규 수집
- official_assets 1건 추가
- official_document_chunks 1건 추가
- embedding 1건 생성
- product_code_registry: verified / registration_supported=1
- product_model_id: PM_AC_AWQ24WWXA_001

LGIN-STANDING-AC-CATEGORY-ONLY
- LG India Business floor standing 공식 카테고리 페이지 확인
- exact model code가 공식 페이지에서 확인되지 않음
- product_code_registry: unverified / registration_supported=0
- 등록 차단
```

산출물:

```text
01_정의서/ProductCodeRegistry_제품등록흐름_정의서.md
01_정의서/최종_DB_테이블_전체정리.md
02_데이터연동/mock_data/product_code_registry.json
02_데이터연동/mock_data/product_code_aliases.json
02_데이터연동/mock_data/supported_languages.json
02_데이터연동/source_data/official_lg_india/product_code_registry/raw/
02_데이터연동/source_data/official_lg_india/product_code_registry/product_code_registry_source_manifest_2026-06-05.json
02_데이터연동/db/schema.sql
02_데이터연동/db/migration_20260605_product_code_registry.sql
05_DB/postgres/schema.sql
05_DB/postgres/migrations/003_product_code_registry.sql
```

검증 결과:

```text
SQLite:
official_assets: 792
official_document_chunks: 1,891
official_document_embeddings: 1,891
product_models: 3
product_code_registry: 3
product_code_aliases: 3
supported_languages: 8

PostgreSQL + pgvector:
official_assets: 792
official_document_chunks: 1,891
official_document_embeddings: 1,891
product_code_registry: 3
supported_languages: 8
pgvector HNSW index exists: true
all_query_top1_matches: true

pytest:
18 passed
```

중간 실패와 보정:

```text
1. PostgreSQL reset seed 후 supported_languages가 0건으로 떨어지는 문제 발견
   -> supported_languages.json 생성 및 seed_ar_mock_db.py에 seed_supported_languages 추가
2. PostgreSQL seed script에 한글 경로가 깨진 SQLite DB 경로 문자열이 남아 있었음
   -> 02_ 데이터 폴더를 동적으로 탐색하도록 수정
3. repository 테스트의 수량 기대값이 기존 791/1,890에 고정되어 있었음
   -> 신규 공식 AW-Q24WWXA 수집 수량 792/1,891 기준으로 수정
4. PostgreSQL repository 테스트 DSN이 psycopg2 dialect로 해석되어 실패
   -> 검증 DSN을 postgresql+psycopg:// 로 지정해 실제 PostgreSQL 테스트 통과
```

최신 기준 다음 작업:

```text
17.3 Device Care History 조회 View/API 구현
```

## 29. 17.1-A단계: API 표면 최종 정리 - 수행됨 / 검증 완료

17.1-A단계는 기존 `PREVENTIVE_ALERT`, `ContentViewLog`, `ADMIN_REVIEW` 중심 API 표면을 최종 21개 테이블 구조에 맞게 정리한 단계다. 최종 구조에서는 예방 알림을 별도 테이블에 저장하지 않고, Care Risk Score를 실시간 계산한 뒤 Manual Guide와 AR Guide를 함께 제공한다. Guide 완료 이력은 Manual/AR 수행 방식 구분 없이 `SELF_MANAGEMENT_HISTORY`에 저장한다.

구현 파일:

```text
04_백엔드/app/schemas.py
04_백엔드/app/routers/care.py
04_백엔드/app/routers/guides.py
04_백엔드/app/main.py
04_백엔드/app/services.py
04_백엔드/app/repositories/sqlalchemy_repositories.py
04_백엔드/tests/test_content_option_flow.py
04_백엔드/tests/test_self_management_history_lifecycle.py
```

최종 유지 API:

```text
POST /api/v1/care/risk/evaluate
GET  /api/v1/guides/options
POST /api/v1/guides/{guide_id}/complete
```

최종 제거 API:

```text
GET  /api/v1/care/alerts
GET  /api/v1/care/alerts/{alert_id}/options
POST /api/v1/care/alerts/{alert_id}/select-manual
POST /api/v1/care/alerts/{alert_id}/start-ar
POST /api/v1/contents/{content_id}/view/start
POST /api/v1/contents/{content_id}/view/complete
GET  /api/v1/admin/reviews
POST /api/v1/admin/reviews/{id}/approve
POST /api/v1/admin/reviews/{id}/reject
```

구현 내용:

```text
1. care router 정리
   - /care/risk/evaluate만 유지
   - score가 기준 이상이면 응답에 guide_options를 포함
   - score는 stored: false로 반환하고 별도 PREVENTIVE_ALERT를 만들지 않음

2. guides router 추가
   - GET /api/v1/guides/options 구현
   - product/device/procedure/service_flow_type 기준으로 Manual Guide와 AR Guide를 함께 반환
   - POST /api/v1/guides/{guide_id}/complete 구현
   - 완료 이력은 SELF_MANAGEMENT_HISTORY에 저장

3. old router 제거
   - app/routers/contents.py 삭제
   - app/routers/admin.py 삭제
   - main.py에서 contents/admin router include 제거

4. schema 정리
   - ContentViewStartRequest, ContentViewCompleteRequest, AdminReviewDecisionRequest 제거
   - GuideCompleteRequest 추가
   - 프론트 타입은 GuideOptionSet 기준으로 정리
```

검증 결과:

```text
OpenAPI path count: 14
old path count: 0
guide paths: /api/v1/guides/options, /api/v1/guides/{guide_id}/complete
python -m pytest -q -rs: 25 passed, 1 skipped
PostgreSQL pgvector repository test: 1 passed
```

중간 실패와 보정:

```text
1. content view lifecycle API가 최종 21개 테이블 구조와 충돌
   -> /contents/*/view/* 제거, SELF_MANAGEMENT_HISTORY 완료 이력으로 단순화
2. 예방 알림 저장형 API가 PREVENTIVE_ALERT 테이블 재도입을 유도
   -> /care/alerts/* 제거, /care/risk/evaluate 응답형 guide_options로 변경
3. 관리자 리뷰 API가 현재 self care/self A/S 발표 범위와 불일치
   -> /admin/reviews/* 제거
```

최신 기준 다음 작업:

```text
18. ChatbotEngine 구현
```

## 30. 17.3단계: Device Care History 조회 View/API 구현 - 수행됨 / 검증 완료

17.3단계는 가전 탭의 “관리/A/S 내역”을 프론트가 여러 로그 테이블에서 직접 조합하지 않도록, 백엔드에서 통합 조회 API로 제공하는 단계다. 2026-06-09 기준 구현 및 검증 완료되었다.

구현된 내용:

```text
1. content_view_logs, ar_session_logs, ar_step_logs, care_activity_logs, service_route_logs, expert_as_requests를 통합 조회하는 device_care_history_view 설계
2. DeviceCareHistoryRepository 또는 기존 repository에 get_device_care_history(user_id, device_id) 메서드 추가
3. FastAPI endpoint GET /api/v1/devices/{device_id}/care-history 구현
4. 응답에는 DeviceCareSummary와 CareHistoryItem[]을 함께 반환
5. service_flow_type 기준으로 self_care / self_as / expert_as 필터 지원
6. started_at 또는 completed_at 기준 최신순 정렬 지원
7. 프론트 DeviceTab/CareHistoryPanel은 이 API만 사용하고 원천 로그 테이블 join 로직을 갖지 않음
```

권장 응답 구조:

```text
DeviceCareHistoryResponse
- user_id
- device_id
- summary: DeviceCareSummary
- items: CareHistoryItem[]

CareHistoryItem
- history_id
- service_flow_type
- activity_channel
- procedure_type
- title
- status
- started_at
- completed_at
- source_content_view_id
- source_ar_session_id
- source_route_log_id
- source_expert_as_request_id
```

산출물:

```text
04_백엔드/app/repositories/sqlalchemy_repositories.py: get_device_care_history
04_백엔드/app/services.py: DeviceCareHistoryResponse 조립
04_백엔드/app/routers/devices.py: GET /api/v1/devices/{device_id}/care-history
04_백엔드/app/routers/frontend_compat.py: GET /api/devices, GET /api/devices/{device_id} care_summary/recent_history 응답 확장
04_백엔드/tests/test_device_care_history.py: 17.3 API 검증
04_백엔드/tests/test_frontend_compat_api.py: 프론트 호환 관리 요약 응답 검증
05_프론트엔드/types/careshot.ts: CareHistoryItem, DeviceCareHistoryResponse
05_프론트엔드: CareHistoryPanel 구현 기준 유지
```

완료 기준:

```text
1. self care 공식 콘텐츠 열람 이력 조회 가능 - 검증 완료
2. self care AR 실행 이력 조회 가능 - 검증 완료
   - `ar_step_logs` 집계 반영 포함
3. self A/S 공식 콘텐츠/AR 이력 조회 가능 - service_flow_type 필터 구조 구현
4. expert A/S 연결/접수 이력 조회 가능 - 검증 완료
5. DeviceTab이 care-summary와 care-history API만으로 요약과 내역을 표시 가능 - API 응답 계약 구현
6. 프론트 코드에 ar_session_logs/service_route_logs 직접 조합 로직이 없어야 함 - 프론트 문서/타입 기준 유지
7. 2026-06-16 보강: DeviceDetail 관리 요약 화면용 프론트 호환 API가 `SELF_MANAGEMENT_HISTORY`에서 self care/self A/S 횟수와 최근 3건을 계산해 반환 - 백엔드 검증 완료, 프론트 소스는 사용자 요청에 따라 미수정
```

검증 결과:

```text
python -m pytest tests/test_device_care_history.py -q
결과: 2 passed

2026-06-16 추가 검증:
$env:PYTHONPATH='.'; pytest tests/test_device_care_history.py tests/test_frontend_compat_api.py
결과: 14 passed

$env:PYTHONPATH='.'; pytest
결과: 90 passed, 1 skipped

API smoke:
GET /api/v1/devices/D001/care-history?user_id=U001&limit=3
GET /api/devices
GET /api/devices/D001
결과: self_care_count=5, self_as_count=2, recent_history 3건 반환

python -m pytest tests/test_content_option_flow.py -q
결과: 2 passed

python -m pytest tests/test_content_option_flow.py tests/test_care_risk_engine.py tests/test_environment_data_adapter.py tests/test_repositories_sqlalchemy.py -q
결과: 19 passed

$env:CARESHOT_POSTGRES_TEST_DSN='postgresql+psycopg://careshot:careshot@127.0.0.1:55432/careshot_ar'
python -m pytest tests/test_postgres_repository_pgvector.py -q
결과: 1 passed
```

17.3 완료 후 다음 작업:

```text
18. ChatbotEngine 구현
```

### 24.1 14단계 추가 보정 및 최종 재검증

14단계 완료 감사 중 legacy AR demo server와 과거 검증 스크립트가 기존 `ar_db_repository` import를 유지하고 있던 부분을 추가 보정했다.

추가 보정:

```text
1. 04_AR가이드/backend/server.py -> app.repositories.CareShotRepository 사용
2. 03_AI로직/rules/ai_decision_engine.py -> app.repositories.CareShotRepository 사용
3. RAG 검증 스크립트 2개 -> app.repositories.CareShotRepository 사용
4. BaseRepository의 SQL parameter binding을 SQLAlchemy named parameter 방식으로 변경
```

최종 재검증:

```text
.py 파일 기준 기존 ar_db_repository CareShotRepository import: 없음
repository pytest: 8 passed
FastAPI RAG 40 query: 40 passed / 0 failed
GET /api/v1/health: 200
POST /api/v1/rag/search: metadata_strict_vector_similarity
POST /api/v1/ai/analyze: low / prepare_ar_guide_session
GET http://127.0.0.1:8787/: 200
```

## 25. 15단계: PostgreSQL + pgvector 최종 DB 전환 - 수행됨 / 검증 완료

15단계는 schema 파일 작성만으로 완료 처리하지 않고, 실제 PostgreSQL + pgvector 컨테이너에서 seed, top-k 검색, SQLite 비교, FastAPI PostgreSQL 모드까지 검증했다.

수행 내용:

```text
1. 로컬 PostgreSQL 16 실행 확인
2. 로컬 PostgreSQL에는 pgvector extension이 없음을 확인
3. Docker Desktop 실행
4. pgvector/pgvector:pg16 컨테이너 실행
5. PostgreSQL + pgvector schema.sql 작성
6. migration 001_init_pgvector.sql 작성
7. SQLite -> PostgreSQL seed script 작성
8. official_document_embeddings.embedding_vector vector(512) 적재
9. HNSW index 생성
10. 예방 알림형 테이블 포함 확인
11. AR 확장 테이블 포함 확인
12. wall_mounted_ac / standing_ac / window_ac canonical structure type 추가
13. pgvector top-k 검색 검증
14. SQLite 주요 query count와 PostgreSQL count 비교
15. FastAPI PostgreSQL mode 검증
```

산출물:

```text
05_DB/postgres/schema.sql
05_DB/postgres/migrations/001_init_pgvector.sql
05_DB/postgres/docker/docker-compose.yml
05_DB/postgres/scripts/generate_postgres_schema.py
05_DB/postgres/scripts/seed_postgres_from_sqlite.py
05_DB/postgres/scripts/verify_pgvector_topk.py
05_DB/postgres/reports/pgvector_검증리포트_2026-06-04.md
05_DB/postgres/reports/pgvector_검증결과_2026-06-04.json
05_DB/postgres/PostgreSQL_pgvector_전환_정리.md
```

검증 결과:

```text
pgvector version: 0.8.2
HNSW index exists: true
official_assets: 791
official_document_chunks: 1,890
official_document_embeddings: 1,890
vector_dims min/max: 512 / 512
canonical_aircon_structure_types: 3
all_query_top1_matches: true
repository tests: 9 passed
FastAPI PostgreSQL mode health: 200
FastAPI PostgreSQL mode RAG: metadata_strict_vector_similarity
FastAPI PostgreSQL mode AI analyze: low / prepare_ar_guide_session
```

중간 실패와 보정:

```text
1. 로컬 PostgreSQL에는 pgvector가 없었음 -> Docker pgvector 컨테이너로 보정
2. 검증 케이스 procedure_type이 실제 DB와 불일치했음 -> odor_mold_care로 보정
3. PostgreSQL JSONB 반환 처리 미흡 -> row_to_dict 보정
4. embedding stats 조회가 SQLite 전용이었음 -> PostgreSQL information_schema 분기 추가
```

당시 다음 작업:

```text
16. EnvironmentDataAdapter 구현
```

## 30. AR 개발방향 상세 정의서 찐최종 정리 - 수행됨 / 문서 검증 완료

배경:

```text
첨부된 화면 설계서, DB 요구사항 분석서, 기능 및 비기능 명세서 구조를 벗어나지 않고
AI 제품군 분류 + Web Image Tracking AR 개발 방향을 다시 정리해야 했다.
기존 자유형 AR 개발방향 문서에는 AI 분류, MindAR, AR session/step log, part_map 등
확장 표현이 섞여 있어 최종 21테이블 기준과 분리해 재정의가 필요했다.
```

수행 내용:

```text
1. 첨부 DOCX 3종의 목차와 표 컬럼 확인
2. 붙여넣은 AR 개발 방향 메모 확인
3. 기존 AI_제품군분류_WebAR_MVP_개발방향_2026-06-12.md 확인
4. 현재 careshot_ar_mock.db 테이블 21개 확인
5. 최종 기준에서 AR session log, AR step log, AI 분류 결과 저장, part map 별도 테이블을 제외
6. 첨부 문서 구조에 맞춰 기능/비기능 명세서, DB 요구사항 분석서, 화면설계서 3개 구조로 새 정의서 작성
```

생성 파일:

```text
01_정의서/AR_개발방향_상세정의서_찐최종_2026-06-12.md
```

최종 결정:

```text
AI 제품군 분류는 wall_split_ac / floor_standing_ac / window_ac / not_ac 분류 보조만 수행한다.
AR 허용 여부는 DecisionEngineV2, Safety Rule, 공식자료 match, GUIDE/AR_GUIDE/AR_TARGET 존재 여부가 결정한다.
AI 분류 결과와 confidence는 DB에 저장하지 않는다.
AR 단계 분리 결과, MindAR lock 상태, 단계별 이동 로그, AR session/step log도 저장하지 않는다.
완료 이력은 기존 SELF_MANAGEMENT_HISTORY에만 저장한다.
AR 오버레이 기준은 최종 21테이블 기준 AR_TARGET.reference_image_path, AR_TARGET.mind_target_path, AR_GUIDE.overlay_config_json을 사용한다.
```

검증:

```text
첨부 DOCX 구조 추출:
- 기능/비기능 명세서: 기능 요구사항 표(ID/요구사항 명칭/설명/우선 순위), 비기능 요구사항 표(ID/요구사항 명칭/설명/적용 시점)
- DB 요구사항 분석서: 요구사항 분석 개요, 객체 정의서, E-R 관계 정의서, 요구사항-테이블 매핑표, 구현 여부, 저장/비저장 구분, 확인 필요 사항
- 화면설계서: 화면설계서 개요, 메뉴 구조, 서비스 흐름도 목록, 화면 정의, 변경이력

현재 SQLite DB 확인:
- table_count: 21
- AR 관련 현재 테이블: AR_TARGET, AR_GUIDE, GUIDE, SELF_MANAGEMENT_HISTORY
- 미존재 저장 테이블: ar_session_logs, ar_step_logs, part_maps, AI 제품군 분류 결과 테이블
```

남은 작업:

```text
이 정의서를 기준으로 기존 자유형 AR 개발방향 문서의 session/step log 저장 표현,
part_map 별도 객체 표현, AI 분류 결과 저장 표현을 후속 정리할 수 있다.
프론트 구현 단계에서는 wall_split_ac 1차 시연 기준으로 ProductClassifierService,
MindAR target, AR_GUIDE.overlay_config_json 렌더링을 연결해야 한다.
```

추가 보정:

```text
최초 작성본이 첨부 문서 구조 준수에 치우쳐 실제 AR 개발 방향보다 분석서/정의서 구조 나열처럼 보이는 문제가 있었다.
사용자 피드백에 따라 같은 첨부 구조는 유지하되, 본문을 실제 개발 중심으로 재작성했다.

재작성 후 문서는 다음 개발 항목을 직접 정의한다.
- 1차 MVP 범위: wall_split_ac 필터 청소 AR Guide
- 런타임 흐름: 카메라 권한 -> AI 제품군 분류 -> 지원 대상 확인 -> MindAR target tracking -> overlay 표시 -> 완료 확인
- 프론트 상태: 카메라 권한 대기, AI 분류 중, wall_split_ac 감지, window_ac/not_ac 차단, target locked/lost, 단계 진행, 완료 확인
- DB 사용: PRODUCT, USER_PRODUCT, GUIDE, AR_TARGET, AR_GUIDE, AI_INQUIRY_ANALYSIS, RAG_SEARCH_LOG, SELF_MANAGEMENT_HISTORY
- 신규 테이블 미생성: AI 분류 결과, AR session log, AR step log, Part Map 전용 테이블
```

### 30.1 MindAR 폐기 후 YOLO 실시간 필터 탐지 데이터셋 1차 착수 - 진행 중

배경:

```text
MindAR image target 방식은 기준 이미지를 화면에 맞춰 띄우는 느낌이 강해,
실제 카메라 화면 안에서 에어컨 내부 필터를 직접 찾는 방식으로 전환한다.
새 방향은 YOLO 기반 실시간 filter bbox 탐지 + canvas overlay Web AR POC이다.
```

수행 내용:

```text
1. 1번 작업을 필터 탐지용 데이터셋 100~200장 구성으로 확정
2. 학습 class를 `filter` 1개로 제한
3. 공개 웹 이미지 무단 수집 대신 직접 촬영/사용 허가/공개 라이선스 후보 중심으로 수집 기준 정의
4. 로컬 reference 이미지 4개는 학습 주력 데이터가 아니라 라벨링 기준/시연 seed로 분리
5. Roboflow 라벨링 전 manifest 기록 기준 생성
```

생성 파일:

```text
02_데이터연동/filter_detection_dataset/README.md
02_데이터연동/filter_detection_dataset/candidate_sources.md
02_데이터연동/filter_detection_dataset/dataset_inventory.md
02_데이터연동/filter_detection_dataset/manifest_template.csv
02_데이터연동/filter_detection_dataset/dataset_manifest.csv
02_데이터연동/filter_detection_dataset/official_manual_page_candidates_manifest.csv
02_데이터연동/filter_detection_dataset/open_license_download_failures.log
02_데이터연동/filter_detection_dataset/raw/local_reference_seed/*
02_데이터연동/filter_detection_dataset/raw/official_manual_page_candidates/*
```

결정:

```text
1차 POC는 데이터셋 구성부터 진행한다.
공개 데이터만으로 에어컨 내부 필터 bbox 100~200장을 안정 구성하기 어렵기 때문에,
직접 촬영/허가 이미지 60~100장 + 공개 라이선스 후보 30~60장 + negative sample 20~40장으로 시작한다.
유튜브/블로그/stock preview 이미지는 사용 허가 또는 명시 라이선스가 없으면 학습 데이터에 넣지 않는다.
```

남은 작업:

```text
1. 실제 이미지 파일을 raw/ 하위 폴더에 추가 수집
2. manifest에 이미지별 출처/라이선스/사용 가능 여부 기록
3. Roboflow Object Detection 프로젝트 생성 및 filter bbox 라벨링
4. YOLO export 후 Colab 학습
5. best.pt 생성 후 FastAPI inference 서버 연결
```

현재 확보:

```text
local_reference_seed 4장 복사 완료
LG 공식 에어컨 매뉴얼 PDF의 필터/청소 관련 페이지 19장 렌더링 완료
dataset_manifest.csv 기준 후보 23장 확보
Wikimedia Commons 자동 다운로드는 429 robot policy로 실패
추가 필요: 최소 77장, 권장 177장까지
```

2026-06-15 추가 수집:

```text
사용자 피드백에 따라 1번 데이터셋 수집이 끝나기 전에는 Roboflow/학습 단계로 넘어가지 않는 기준으로 재고정했다.

LG 공식 지원 페이지 23개를 대상으로 필터/청소 관련 이미지 URL을 수집했다.
- gscs.lge.com 공식 지원 이미지 candidate URL: 113개
- 다운로드 성공 unique 이미지: 100장
- 중복 SHA 제외: 13장
- 다운로드 실패/스킵: 0장

raw/direct_or_approved/ 하위 생성:
- lg_official_support_crawled: 100장
- lg_official_filter_visible_candidates: 74장
- lg_official_filter_training_seed_accepted: 71장

생성 manifest:
- lg_official_support_crawled_manifest.csv
- lg_official_filter_visible_candidates_manifest.csv
- lg_official_filter_training_seed_accepted_manifest.csv

시각 검토:
- contact sheet 생성 후 필터/필터케이스/필터 분리 장면 중심으로 확인
- 043, 046, 047은 표시창/버튼 UI 위주라 bbox 라벨링 대상에서 제외

현재 1차 라벨링 seed:
- 공식 LG 지원 페이지 기반 accepted 후보 71장
- 기존 local/reference/manual 후보 포함 전체 manifest 기준 123장

주의:
- 폴더는 기존 계획명 raw/direct_or_approved/를 사용했지만,
  라이선스 상태는 `official_public_support_candidate_not_explicit_training_license`로 기록했다.
- 즉, 공식 공개 지원 콘텐츠 후보이며 학습/배포 사용권은 별도 확인 필요하다.
- 실제 앱 품질 기준으로는 직접 촬영 또는 명시 허가 사진 30장 이상을 추가해
  최종 100~200장 균형 데이터셋으로 보강해야 한다.
```

2026-06-15 추가 수집 라운드2/3 및 최종 선별:

```text
100~200장 목표에 아직 부족하므로 추가 수집을 계속했다.

추가 수집:
- LG 공식 지원 이미지 round2 신규 unique: 27장
- LG 공식/웹 제품 상세 및 가이드 round3 partial: 94장
- iFixit LG/Goldstar 에어컨 필터 실사진 신규 unique: 36장

최종 합산:
- filter_bbox_seed_100plus: 128장
- contact sheet 시각 검토 후 제외: 13장
- 최종 Roboflow bbox 라벨링 seed: 115장

최종 위치:
- raw/training_candidates/filter_bbox_seed_final_reviewed_115/
- filter_bbox_seed_final_reviewed_115_manifest.csv
- filter_bbox_seed_final_reviewed_115_contact_sheet.jpg

상태 판단:
- 1번 데이터셋 구성은 최소 수량 기준 100장을 넘긴 상태다.
- 아직 Roboflow 라벨링은 시작하지 않았다.
- 다음 단계는 이 115장을 Roboflow에 업로드하고 `filter` bbox 라벨링을 수행하는 것이다.

주의:
- LG 공식 공개 지원 콘텐츠와 iFixit 공개 가이드 후보가 섞여 있으므로,
  산출물/배포 전에는 manifest의 license_status 기준으로 사용 가능성을 확인한다.
- 모델 품질 보강을 위해 직접 촬영/명시 허가 실사진 30장 이상과 negative sample 20~40장을 추가하는 것이 좋다.
```

2026-06-15 Roboflow 라벨링 준비:

```text
2번 Roboflow bbox 라벨링 단계로 넘어가기 위한 업로드 패키지를 생성했다.
실제 Roboflow 웹 라벨링은 아직 완료하지 않았다.

생성 위치:
- 02_데이터연동/filter_detection_dataset/roboflow_upload/filter_bbox_seed_final_reviewed_115/

패키지:
- images/ : 115장
- filter_bbox_seed_final_reviewed_115_images.zip : zip entries 115
- roboflow_upload_manifest.csv : 115행
- roboflow_labeling_checklist.csv : 115행
- roboflow_labeling_guide.md : filter bbox 라벨링 기준
- roboflow_upload_status.md : 업로드 상태 및 차단 조건
- upload_to_roboflow.py : API 키가 있을 때 사용할 업로드 스크립트 템플릿

Roboflow 프로젝트 기준:
- Project Type: Object Detection
- Project Name: careshot-lg-ac-filter-detection
- Class: filter
- Export Target: YOLOv8

현재 차단:
- ROBOFLOW_API_KEY 미설정
- ROBOFLOW_WORKSPACE 미설정
- ROBOFLOW_PROJECT 미설정
- roboflow Python SDK 미설치

따라서 자동 API 업로드는 실행하지 않았다.
다음 단계는 Roboflow 계정/프로젝트 접근 후 zip 업로드 및 filter bbox 수동 라벨링이다.
라벨링 완료 증거가 없으면 YOLO 학습으로 넘어가지 않는다.
```

2026-06-15 Roboflow export 검증/Colab 학습 준비:

```text
Roboflow 라벨링이 완료된 뒤 YOLO 학습으로 넘어가기 위한 검증/학습 준비 파일을 생성했다.
실제 학습은 아직 실행하지 않았다.

생성 파일:
- roboflow_export/verify_roboflow_yolov8_export.py
- training_runs/train_yolo_filter_colab.py
- training_runs/colab_training_README.md

검증 스크립트 역할:
- data.yaml 존재 확인
- class names가 ['filter']인지 확인
- train/valid/test images/labels 존재 확인
- label txt가 YOLO 형식 5컬럼인지 확인
- class id가 0만 존재하는지 확인
- bbox 좌표가 0..1 정규화 범위인지 확인
- total_images, total_boxes가 0보다 큰지 확인

학습 게이트:
- Roboflow bbox labeling 완료 전 학습 금지
- YOLOv8 export 미확보 상태에서 학습 금지
- verify_roboflow_yolov8_export.py errors=[] 통과 전 학습 금지

현재 상태:
- roboflow_upload package 준비 완료
- roboflow_export 실제 dataset export 미확보
- best.pt 미생성
```

2026-06-15 벽걸이형 시연 기준 데이터셋 재정의:

```text
사용자 피드백에 따라 발표/시연 대상을 LG 벽걸이형 에어컨으로 고정했다.
따라서 기존 115장 broad seed는 창문형/도식/공식 안내 이미지가 섞여 있으므로 core training seed가 아니라 reference 후보로 내린다.

새로 생성한 벽걸이 전용 후보:
- raw/training_candidates/lg_wall_mounted_filter_real_photo_candidates/: 208장
- raw/training_candidates/lg_wall_mounted_filter_video_frame_candidates/: 105장
- raw/training_candidates/lg_wall_mounted_filter_real_photo_reviewed_086/: 86장

Roboflow 우선 업로드 패키지:
- roboflow_upload/lg_wall_mounted_filter_real_photo_reviewed_086/images/: 86장
- roboflow_upload/lg_wall_mounted_filter_real_photo_reviewed_086/lg_wall_mounted_filter_real_photo_reviewed_086_images.zip: zip entries 86
- roboflow_upload/lg_wall_mounted_filter_real_photo_reviewed_086/roboflow_upload_manifest.csv
- roboflow_upload/lg_wall_mounted_filter_real_photo_reviewed_086/roboflow_labeling_checklist.csv
- roboflow_upload/lg_wall_mounted_filter_real_photo_reviewed_086/upload_to_roboflow.py

라벨링 게이트:
- `filter` bbox는 실제 필터 mesh/필터 부품이 보이는 장면만 지정한다.
- 필터 접근부/슬롯만 보이고 필터 mesh가 애매한 프레임은 Roboflow에서 skip 또는 negative 후보로 분리한다.
- 블로그/영상 프레임은 `unknown_verify_before_training`이므로 최종 발표/배포 전 직접 촬영/허가 이미지로 교체 또는 보강한다.
- DB 구조 변경 없음. front/backend 수정 없음.
```

2026-06-15 사용자 제공 이미지/기존 학습 노트북 반영:

```text
사용자가 LG 벽걸이 에어컨 필터 이미지 zip 2개와 DX_AR_TEST zip을 추가 제공했다.

이미지 반영:
- 원본 추출: raw/direct_or_approved/user_provided_wall_filter_20260615/: 100장
- 중복 제거 normalized: raw/direct_or_approved/user_provided_wall_filter_20260615_normalized/: 99장
- Roboflow 1차 학습 권장 패키지: roboflow_upload/lg_wall_mounted_filter_user_primary_099/: 99장
- 보강 후보 패키지: roboflow_upload/lg_wall_mounted_filter_user_plus_reviewed_185/: 185장

학습 파일 판단:
- DX_AR_TEST의 aircon_filter_test / aircon_test / aircon_top_bottom_test는 실제 best.pt가 아니라 Jupyter Notebook 파일이다.
- notebooks_with_extension/ 아래에 .ipynb 사본을 생성했다.
- aircon_filter_test.ipynb는 filter 1클래스 학습 기록으로 참고한다.
- 실제 best.pt 가중치는 포함되지 않았으므로 백엔드 모델 경로 배치는 아직 하지 않는다.

최신 게이트:
- 1차 재라벨링/재학습은 사용자 제공 primary 99장을 우선한다.
- 기존 웹/영상 후보는 2차 recall 보강용으로만 사용한다.
- Roboflow bbox 라벨링 완료 및 YOLOv8 export 검증 전에는 학습 완료/best.pt 확보로 보지 않는다.
```

2026-06-15 사용자 제공 primary 99장 사전 라벨 패키지:

```text
Roboflow 검수 시간을 줄이기 위해 사용자 제공 primary 99장에 대해 YOLOv8 형식 사전 라벨 패키지를 생성했다.

생성 위치:
- 02_데이터연동/filter_detection_dataset/roboflow_upload/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8/

구성:
- images/: 99장
- labels/: 99개
- data.yaml
- prelabel_manifest.csv
- prelabel_overlay_contact_sheet.jpg
- lg_wall_mounted_filter_user_primary_099_prelabel_yolov8.zip

판단:
- 사전 라벨 bbox는 정답이 아니라 Roboflow 검수 시작점이다.
- contact sheet 기준 일부 bbox는 필터 mesh보다 넓게 AC 전면부를 포함한다.
- Roboflow에서 99장 전체를 직접 수정/삭제/확정하기 전에는 2번 라벨링 완료로 보지 않는다.
- 유효한 ROBOFLOW_API_KEY가 현재 shell에 없어 API 업로드는 실행하지 않았다.
- DB 구조 변경 없음. 프론트/백엔드 수정 없음.
```

2026-06-15 Roboflow pre-label 업로드 helper 및 로컬 YOLOv8 포맷 검증:

```text
추가 생성:
- 02_데이터연동/filter_detection_dataset/roboflow_upload/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8/upload_prelabels_to_roboflow.py
- 02_데이터연동/filter_detection_dataset/create_local_prelabel_yolov8_export.py
- 02_데이터연동/filter_detection_dataset/roboflow_export/local_prelabel_yolov8_review_only/
- 02_데이터연동/filter_detection_dataset/roboflow_export/local_prelabel_yolov8_review_only_summary.json

검증:
- upload_prelabels_to_roboflow.py --dry-run: image_label_pairs=99, no upload attempted
- local_prelabel_yolov8_review_only: train 88, valid 7, test 4
- verify_roboflow_yolov8_export.py: total_images=99, total_labels=99, total_boxes=99, errors=[]

상태:
- YOLOv8 파일 형식은 검증 완료
- bbox 정답성은 Roboflow 수동 검수 전이므로 라벨링 완료 아님
- best.pt 미생성
- DB 구조 변경 없음. 프론트/백엔드 수정 없음.
```

2026-06-15 refined v2 사전 라벨 및 COCO fallback 보강:

```text
문제:
- v1 사전 bbox가 필터 mesh보다 넓게 잡혀 열린 에어컨 전면부 전체를 학습할 위험이 확인됐다.

추가 생성:
- 02_데이터연동/filter_detection_dataset/refine_filter_bbox_prelabels.py
- 02_데이터연동/filter_detection_dataset/create_coco_prelabel_package.py
- 02_데이터연동/filter_detection_dataset/roboflow_upload/upload_prelabels_to_roboflow.py
- 02_데이터연동/filter_detection_dataset/roboflow_upload/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2/
- 02_데이터연동/filter_detection_dataset/roboflow_upload/lg_wall_mounted_filter_user_primary_099_prelabel_refined_v2_coco/
- 02_데이터연동/filter_detection_dataset/roboflow_export/local_prelabel_yolov8_refined_v2_review_only/
- 02_데이터연동/filter_detection_dataset/roboflow_export/local_prelabel_yolov8_refined_v2_review_only_summary.json

검증:
- refined_v2 images=99, labels=99, zip_entries=201
- refined_v2 tightened=97
- high_priority_review: v1 92 -> refined_v2 45
- refined_v2 COCO fallback: images=99, annotations=99, zip_entries=100
- refined_v2 local YOLOv8 export: train 88, valid 7, test 4, errors=[]
- Roboflow UI 접근: Chrome에서 app.roboflow.com/login으로 리다이렉트되어 UI 업로드 불가
- DB 구조 변경 없음. 프론트/백엔드 수정 없음.

상태:
- Roboflow 업로드 우선 후보는 refined_v2 YOLO zip
- YOLO txt import 실패 시 refined_v2 COCO zip 사용
- 수동 검수 전 학습 금지 및 best.pt 미생성 상태 유지
```

### 30.2 YOLO 필터 탐지 FastAPI/웹캠 overlay 연결 뼈대 - 진행 중

배경:

```text
필터 탐지용 best.pt가 아직 생성되지 않았지만,
best.pt 생성 이후 바로 연결할 수 있도록 FastAPI inference endpoint와
프론트 웹캠 프레임 전송/canvas bbox overlay/smoothing 구조를 먼저 준비했다.

사용자 추가 지시에 따라 DB 구조는 변경하지 않고,
프론트/백엔드 영역은 백업 후 후속 작업 기준으로 관리한다.
```

백업:

```text
99_백업/2026-06-15_17-05-42_yolo_filter_front_backend_backup/
```

수정 파일:

```text
04_백엔드/app/schemas.py
04_백엔드/app/routers/ar.py
04_백엔드/app/yolo_filter_service.py
04_백엔드/tests/test_ar_filter_detection.py
05_프론트엔드/react-vite/src/app/pages/ARGuide.tsx
```

구현 내용:

```text
1. POST /api/v1/ar/filter-detect 추가
2. CARESHOT_FILTER_YOLO_MODEL_PATH 또는 기본 경로의 best.pt가 있으면 Ultralytics YOLO 추론 사용
3. best.pt가 없으면 mock_fallback=true 기준 중앙 filter bbox 반환
4. ARGuide 화면에서 웹캠 video, capture canvas, overlay canvas 구성
5. 700ms 간격으로 카메라 프레임을 JPEG data URL로 전송
6. 응답 bbox를 canvas에 표시
7. 이전 bbox와 현재 bbox를 EMA 방식으로 smoothing
8. 기존 단계 이동/완료 확인 흐름은 유지
```

검증:

```text
python -m pytest -q tests/test_ar_filter_detection.py
-> 1 passed

npm run build
-> built successfully

HTTP smoke:
POST http://127.0.0.1:8791/api/v1/ar/filter-detect
-> mode=mock, detections[0].class_name=filter, image_width=640, image_height=480

브라우저 확인:
http://127.0.0.1:5173/ar-guide
-> video element 1개, canvas 2개, AR 단계 텍스트 렌더링, console error 0건
```

DB 기준:

```text
DB 구조 변경 없음.
SQLite careshot_ar_mock.db table_count=21 유지.
신규 테이블/ALTER/DROP/CREATE 없음.

주의:
처음 백엔드를 일반 기동했을 때 기존 environment auto-refresh loop가 동작해 DB 파일 LastWriteTime이 갱신되었다.
스키마는 변하지 않았다.
DB 구조 변경 금지 조건은 table_count와 sqlite schema 기준으로 검증한다.
환경 자동갱신 루프는 기존 런타임 기능이므로 임의로 비활성화하지 않는다.
```

남은 작업:

```text
1. 실제 filter 사진 100~200장 확보
2. Roboflow filter bbox 라벨링
3. YOLO 학습 후 03_AI로직/models/filter_detection/best.pt 배치
4. mock_fallback 대신 실제 YOLO mode로 탐지 검증
5. guide step별 target label/안전문구를 detection 상태와 더 정교하게 연결
```

2026-06-15 ARGuide object-cover bbox 좌표 보정:

```text
문제:
- ARGuide의 video는 object-cover로 표시되므로 화면 비율에 따라 실제 영상이 좌우/상하 크롭될 수 있다.
- 기존 overlay 좌표는 단순 scaleX/scaleY만 적용해, 크롭이 있는 화면에서 bbox가 실제 영상 위치와 어긋날 수 있었다.

수정:
- 05_프론트엔드/react-vite/src/app/pages/ARGuide.tsx 백업 후 수정
- CAPTURE_WIDTH=416 기준 capture 크기를 getCaptureSize(video)로 통일
- getObjectCoverTransform(container, source) 추가
- object-cover 렌더 크기, offsetX/offsetY, scaleX/scaleY를 반영해 overlay bbox 좌표 변환
- 화면 밖으로 나간 bbox는 visible 영역으로 clip

백업:
- 99_백업/2026-06-15_19-24-29_ar_overlay_object_cover_mapping_backup/ARGuide.tsx

검증:
- python -m pytest -q tests/test_ar_filter_detection.py -> 1 passed
- npm run build -> success, 기존 500kB chunk warning 유지
- HTTP POST /api/v1/ar/filter-detect -> 200, mode=mock, class_name=filter
- Browser http://127.0.0.1:5173/ar-guide -> video 1개, canvas 2개, console error 0건
- DB table_count=21 유지

제한:
- 브라우저 카메라 권한은 허용하지 않아 실제 카메라 프레임 bbox 움직임은 사용자가 브라우저에서 권한 허용 후 확인해야 한다.
- best.pt 미생성 상태이므로 실제 YOLO bbox가 아니라 mock fallback으로 검증했다.
```

2026-06-15 Roboflow export 이후 학습/배치 자동화 보강:

```text
목적:
- Roboflow에서 99장 bbox 수동 검수 완료 후 YOLOv8 export를 받으면,
  검증 -> 학습 -> best.pt 배치 -> metadata 기록까지 한 번에 이어지도록 한다.

추가/수정:
- 02_데이터연동/filter_detection_dataset/training_runs/train_and_stage_filter_detector.py 추가
- 02_데이터연동/filter_detection_dataset/training_runs/train_yolo_filter_colab.py 기본값 보정
  - epochs: 80 -> 50
  - name: yolov8n_filter_poc -> yolov8n_filter_wall_primary_099
- 03_AI로직/models/filter_detection/README.md 추가
- 02_데이터연동/filter_detection_dataset/training_runs/colab_training_README.md 갱신

자동화 동작:
- verify_roboflow_yolov8_export.py 기준 export 검증
- review_only export는 기본 차단
- --allow-review-only-training은 non-final smoke 용도로만 허용
- YOLO 학습 후 weights/best.pt 존재 확인
- 기존 배치 모델이 있으면 백업
- FastAPI 기본 경로인 03_AI로직/models/filter_detection/best.pt로 복사
- best_pt_deployment_metadata.json 기록

검증:
- python -m py_compile train_yolo_filter_colab.py train_and_stage_filter_detector.py -> ok
- review_only export dry-run without allow flag -> 차단 성공
- review_only export dry-run with allow flag -> verify_errors=[], deploy_path가 06_AR 가전케어 AI/03_AI로직/models/filter_detection/best.pt로 계산됨
- DB table_count=21 유지
- best.pt는 아직 없음

상태:
- 실제 final 학습은 Roboflow 수동 검수 완료 export 전까지 금지
```


### 26.5 power_troubleshooting 동적 매뉴얼 + 제한 AR 보강 - 완료

배경:

```text
RAG chunk 기반 동적 매뉴얼 가이드 방향을 채택한다면,
DB GUIDE에 특정 procedure_type 매뉴얼 row가 없더라도 안전하게 생성 가능한 self-AS 절차는
RAG/official_youtube 근거를 붙여 동적 매뉴얼 후보를 내려야 한다.

전원 꺼짐/No Power는 filter_cleaning fallback은 금지해야 하지만,
리모컨/전원표시등/안전하게 접근 가능한 플러그/차단기 1회 확인 같은 외부 안전 점검은 제공 가능하다.
따라서 AR도 내부 수리 AR이 아니라 external_safe_check_only 제한 AR로 생성한다.
```

결정:

```text
procedure_type: power_troubleshooting
service_flow_type: self_as
risk_level: medium
decision_action: prepare_limited_ar_safe_check
ar_guide_allowed: True
ar_scope: external_safe_check_only
```

구현:

```text
1. ai_decision_engine.py
   - power_troubleshooting을 manual-only 차단에서 limited AR 허용으로 변경

2. services.py
   - DB manual guide가 0건이면 power_troubleshooting 동적 매뉴얼 생성
   - official_youtube/RAG evidence를 동적 매뉴얼 evidence로 연결
   - DB AR_GUIDE 후보가 0건이면 동적 제한 AR option 생성

3. aircon_power_troubleshooting_safe_check_v1.json
   - No Power / power off 전용 AR 템플릿 추가
   - 내부 전기 수리/분해/냉매/컴프레서 조치 금지

4. careshot.ts
   - dynamic manual/AR 응답 필드 타입 추가
```

검증:

```text
POST /api/v1/chat/messages
message: The AC power suddenly turns off.

manual_count: 1
ar_count: 1
youtube_count: 2
selected_template_id: aircon_power_troubleshooting_safe_check_v1
overlay_warning: None

python -m pytest tests -q
-> 33 passed, 1 skipped
```


### 27. AR 안내 단계-탐지 상태 연결 - 부분 완료

배경:

```text
YOLO 필터 탐지 결과가 프론트 오버레이에 표시되는 것만으로는 실제 사용자 안내 흐름과 연결성이 부족하다.
단계별 안내 문구, 안전 확인 문구, 현재 탐지 상태를 한 화면에서 같이 보여줘야
벽걸이 LG 에어컨 필터 청소 AR 시연 흐름이 "bbox 표시"가 아니라 "작업 안내"로 보인다.
```

구현:

```text
1. ARGuide.tsx
   - ARGuideStep에 optional safety, targetHint 필드 추가
   - 기본 5단계에 단계별 안전문구와 확인 위치 추가
   - detectionMode/lastDetection/cameraState 기반 안내 문구 생성
   - 상단 오버레이 상태 문구를 mock/yolo/권한/대기 상태별 사용자 안내로 변경
   - 하단 STEP 패널에 확인 위치와 안전 확인 문구 표시

2. 백업
   - 프론트 수정 전 ARGuide.tsx 백업 생성
   - 개발순서/개발로그 수정 전 문서 백업 생성
```

검증:

```text
npm run build
-> Vite build 성공
-> 기존과 동일하게 index JS chunk 500 kB 초과 경고만 존재

python -m pytest -q tests/test_ar_filter_detection.py
-> 1 passed

POST http://127.0.0.1:8791/api/v1/ar/filter-detect
-> 200 OK
-> mode=mock, class_name=filter
-> best.pt 미배치 상태라 mock fallback 동작 확인

Browser http://127.0.0.1:5173/ar-guide
-> video=1, canvas=2
-> 확인 위치/안전문구/탐지 안내 렌더링 확인
-> console error 0

DB 확인
-> 02_데이터연동/db/careshot_ar_mock.db table_count=21
```

실패/수정:

```text
- DB table_count 1차 확인에서 Python stdin 경로 인코딩 문제로 sqlite open 실패
  -> PowerShell Resolve-Path 결과를 Python argv로 전달하는 방식으로 재검증 성공
- 개발순서 문서 1차 업데이트가 기존 섹션 중간에 들어가 위치를 조정했다.
  -> 중간 블록 제거 후 파일 마지막 26.5 뒤에 다시 배치했다.
```

남은 제한/다음 작업:

```text
- best.pt가 아직 배치되지 않아 실제 YOLO 탐지는 미완료이며, 현재 런타임은 mock fallback이다.
- Roboflow 수동 검수 완료 export 또는 검수된 YOLO 데이터셋이 확정되면 train_and_stage_filter_detector.py로 best.pt를 배치해야 한다.
- 카메라 권한은 브라우저 검증 중 임의 허용하지 않았으므로 실제 카메라 bbox 정합성은 사용자 허용 후 재검증해야 한다.
```


### 27.1 필터 탐지 데이터셋 1번 상태 재판정 - 부분 완료

배경:

```text
전체 목표의 1번은 "필터 탐지용 데이터셋 100~200장 구성"이다.
사용자가 추가로 제공한 LG 벽걸이 에어컨 필터 zip과 기존 수집본을 바탕으로,
외부 크롤링을 더 해야 하는지 먼저 현재 파일 기준으로 판정했다.
```

판정:

```text
- 1번은 수량/품질 관점에서 거의 충족 상태다.
- 최우선 1차 seed는 user primary 99장이다.
- 100장 조건에는 1장 모자라지만, 중복 제거 후 99장이므로 중복을 되살려 억지로 100장으로 만들지 않는다.
- user plus reviewed 185장은 수량은 충족하지만 unknown license 56장과 small_lt256 10장이 있어 최종 학습 전 추가 검수가 필요하다.
- 외부 크롤링은 가능하지만, 최종 학습셋에는 직접 촬영/허가/라이선스 확인 이미지 위주로만 넣는 것이 맞다.
```

검증:

```text
user primary package:
-> images=99
-> unique_sha256=99
-> duplicate_groups=0
-> unreadable=0
-> small_lt256=0
-> appliance_form=wall_mounted 99
-> target_class=filter 99
-> source_type=user_provided_wall_mounted_filter_image 99

user plus reviewed package:
-> images=185
-> unique_sha256=185
-> duplicate_groups=0
-> unreadable=0
-> small_lt256=10
-> appliance_form=wall_mounted 185
-> target_class=filter 185

첨부 zip:
-> LG 벽걸이 에어컨 필터 사진.zip images=70
-> LG 벽걸이 에어컨 필터 사진 2차.zip images=30
-> DX_AR_TEST zip best.pt=0
```

산출물:

```text
02_데이터연동/filter_detection_dataset/DATASET_STATUS_20260615.md
```

다음 작업:

```text
2번 Roboflow filter bbox 라벨링으로 진행한다.
권장 업로드 대상은 lg_wall_mounted_filter_user_primary_099_images.zip이다.
수량을 100장 이상으로 엄격히 맞춰야 하면 직접 촬영/허가 이미지 1장 이상을 추가하거나,
user plus reviewed 중 라이선스/품질 확인된 후보만 선별해 보강한다.
```


### 27.2 Roboflow 라벨링 진입 준비 - 대기

배경:

```text
1번 데이터셋 구성이 거의 충족되었으므로 2번 Roboflow filter bbox 라벨링으로 넘어가기 위해
업로드 스크립트, pre-label 패키지, 현재 API 환경을 점검했다.
```

구현/정리:

```text
1. primary_099 업로드 스크립트 보정
   - upload_to_roboflow.py 기본 batch_name을 현재 패키지명인 lg_wall_mounted_filter_user_primary_099로 수정

2. pre-label review 경로 확정
   - upload_prelabels_to_roboflow.py 사용
   - package_slug=lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2
   - image_label_pairs=99
   - as_predictions=True

3. 문서화
   - ROBOFLOW_LABELING_NEXT_STEP_20260615.md 추가
   - primary_099 roboflow_upload_status.md 갱신
```

검증:

```text
python -m pip show roboflow
-> roboflow SDK installed, version 1.3.10

python -m py_compile upload_to_roboflow.py
-> ok

python -m py_compile upload_prelabels_to_roboflow.py
-> ok

python upload_prelabels_to_roboflow.py --dry-run
-> image_label_pairs=99
-> as_predictions=True
-> dry_run=true; no upload attempted

현재 프로세스 env:
-> ROBOFLOW_API_KEY missing
-> ROBOFLOW_WORKSPACE missing
-> ROBOFLOW_PROJECT missing
```

상태:

```text
- 실제 Roboflow 업로드는 아직 수행하지 않았다.
- 이유: 현재 Codex 실행 셸에 Roboflow 인증 env가 없다.
- API key/워크스페이스/프로젝트 env가 설정되면 pre-label 업로드를 바로 실행할 수 있다.
- pre-label bbox는 정답 라벨이 아니며, Roboflow에서 모든 bbox를 검수해야 한다.
```


### 27.3 YOLO 학습 파이프라인 smoke 검증 - 부분 완료

배경:

```text
2번 Roboflow 수동 라벨링은 인증/env 대기 상태다.
그 사이 3번 YOLO 학습 및 best.pt 생성 파이프라인이 final export를 받았을 때 바로 동작하는지 확인했다.
검수 전 pre-label 모델은 최종 모델로 배치하지 않는다.
```

구현/수정:

```text
1. train_and_stage_filter_detector.py
   - --no-deploy 옵션 추가
   - smoke 학습 시 best.pt를 생성하더라도 FastAPI 모델 경로로 복사하지 않도록 분리
   - Ultralytics 학습 전 export 절대경로를 담은 _ultralytics_data.yaml 생성

2. 로컬 학습 의존성 설치/정리
   - ultralytics 8.4.67 설치
   - torch 2.12.0+cpu
   - numpy는 pykrx 호환을 위해 1.26.4 유지
   - opencv-python은 numpy 1.26 호환 버전 4.10.0.84로 조정
```

검증:

```text
python -m pip check
-> No broken requirements found.

python -c "import ultralytics, numpy, cv2, torch; import pykrx"
-> ultralytics=8.4.67
-> numpy=1.26.4
-> opencv=4.10.0
-> torch=2.12.0+cpu
-> pykrx_import=ok

python -m py_compile train_and_stage_filter_detector.py
-> ok

review-only dry-run guard:
-> --allow-review-only-training 없으면 차단
-> --allow-review-only-training --no-deploy 있으면 dry-run 통과

non-final smoke 학습:
python train_and_stage_filter_detector.py --export-dir roboflow_export/local_prelabel_yolov8_refined_v2_review_only --epochs 1 --imgsz 320 --batch 4 --name smoke_review_only_no_deploy_test --allow-review-only-training --no-deploy
-> exit code 0
-> smoke best.pt exists=True
-> smoke best.pt size=6,218,033 bytes
-> runtime deployed best.pt exists=False

python -m pytest -q tests/test_ar_filter_detection.py
-> 1 passed

DB 확인
-> careshot_ar_mock.db table_count=21
```

실패/수정:

```text
- ultralytics 설치 중 numpy가 2.4.6으로 올라가 pykrx와 충돌했다.
  -> numpy 1.26.4로 되돌리고 opencv-python을 4.10.0.84로 낮춰 pip check 통과.

- 1차 smoke 학습에서 Ultralytics가 data.yaml의 path: .를 현재 작업 디렉터리 기준으로 해석해 valid/images를 찾지 못했다.
  -> train_and_stage_filter_detector.py가 _ultralytics_data.yaml을 만들고 export 절대경로를 path로 쓰도록 수정.
```

상태:

```text
- 목표 3번의 최종 best.pt 생성은 아직 완료가 아니다.
- 이유: Roboflow 수동 bbox 검수 완료 export가 아직 없다.
- 이번 smoke best.pt는 검수 전 pre-label 기반 non-final 산출물이며, FastAPI 모델 경로로 배치하지 않았다.
```


### 27.4 FastAPI YOLO inference smoke 검증 - 부분 완료

배경:

```text
목표 4번은 FastAPI YOLO inference 서버 작성이다.
기본 구현은 이미 존재하지만, best.pt가 런타임 경로에 없어 mock fallback만 확인된 상태였다.
검수 전 smoke 모델을 앱에 배치하지 않고, env/model_path 주입으로 라우터가 실제 YOLO 모델을 로드하는지 격리 검증했다.
```

추가:

```text
02_데이터연동/filter_detection_dataset/training_runs/smoke_test_fastapi_filter_yolo.py
```

검증:

```text
python training_runs/smoke_test_fastapi_filter_yolo.py
-> status_code=200
-> mode=yolo
-> model_loaded=True
-> detections_count=97
-> first_detection.class_name=filter
-> first_detection.confidence=0.015029818750917912

python -m py_compile smoke_test_fastapi_filter_yolo.py
-> ok

python -m pytest -q tests/test_ar_filter_detection.py
-> 1 passed

runtime deployed best.pt
-> 03_AI로직/models/filter_detection/best.pt exists=False

DB 확인
-> careshot_ar_mock.db table_count=21
```

실패/수정:

```text
- smoke 스크립트 1차 실행에서 backend_dir 기본 경로가 07_개발단계/04_백엔드로 잘못 계산되었다.
  -> dataset_root 기준 같은 AR 루트의 04_백엔드를 가리키도록 수정했다.
```

상태:

```text
- FastAPI YOLO inference 경로는 실제 모델 로드와 bbox 응답까지 smoke 통과했다.
- 다만 최종 best.pt가 아니므로 production/runtime 모델 배치는 아직 하지 않았다.
- 목표 4번은 구현/격리 검증 완료에 가깝지만, 최종 완료 판정은 Roboflow 검수 완료 best.pt 배치 후 다시 확인한다.
```


### 27.5 ARGuide 프론트 smoke 검증 보강 - 완료

배경:

```text
목표 5~8은 웹캠 프레임 전송, bbox canvas overlay, bbox smoothing, guide step/안전문구 연결이다.
실제 카메라 권한을 자동 허용하지 않는 조건에서도 회귀를 잡을 수 있도록
ARGuide의 핵심 계산 로직과 fetch payload 계약을 smoke script로 검증한다.
```

구현:

```text
1. ARGuide helper 분리
   - arGuideDetection.ts 추가
   - smoothBox
   - getCaptureSizeFromDimensions
   - getObjectCoverTransform
   - getDetectionGuideText
   - DetectionBox/FilterDetectionResponse type

2. ARGuide.tsx
   - 기존 로직을 helper import로 연결
   - UI/동작 계약은 유지

3. smoke script
   - scripts/smoke-arguide-detection.mjs 추가
   - package.json에 smoke:ar-guide 추가
```

검증:

```text
npm run smoke:ar-guide
-> ok=true
-> smoothing: x=35, y=28, width=135, height=64
-> capture: width=416, height=312
-> object-cover: offsetX=-205, scaleX=scaleY=1.9230769230769231
-> static_contracts=10

npm run build
-> Vite build 성공
-> 기존 chunk size warning 유지

Browser http://127.0.0.1:5173/ar-guide
-> video=1
-> canvas=2
-> STEP 1 / 5 렌더링
-> 확인 위치/안전문구/카메라 안내 렌더링
-> console error 0

python -m pytest -q tests/test_ar_filter_detection.py
-> 1 passed

DB 확인
-> careshot_ar_mock.db table_count=21
```

상태:

```text
- 목표 5~8은 구현과 회귀 smoke 검증이 존재한다.
- 실제 카메라 권한 기반 bbox 움직임은 사용자가 브라우저에서 권한 허용 후 추가 확인해야 한다.
- 최종 YOLO best.pt가 아직 없으므로 실제 yolo bbox 기준 프론트 검증은 final model 배치 후 다시 수행한다.
```


### 27.6 Roboflow final export 이후 원클릭 검증/배치 wrapper - 완료

배경:

```text
현재 전체 목표의 병목은 2번 Roboflow bbox 수동 검수 완료 export다.
final export를 확보한 뒤에는 3~8번을 끊기지 않고 검증해야 하므로,
검증/학습/배치/백엔드 smoke/프론트 smoke/DB 확인을 한 번에 실행하는 wrapper를 추가했다.
```

추가:

```text
02_데이터연동/filter_detection_dataset/training_runs/finalize_filter_detector_after_export.py
```

동작:

```text
1. review_only export 기본 차단
2. train_and_stage_filter_detector.py 실행
3. best.pt를 03_AI로직/models/filter_detection/best.pt로 배치
4. smoke_test_fastapi_filter_yolo.py 실행
5. python -m pytest -q tests/test_ar_filter_detection.py 실행
6. npm run smoke:ar-guide 실행
7. npm run build 실행
8. careshot_ar_mock.db table_count=21 확인
```

검증:

```text
python -m py_compile finalize_filter_detector_after_export.py
-> ok

review-only export dry-run without allow flag
-> blocked=True
-> exit code 1

review-only export dry-run with --allow-review-only-smoke
-> train_and_stage_filter_detector.py dry-run 통과
-> no_deploy=True
-> exit code 0

python training_runs/smoke_test_fastapi_filter_yolo.py
-> mode=yolo
-> model_loaded=True
-> detections_count=97

npm run smoke:ar-guide
-> ok=True
-> static_contracts=10

python -m pytest -q tests/test_ar_filter_detection.py
-> 1 passed

DB 확인
-> careshot_ar_mock.db table_count=21
```

상태:

```text
- 최종 Roboflow export가 아직 없어 실제 final 배치는 수행하지 않았다.
- wrapper는 final export가 들어오면 목표 3~8을 한 번에 재검증하는 실행 경로다.
- review-only export는 기본 차단되므로 검수 전 pre-label 모델이 runtime best.pt로 배치되는 위험을 줄였다.
```


### 27.7 Filter detection goal audit - 외부 대기

배경:

```text
목표 1~8 전체에 대해 현재 증거로 완료/미완료 상태를 재점검했다.
완료로 주장 가능한 항목과 Roboflow 외부 입력이 필요한 항목을 분리했다.
```

산출물:

```text
00_계획수립/CareShot_AR_filter_detection_goal_audit_20260615.md
```

현재 상태:

```text
ROBOFLOW_API_KEY missing
ROBOFLOW_WORKSPACE missing
ROBOFLOW_PROJECT missing
Roboflow upload results missing
Roboflow final reviewed export missing
runtime best.pt missing
best_pt_deployment_metadata.json missing
```

판정:

```text
- 1번 데이터셋 구성은 user primary 99장 + 185장 후보로 부분 충족.
- 2번 Roboflow bbox 라벨링은 미완료/외부 대기.
- 3번 최종 best.pt 생성은 미완료. smoke best.pt만 존재.
- 4~8번 구현/스모크 검증은 존재하지만, final best.pt 기준 재검증이 필요.
```

재개 조건:

```text
1. 유효한 Roboflow API key 또는 Roboflow Web UI 로그인
2. lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2 업로드
3. Roboflow에서 모든 filter bbox 수동 검수
4. final YOLOv8 export를 roboflow_export/carevision-ar-filter-yolov8에 배치
5. finalize_filter_detector_after_export.py 실행
```


### 27.8 Legacy Roboflow notebook 기반 filter bbox 1차 모델 - 완료

배경:

```text
사용자가 추가 제공한 DX_AR_TEST zip은 best.pt 파일이 아니라 Colab/Jupyter notebook 3개였다.
이 중 aircon_filter_test notebook에는 Roboflow test_filter v1 학습 데이터셋 정보와 학습 로그가 남아 있었다.
해당 데이터셋을 내려받아 segmentation/polygon label을 filter bbox label로 변환하고,
YOLOv8n 50 epoch 학습 후 FastAPI runtime best.pt로 배치했다.
```

입력 확인:

```text
LG 벽걸이 에어컨 필터 사진.zip: image 70, best.pt 0
LG 벽걸이 에어컨 필터 사진 2차.zip: image 30, best.pt 0
DX_AR_TEST-20260615T073404Z-3-001.zip: notebook 3, best.pt 0

notebook dataset:
- project: test_filter v1
- class: test-filter -> runtime class_name filter로 정규화
- split: train 48 / valid 12 / test 6
```

추가 산출물:

```text
02_데이터연동/filter_detection_dataset/roboflow_export/legacy_notebook_test_filter_v1_yolov8
02_데이터연동/filter_detection_dataset/roboflow_export/legacy_notebook_test_filter_v1_bbox_yolov8
02_데이터연동/filter_detection_dataset/training_runs/prepare_legacy_notebook_filter_bbox_export.py
02_데이터연동/filter_detection_dataset/training_runs/filter_detection_yolo/legacy_notebook_test_filter_v1_bbox_50e/weights/best.pt
03_AI로직/models/filter_detection/best.pt
03_AI로직/models/filter_detection/best_pt_deployment_metadata.json
02_데이터연동/filter_detection_dataset/training_runs/legacy_notebook_test_filter_v1_user_primary_099_inference_summary.json
02_데이터연동/filter_detection_dataset/training_runs/legacy_notebook_test_filter_v1_user_primary_099_contact_sheet.jpg
```

학습 결과:

```text
model: yolov8n.pt
epochs: 50
imgsz: 640
batch: 4
runtime best.pt size: 6,268,785 bytes

valid result:
precision(B): 0.91595
recall(B): 1.0
mAP50(B): 0.98885
mAP50-95(B): 0.75660
```

사용자 제공 99장 이미지 대상 추가 확인:

```text
target: roboflow_upload/lg_wall_mounted_filter_user_primary_099/images
images: 99
confidence threshold: 0.25
images_with_detection: 88
detection_rate: 0.8889
max_conf_median: 0.6929
max_conf_mean: 0.6558
max_conf_max: 0.9480
```

검증:

```text
FastAPI smoke with deployed best.pt
-> status_code=200
-> mode=yolo
-> model_loaded=True
-> detections_count=1
-> first_detection.class_name=filter
-> first_detection.confidence=0.8145

python -m pytest -q tests/test_ar_filter_detection.py
-> 1 passed

npm run smoke:ar-guide
-> ok=True
-> static_contracts=10

npm run build
-> passed
-> existing chunk-size warning only

DB 확인
-> careshot_ar_mock.db table_count=21
```

실패 및 수정:

```text
1. DX_AR_TEST zip 내부 파일은 확장자가 없었으나 magic byte 확인 결과 notebook JSON이었다.
2. notebook dataset의 YOLOv8 export label은 bbox 5컬럼이 아니라 polygon/segmentation 형식이었다.
   -> prepare_legacy_notebook_filter_bbox_export.py를 추가해 polygon min/max bbox로 변환했다.
3. PowerShell here-string에서 한글 경로가 깨져 일부 검증 명령이 실패했다.
   -> cwd 기준 07_/06_AR/02_/03_ prefix 탐색 방식으로 재실행했다.
4. pytest는 repo root에서 실행해 app import가 실패했다.
   -> 04_백엔드 폴더를 cwd로 지정해 재검증했다.
```

상태:

```text
- 시연 가능한 1차 filter bbox YOLO runtime model은 생성 및 배치 완료.
- DB 스키마 변경 없음. table_count=21 유지.
- 프론트/백엔드 코드 변경 없음.
- 단, 학습셋은 legacy notebook의 labeled 66장 기준이므로, 최종 발표/운영 품질을 위해서는 user primary 99장의 Roboflow 수동 bbox 검수 후 재학습이 여전히 권장된다.
```


### 27.9 User primary 99장 모델 기반 prelabel package 생성 - 완료

배경:

```text
기존 heuristic prelabel 대신, 현재 배포된 filter best.pt로 user primary 99장에 자동 bbox를 생성하는 방식으로 전환했다.
목적은 Roboflow에서 처음부터 모든 박스를 새로 그리지 않고, 모델이 잡은 박스를 검수/수정하는 흐름을 만드는 것이다.
```

YOLOv12 판단:

```text
YOLOv12는 최종 재학습 모델 후보로 사용할 수 있다.
다만 prelabel 생성은 "현재 filter 클래스를 학습한 모델"이 박스를 예측해야 하므로,
아직 filter로 재학습되지 않은 yolo12n.pt 기본 가중치로 진행하지 않았다.
현재 로컬 작업공간에는 yolo12n.pt/yolov12n.pt가 없고, ultralytics 버전은 8.4.67이다.
```

추가/수정:

```text
추가:
- 02_데이터연동/filter_detection_dataset/generate_model_prelabel_package.py
- 02_데이터연동/filter_detection_dataset/roboflow_upload/lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8

수정:
- 02_데이터연동/filter_detection_dataset/roboflow_upload/upload_prelabels_to_roboflow.py
  - 빈 label txt 이미지는 annotation 없이 이미지로만 업로드하도록 보강
  - label이 있는 이미지는 prediction label로 업로드
```

생성 결과:

```text
source images:
roboflow_upload/lg_wall_mounted_filter_user_primary_099/images

output package:
roboflow_upload/lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8

zip:
roboflow_upload/lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8/lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8.zip

contact sheet:
roboflow_upload/lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8/model_prelabel_contact_sheet.jpg

summary:
roboflow_upload/lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8/model_prelabel_summary.json
```

수량:

```text
images: 99
label_files: 99
images_with_detection: 88
images_without_detection: 11
total_boxes: 92
confidence_threshold: 0.25
iou_threshold: 0.4
max_detections_per_image: 3
```

검증:

```text
python -m py_compile generate_model_prelabel_package.py
-> ok

python generate_model_prelabel_package.py --force
-> images=99
-> labels=99
-> images_with_detection=88
-> images_without_detection=11
-> total_boxes=92

YOLO label 검증
-> label_files=99
-> boxes=92
-> errors=[]

python upload_prelabels_to_roboflow.py --package-slug lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8 --dry-run
-> image_label_pairs=99
-> as_predictions=True
-> dry_run=true

ROBOFLOW_API_KEY
-> current shell missing
```

다음 작업:

```text
1. 현재 셸에 ROBOFLOW_API_KEY를 설정한다.
2. upload_prelabels_to_roboflow.py로 model_prelabel package를 Roboflow에 업로드한다.
3. Roboflow에서 88장 prediction box를 수정/확정하고, 11장 no detection 이미지는 직접 bbox를 추가한다.
4. 검수 완료 YOLOv8 export 또는 YOLOv12 재학습용 동일 YOLO format export를 내려받아 최종 재학습한다.
```


### 27.10 Roboflow model prelabel 실제 업로드 - 완료

배경:

```text
carevision_AI.env.txt에 있는 ROBOFLOW_API_KEY를 사용해 model-based prelabel package를 Roboflow에 실제 업로드했다.
env 파일의 ROBOFLOW_PROJECT 값은 "carevision AR"였으나 Roboflow SDK에서는 해당 값이 실패했고,
프로젝트 URL/SDK 접근 기준 slug인 "carevision-ar"로 보정해 업로드했다.
```

대상:

```text
workspace: s-workspace-fmrs3
project: carevision-ar
package: lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8
batch_name: lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8
split: train
as_predictions: True
```

업로드 결과:

```text
results_csv:
02_데이터연동/filter_detection_dataset/roboflow_upload/lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8/roboflow_prelabel_upload_results.csv

total: 99
uploaded: 99
failed: 0
uploaded_with_prediction_label: 88
uploaded_without_prediction_label: 11
```

검증:

```text
Roboflow SDK project access check:
carevision AR -> fail
carevision-ar -> ok

python upload_prelabels_to_roboflow.py --package-slug lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8
-> done uploaded=99 failed=0 total=99

CSV status count:
-> uploaded_with_prediction_label: 88
-> uploaded_without_prediction_label: 11
```

다음 작업:

```text
Roboflow Web UI에서 batch lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8를 열고,
88장 prediction box를 수정/확정한다.
11장 uploaded_without_prediction_label 이미지는 직접 filter bbox를 추가한다.
검수 완료 후 YOLO export를 내려받아 YOLOv8 또는 YOLOv12로 최종 재학습한다.
```

### 27.11 filter_detection_dataset 한글 폴더 구조 정리 - 완료

배경:

```text
사용자가 filter_detection_dataset 폴더를 한글명 중심으로 정리하고,
코딩/마크다운/CSV/검수 이미지/로그/원천 이미지/Roboflow/학습 결과가 섞이지 않도록 폴더별로 구분하라고 요청했다.
```

수행:

```text
기존 최상위 raw/roboflow_upload/roboflow_export/training_runs 구조를 다음 현재 구조로 정리했다.

02_데이터연동/filter_detection_dataset/00_코드_스크립트
02_데이터연동/filter_detection_dataset/01_문서_설명
02_데이터연동/filter_detection_dataset/02_매니페스트_CSV
02_데이터연동/filter_detection_dataset/03_검수용_컨택트시트
02_데이터연동/filter_detection_dataset/04_로그
02_데이터연동/filter_detection_dataset/10_원천이미지_raw
02_데이터연동/filter_detection_dataset/20_Roboflow_업로드패키지
02_데이터연동/filter_detection_dataset/30_Roboflow_내보내기_YOLO
02_데이터연동/filter_detection_dataset/40_학습실행결과
02_데이터연동/filter_detection_dataset/90_파이썬캐시
```

주요 산출물:

```text
신규 생성:
- 02_데이터연동/filter_detection_dataset/README_데이터셋_폴더구조_한글정리.md

주요 한글화:
- raw -> 10_원천이미지_raw
- roboflow_upload -> 20_Roboflow_업로드패키지
- roboflow_export -> 30_Roboflow_내보내기_YOLO
- training_runs -> 40_학습실행결과
- 주요 수집/라벨/학습 Python 스크립트 파일명을 한글 설명형 파일명으로 변경
- 주요 README/runbook/검증 이미지/추론 요약 파일명을 한글 설명형 파일명으로 변경
```

데이터셋 성격:

```text
이 폴더는 CareShot AR의 벽걸이 에어컨 필터 위치 탐지용 데이터셋 작업 공간이다.

현재 집계:
- 전체 이미지 파일: 3,946
- 원천 이미지: 1,827
- Roboflow 업로드 패키지 이미지: 985
- Roboflow YOLO export 이미지: 1,085
- label txt 파일: 1,388
- Python 파일: 21
- Markdown 파일: 22
- CSV 파일: 40
- contact sheet 파일: 17
```

검증:

```text
1. 옛 최상위 폴더 잔존 확인:
   raw=false
   roboflow_upload=false
   roboflow_export=false
   training_runs=false

2. Python 문법 검증:
   python -m py_compile 대상 21개
   errors=[]

3. 한글 파일명 상태의 학습 스테이징 dry-run:
   python "40_학습실행결과/필터검출기_학습및배포스테이징.py" --export-dir "30_Roboflow_내보내기_YOLO/local_prelabel_yolov8_refined_v2_review_only" --dry-run --allow-review-only-training
   verify_errors=[]
   total_images=99
   total_labels=99
   total_boxes=99

4. 한글 파일명 상태의 YOLO export 검증:
   python "30_Roboflow_내보내기_YOLO/Roboflow_YOLOv8_내보내기_검증.py" "30_Roboflow_내보내기_YOLO/local_prelabel_yolov8_refined_v2_review_only"
   errors=[]
```

주의:

```text
YOLO/Roboflow 내부 표준 폴더명 images, labels, train, valid, test는 변경하지 않았다.
이미지 파일명과 라벨 파일명은 stem 1:1 매칭이 필요하므로 대량 한글화하지 않았다.
```

### 27.12 GitHub taehee 브랜치 반영 전 repo 구조 호환 보강 - 완료

```text
GitHub checkout은 백엔드 폴더명이 04_백엔드가 아니라 backend이므로,
03_AI로직/rules/ai_decision_engine.py의 FastAPI backend 경로 탐색을 04_* 또는 backend 둘 다 허용하도록 보강했다.

검증:
- GitHub checkout backend 기준 python -m pytest tests
- 결과: 90 passed, 1 skipped

추가 검증:
- frontend npm run build 통과
- filter_detection_dataset Python 24개 py_compile 통과
```

### 27.12 Roboflow 최신 4개 export 반영 및 YOLO12 필터 검출 모델 재학습 - 완료

배경:

```text
Roboflow에서 최신 YOLOv8 zip 4개를 내려받았다.
- carevision AR.yolov8.zip: 검수 완료 user primary filter 99장
- test_filter.yolov8.zip: legacy notebook 학습에 사용한 filter 66장
- aircon.yolov8.zip: 에어컨 외부 객체 74장
- aircon_top_bottom.yolov8.zip: 상단/하단 영역 93장

이번 runtime 필터 검출 모델은 필터 bbox만 사용하므로,
carevision AR 99장과 test_filter 66장을 통합해 학습했다.
aircon / aircon_top_bottom export는 별도 외부/영역 인식 실험용으로 보관한다.
```

데이터셋 처리:

```text
Roboflow export 원본 위치:
02_데이터연동/filter_detection_dataset/30_Roboflow_내보내기_YOLO

polygon/segmentation label을 YOLO bbox 5-column label로 변환:
- carevision_ar_reviewed_099_bbox_yolov8_20260616
- test_filter_v1_bbox_yolov8_20260616
- aircon_top_bottom_bbox_yolov8_20260616

통합 필터 학습 데이터셋:
combined_filter_carevision099_testfilter066_bbox_yolov8_20260616
```

통합 데이터셋 검증:

```text
train: 147 images / 147 labels / 159 boxes
valid: 12 images / 12 labels / 12 boxes
test: 6 images / 6 labels / 6 boxes
total: 165 images / 165 labels / 177 boxes
verify_errors: []
```

실패 및 수정:

```text
1차 YOLO12 학습은 한글/공백이 포함된 긴 프로젝트 경로에서 OpenCV cv2.imread가 이미지를 안정적으로 읽지 못해 중단됐다.
대표 증상: FileNotFoundError: Image Not Found ... carevision099_train_0075.jpg

확인 결과 파일은 실제 존재했으나, cv2.imread 검사에서 한글 경로의 165장 전부가 None으로 반환됐다.
동일 데이터셋을 ASCII 경로 C:\Users\TAEHEE\lgdx_ar_yolo_work\datasets 로 복사하자 165장 전부 읽기 통과했다.

해결:
- 학습용 export와 run output은 ASCII 작업 경로에서 실행
- 성공한 best.pt만 원래 프로젝트 runtime 경로로 배포
```

학습/배포:

```text
model: YOLO12n
requested_epochs: 50
actual_epochs: 34 (early stopping)
imgsz: 640
batch: 4
source dataset: C:\Users\TAEHEE\lgdx_ar_yolo_work\datasets\combined_filter_carevision099_testfilter066_bbox_yolov8_20260616
run: C:\Users\TAEHEE\lgdx_ar_yolo_work\runs\filter_detection_yolo\yolo12n_filter_carevision099_testfilter066_50e_ascii

deployed:
03_AI로직/models/filter_detection/best.pt

backup:
03_AI로직/models/filter_detection/best_20260616_112754_backup.pt
```

학습 지표:

```text
Ultralytics final best.pt validation:
precision(B): 0.9229
recall(B): 0.9983
mAP50(B): 0.9758
mAP50-95(B): 0.7533

results.csv last row:
epoch: 34
mAP50(B): 0.995
mAP50-95(B): 0.73216
```

런타임 검증:

```text
FastAPI smoke:
python FastAPI_필터_YOLO_스모크테스트.py --confidence-threshold 0.25
-> status_code=200
-> mode=yolo
-> model_loaded=true
-> detections_count=1
-> first_detection.confidence=0.9171753526
-> first_detection.class_name=filter

Backend test:
python -m pytest -q tests/test_ar_filter_detection.py
-> 1 passed

Frontend smoke:
npm run smoke:ar-guide
-> ok=true

Frontend build:
npm run build
-> success
-> warning: JS chunk larger than 500 kB

DB structure check:
careshot_ar_mock.db table_count=21
```

주의:

```text
이번 작업은 DB schema를 변경하지 않았다.
프론트/백엔드 source code도 수정하지 않았다.
npm build로 dist 산출물은 갱신될 수 있으나, runtime 연동 소스 변경은 없다.
```

### 27.13 AR 직접 검증용 mock fallback 비활성화 - 완료

배경:

```text
브라우저 AR 화면에서 카메라 권한은 허용됐지만 "필터 위치 예비 표시"가 떠서,
사용자가 best.pt 실제 연결 여부를 확인했다.
```

확인:

```text
실제 8791 백엔드 API 직접 호출 결과:
model_loaded=true
mode=yolo
detections_count=1
confidence=0.9171753526
class_name=filter
```

수정:

```text
ARGuide.tsx의 /api/v1/ar/filter-detect 요청에서 mock_fallback을 false로 변경했다.
이제 best.pt가 연결되지 않으면 예비 박스를 띄우지 않고, 실제 YOLO 탐지 결과가 있을 때만 박스를 표시한다.
```

백업:

```text
99_백업/2026-06-16_ARGuide_disable_mock_fallback_backup/ARGuide.tsx
99_백업/2026-06-16_ARGuide_disable_mock_fallback_backup/smoke-arguide-detection.mjs
```

검증:

```text
npm run smoke:ar-guide -> ok=true
npm run build -> success
POST http://127.0.0.1:8791/api/v1/ar/filter-detect mock_fallback=false -> mode=yolo, model_loaded=true
```

### 27.14 AR 발표/시연용 탐지 라벨 문구 변경 - 완료

배경:

```text
AR 화면의 bbox 라벨이 현재 단계명과 confidence를 함께 표시해 "전원 차단 79%"처럼 보였다.
실제 모델은 filter 객체를 탐지하는 것이므로 발표/시연 화면에서는 "필터 79%"가 더 명확하다.
```

수정:

```text
05_프론트엔드/react-vite/src/app/pages/ARGuide.tsx
- bbox canvas label: `${steps[current].title} NN%` -> `필터 NN%`
```

백업:

```text
99_백업/2026-06-16_ARGuide_filter_label_backup/ARGuide.tsx
```

검증:

```text
npm run smoke:ar-guide -> ok=true
npm run build -> success
```

### 27.15 Render/Supabase 환경 API PostgreSQL region lookup 보정 - 완료

배경:

```text
Render 배포 프론트 Home 화면에서 Fine Dust가 10으로 표시됐다.
원인 확인 결과 실제 미세먼지 값이 10인 것이 아니라, live 환경 API가 fallback_cache로 내려오면서 observation.aqi, pm25, pm10이 null이었고 프론트가 null fallback 기본값 10을 표시했다.
```

원인:

```text
백엔드 환경 refresh 중 create_environment_observation -> resolve_region_id 경로에서 PostgreSQL/Supabase가 아래 조건의 파라미터 타입을 추론하지 못했다.
(? IS NULL OR city = ?)
오류: psycopg.errors.IndeterminateDatatype / could not determine data type of parameter
```

수정:

```text
backend/app/repositories/sqlalchemy_repositories.py
- resolve_region_id에서 city가 있으면 AND city = ? 조건을 SQL에 직접 추가
- city가 없으면 city 조건을 붙이지 않도록 SQL 분기
- PostgreSQL의 untyped null predicate를 제거
```

검증:

```text
python -m pytest tests/test_environment_data_adapter.py -q --basetemp C:\Users\TAEHEE\carevision_pytest_tmp_env -p no:cacheprovider
-> 9 passed
```

추가 회귀 테스트:

```text
test_resolve_region_id_avoids_postgres_untyped_null_city_predicate
- resolve_region_id("Telangana", "Hyderabad") 호출 시 "? IS NULL OR" 패턴이 생성되지 않는지 확인
- city가 있을 때 "AND city = ?" 조건과 파라미터 순서 확인
```

남은 확인:

```text
GitHub push 후 Render 백엔드가 자동 배포되면 /api/v1/environment/current?region=India&city=Hyderabad 또는 실제 사용자 지역 기준으로 재호출해 fallback_cache/null 문제가 해소됐는지 live 재검증한다.
```

### 27.16 Home 환경 정보/Care Risk Score 초기 표시 지연 보정 - 완료

배경:

```text
Render 프론트 Home 화면에서 환경 정보와 Care Risk Score가 늦게 반영되어 보였다.
실제 원인은 API 응답 전까지 프론트가 New Delhi, 24도/56%/AQI 10/PM 10, Care Risk 82 같은 기본/데모 값을 먼저 표시한 뒤 실제 API 값으로 바꾸는 구조였다.
```

수정:

```text
frontend/src/app/pages/Home.tsx
- 사용자 프로필 조회 후 care risk API와 environment API를 독립적으로 호출하도록 분리
- care risk 응답이 오기 전에는 기본 점수 82 대신 Updating 상태와 0 기반 gauge를 표시
- 환경 응답이 오기 전에는 24/56/10 같은 fallback 숫자 대신 ... 또는 -- 표시
- location label을 New Delhi 고정 분기가 아니라 API observation 또는 사용자 profile region/city 기반으로 표시
- 하나의 API가 늦어져도 다른 카드 갱신이 같이 막히지 않도록 로딩 상태를 분리
```

검증:

```text
cd frontend
npm run build
-> success
```

특이사항:

```text
최초 일반 빌드는 esbuild spawn EPERM 권한 문제로 실패했다.
권한 상승 후 동일 명령을 재실행했고 Vite production build가 성공했다.
chunk size warning은 기존 번들 크기 경고이며 이번 수정의 컴파일 실패는 아니다.
```

남은 확인:

```text
프론트 Render Static Site가 main 브랜치를 보고 있으므로, taehee 브랜치 반영만으로는 live 프론트에 바로 배포되지 않을 수 있다.
live 반영은 main merge 또는 Render 프론트 브랜치를 taehee로 변경한 뒤 확인한다.
```

### 27.17 Home Care Risk Score 게이지 단위 영문화 - 완료

배경:

```text
Home 화면 Care Risk Score 중앙 게이지의 점수 단위가 "점"으로 표시되어 영어 UI와 맞지 않았다.
발표/시연용 프론트 문구 일관성을 위해 영어 단위 "pt"로 변경했다.
```

수정:

```text
frontend/src/app/pages/Home.tsx
- SegmentedGauge 중앙 점수 단위: 점 -> pt
```

검증:

```text
cd frontend
npm run build
-> success
```

특이사항:

```text
빌드 중 chunk size warning은 남아 있으나 기존 번들 크기 경고이며 이번 단위 변경의 실패 요인은 아니다.
```
