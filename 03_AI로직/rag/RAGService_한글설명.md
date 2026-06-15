# RAGService 한글 설명

작성일: 2026-06-04

## 1. 목적

`rag_service.py`는 고객 문의, 제품군, 모델명, 절차 타입을 기준으로 LG India 공식자료 chunk에서 AR Guide에 사용할 수 있는 공식근거 passage를 검색하는 서비스 계층이다.

## 2. 현재 구현 상태

현재 구현은 `RAGService v2`다.

| 항목 | 구현 상태 |
|---|---|
| metadata strict filter | 구현됨 |
| vector similarity search | 구현됨 |
| lexical fallback | 구현됨 |
| official_assets strict matching 우선순위 | score bonus로 반영 |
| no-match 시 ARGuidePlan 차단 | `ar_guide_blocked=True` 반환 |
| 검색 로그 저장 | `rag_search_logs` 저장 |
| API 연결 | `/rag/search`, `/chat/messages` 연결 |

## 3. 공식자료 허용 도메인

검색 대상은 공식자료로 확인된 아래 도메인만 허용한다.

```text
https://www.lg.com/in/
https://gscs-manual.lge.com/
```

`gscs-manual.lge.com`은 LG Online Manual 원본 도메인이므로 embedding과 RAG 검색 대상에 포함한다.

## 4. Embedding 모델

| 항목 | 값 |
|---|---|
| 모델명 | `careshot_local_hashing_v1` |
| 차원 | 512 |
| 방식 | 단어/바이그램/문자 n-gram deterministic hashing embedding |
| 비용 | 로컬 실행, API 비용 없음 |

개발 단계에서는 API 비용 없이 재현 가능한 로컬 embedding을 사용한다. 운영 단계에서는 같은 DB 구조를 유지하고 OpenAI embeddings 또는 다국어 sentence-transformer 계열 모델로 교체할 수 있다.

## 5. 검색 순서

```text
사용자 query
→ metadata strict filter
→ vector similarity search
→ 결과가 없으면 같은 strict filter 안에서 lexical fallback
→ 결과가 없으면 ar_guide_blocked=True
```

절차 타입이 주어졌을 때는 `procedure_type`을 느슨하게 풀지 않는다. 공식근거가 없는 절차에 대해 ARGuidePlan을 생성하지 않기 위해서다.

## 6. 반환 핵심 필드

| 필드 | 의미 |
|---|---|
| `retrieval_mode` | vector 검색 / lexical fallback / no-match 구분 |
| `result_count` | 공식근거 검색 결과 수 |
| `results[].chunk_id` | 근거 chunk id |
| `results[].asset_id` | 공식자료 asset id |
| `results[].source_url` | 공식자료 URL |
| `results[].source_section` | 원문 추출 구간 |
| `results[].vector_score` | query와 chunk의 vector similarity |
| `results[].match_reason` | 절차 일치, 모델 일치, asset 우선순위 여부 |
| `ar_guide_blocked` | 근거 없음으로 AR Guide 차단 여부 |

## 7. 검증 산출물

```text
06_산출물/Embedding_VectorDB_검증리포트_2026-06-04.md
06_산출물/RAGService_v2_Vector검색검증리포트_2026-06-04.md
```

기본 검증 결과는 5개 케이스 통과다. 최종 품질 검증에서는 더 많은 query set으로 top-k 근거 정확도와 no-match 차단 품질을 검증해야 한다.
