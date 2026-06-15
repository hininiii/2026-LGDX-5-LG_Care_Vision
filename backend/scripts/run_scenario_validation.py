from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH
from app.routers.frontend_compat import _frontend_ai_chat_response
from app.services import CareShotBackendService


KST = ZoneInfo("Asia/Seoul")
ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "02_데이터연동" / "eval_sets"
REPORT_DIR = ROOT / "06_산출물"


@dataclass
class ScenarioResult:
    scenario_id: str
    title: str
    category: str
    status: str = "passed"
    checks: list[dict[str, Any]] = field(default_factory=list)
    observed: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def check(self, label: str, passed: bool, detail: Any = None) -> None:
        self.checks.append({"label": label, "passed": bool(passed), "detail": detail})
        if not passed:
            self.status = "failed"
            self.failures.append(f"{label}: {detail}")


class ScenarioRunner:
    def __init__(self, run_id: str, report_date: str) -> None:
        self.run_id = run_id
        self.report_date = report_date
        self.results: list[ScenarioResult] = []
        self.temp_db_path = EVAL_DIR / f"scenario_validation_{report_date.replace('-', '')}.sqlite"
        self.service = CareShotBackendService()
        self.service.repo = self.prepare_repository()
        app.dependency_overrides[get_service] = lambda: self.service
        self.client = TestClient(app)

    def prepare_repository(self) -> CareShotRepository:
        EVAL_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEFAULT_SQLITE_DB_PATH, self.temp_db_path)
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute('DELETE FROM "SELF_MANAGEMENT_HISTORY"')
        return CareShotRepository(self.temp_db_path)

    def run(self) -> dict[str, Any]:
        scenarios: list[Callable[[], ScenarioResult]] = [
            self.scenario_preventive_alert,
            self.scenario_normal_management,
            self.scenario_ambiguous_clarification,
            self.scenario_medium_self_as_cooling,
            self.scenario_high_risk_service_route,
            self.scenario_official_no_match_policy,
            self.scenario_save_and_rewatch,
        ]
        for scenario in scenarios:
            try:
                self.results.append(scenario())
            except Exception as exc:  # noqa: BLE001 - report every QA failure explicitly.
                failed = ScenarioResult(
                    scenario_id=scenario.__name__.replace("scenario_", ""),
                    title=scenario.__name__,
                    category="unexpected_error",
                    status="failed",
                )
                failed.failures.append(str(exc))
                self.results.append(failed)

        total = len(self.results)
        passed = sum(1 for result in self.results if result.status == "passed")
        failed = total - passed
        return {
            "run_id": self.run_id,
            "report_date": self.report_date,
            "generated_at": datetime.now(KST).isoformat(),
            "isolated_db_path": str(self.temp_db_path),
            "summary": {
                "total_scenarios": total,
                "passed_scenarios": passed,
                "failed_scenarios": failed,
                "status": "passed" if failed == 0 else "failed",
            },
            "scenarios": [result.__dict__ for result in self.results],
        }

    def post_front_chat(self, message: str, session_id: Any = None) -> tuple[int, dict[str, Any]]:
        context: dict[str, Any] = {"deviceId": "D001"}
        if session_id is not None:
            context["session_id"] = session_id
        response = self.client.post("/api/ai/chat", json={"message": message, "context": context})
        return response.status_code, response.json()

    def scenario_preventive_alert(self) -> ScenarioResult:
        result = ScenarioResult("preventive_alert", "예방 관리 알림", "self_care_alert")
        response = self.client.post(
            "/api/v1/care/risk/evaluate",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "procedure_type": "filter_cleaning",
                "region": "Delhi",
                "city": "New Delhi",
                "force_environment_refresh": False,
            },
        )
        payload = response.json()
        score = ((payload.get("care_risk_score") or {}).get("score"))
        reasons = ((payload.get("care_risk_score") or {}).get("trigger_reason") or [])
        guide_options = payload.get("guide_options") or {}
        result.observed = {
            "status_code": response.status_code,
            "score": score,
            "risk_level": (payload.get("care_risk_score") or {}).get("risk_level"),
            "trigger_reason_count": len(reasons),
            "manual_count": len(guide_options.get("manual_guides") or []),
            "youtube_count": len(guide_options.get("youtube_recommendations") or []),
            "ar_count": len(guide_options.get("ar_guides") or []),
        }
        result.check("Care Risk API returns 200", response.status_code == 200, response.status_code)
        result.check("Care Risk score is calculated", isinstance(score, (int, float)), score)
        result.check("trigger_reason exists", len(reasons) > 0, reasons)
        result.check("recommended guide option exists", bool(guide_options), list(guide_options.keys()))
        return result

    def scenario_normal_management(self) -> ScenarioResult:
        result = ScenarioResult("normal_management", "정상 관리 문의", "self_care_chat")
        status_code, payload = self.post_front_chat("필터 청소 방법 알려줘")
        card = payload.get("card_policy") or {}
        guide_options = payload.get("guide_options") or {}
        result.observed = {
            "status_code": status_code,
            "message": payload.get("message"),
            "service_flow_type": payload.get("service_flow_type"),
            "risk_level": payload.get("risk_level"),
            "procedure_type": payload.get("procedure_type"),
            "card_type": card.get("card_type"),
            "show_manual_button": card.get("show_manual_button"),
            "show_ar_button": card.get("show_ar_button"),
            "guide_options_present": bool(guide_options),
        }
        result.check("Frontend chat API returns 200", status_code == 200, status_code)
        result.check("self_care flow selected", payload.get("service_flow_type") == "self_care", payload.get("service_flow_type"))
        result.check("filter_cleaning procedure selected", payload.get("procedure_type") == "filter_cleaning", payload.get("procedure_type"))
        result.check("manual button is visible", card.get("show_manual_button") is True, card)
        result.check("AR button is visible", card.get("show_ar_button") is True, card)
        result.check("guide options are returned", bool(guide_options), guide_options)

        plan_response = self.client.post("/api/v1/ar/plans", json={"user_id": "U001", "device_id": "D001", "message": "필터 청소 방법 알려줘"})
        plan_payload = plan_response.json()
        steps = ((plan_payload.get("ar_overlay_data") or {}).get("guide_steps") or [])
        result.check("AR plan returns overlay steps", plan_response.status_code == 200 and len(steps) > 0, {"status": plan_response.status_code, "steps": len(steps)})
        return result

    def scenario_ambiguous_clarification(self) -> ScenarioResult:
        result = ScenarioResult("ambiguous_clarification", "모호 문의 추가 질문", "clarification")
        status_code, payload = self.post_front_chat("이상해요")
        result.observed = {
            "status_code": status_code,
            "message": payload.get("message"),
            "needs_clarification": payload.get("needs_clarification"),
            "missing_slots": payload.get("missing_slots"),
            "procedure_type": payload.get("procedure_type"),
            "guide_options_present": bool(payload.get("guide_options")),
            "card_type": (payload.get("card_policy") or {}).get("card_type"),
        }
        result.check("Frontend chat API returns 200", status_code == 200, status_code)
        result.check("needs clarification", payload.get("needs_clarification") is True, payload)
        result.check("asks symptom_type first", payload.get("missing_slots") == ["symptom_type"], payload.get("missing_slots"))
        result.check("does not default to filter_cleaning", payload.get("procedure_type") != "filter_cleaning", payload.get("procedure_type"))
        result.check("does not return guide options yet", payload.get("guide_options") is None, payload.get("guide_options"))
        return result

    def scenario_medium_self_as_cooling(self) -> ScenarioResult:
        result = ScenarioResult("medium_self_as_cooling", "Medium 자가점검 냉방/바람 약함", "self_as_chat")
        first_status, first = self.post_front_chat("냉방/기능이 잘 작동하지 않아요")
        session_id = first.get("session_id")
        second_status, second = self.post_front_chat("아니요", session_id=session_id)
        third_status, third = self.post_front_chat("바람이 약하고 안시원해요. 송풍구에서 나오고 먼지가 많아요.", session_id=session_id)
        third_card = third.get("card_policy") or {}
        result.observed = {
            "first": {
                "status_code": first_status,
                "message": first.get("message"),
                "missing_slots": first.get("missing_slots"),
                "procedure_type": first.get("procedure_type"),
            },
            "second": {
                "status_code": second_status,
                "message": second.get("message"),
                "missing_slots": second.get("missing_slots"),
                "procedure_type": second.get("procedure_type"),
            },
            "third": {
                "status_code": third_status,
                "message": third.get("message"),
                "service_flow_type": third.get("service_flow_type"),
                "risk_level": third.get("risk_level"),
                "procedure_type": third.get("procedure_type"),
                "needs_clarification": third.get("needs_clarification"),
                "card_type": third_card.get("card_type"),
                "guide_options_present": bool(third.get("guide_options")),
            },
        }
        result.check("first turn asks risk signal first", first_status == 200 and first.get("missing_slots", [None])[0] == "risk_signal", first)
        result.check("risk-negative turn asks symptom detail", second_status == 200 and "위험 신호" not in str(second.get("message")), second)
        result.check("final turn selects self_as", third.get("service_flow_type") == "self_as", third)
        result.check("final turn keeps cooling procedure", third.get("procedure_type") == "no_cooling_self_check", third)
        result.check("final turn no filter-cleaning misroute", third.get("procedure_type") != "filter_cleaning", third)
        result.check("final turn returns guide options", bool(third.get("guide_options")), third)
        return result

    def scenario_high_risk_service_route(self) -> ScenarioResult:
        result = ScenarioResult("high_risk_service_route", "High Risk A/S 연결", "expert_as")
        status_code, payload = self.post_front_chat("연기와 타는 냄새가 나요")
        card = payload.get("card_policy") or {}
        result.observed = {
            "status_code": status_code,
            "message": payload.get("message"),
            "service_flow_type": payload.get("service_flow_type"),
            "risk_level": payload.get("risk_level"),
            "card_type": card.get("card_type"),
            "show_service_button": card.get("show_service_button"),
            "show_ar_button": card.get("show_ar_button"),
            "guide_options_present": bool(payload.get("guide_options")),
        }
        result.check("Frontend chat API returns 200", status_code == 200, status_code)
        result.check("expert_as flow selected", payload.get("service_flow_type") == "expert_as", payload)
        result.check("risk level is high", payload.get("risk_level") == "high", payload)
        result.check("service route card is selected", card.get("card_type") == "service_route", card)
        result.check("AR button is hidden", card.get("show_ar_button") is False, card)
        result.check("guide options blocked", payload.get("guide_options") is None, payload.get("guide_options"))
        return result

    def scenario_official_no_match_policy(self) -> ScenarioResult:
        result = ScenarioResult("official_no_match_policy", "공식근거 없음 카드 정책", "no_match")
        raw = {
            "chat_session": {"session_id": "SCENARIO_NO_MATCH"},
            "analysis": {
                "official_asset_match": {"match_status": "needs_review"},
                "decision_result": {
                    "intent_type": "self_check",
                    "service_flow_type": "self_as",
                    "risk_level": "unknown",
                    "decision_action": "official_match_review_needed",
                    "ar_guide_allowed": False,
                    "blocked_reason": "Official asset match is not verified.",
                },
            },
            "chatbot_engine": {
                "ai_message": {"message_type": "text", "message_content": "Official guide options are not ready."},
                "conversation_state": {"session_id": "SCENARIO_NO_MATCH", "missing_slots": []},
                "guide_options": None,
            },
        }
        payload = _frontend_ai_chat_response(raw)
        card = payload.get("card_policy") or {}
        result.observed = {
            "message": payload.get("message"),
            "recommended_action": payload.get("recommended_action"),
            "card_type": card.get("card_type"),
            "card_title": card.get("title"),
            "show_ar_button": card.get("show_ar_button"),
            "show_manual_button": card.get("show_manual_button"),
            "show_service_button": card.get("show_service_button"),
            "note": "Policy-level no-match mapping. Current seeded runtime corpus does not contain expected no-match evaluation rows.",
        }
        result.check("safety block card is selected", card.get("card_type") == "safety_block", card)
        result.check("official no-match title is localized", card.get("title") == "공식자료 확인 불가", card)
        result.check("manual and AR buttons are hidden", card.get("show_manual_button") is False and card.get("show_ar_button") is False, card)
        result.check("service button is visible", card.get("show_service_button") is True, card)
        return result

    def scenario_save_and_rewatch(self) -> ScenarioResult:
        result = ScenarioResult("save_and_rewatch", "저장/재시청 이력", "history")
        complete_response = self.client.post(
            "/api/v1/guides/GUIDE_1/complete",
            json={"user_id": "U001", "device_id": "D001", "service_flow_type": "self_care"},
        )
        history_response = self.client.get("/api/v1/devices/D001/care-history?user_id=U001")
        history_payload = history_response.json()

        create_response = self.client.post(
            "/api/v1/ar/sessions",
            json={
                "guide_id": "GUIDE_AC_FILTER_CARE_AR_V1",
                "user_id": "U001",
                "device_id": "D001",
                "guide_type": "preventive_care",
                "service_flow_type": "self_care",
                "procedure_type": "filter_cleaning",
                "structure_type": "wall_ac_type_a",
            },
        )
        ar_session = create_response.json()
        session_id = ar_session.get("session_id")
        plan_response = self.client.post(
            "/api/v1/ar/plans",
            json={"user_id": "U001", "device_id": "D001", "message": "필터 청소 방법 알려줘"},
        )
        steps = ((plan_response.json().get("ar_overlay_data") or {}).get("guide_steps") or [])[:2]
        completed_steps = [step.get("guide_step_id") for step in steps if step.get("guide_step_id")]
        update_response = self.client.patch(
            f"/api/v1/ar/sessions/{session_id}",
            json={"completed_steps": completed_steps, "completed": True, "solved": True},
        )
        rewatch_response = self.client.get(f"/api/v1/ar/sessions/{session_id}")

        result.observed = {
            "complete_status": complete_response.status_code,
            "history_status": history_response.status_code,
            "history_count": len(history_payload.get("items") or []),
            "ar_session_create_status": create_response.status_code,
            "ar_session_id": session_id,
            "completed_steps": completed_steps,
            "ar_session_update_status": update_response.status_code,
            "rewatch_status": rewatch_response.status_code,
            "rewatch_step_log_count": len((rewatch_response.json() if rewatch_response.status_code == 200 else {}).get("step_logs") or []),
        }
        result.check("guide completion API succeeds", complete_response.status_code == 200, complete_response.text)
        result.check("care history contains saved item", history_response.status_code == 200 and len(history_payload.get("items") or []) >= 1, history_payload)
        result.check("AR session is created", create_response.status_code == 201 and bool(session_id), ar_session)
        result.check("AR session has completed steps", update_response.status_code == 200 and len(completed_steps) > 0, update_response.text)
        result.check("AR session can be rewatched/read", rewatch_response.status_code == 200 and len(rewatch_response.json().get("step_logs") or []) == len(completed_steps), rewatch_response.text)
        return result


def write_report(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# 28번 통합 시나리오 QA 리포트 - {report['report_date']}",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- generated_at: `{report['generated_at']}`",
        f"- isolated_db_path: `{report['isolated_db_path']}`",
        f"- total/pass/fail: {report['summary']['total_scenarios']} / {report['summary']['passed_scenarios']} / {report['summary']['failed_scenarios']}",
        f"- status: `{report['summary']['status']}`",
        "",
        "## 시나리오 결과",
        "",
        "| ID | 분류 | 결과 | 주요 관측 |",
        "| --- | --- | --- | --- |",
    ]
    for scenario in report["scenarios"]:
        observed = scenario.get("observed") or {}
        compact = json.dumps(observed, ensure_ascii=False)
        if len(compact) > 220:
            compact = compact[:217] + "..."
        lines.append(f"| `{scenario['scenario_id']}` | {scenario['category']} | {scenario['status']} | {compact} |")

    failures = [scenario for scenario in report["scenarios"] if scenario.get("failures")]
    lines.extend(["", "## 실패/보정 대상", ""])
    if not failures:
        lines.append("- 자동 검증 기준 실패 없음.")
    else:
        for scenario in failures:
            lines.append(f"### {scenario['scenario_id']}")
            for failure in scenario.get("failures") or []:
                lines.append(f"- {failure}")

    screenshots = report.get("screenshots") or []
    lines.extend(["", "## 화면 캡처", ""])
    if screenshots:
        for screenshot in screenshots:
            lines.append(f"- `{screenshot}`")
    else:
        lines.append("- 화면 캡처 파일은 이 스크립트 밖에서 Playwright CLI로 별도 생성한다.")

    lines.extend(
        [
            "",
            "## 검증 범위",
            "",
            "- `/api/ai/chat` 프론트 호환 챗봇 응답과 card_policy 확인",
            "- `/api/v1/chat/messages`가 감싸는 ChatbotEngine/DecisionEngine 흐름은 프론트 호환 API를 통해 간접 검증",
            "- `/api/v1/care/risk/evaluate` 예방 알림/Care Risk/guide option 확인",
            "- `/api/v1/ar/plans`, `/api/v1/ar/sessions`, `/api/v1/guides/{guide_id}/complete`, `/api/v1/devices/{device_id}/care-history` 저장/재시청 흐름 확인",
            "- 공식근거 no-match는 현재 seed 평가셋에 expected no-match row가 없어 프론트 card_policy mapping 단위로 검증",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CareShot scenario validation for step 28.")
    today = datetime.now(KST).date().isoformat()
    parser.add_argument("--run-id", default=f"SCENARIO_28_{today.replace('-', '')}")
    parser.add_argument("--report-date", default=today)
    parser.add_argument("--json-path", default=None)
    parser.add_argument("--md-path", default=None)
    args = parser.parse_args()

    json_path = Path(args.json_path) if args.json_path else EVAL_DIR / f"scenario_validation_results_{args.report_date.replace('-', '')}.json"
    md_path = Path(args.md_path) if args.md_path else REPORT_DIR / f"{args.report_date}_scenario_validation_report.md"

    runner = ScenarioRunner(run_id=args.run_id, report_date=args.report_date)
    try:
        report = runner.run()
    finally:
        app.dependency_overrides.clear()

    screenshot_dir = REPORT_DIR / f"scenario_screenshots_{args.report_date.replace('-', '')}"
    report["screenshots"] = [
        str(path)
        for path in sorted(screenshot_dir.glob("*_authenticated.png"))
        if path.is_file()
    ]

    write_report(report, json_path=json_path, md_path=md_path)
    print(json.dumps({"summary": report["summary"], "json_path": str(json_path), "md_path": str(md_path)}, ensure_ascii=False, indent=2))
    return 0 if report["summary"]["failed_scenarios"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
