# 28번 통합 시나리오 QA 리포트 - 2026-06-15

- run_id: `SCENARIO_28_FULL_20260615`
- generated_at: `2026-06-15T18:20:44.304690+09:00`
- isolated_db_path: `C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\02_데이터연동\eval_sets\scenario_validation_20260615.sqlite`
- total/pass/fail: 7 / 7 / 0
- status: `passed`

## 시나리오 결과

| ID | 분류 | 결과 | 주요 관측 |
| --- | --- | --- | --- |
| `preventive_alert` | self_care_alert | passed | {"status_code": 200, "score": 65.0, "risk_level": "medium", "trigger_reason_count": 2, "manual_count": 1, "youtube_count": 3, "ar_count": 1} |
| `normal_management` | self_care_chat | passed | {"status_code": 200, "message": "공식 근거에 맞는 필터 청소 안내를 준비했어요. 안전 규칙상 허용되는 단계만 보여드릴게요.", "service_flow_type": "self_care", "risk_level": "low", "procedure_type": "filter_cleaning", "card_type": "ar_start", "show_manual_b... |
| `ambiguous_clarification` | clarification | passed | {"status_code": 200, "message": "어떤 문제가 있나요? 냉방/바람, 소음/진동, 냄새, 물샘, 전원 문제, 필터 관리 중 가까운 증상을 알려주세요.", "needs_clarification": true, "missing_slots": ["symptom_type"], "procedure_type": null, "guide_options_present": false... |
| `medium_self_as_cooling` | self_as_chat | passed | {"first": {"status_code": 200, "message": "연기, 스파크, 타는 냄새, 감전, 냉매/가스 냄새 같은 위험 신호가 있나요? 없다면 '아니요'라고 답해주세요.", "missing_slots": ["risk_signal", "symptom_location", "environment_context"], "procedure_type": "no_cooling_se... |
| `high_risk_service_route` | expert_as | passed | {"status_code": 200, "message": "위험 신호가 있어 AR 자가 안내는 차단했어요. 공식 A/S 또는 서비스센터 연결을 권장합니다.", "service_flow_type": "expert_as", "risk_level": "high", "card_type": "service_route", "show_service_button": true, "show_ar_butt... |
| `official_no_match_policy` | no_match | passed | {"message": "Official guide options are not ready.", "recommended_action": "official_match_review_needed", "card_type": "safety_block", "card_title": "공식자료 확인 불가", "show_ar_button": false, "show_manual_button": false,... |
| `save_and_rewatch` | history | passed | {"complete_status": 200, "history_status": 200, "history_count": 1, "ar_session_create_status": 201, "ar_session_id": "ARS_20260615092044157306", "completed_steps": ["2_STEP_01", "2_STEP_02"], "ar_session_update_statu... |

## 실패/보정 대상

- 자동 검증 기준 실패 없음.

## 화면 캡처

- `C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\06_산출물\scenario_screenshots_20260615\01_home_authenticated.png`
- `C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\06_산출물\scenario_screenshots_20260615\02_chat_authenticated.png`
- `C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\06_산출물\scenario_screenshots_20260615\03_ar_guide_authenticated.png`

## 검증 범위

- `/api/ai/chat` 프론트 호환 챗봇 응답과 card_policy 확인
- `/api/v1/chat/messages`가 감싸는 ChatbotEngine/DecisionEngine 흐름은 프론트 호환 API를 통해 간접 검증
- `/api/v1/care/risk/evaluate` 예방 알림/Care Risk/guide option 확인
- `/api/v1/ar/plans`, `/api/v1/ar/sessions`, `/api/v1/guides/{guide_id}/complete`, `/api/v1/devices/{device_id}/care-history` 저장/재시청 흐름 확인
- 공식근거 no-match는 현재 seed 평가셋에 expected no-match row가 없어 프론트 card_policy mapping 단위로 검증
