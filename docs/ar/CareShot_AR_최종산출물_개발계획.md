# CareShot AR 가전케어 AI 최종 산출물 개발계획

## 1. 기준 변경

이 문서는 “현재 코드가 어디까지 돌아가는가”가 아니라, **최종 제출/발표 산출물로 무엇을 완성해야 하는가**를 기준으로 작성한다.

현재 구현된 AR 화면, API, rule 기반 판단엔진은 로컬 검증용이다. 최종 산출물은 다음 조건을 만족해야 한다.

```text
학습/LLM/RAG 기반 챗봇
→ 공식자료 근거 검색
→ 안전 판단
→ ARGuidePlan 생성
→ 실제 reference image 기반 AR 안내
→ 세션 저장 및 검증 로그
```

따라서 “완료”는 단순 실행이 아니라, 최종 서비스 구조를 설명하고 시연할 수 있는 수준을 의미한다.

## 1.1 2026-06-05 서비스 명칭 및 제공 방식 변경

서비스 명칭은 아래처럼 통일한다.

| 명칭 | 최종 의미 |
|---|---|
| `self_care` | 고장 전 예방 관리. 회원가입 주소 기반 환경 API + ThinQ 사용 로그 + 관리 이력으로 알림 생성 |
| `self_as` | 고객이 직접 수행 가능한 자가 A/S. 챗봇 문의와 스마트 진단을 바탕으로 Low/Medium Risk에서 제공 |
| `expert_as` | 공식 A/S 연결. High Risk, 공식 근거 부재, 자가 조치 불가 시 제공 |

최종 제공 방식:

- 고객은 매뉴얼 방식과 AR 방식을 하나만 선택받지 않는다.
- `self_care`와 `self_as` 응답에는 공식 콘텐츠와 AR Guide가 함께 제공된다.
- 공식 콘텐츠 열람과 AR 실행은 각각 저장하고, 통합 `care_activity_logs`로 합산한다.
- `device_care_summary`는 가전 탭에서 self care count, self A/S count, total care count, care score를 보여준다.
- 관리/A/S 내역 리스트는 백엔드의 통합 조회 View/API로 제공한다. 프론트는 `ar_session_logs`, `service_route_logs` 등 원천 로그 테이블을 직접 조합하지 않는다.
- 회원가입 주소는 환경 API 조회와 `expert_as` 연결 주소의 기준이다.
- 고객 선택 언어는 웹 UI, 챗봇, 공식 콘텐츠, AR 안내, TTS/자막에 반영한다.

## 1.2 2026-06-19 TTS 단계별 음성 안내 상태

- `POST /api/v1/tts/synthesize`: Google Cloud TTS 직접 mp3 합성 완료.
- `POST /api/v1/tts/generate`: step 텍스트를 mp3로 생성하고 `audio_url` 반환 완료.
- `GET /api/v1/tts/audio/{cache_key}.mp3`: runtime cache mp3 재생 URL 제공 완료.
- `GOOGLE_TTS_PREGENERATE=1`: guide step 응답에 `audio_url` 사전 부착 가능.
- 2026-06-19 최종 재검증 기준: GitHub `taehee` 브랜치와 Render live 모두 `/api/v1/tts/generate`, `/api/v1/tts/audio/{cache_key}.mp3`가 반영되었다. Live `/tts/generate`는 mp3 URL 생성과 `audio/mpeg` 재생까지 통과했다. `GOOGLE_TTS_PREGENERATE=1` 적용 후 `/api/v1/ar/plans` 7개 step 모두 `audio_url`이 생성되었고, `/api/v1/guides/options`의 `manual_guides.display_steps`에도 `audio_url`이 생성되었다.
- 2026-06-19 Task 8 구현 기준: `SUPABASE_TTS_STORAGE_ENABLED=1`이면 `tts/{language_code}/{voice_name}/{cache_key}.mp3` 경로로 Supabase Storage `tts-audio` bucket을 우선 사용한다. Storage 객체가 이미 있으면 public URL을 재사용하고, 없으면 Google TTS 생성 후 업로드한다. Supabase 설정/업로드 실패 시 발표 안정성을 위해 기존 Render runtime cache URL로 fallback한다.
- 2026-06-19 Task 8 live 검증 기준: Render live `/api/v1/tts/generate`, `/api/v1/ar/plans`, `/api/v1/guides/options` 모두 Supabase Storage public URL을 반환했고, 각 mp3 URL은 `200 audio/mpeg`로 재생 검증되었다.

## 2. 최종 산출물 정의

최종 산출물은 아래 8개 묶음으로 제출/발표 가능해야 한다.

| 번호 | 산출물 | 최종 기준 |
|---|---|---|
| 1 | 서비스 아키텍처 문서 | 프론트/백엔드/AI/DB/AR 흐름이 설명 가능 |
| 2 | 데이터베이스 및 mock 데이터 | ThinQ 미접근 상황에서도 최종 구조와 유사하게 동작 |
| 3 | 챗봇 대화 엔진 | 자연어 문의, 추가 질문, High Risk 분기 가능 |
| 4 | LLM/RAG 모듈 | 공식자료 근거 검색과 자연어 응답 구조 구현 |
| 5 | AI 판단엔진 v2 | 챗봇/RAG/로그/진단/환경을 종합해 최종 action 결정 |
| 6 | ARGuidePlan 생성기 | 안전하고 공식 근거 있는 경우만 AR plan 생성 |
| 7 | AR 프론트 시연 화면 | reference image + Part Map + step overlay 시연 |
| 8 | 검증/발표 패키지 | 정상/모호/High Risk 시나리오와 테스트 결과 정리 |

필수 백엔드 조회 API:

```text
GET /api/v1/devices/{device_id}/care-summary
- 가전 탭 상단 count/score 요약

GET /api/v1/devices/{device_id}/care-history
- self care/self A/S/expert A/S 통합 내역
- source: content_view_logs, ar_session_logs, ar_step_logs, care_activity_logs, service_route_logs, expert_as_requests
- 프론트 원천 로그 join 금지
```

## 3. 현재 상태 재정의

기존 문서에서 “완료”라고 적힌 항목은 최종 기준으로 다시 봐야 한다.

| 영역 | 현재 상태 | 최종 기준 판단 |
|---|---|---|
| DB | SQLite mock DB 구현, embedding table/JSONL vector index 구축 | 구현됨 / 최종 DB는 PostgreSQL + pgvector 전환 필요 |
| Backend API | 기본 API 구현 | 구현됨 / FastAPI + Pydantic + repository 구조 전환 필요 |
| Frontend | 챗봇 + AR 화면 1차 구현 구현 | 구현됨, multi-turn UX/공식근거 카드 필요 |
| AR | reference image overlay 구현 | 구현됨, 좌표 보정/완료/중단/해결 UX 필요 |
| AI 판단엔진 | rule 기반 판단엔진 1차 구현 | 구현됨 / 고도화 필요 |
| 챗봇 | rule mock 형태 | 최종 기준 미구현 |
| LLM | 없음 | 최종 기준 미구현 |
| RAG | 1,889개 공식자료 chunk, 1,889개 embedding, RAGService v2 구현 | 구현됨 / RAGService v2 검색 품질 평가 필요 |
| 안전검증 | High Risk keyword 차단 | 구현됨, 근거/차단 로그 고도화 필요 |

## 4. 최종 개발 순서

최종 개발은 아래 순서로 진행한다.

```text
1. AS-Q24ENXE support/FAQ 전체 수집 간극 검증 - 수행됨
2. 공식 FAQ/Help Library 추가 수집 및 chunk 확장 - 수행됨
3. 신규 chunk embedding 재생성 - 수행됨
4. RAGService v2 검색 품질 검증 - 지금 다음 작업
5. FastAPI 백엔드 구조 전환
6. SQLAlchemy 또는 SQLModel repository 계층 작성
7. PostgreSQL + pgvector 최종 DB 전환
8. React + TypeScript 프론트 구조 전환
9. 프론트/백 API contract freeze
10. 챗봇 대화 엔진 구현
11. LLMService mock 또는 실제 LLM adapter 구현
12. AI 판단엔진 v2 구현
13. ARGuidePlan/AR 화면 연동 고도화
14. 안전/근거/좌표 검증
15. 발표용 시나리오 polish
```

현재는 RAG 데이터 구축 고도화, AS-Q24ENXE support/FAQ 누락분 추가 수집, Embedding/Vector DB, RAGService v2, AI 판단엔진 1차 rule, API 뼈대, AR 1차 화면이 구현된 상태다.

현재 RAG corpus는 LG India 공식자료 기반 1,889개 chunk와 1,889개 embedding까지 구축되어 있다. AS-Q24ENXE support/FAQ 간극 검증과 누락분 추가 수집은 수행되었으므로, 다음 개발은 **RAG 품질 검증 → FastAPI 전환 → PostgreSQL + pgvector 전환** 순서로 진행한다.

## 5. 최종 Backend 산출물

### 5.1 최종 역할

백엔드는 프론트 요청을 받아 챗봇, RAG, 판단엔진, ARGuidePlan, 세션 저장을 연결한다.

### 5.2 최종 API

| Method | Path | 최종 역할 |
|---|---|---|
| `POST` | `/chat/messages` | multi-turn 챗봇 메시지 처리 |
| `POST` | `/chat/sessions` | 대화 세션 생성 |
| `GET` | `/chat/sessions/{id}` | 대화 상태 조회 |
| `POST` | `/ai/analyze` | 구조화된 문의 분석 |
| `POST` | `/rag/search` | 공식자료 검색 |
| `POST` | `/ar/guides/plan` | ARGuidePlan 생성 |
| `POST` | `/ar/sessions` | AR 세션 시작 |
| `PATCH` | `/ar/sessions/{id}` | AR 진행 상태 저장 |
| `POST` | `/safety/check` | 위험도/금지 action 검증 |

### 5.3 현재와 차이

현재 `/chat/messages`는 한 번에 rule 판단과 ARGuidePlan을 생성한다.  
최종 구조에서는 `/chat/messages`가 먼저 대화 상태를 관리하고, 필요한 경우 추가 질문을 반환해야 한다.

예:

```json
{
  "message_state": "clarifying",
  "question": "타는 냄새인가요, 곰팡이 냄새인가요?",
  "next_required_slot": "odor_type"
}
```

## 6. 최종 Frontend 산출물

### 6.1 최종 역할

프론트는 ThinQ 앱 내 챗봇 경험을 가정한 자체 데모 화면이다.

### 6.2 최종 화면 상태

| 상태 | 설명 |
|---|---|
| `idle` | 문의 입력 전 |
| `analyzing` | 챗봇/AI 분석 중 |
| `clarifying` | 추가 질문 필요 |
| `official_content_ready` | 공식 콘텐츠 제공 가능 |
| `ar_ready` | AR Guide Session 시작 가능 |
| `ar_running` | AR 단계 진행 중 |
| `completed` | 관리/자가점검 완료 |
| `high_risk_service_route` | A/S 연결 |
| `blocked_no_official_basis` | 공식 근거 부족으로 차단 |

### 6.3 최종 UI 구성

```text
챗봇 패널
→ 추가 질문 카드
→ 공식자료 근거 카드
→ AR 시작 카드
→ High Risk expert A/S 연결 카드

AR 패널
→ reference image
→ Part Map overlay
→ 단계별 안내
→ 안전 문구
→ 완료/해결 안 됨/A/S 연결
```

## 7. 최종 AI 산출물

## 7.1 챗봇 대화 엔진

챗봇은 단순 입력창이 아니라, 사용자의 증상을 구조화해야 한다.

### 최종 기능

| 기능 | 설명 |
|---|---|
| intent 분류 | care / self_check / high_risk / out_of_scope |
| slot 추출 | symptom, odor_type, duration, severity, visible_damage |
| 추가 질문 | 정보가 부족하면 질문 |
| 대화 상태 저장 | multi-turn 흐름 유지 |
| 판단엔진 입력 생성 | 구조화된 payload 생성 |

### 예시

```text
사용자: 냄새가 나요.
챗봇: 타는 냄새인가요, 곰팡이 냄새인가요?

사용자: 곰팡이 냄새요.
챗봇: 필터와 송풍구 표면 점검을 안내할 수 있습니다.
```

## 7.2 LLMService

LLM은 자연어 이해와 응답 생성을 담당한다. 단, 최종 safety decision은 하지 않는다.

### LLM 허용 역할

```text
문의 요약
증상 slot 추출 보조
추가 질문 문장 생성
공식자료 검색 query 생성
고객 안내 문장 생성
다국어 번역
```

### LLM 금지 역할

```text
공식자료 없는 수리 절차 생성
High Risk를 Low Risk로 낮추기
내부 분해/전기/냉매 작업 안내
모델에 없는 부품명 생성
```

개발 단계에서는 비용을 아끼기 위해 `LLMServiceMock`을 먼저 만들고, API 연결부만 교체 가능하게 둔다.

## 7.3 RAGService

RAG는 공식자료 근거를 찾는다.

현재 RAGService는 1차 구현 상태다.

```text
구현됨:
- 217개 정제 official_document_chunks 검색
- 공식 URL 검증
- boilerplate chunk 제외
- lexical scoring
- /rag/search API
- /chat/messages rag_evidence 연결

미구현:
- 공식 PDF RAG(Owner's Manual/Spec/Dimension 포함)
- 충분한 공식 FAQ/Help Library corpus
- embedding model
- Vector DB
- semantic similarity search
```

### 최종 검색 대상

```text
Owner's Manual
Online Manual
Official FAQ
Support Page
Product Image
Product Type Common Procedure
```

### 최종 개발 순서

```text
1. LG India 공식 PDF(Owner's Manual/Spec/Dimension 포함)/Online Manual/FAQ/Help Library 원본 수집
2. PDF/HTML 원본 파일 저장 및 source manifest 기록
3. PDF 텍스트, JSON-LD articleBody, FAQ Q/A 추출
4. cookie/footer/navigation/OTP boilerplate 제거
5. official_document_chunks 확장
6. chunk coverage 검수 리포트 생성
7. embedding model 선정 및 vector index 구축
8. RAGService v2에서 metadata strict filter + vector similarity 검색 구현
9. no-match 시 ARGuidePlan 차단 정책 연결
```

### 최종 반환값

```json
{
  "match_status": "verified",
  "match_type": "exact_model",
  "asset_ids": ["OA_AC_ASQ24ENXE_MANUAL_001"],
  "chunk_ids": ["CHUNK_AC_FILTER_001"],
  "procedure_type": "filter_cleaning",
  "forbidden_actions": ["internal_disassembly", "pcb_repair"]
}
```

## 7.4 AI 판단엔진 v2

현재 1차 판단엔진은 keyword/rule 기반이다. 최종 판단엔진 v2는 아래 입력을 모두 받아야 한다.

```text
conversation_state
llm_summary
rag_result
device_context
usage_log
smart_diagnosis
environment_context
official_asset_match
```

### 최종 판단 결과

```json
{
  "intent_type": "care",
  "risk_level": "low",
  "decision_action": "prepare_ar_guide_session",
  "official_basis_status": "verified",
  "ar_guide_allowed": true,
  "service_route_required": false,
  "reason_codes": ["FILTER_CLEANING_OVERDUE", "OFFICIAL_MANUAL_MATCHED"],
  "evidence_asset_ids": ["OA_AC_ASQ24ENXE_MANUAL_001"]
}
```

### 판단엔진 v2에서 꼭 필요한 것

| 항목 | 필요 이유 |
|---|---|
| 모호성 판단 | 바로 AR을 열면 안 되는 문의 식별 |
| 추가 질문 필요 여부 | 챗봇 multi-turn 처리 |
| RAG 근거 확인 | 환각 방지 |
| High Risk hard block | 안전 확보 |
| forbidden action 검사 | 내부 분해/전기/냉매 차단 |
| reason code | 발표/검증/로그 설명 |

## 8. 최종 DB 산출물

### 8.1 현재 DB

현재 SQLite mock DB는 로컬 검증용이다.

### 8.2 최종 추가 필요 테이블

| 테이블 | 목적 |
|---|---|
| `chat_sessions` | 대화 세션 |
| `chat_messages` | 사용자/챗봇 메시지 |
| `conversation_slots` | 증상 slot 저장 |
| `official_document_chunks` | RAG 검색 단위 |
| `rag_search_logs` | 검색 결과 로그 |
| `decision_logs` | 판단엔진 결과 로그 |
| `safety_check_logs` | 차단 사유 로그 |
| `part_map_versions` | 좌표 보정 버전 |

### 8.3 최종 DB 방향

`care_videos`는 최종 DB 방향에서 제외한다. CareShot AR은 영상을 생성하지 않고, 관리 영상 재사용 DB도 운영하지 않는다.

공식 콘텐츠 제공은 `official_contents`로 통합한다. 이 테이블은 LG India 공식 매뉴얼, FAQ, Help Library, 지원 페이지, 공식 PDF 등 고객에게 보여줄 공식자료 단위를 관리한다. 기존 `care_videos`, `care_video_db.json`, `find_reusable_care_video` 계열 구현은 다음 DB/백엔드 정리 단계에서 제거하거나 `official_contents` 조회로 대체한다.

## 9. 최종 AR 산출물

### 9.1 현재 AR 상태

현재는 AS-Q24ENXE 필터 청소 시나리오가 동작한다.

```text
reference image
→ Part Map 좌표
→ AR Guide Step
→ overlay 표시
```

### 9.2 최종 AR 기준

| 기준 | 설명 |
|---|---|
| reference image | 제품/구조 타입별 기준 이미지 |
| part map | 부품 위치 좌표 |
| allowed action | 사용자가 해도 되는 동작 |
| forbidden action | 절대 안내하면 안 되는 동작 |
| overlay type | outline, arrow, pulse, dim |
| step state | 진행/완료/중단 |

### 9.3 최종 AR 검증

```text
필터 라벨이 실제 필터에 붙는지
커버 안내가 실제 커버에 붙는지
송풍구가 필터로 오인되지 않는지
금지 영역이 사용자 action으로 안내되지 않는지
High Risk에서 AR 화면이 열리지 않는지
```

## 10. 최종 테스트/검증 산출물

최종 제출 전 아래 테스트 결과가 있어야 한다.

| 테스트 | 기대 결과 |
|---|---|
| 필터 청소 문의 | AR Guide 제공 |
| 곰팡이 냄새 문의 | 추가 질문 후 관리 AR 제공 |
| 타는 냄새 문의 | High Risk A/S 연결 |
| 모델명 공식자료 없음 | AR 차단 |
| 내부 분해 요청 | AR 차단 |
| Part Map 오차 | 좌표 보정 대상 표시 |
| AR 세션 완료 | 21개 최종 테이블 유지 기준에서는 `SELF_MANAGEMENT_HISTORY`에 완료 이력 1줄 저장 |

## 11. 발표용 최종 시연 구성

### 시연 1: 정상 관리

```text
Please help me clean the AC filter.
→ 공식자료 근거 확인
→ Low Risk
→ AR Guide Session
→ 내부 필터 하이라이트
```

### 시연 2: 모호한 문의

```text
냄새가 나요.
→ 챗봇 추가 질문
→ 곰팡이 냄새 선택
→ 필터/송풍구 관리 안내
```

### 시연 3: High Risk

```text
타는 냄새가 나요.
→ High Risk
→ AR 차단
→ A/S 연결
```

## 12. 최종 개발 우선순위

지금부터의 우선순위는 다음과 같다.

```text
1. ChatbotEngine 구현
2. ConversationState / chat_sessions DB 추가
3. LLMServiceMock 구현
4. official_document_chunks DB 추가
5. RAGService 구현
6. AI 판단엔진 v2 구현
7. /chat/messages를 multi-turn 구조로 변경
8. 프론트 챗봇 UI를 추가 질문/근거 카드 구조로 변경
9. 모호한 문의/High Risk/정상 관리 테스트 작성
10. 발표용 polish
```

## 13. 최종 기준에서의 결론

현재 상태는 “AR이 보이고 API가 돌아가는 1차 구현”다.  
최종 산출물로는 아직 부족하다.

가장 중요한 미구현 영역은 다음 3개다.

```text
챗봇 대화 엔진
LLM 기반 대화 응답
RAG 기반 공식문서 검색
```

따라서 다음 개발은 AR이 아니라 **RAG 데이터 구축 고도화와 Vector DB 구축**을 먼저 진행하고, 그 결과를 RAGService v2, 챗봇/LLM, AI 판단엔진 v2와 연결하는 방향으로 진행한다.

## 14. 고도화 필요 추적 기준

현재까지 구현한 산출물은 최종 기준으로 `완료` 처리하지 않는다.

상태 관리는 아래 문서를 기준으로 한다.

```text
00_계획수립/CareShot_AR_고도화필요_추적표.md
```

특히 `rule 기반 판단엔진 1차 구현`은 다음 의미로만 사용한다.

```text
AI / rule 기반 판단엔진 1차 구현 / 구현됨 / 고도화 필요
```

최종 산출물 기준에서는 ChatbotEngine, ConversationState, LLMServiceMock, RAGService, AI 판단엔진 v2가 연결되어야 한다.


