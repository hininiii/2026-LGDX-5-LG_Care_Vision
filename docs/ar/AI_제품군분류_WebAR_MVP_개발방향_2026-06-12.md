# CareShot AI 제품군 분류 + Web Image Tracking AR MVP 개발 방향

작성일: 2026-06-12

## 1. 최종 방향

CareShot AR MVP는 단순히 정적인 제품 이미지 위에 안내 박스를 올리는 화면이 아니라, 모바일 브라우저 카메라에서 제품을 비추면 먼저 AI 이미지 분류 모델이 제품군을 판별하고, 지원 대상이면 Web Image Tracking AR로 reference image를 인식한 뒤 공식자료 기반 필터 청소 가이드를 표시하는 구조로 개발한다.

최종 표현은 다음과 같이 정리한다.

```text
AI Product Classification + Web Image Tracking AR MVP
```

발표용 설명:

```text
CareShot AR은 사용자가 모바일 카메라로 에어컨을 비추면
AI 이미지 분류 모델이 벽걸이형, 스탠드형, 창문형, 비에어컨 여부를 먼저 판단하고,
지원 가능한 제품군에 대해 공식 reference image target을 추적하여
필터 청소 위치와 단계별 안내 overlay를 표시하는 웹 기반 AR MVP이다.
```

## 2. 핵심 원칙

AI 이미지 분류 모델은 제품군 인식 보조 역할만 수행한다.

AI가 최종으로 AR 허용 여부, 안전 여부, 자가조치 가능 여부를 결정하지 않는다. 최종 AR 표시 여부는 기존 백엔드의 Safety Rule, DecisionEngineV2, 공식자료 match, High Risk 차단, guide/template availability 기준으로 결정한다.

정리하면 역할은 다음과 같다.

| 구성 | 역할 | 최종 판단 권한 |
|---|---|---|
| AI Product Classifier | 카메라 화면 속 제품군 분류 | 없음 |
| MindAR Image Tracking | 등록된 reference image target 인식 및 tracking | 없음 |
| Part Map | reference image 기준 부품 좌표 제공 | 없음 |
| AR Guide Template | 절차별 안내 단계 제공 | 없음 |
| DecisionEngineV2 / Safety Rule | 위험도, 공식근거, AR 허용 여부 판단 | 있음 |

## 3. 지원 제품군 범위

MVP 분류 클래스는 다음 4개로 구성한다.

| Class | 의미 | MVP 처리 |
|---|---|---|
| `wall_split_ac` | 벽걸이형 / split AC | AR 지원 |
| `floor_standing_ac` | 스탠드형 / floor standing AC | AR 지원 |
| `window_ac` | 창문형 AC | 인식은 하지만 미지원 또는 제한 안내 |
| `not_ac` | 에어컨이 아닌 배경/가전/사물 | 재촬영 안내 |

벽걸이형과 스탠드형은 MVP AR 지원 대상으로 둔다. 단, 두 제품군은 구조가 다르므로 각각 별도의 reference image target, part map, AR guide template이 필요하다.

창문형은 분류 모델에는 포함하지만, 1차 MVP에서는 AR 가이드를 제공하지 않는다. 사용자가 창문형으로 분류된 제품을 비추면 다음과 같은 안내를 제공한다.

```text
창문형 에어컨으로 인식되었습니다.
현재 AR 필터 청소 가이드는 벽걸이형/스탠드형 에어컨을 우선 지원합니다.
공식 관리 문서 또는 고객센터 연결로 안내합니다.
```

## 4. 수집 데이터셋

AI 제품군 분류 모델을 위한 LG 공식 이미지 데이터셋은 다음 위치에 수집했다.

```text
04_AR가이드/ai_product_classifier_dataset/
```

수집 결과:

| Class | Count |
|---|---:|
| `wall_split_ac` | 100 |
| `floor_standing_ac` | 70 |
| `window_ac` | 43 |
| `not_ac` | 65 |

이미지 합계: 278장

공식 매뉴얼/필터 청소 근거 문서: 4건

주요 파일:

```text
official_image_manifest.json
official_manual_manifest.json
collection_summary.json
collection_errors.json
raw/<class>/
raw/manuals/
```

이미지 파일은 다운로드 후 헤더 검증을 수행했고, 최종 검증 결과는 다음과 같다.

```text
bad_image_header_count = 0
```

주의:

```text
수집 이미지는 LG 공식 웹사이트 기반 발표/개발용 데이터셋이다.
외부 공개, 재배포, 패키징 전에는 라이선스와 재배포 가능 여부를 별도로 확인해야 한다.
```

## 5. 전체 실행 흐름

AR 화면의 시간순 처리 흐름은 다음과 같다.

```text
1. 사용자가 AR 화면에 진입한다.
2. 프론트엔드가 카메라 권한을 요청한다.
3. ProductClassifierService가 AI 이미지 분류 모델을 로드한다.
4. 카메라 프레임을 일정 주기로 캡처한다.
5. AI 모델이 wall_split_ac / floor_standing_ac / window_ac / not_ac를 분류한다.
6. confidence가 기준값 이상인지 확인한다.
7. 지원 대상이면 백엔드에 AR guide 가능 여부를 확인한다.
8. 백엔드는 DecisionEngineV2, safety rule, official match, RAG 근거, guide template 여부를 확인한다.
9. AR 허용이면 제품군에 맞는 MindAR target과 part map을 로드한다.
10. MindAR가 카메라 화면에서 reference image target을 추적한다.
11. target tracking이 성공하면 AR overlay를 표시한다.
12. 사용자는 단계별 필터 청소/분리 안내를 진행한다.
13. 단계 진행, 완료, 중단 로그를 저장한다.
```

## 6. 프론트엔드 모듈 구조

프론트엔드는 기존 화면과 별도로 `web-ar-mvp` 흐름을 두는 것이 좋다.

권장 위치:

```text
05_프론트엔드/web-ar-mvp/
```

권장 모듈:

```text
ProductClassifierService
- TensorFlow.js 또는 Teachable Machine export model 로드
- 카메라 frame classification
- class/confidence 반환

ARSessionController
- 카메라 권한 상태 관리
- classifier 결과와 backend guide 가능 여부 연결
- MindAR scene 시작/중지

MindARTargetLoader
- 제품군/모델에 맞는 .mind target 로드
- wall_split_ac target, floor_standing_ac target 분리

GuideOverlayRenderer
- part map 좌표를 overlay로 변환
- highlight box, arrow, step label 표시

GuideStepController
- 이전/다음 단계 이동
- 완료/중단 처리
- backend log 호출
```

## 7. 백엔드 연동 흐름

프론트 AI 분류 결과는 백엔드에 다음 형태로 전달한다.

```json
{
  "session_id": "AR_SESSION_001",
  "user_id": "USER_001",
  "product_family": "air_conditioner",
  "detected_type": "wall_split_ac",
  "confidence": 0.86,
  "classifier_model": "teachable_machine_tfjs_v1",
  "requested_procedure_type": "filter_cleaning"
}
```

백엔드는 이 값을 신뢰해서 바로 AR을 띄우지 않는다.

백엔드 확인 순서:

```text
1. user/product/session context 확인
2. detected_type이 지원 제품군인지 확인
3. 문의/시나리오의 service_flow_type 확인
4. High Risk 여부 확인
5. 공식자료 match 여부 확인
6. RAG 근거 존재 여부 확인
7. 해당 제품군/절차의 AR guide template 존재 여부 확인
8. reference image / part map 존재 여부 확인
9. AR 허용 또는 차단 응답 반환
```

응답 예시:

```json
{
  "ar_allowed": true,
  "detected_type": "wall_split_ac",
  "procedure_type": "filter_cleaning",
  "reference_image_id": "REF_WALL_SPLIT_AC_US_Q19BNZE_FRONT_OPEN",
  "mindar_target_path": "/assets/mind/wall_split_ac_us_q19bnze.mind",
  "part_map_version_id": "PMV_WALL_SPLIT_FILTER_V1",
  "guide_template_id": "ARG_WALL_SPLIT_FILTER_CLEANING_V1",
  "safety_message": "전원을 끄고 필터 청소를 진행하세요."
}
```

차단 응답 예시:

```json
{
  "ar_allowed": false,
  "detected_type": "window_ac",
  "blocked_reason": "unsupported_product_type",
  "fallback_action": "show_official_document"
}
```

## 8. 제품군별 AR 가이드 구성

### 8.1 wall_split_ac

벽걸이형은 1차 고정밀 시연 대상으로 둔다.

필요 asset:

```text
front_closed reference image
front_open reference image
side_open reference image
MindAR target
filter area part map
front panel part map
air outlet/louver part map
filter cleaning guide template
```

주요 절차:

```text
1. 전원 차단 안내
2. 전면 패널 위치 highlight
3. 패널 열기 방향 arrow
4. 필터 위치 highlight
5. 필터 분리 방향 arrow
6. 진공청소기/부드러운 브러시/물세척 안내
7. 그늘 건조 안내
8. 재장착 안내
```

### 8.2 floor_standing_ac

스탠드형도 MVP AR 지원 대상이지만, 벽걸이형과 구조가 다르므로 별도 guide가 필요하다.

필요 asset:

```text
front_closed reference image
front_filter_panel reference image
side reference image
MindAR target
filter cover part map
air inlet part map
filter handle/slot part map
floor-standing filter cleaning guide template
```

주요 절차:

```text
1. 전원 차단 안내
2. 필터 커버 위치 highlight
3. 커버 열기 또는 분리 방향 안내
4. 필터 위치 highlight
5. 필터 분리 방향 안내
6. 세척/건조/재장착 안내
```

주의:

```text
스탠드형은 모델별 필터 위치가 다를 수 있으므로
generic guide를 쓸 경우 반드시 공식자료 근거와 reference image 기준을 명확히 표시해야 한다.
```

### 8.3 window_ac

창문형은 제품군 인식 대상이지만 1차 MVP AR guide 지원 대상은 아니다.

처리:

```text
AI 분류: window_ac
AR guide: 차단 또는 준비중 안내
fallback: 공식 문서 / 일반 필터 관리 안내 / 고객센터 연결
```

### 8.4 not_ac

에어컨이 아닌 것으로 분류되면 AR을 시작하지 않는다.

처리:

```text
AI 분류: not_ac
AR guide: 차단
UI: 에어컨이 화면 중앙에 오도록 다시 비춰달라는 안내
```

## 9. AI 모델 개발 방식

발표용 MVP에서는 커스텀 객체탐지 모델보다 이미지 분류 모델을 우선한다.

이유:

```text
1. 라벨링 비용이 낮다.
2. bounding box annotation이 필요 없다.
3. Teachable Machine / TensorFlow.js export로 빠르게 웹에 붙일 수 있다.
4. 발표 목적의 제품군 구분에는 충분하다.
```

권장 방식:

```text
1. raw dataset 정리
2. train/test split 생성
3. Teachable Machine 또는 TensorFlow.js transfer learning 사용
4. 4-class image classifier 학습
5. model.json / weights export
6. web-ar-mvp에서 로드
7. 모바일 Chrome에서 실시간 분류 테스트
```

권장 confidence 기준:

```text
0.75 이상: 제품군 인식 성공
0.50 ~ 0.75: 추가 정렬 요청
0.50 미만: 인식 실패 / 재촬영 안내
```

단, confidence 기준은 실제 모바일 테스트 결과에 따라 조정한다.

## 10. MindAR 개발 방식

MindAR는 제품군을 분류하는 AI가 아니라, 등록된 reference image target을 카메라 화면에서 찾아 overlay 기준 좌표를 제공하는 역할이다.

제품군별 target은 분리한다.

```text
wall_split_ac target
floor_standing_ac target
```

target 생성 기준:

```text
1. 흰 배경의 단순 정면 이미지만 쓰면 tracking이 약할 수 있다.
2. 패널 경계, 로고, 내부 그릴, 필터 커버 등 특징점이 보이는 이미지를 우선한다.
3. 벽걸이형은 front_open 또는 side_open 이미지가 유리하다.
4. 스탠드형은 전면 패널/필터 커버 경계가 보이는 이미지를 우선한다.
5. 발표 fallback을 위해 reference image 출력물 또는 모니터 표시 이미지를 준비한다.
```

## 11. DB/데이터 연결 방향

최종 구조에서는 다음 데이터가 연결되어야 한다.

```text
PRODUCT
-> product_type
-> structure_type
-> OFFICIAL_ASSET
-> reference_image
-> AR_TARGET
-> part_map
-> AR_GUIDE
-> guide_steps
```

AI 분류 결과는 `detected_type` 또는 `structure_type_candidate`로 저장할 수 있다.

예시:

```json
{
  "detected_type": "wall_split_ac",
  "structure_type_candidate": "wall_mounted_split",
  "confidence": 0.86,
  "source": "product_classifier_v1"
}
```

단, 실제 guide 선택은 다음 순서를 따른다.

```text
1. ThinQ / USER_PRODUCT의 exact model match
2. exact model reference image
3. 같은 structure_type의 approved generic reference image
4. 없으면 AR 차단
```

AI 분류 결과는 exact model match를 대체하지 않는다.

## 12. 발표용 시연 시나리오

추천 시나리오:

```text
1. 사용자가 챗봇에 "에어컨 필터 청소 어떻게 해?"라고 입력한다.
2. ChatbotEngine이 self_care / filter_cleaning으로 분기한다.
3. DecisionEngineV2가 high risk가 아니고 공식자료 근거가 있음을 확인한다.
4. 사용자가 AR 가이드 시작 버튼을 누른다.
5. 모바일 브라우저가 카메라를 연다.
6. AI가 wall_split_ac 또는 floor_standing_ac를 인식한다.
7. 화면에 "AI detected: Wall-mounted Split AC / 86%"를 표시한다.
8. MindAR가 reference target을 인식한다.
9. 필터 위치 highlight와 분리 방향 arrow가 표시된다.
10. 사용자가 단계별 안내를 넘긴다.
11. 완료 로그가 저장된다.
```

fallback 시나리오:

```text
실제 에어컨이 없거나 tracking이 불안정하면
공식 reference image를 모니터에 띄우거나 출력물로 준비해 모바일 카메라로 인식시킨다.
```

## 13. 개발 순서

권장 작업 순서는 다음과 같다.

```text
1. AI 제품군 분류 데이터셋 train/test split 생성
2. 4-class classifier 학습
3. model.json / weights export
4. web-ar-mvp 폴더 생성
5. TensorFlow.js classifier 로더 구현
6. 카메라 frame classification UI 구현
7. wall_split_ac / floor_standing_ac / window_ac / not_ac 상태별 UI 구현
8. wall_split_ac MindAR target 생성
9. floor_standing_ac MindAR target 생성
10. wall_split_ac part map 작성
11. floor_standing_ac part map 작성
12. filter_cleaning guide step 연결
13. backend guide availability API 연결
14. AR session / step log 저장 연결
15. Android Chrome 실제 기기 검증
16. 발표용 fallback reference image 준비
```

## 14. 완료 기준

MVP 완료 기준:

```text
1. 모바일 브라우저에서 카메라 권한 요청이 정상 동작한다.
2. 카메라 화면에서 wall_split_ac / floor_standing_ac / window_ac / not_ac 분류 결과가 표시된다.
3. wall_split_ac와 floor_standing_ac는 AR 지원 대상으로 분기된다.
4. window_ac와 not_ac는 AR을 시작하지 않고 적절한 안내를 표시한다.
5. MindAR target 인식 성공 시 overlay가 reference image 위에 붙는다.
6. 필터 위치 highlight와 분리 방향 arrow가 표시된다.
7. 이전/다음 단계 이동이 가능하다.
8. High Risk 또는 공식자료 미확인 상태에서는 AR이 차단된다.
9. 시연용 reference image 출력물/모니터 fallback으로 안정적인 발표가 가능하다.
```

## 15. 이번 방향에서 바뀐 점

기존 방향:

```text
reference image 기반 static overlay 또는 image tracking AR
```

변경된 방향:

```text
AI 제품군 분류
-> 지원 제품군 gate
-> Web Image Tracking AR
-> 공식자료 기반 guide overlay
```

즉, AR 앞단에 발표용으로 설득력 있는 AI 인식 단계를 추가하되, 안전 판단과 AR 허용 판단은 기존 rule/RAG/DecisionEngineV2 구조를 유지한다.
