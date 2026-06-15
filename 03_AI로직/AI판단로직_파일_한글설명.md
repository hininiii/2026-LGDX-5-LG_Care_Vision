# AI 판단로직 파일 한글 설명

작성일: 2026-06-03

## 1. 현재 AI 로직 상태

현재 AI 판단엔진은 학습 모델이 아니다.

현재 상태:

```text
rule 기반 1차 판단엔진
1차 구현 흐름 검증 가능
최종 기준으로는 고도화 필요
```

즉, 지금 단계에서는 키워드, 스마트 진단 severity, 공식자료 매칭 여부를 조합해서 판단한다.

## 2. `rules/ai_decision_engine.py`

역할:

```text
사용자 문의
+ ThinQ mock 제품 정보
+ 사용 로그
+ 스마트 진단
+ 인도 환경 context
+ 공식자료 strict matching
→ intent / risk / action 판단
```

판단 흐름:

```text
1. 사용자/제품/로그/진단/환경 조회
2. LG India 공식자료 strict matching
3. 문의 intent 분류
4. Low / Medium / High / Unknown 위험도 판단
5. 절차 유형 결정
6. 기존 관리 콘텐츠 재사용 가능 여부 확인
7. DecisionResult 생성
8. 챗봇 응답 상태 생성
```

현재 intent 분류:

| intent | 의미 |
|---|---|
| `care` | 청소/관리 문의 |
| `self_check` | 사용자가 직접 확인 가능한 자가점검 문의 |
| `high_risk` | 감전, 스파크, 냉매, 배선, 내부 분해 등 위험 문의 |

현재 위험도 판단:

| risk | 현재 기준 |
|---|---|
| `low` | 공식자료 매칭 성공 + 사용자 접근 가능한 관리/점검 |
| `medium` | 누수, 내부, 소음, 냉방 불량, error 등 주의 신호 |
| `high` | 스파크, 연기, 감전, 냉매, 배선, PCB, compressor 등 위험 신호 |
| `unknown` | 공식자료 strict matching 실패 |

한계:

- 실제 LLM 학습 모델 아님
- 분류 정확도 아직 미측정
- 240건 테스트셋으로 평가 실행 필요
- RAG 공식근거와 결합한 AI 판단엔진 v2 필요

## 3. `rules/ar_guide_template_selector.py`

역할:

```text
DecisionResult
+ 공식자료 매칭 결과
+ 제품군
+ procedure_type
→ ARGuidePlan 생성
```

주요 기능:

| 기능 | 설명 |
|---|---|
| AR 허용 여부 확인 | High Risk, Unknown, 공식자료 미매칭이면 AR 차단 |
| 템플릿 선택 | 제품군 + 절차 유형에 맞는 AR Guide Template 선택 |
| 위험도 ceiling 확인 | 템플릿이 허용하는 risk 범위 확인 |
| ARGuidePlan 생성 | step, target part, highlight, 금지 action 포함 |

## 4. `ar_guide_templates/*.json`

역할:

```text
제품군/절차별 AR 안내 템플릿
```

예시:

| 파일 | 의미 |
|---|---|
| `aircon_filter_cleaning_v1.json` | 에어컨 필터 청소 AR Guide Template |
| `washing_machine_tub_clean_v1.json` | 세탁기 통세척 AR Guide Template |
| `air_purifier_filter_replacement_v1.json` | 공기청정기 필터 교체 AR Guide Template |
| `water_purifier_limescale_care_v1.json` | 정수기 석회질 관리 AR Guide Template |

주의:

템플릿 JSON은 코드에서 읽는 실행 데이터라 영어 파일명을 유지한다.
대신 이 설명서에서 한글 의미를 관리한다.
