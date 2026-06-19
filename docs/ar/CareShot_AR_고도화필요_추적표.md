# CareShot AR 고도화 필요 추적표

이 문서는 현재까지 구현된 작업을 최종 산출물 기준으로 다시 분류하기 위한 추적표다.

중요 기준:

- `완료`라는 표현은 최종 개발 완료로 사용하지 않는다.
- 현재 구현된 기능은 원칙적으로 `구현됨 / 고도화 필요`로 기록한다.
- 최종 산출물 기준에서 아직 구현되지 않은 기능은 `미구현 / 개발 필요`로 기록한다.
- 기능이 실제 제출/발표 산출물 수준이 되었을 때만 별도 검수 후 `최종 기준 충족`으로 바꾼다.

## 1. 전체 상태 기준

| 상태 | 의미 | 사용 조건 |
|---|---|---|
| 구현됨 / 고도화 필요 | 데모 흐름은 동작하지만 최종 산출물 기준으로 보완 필요 | 현재 구현된 DB/API/AI/AR/프론트 대부분 |
| 초안 작성 / 고도화 필요 | 문서나 정의는 있으나 개발 적용/검증이 부족함 | 정의서, 로드맵, 설계 문서 |
| 미구현 / 개발 필요 | 아직 코드나 DB 구조가 없음 | ChatbotEngine, LLMService, Embedding/Vector DB 등 |
| 검증 필요 | 구현은 있으나 테스트/시나리오 검증이 부족함 | API, 좌표, 안전 분기, 프론트 상태 |
| 최종 기준 충족 | 최종 발표/제출 기준을 만족하고 검증 로그가 있음 | 현재는 사용하지 않음 |

## 2. 현재 구현 항목별 고도화 필요 사항

| 영역 | 현재 산출물 | 현재 상태 | 고도화 필요 사항 |
|---|---|---|---|
| DB | SQLite mock DB, seed script, repository | 실제 근거 기반 seed 재구축 및 RAG corpus 확장 수행됨 / 평가·Vector DB 고도화 필요 | Embedding/Vector DB, 평가 실행 로직, AI 판단엔진 v2 연결 필요 |
| Mock Data | 고객/제품/로그/진단/환경/공식자료/AR step JSON | 15-2-B 실제 근거 기반 데이터 확장 수행됨 / intent 평가셋 미수행 | 임시 평가셋은 보류 폴더로 분리. 다음 단계에서 평가 기준 확정 후 intent/risk 테스트셋 생성 필요 |
| Backend API | `server.py` 기반 API | 구현됨 / 고도화 필요 | 서비스 계층 분리, request/response schema 고정, OpenAPI 문서, API 테스트, 오류 응답 표준화 |
| ThinQ Adapter | mock DB 직접 조회 | 구현됨 / 고도화 필요 | `ThinQMockAdapter` 분리, ThinQ Connect MCP/Open API 대체 가능 인터페이스 정의 |
| AI 판단엔진 | rule 기반 판단엔진 1차 구현 | 구현됨 / 고도화 필요 | intent rule table, conversation state, LLM 요약, RAG 근거, confidence, 안전 근거 로그를 받는 AI 판단엔진 v2 구현 |
| 위험도 판단 | Low/Medium/High rule 분기 | 구현됨 / 고도화 필요 | 자연어 위험 신호와 스마트 진단 severity 결합, Medium Risk 정책, 금지 action 검증 강화 |
| 공식자료 매칭 | official_assets strict matching + RAGService v2 검색 | 공식자료 corpus 확장, 실패 케이스 보정, RAGService v2 재검증 수행됨 / 40개 query 통과 | FastAPI 전환 후 API 레벨 strict matching 회귀 테스트 필요 |
| 공식 콘텐츠 매칭 | 관리 콘텐츠 재사용 로직 | 구현됨 / 고도화 필요 | 영상/문서/FAQ를 포괄하는 `official_contents` 구조로 일반화, 언어/길이/제품군 기준 재정의 |
| AR Guide Template | `aircon_filter_cleaning_v1` 등 template 개념 | 구현됨 / 고도화 필요 | template validation, allowed/forbidden action 자동검증, 제품군별 template 확장 |
| ARGuidePlan | 판단 결과와 AR step 연결 | 구현됨 / 고도화 필요 | RAG 근거, 안전 차단 사유, part map version, language output, step confidence 포함 |
| Part Map | reference image 정규화 좌표 | 구현됨 / 고도화 필요 | 좌표 보정 UI, reference image별 version 관리, 오버레이 정확도 검수 로그 |
| Reference Image | open-cover filter reference 적용 | 구현됨 / 고도화 필요 | 제품군/모델별 reference asset 확장, clean reference와 annotated overlay 분리 관리 |
| AR Frontend | reference image 기반 overlay 화면 | 구현됨 / 고도화 필요 | mobile flow, step 완료/중단/해결 상태, A/S 연결 CTA, 근거 카드, 실제 카메라처럼 보이는 시연 polish |
| Chatbot UI | 단일 입력 기반 챗봇 패널 | 구현됨 / 고도화 필요 | multi-turn 대화, 추가 질문, RAG 근거 카드, 안전 차단 문구, 언어 선택 반영 |
| ChatbotEngine | 없음 | 미구현 / 개발 필요 | 문의 slot 추출, 추가 질문, 대화 상태 관리, 최종 판단 호출 흐름 구현 |
| LLMService | 없음 | 미구현 / 개발 필요 | 개발 단계 mock 우선, 최종 API 교체 가능 구조, 고객 응답/요약/번역 역할 분리 |
| RAG 데이터 구축 | 공식자료 chunk 1,890개 / embedding 1,890개 | 수행됨 / 실패 케이스 보정 후 재검증 통과 | FastAPI 전환 후 repository/API 검색 결과가 동일한지 회귀 검증 필요 |
| Embedding/Vector DB | `official_document_embeddings`, JSONL vector index | 수행됨 / 1,890개 chunk와 embedding 연결 완료 | PostgreSQL + pgvector 전환 시 동일 top-k 결과 검증 필요 |
| RAGService | RAGService v2, metadata strict filter, vector similarity, lexical fallback | 구현됨 / 40개 query 재검증 통과 | FastAPI endpoint, 로그 저장, API 오류 응답 표준화 필요 |
| 다국어 / TTS | 영어 중심 AR step TTS 메타데이터, Web Speech fallback, Google Cloud TTS 직접 합성 endpoint, Supabase Storage 우선 `audio_url` 생성 및 runtime cache fallback | Render live 검증 완료 | 힌디어/지역어 음성 정책, 언어 선택 UI, 비용/캐시 운영 기준 보완 필요 |
| 안전검증 | High Risk keyword 차단 | 구현됨 / 고도화 필요 | 금지 부품/금지 action rule, 전기/냉매/PCB/내부 분해 차단, 고객 문구와 내부 로그 분리 |
| QA | 일부 API/브라우저 수동 확인 | 검증 필요 | 정상 관리, 모호한 문의, Medium Risk, High Risk, 매칭 실패, 좌표 오차 시나리오 테스트 작성 |
| 발표 산출물 | 로드맵/개발계획/README | 초안 작성 / 고도화 필요 | 아키텍처 다이어그램, 시연 시나리오, 최종 흐름 캡처, 제한사항/향후 확장 정리 |

## 3. ThinQ Mock 데이터 고도화 필요

현재 mock ThinQ 데이터는 흐름 검증용 최소 샘플이다.

최종 산출물 관점에서는 현재 데이터만으로 고도화가 불가능하므로, 아래 데이터 확장이 필요하다.

| 데이터 | 현재 수준 | 고도화 필요 |
|---|---|---|
| 고객 프로필 | 4명 수준 | 지역, 언어, 선호 UI, 사용 숙련도, 서비스 이력 다양화 |
| 등록 제품 | 4개 제품군 샘플 | 에어컨/세탁기/공청기/정수기별 모델, alias, series, structure_type 확장 |
| 사용 로그 | 제품당 1개 대표 로그 | 정상/주의/관리지연/과사용/장기미사용 등 상태별 로그 케이스 추가 |
| 스마트 진단 | low 위주 + high 샘플 1개 | Low/Medium/High severity별 result_code, detected_signals 확장 |
| 환경 데이터 | 4개 지역 샘플 | 고온다습, 건조, 경수, 대기질 악화, 몬순 등 조합 케이스 추가 |
| 공식자료 | strict matching 검증용 샘플 | 모델별 manual/FAQ/support page/image/chunk 데이터 확장 |
| 문의 문장 | 코드 내 demo 2개 중심 | 관리/자가점검/모호/High Risk/오타/다국어 질의 세트 구축 |

이 데이터 확장은 단순 “샘플 추가”가 아니라, intent/risk 판단 정확도를 검증하기 위한 테스트셋 역할을 해야 한다.

15-2-A 수행 결과:

| 데이터 | 확장 전 | 확장 후 |
|---|---:|---:|
| 고객 프로필 | 4 | 20 |
| 등록 제품 | 4 | 24 |
| 사용 로그 | 4 | 24 |
| 스마트 진단 | 5 | 36 |
| 환경 데이터 | 4 | 12 |

15-2-A 확장으로 제품군별 6개 등록 제품, 스마트 진단 none/low/medium/high 분포, 인도 12개 지역 환경 mock이 들어갔다.

단, 15-2-A는 작동 검증용 1차 확장이다. 최종 발표/제출 안정권에는 부족하므로 15-2-B 확장이 필요하다.

15-2-B 안정권 기준:

| 데이터 | 안정권 기준 |
|---|---:|
| 고객 프로필 | 120명 이상 |
| 등록 제품 | 240개 이상 |
| 사용 로그 | 720건 이상 |
| 스마트 진단 | 480건 이상 |
| 환경 데이터 | 50지역 이상 + 관측 row 300건 이상 |
| raw VOC cases | 300건 이상 |
| official_assets | 80건 이상 |
| official_document_chunks | 1,890개 공식자료 chunk 구축됨. RAGService v2 실패 케이스 보정 후 검색 품질 재검증 40/40 통과 |

추가 조건:

- 제품군별 air_conditioner / washing_machine / air_purifier / water_purifier 균형 유지
- 영어/힌디어/지역어 사용자 케이스 포함
- none/low/medium/high 진단 severity 균형 유지
- 고온다습, 건조, 경수, AQI 악화, 몬순, 해안/내륙 지역 케이스 포함
- 각 케이스에 실제 인도 사용자 고충 기반 `scenario_basis`, `pain_tags`, `evidence_level` 기록
- `mock://official` 형태의 가짜 공식자료는 최종 기준에서 사용 금지
- 환경 데이터는 실제 API/통계 source_url/source_api/source_date를 기록

15-2-B 실제 근거 기반 재구축 결과:

| 데이터 | 안정권 기준 | 현재 건수 | 판정 |
|---|---:|---:|---|
| 고객 프로필 | 120명 이상 | 120 | 기준 충족 |
| 등록 제품 | 240개 이상 | 240 | 기준 충족 |
| 사용 로그 | 720건 이상 | 720 | 기준 충족 |
| 스마트 진단 | 480건 이상 | 480 | 기준 충족 |
| 환경 데이터 | 50지역 이상 + 관측 row 300건 이상 | 50지역 + 350 row | 기준 충족 |
| raw VOC cases | 300건 이상 | 500 | 기준 충족 |
| official_assets | 80건 이상 | 791 | 기준 충족 |
| official_document_chunks | 공식자료 corpus 확장 수행됨 | 1,890 | LG India 공식 PDF(Owner's Manual/Spec/Dimension 포함)/Online Manual/Help Library/AS-Q24ENXE 검색 support 근거 포함. 1,890개 embedding까지 생성됨 |
| intent/risk 테스트셋 | 현 단계 미수행 | 0 | 다음 단계 |
| intent/risk 평가결과 | 정확도 측정 필요 | 0 | 미측정 |

검증된 coverage:

| 데이터 | air_conditioner | washing_machine | air_purifier | water_purifier |
|---|---:|---:|---:|---:|
| 등록 제품 | 60 | 60 | 60 | 60 |
| 사용 로그 | 180 | 180 | 180 | 180 |
| 스마트 진단 | 120 | 120 | 120 | 120 |
| intent/risk 테스트셋 | 0 | 0 | 0 | 0 |
| 공식자료 asset | 47 | 47 | 16 | 36 |
| 공식문서 chunk | 487 | 407 | 132 | 294 |

공식자료는 `https://www.lg.com/in/` LG India 공식 URL만 수집했고, raw HTML 원본은 `02_데이터연동/source_data/official_lg_india/raw/`에 저장했다.

DB/데이터 게이트 전체 기준으로는 실제 VOC/환경/공식자료 수집 파이프라인과 ThinQ mock 수량/coverage는 충족했다. RAGService v2 검색 품질 검증은 실패 케이스 보정 후 40개 query 모두 통과했다. 단, 15-3 intent/risk 평가셋 구축과 평가 실행은 아직 수행하지 않았다.

## 4. 현재 Intent 분류 한계

현재 intent 분류는 학습 모델이 아니다.

`ai_decision_engine.py` 기준 현재 방식:

```text
1. High Risk keyword 포함 → high_risk
2. Care keyword 포함 → care
3. 스마트 진단 severity가 medium/high → self_check
4. usage_log에 care_triggers 존재 → care
5. 그 외 → self_check
```

따라서 현재 `confidence` 값은 실제 모델 정확도가 아니라 rule 우선순위에 따라 임시 부여한 값이다.

최종 기준에서는 아래가 필요하다.

| 항목 | 고도화 필요 |
|---|---|
| intent label set | care / self_check / high_risk / ambiguous / service_request 등으로 확장 |
| 평가 데이터셋 | 문의 문장별 정답 intent/risk label 구축 |
| 정확도 측정 | accuracy, precision, recall, confusion matrix 산출 |
| 모호한 문의 처리 | 추가 질문으로 slot 채우기 |
| LLM 보조 | 자연어 요약, 증상 추출, 오타/다국어 질의 정규화 |
| RAG 보조 | 공식문서 근거가 있는 절차만 AR Guide로 연결 |

## 5. 현재 Low / Medium / High 판단 방식

현재 위험도 판단도 학습이 아니라 rule 기반이다.

`ai_decision_engine.py` 기준 현재 방식:

```text
High:
  - 문의 문장 또는 스마트 진단 detected_signals에 High Risk keyword 포함
  - 또는 smart_diagnosis.severity == "high"

Medium:
  - 문의 문장 또는 detected_signals에 Medium Risk keyword 포함
  - 또는 smart_diagnosis.severity == "medium"

Unknown:
  - 공식자료 strict matching 실패

Low:
  - High/Medium/Unknown에 해당하지 않고
  - 공식자료 strict matching이 verified인 경우
```

현재 문제:

| 문제 | 설명 |
|---|---|
| 학습 없음 | 실제 문의 데이터로 학습하거나 평가하지 않음 |
| keyword 누락 취약 | 사용자가 다른 표현을 쓰면 놓칠 수 있음 |
| false positive 가능 | 단어 하나 때문에 과차단될 수 있음 |
| Medium 정책 부족 | Medium에서 어떤 AR step까지만 허용할지 세분화 부족 |
| 진단 로그 부족 | 스마트 진단 result_code와 detected_signals 샘플이 부족함 |
| 근거 부족 | 왜 Low/Medium/High인지 고객/관리자에게 보여줄 근거 구조 부족 |

최종 기준에서는 rule을 유지하더라도, rule은 안전장치로 두고 LLM/RAG/진단로그 기반 판단엔진 v2가 필요하다.

## 6. 우선 고도화 순서

1. DB에 `chat_sessions`, `chat_messages`, `official_document_chunks` 추가 - 15-1 수행됨
2. ThinQ mock 데이터 1차 확장 - 15-2-A 수행됨 / 이전 기준 미충족 기록
3. ThinQ mock 데이터 최종 발표 안정권 확장 - 15-2-B 실제 근거 기반 재구축 수행됨
4. intent/risk 평가용 문의 테스트셋 확대 - 15-3 미수행 / 평가 기준 확정 후 진행
5. official_document_chunks 제품군/절차별 확대 - RAG 데이터 구축 고도화 및 AS-Q24ENXE support/FAQ 누락분 추가 수집 수행됨 / chunk 1,890건
6. 공식 PDF/FAQ/Help Library corpus 확장 - 수행됨 / 검증 리포트 생성됨
7. Embedding/Vector DB 구축 - 수행됨 / 1,890개 embedding 생성
8. RAGService v2 구현 - 수행됨 / vector similarity + metadata strict filter 적용
9. RAGService v2 검색 품질 확대 검증 - 수행됨 / 최초 40개 query 중 37개 통과, 3개 실패 확인
10. RAGService v2 실패 케이스 보정 - 수행됨 / 재검증 40개 query 통과
11. FastAPI 백엔드 구조 전환 - 지금 다음 작업
12. SQLAlchemy 또는 SQLModel repository 계층 작성
13. DB/데이터 게이트 검증
14. `ChatbotEngine` 구현
15. `ConversationState` 구현
16. `LLMServiceMock` 구현
17. `RAGService` API 연결 회귀 검증
11. AI 판단엔진 v2 구현
12. `/chat/messages`를 multi-turn 구조로 변경
13. 프론트 챗봇 UI를 추가 질문/근거 카드 구조로 변경
14. 안전검증 로그와 High Risk 차단 근거 저장
15. 정상/모호/Medium/High Risk 시나리오 검증

ChatbotEngine은 15-2-B, 15-3, 15-4가 끝난 뒤 진행한다. ThinQ mock 안정권 확장은 서비스 맥락 데이터이고, 평가셋은 분류 정확도 검증용이며, 공식문서 chunk는 RAG 근거 검색용이므로 서로 다른 작업이다.

## 7. 현재 기준 결론

현재 산출물은 최종 서비스의 골격을 보여주는 1차 구현 상태다.

다만 최종 산출물로 제출하려면 단순 rule 기반 판단이 아니라, 다음 구조가 반드시 연결되어야 한다.

```text
ChatbotEngine
→ ConversationState
→ LLMServiceMock
→ RAGService
→ AI 판단엔진 v2
→ ARGuidePlan
→ AR overlay session
→ 안전/근거/세션 로그
```

따라서 앞으로 작업 로그와 개발 문서에서는 최종 기준 검수가 끝나기 전까지 `완료` 대신 `구현됨 / 고도화 필요`, `초안 작성 / 고도화 필요`, `미구현 / 개발 필요`를 사용한다.

