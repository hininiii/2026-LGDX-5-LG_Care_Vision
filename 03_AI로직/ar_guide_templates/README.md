# AR Guide Templates

작성일: 2026-06-02

이 폴더는 공식자료 매칭과 AI 판단 결과를 실제 `ARGuidePlan`으로 변환하기 위한 제품군/절차별 장면 template을 보관한다.

## Template 목록

- `aircon_filter_cleaning_v1.json`
- `washing_machine_tub_clean_v1.json`
- `air_purifier_filter_replacement_v1.json`
- `water_purifier_limescale_care_v1.json`

## 사용 흐름

```text
AI 판단 결과
-> product_type / procedure_type / risk_level / match_type 확인
-> template 선택
-> scene_steps를 ARGuidePlan.scenes로 변환
-> image/video/TTS/subtitle pipeline으로 전달
```

## 핵심 제약

- `allowed_match_scope`에 없는 공식자료 매칭 결과는 사용하지 않는다.
- `risk_ceiling`을 초과하는 위험도는 사용하지 않는다.
- `forbidden_actions`는 AR Guide 구성 prompt와 AR guide plan에 금지 조건으로 전달한다.
- clean reference와 annotated overlay는 분리해야 한다.
