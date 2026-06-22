# Chat Korean-to-English Copy Update

Date: 2026-06-22

## Summary

Chat에서 사용자에게 노출되던 한국어 안내 문구를 영어 문구로 정리했다. 한국어 입력을 인식하기 위한 내부 키워드는 유지하고, 화면에 표시되는 bot message/fallback response만 영어로 고정했다.

Scope is the backend chat response path, including `/api/v1/chat/messages`, the frontend-compatible `/api/ai/chat` response mapper, and the LLM mock fallback copy used by chat.

## Changed Copy

| Area | Before | After |
| --- | --- | --- |
| Symptom clarification | 어떤 문제가 있나요? 냉방/바람, 소음/진동, 냄새, 물샘, 전원 문제, 필터 관리 중 가까운 증상을 알려주세요. | What issue are you experiencing? Please choose the closest symptom: cooling or airflow, noise or vibration, odor, water leak, power issue, or filter care. |
| LLM fallback translation | 안전한 안내를 위해 증상을 한 가지 더 알려주세요. | Please share one more detail before I guide you. |
| LLM fallback translation | 문의는 확인했지만, 안전하게 제공할 공식 가이드 옵션이 아직 준비되지 않았습니다. | I checked the request, but safe official guide options are not ready yet. |
| High-risk guidance | 위험 신호일 수 있습니다. 제품 사용을 중단하고 공식 A/S로 연결하세요. AR 자가 안내는 차단됩니다. | This may be high risk. Stop using the appliance and connect to official A/S. AR self-guidance is blocked. |
| External safe-check guidance | 외부에서 확인 가능한 안전 점검만 허용됩니다. 커버, 배선, PCB, 컴프레서, 냉매 부품은 열거나 만지지 마세요. | Only external safe-check steps are allowed. Do not open covers, wiring, PCB, compressor, or refrigerant parts. |
| Official-evidence guidance | 공식 근거가 있고 사용자가 접근 가능한 단계만 안내할 수 있습니다. | Only user-accessible steps backed by official evidence are allowed. |
| Official guide ready fallback | 공식 가이드 옵션이 준비되었습니다. 안전 규칙과 공식 근거가 허용한 단계만 안내합니다. | Original English guide-ready message is now preserved. |
| Noise/vibration location clarification | 소음이나 진동이 어디에서 느껴지나요? 실내기 본체, 송풍구, 앞 커버, 배수부, 전원부 중 가까운 위치를 알려주세요. | Where do you notice the noise or vibration? Please choose the closest area, such as the indoor unit body, air outlet, front cover, drain area, or power area. |
| Weak cooling clarification | 냉방이 잘 안 되는 상황을 조금 더 알려주세요. 바람은 나오는지, 바람이 약한지, 송풍구 쪽 문제인지 알려주세요. | Please tell me more about the weak cooling condition. Is air coming out, is the airflow weak, or does it seem related to the air outlet? |

## Implementation Notes

- `backend/app/chatbot_engine.py`
  - Missing `symptom_type` clarification question now returns English copy.
  - Korean keyword matching remains in place for Korean user inputs such as "아니요", "연기", "타는 냄새".

- `backend/app/llm_service.py`
  - Removed Korean translation fallback for chat-facing safety copy.
  - `translate(...)` now returns the original English text.

- `backend/app/routers/frontend_compat.py`
  - Existing visible chat response mapping is kept in English for clarification, risk blocking, and guide-ready states.

- `frontend/src/app/pages/Chat.tsx`
  - Updated chat localStorage key to `chat_messages_v20260622_english_v4`.
  - Added previous English migration keys to legacy cleanup so old Korean bot messages are not reused.
  - Added a legacy Korean chat-copy normalizer for saved chat bubbles and stale backend responses.

- `frontend/src/app/pages/ARGuide.tsx`
  - Updated the shared chat storage key used when returning from AR Guide.

- Tests updated:
  - `backend/tests/test_conversation_state_multiturn.py`
  - `backend/tests/test_frontend_compat_api.py`

## Verification

- `python -m pytest -q --tb=short tests/test_backend_english_response_policy.py tests/test_conversation_state_multiturn.py tests/test_frontend_compat_api.py`
  - Result: 33 passed.
- `npm.cmd run build`
  - Result: build passed.

## Notes

- Korean user input remains supported through keyword matching.
- Backend-visible chat output is expected to remain English even when users type Korean messages such as "아니요" or "필터 청소 방법 알려줘".
- Previously saved Korean bot bubbles such as "공식 근거에 맞는 필터 청소 안내를 준비했어요..." and "연기, 스파크..." are normalized to English on the chat page.
- Legacy clarification bubbles for noise/vibration location and weak cooling details are also normalized to English.
