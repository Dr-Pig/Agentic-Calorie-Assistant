from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt11_final_response_quality.json"

_DEBUG_LEAK_MARKERS = ("trace", "debug", "provider", "request_id", "tool_call")
_LOGGED_MARKERS = ("\u5df2\u5e6b\u4f60\u8a18\u9304", "\u5df2\u8a18\u9304", "\u5148\u5e6b\u4f60\u8a18")
_NO_COMMIT_MARKERS = ("\u5148\u4e0d\u8a18", "\u9084\u6c92\u8a18", "\u672a\u8a18\u9304", "\u4e0d\u6703\u5148\u8a18")
_UPDATED_MARKERS = ("\u5df2\u66f4\u65b0", "\u5df2\u6539\u6210", "\u5df2\u79fb\u9664")
_UNCERTAINTY_MARKERS = ("\u7d04", "\u5927\u7d04", "\u4f30", "\u4f30\u8a08")
_MACRO_VISIBLE_PATTERN = re.compile(
    r"(\u86cb\u767d\u8cea|\u78b3\u6c34|\u8102\u80aa)\s*[:\uff1a]?\s*\d+\s*g",
    re.IGNORECASE,
)
_KCAL_PATTERN = re.compile(r"\d+\s*kcal", re.IGNORECASE)


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    text = str(case["reply_text"])
    lowered = text.lower()
    blockers: list[str] = []

    if any(marker in lowered for marker in _DEBUG_LEAK_MARKERS):
        blockers.append("debug_or_provider_leak_present")

    for marker in case.get("required_markers", []):
        if marker not in text:
            blockers.append(f"missing_required_marker:{marker}")
    for marker in case.get("forbidden_markers", []):
        if marker in text:
            blockers.append(f"forbidden_marker_present:{marker}")

    logged_status = str(case.get("logged_status") or "")
    final_action = str(case.get("final_action") or "")
    if final_action == "correction_applied":
        if not _contains_any(text, _UPDATED_MARKERS):
            blockers.append("correction_update_not_explicit")
        if _contains_any(text, _NO_COMMIT_MARKERS):
            blockers.append("correction_reply_contains_no_commit_marker")
    elif logged_status == "logged":
        if not _contains_any(text, _LOGGED_MARKERS):
            blockers.append("logged_status_not_explicit")
        if _contains_any(text, _NO_COMMIT_MARKERS):
            blockers.append("logged_reply_contains_no_commit_marker")
    elif logged_status == "not_logged":
        if not _contains_any(text, _NO_COMMIT_MARKERS):
            blockers.append("not_logged_status_not_explicit")
        if _contains_any(text, _LOGGED_MARKERS):
            blockers.append("not_logged_reply_contains_logged_marker")

    if case.get("must_include_kcal") is True and not _KCAL_PATTERN.search(text):
        blockers.append("kcal_missing")
    if case.get("must_exclude_kcal") is True and _KCAL_PATTERN.search(text):
        blockers.append("kcal_should_not_be_visible")

    expected_kcal = case.get("expected_kcal")
    if expected_kcal is not None and str(expected_kcal) not in text:
        blockers.append("expected_kcal_value_missing")

    if case.get("must_include_uncertainty") is True and not _contains_any(text, _UNCERTAINTY_MARKERS):
        blockers.append("uncertainty_not_explicit")

    if case.get("must_include_question") is True and "\uff1f" not in text and "?" not in text:
        blockers.append("followup_question_not_explicit")

    if case.get("must_exclude_macro_visible") is True and _MACRO_VISIBLE_PATTERN.search(text):
        blockers.append("macro_visible_claim_present_when_hidden")

    return {
        "case_id": case["case_id"],
        "family": case["family"],
        "status": _status(blockers),
        "blockers": blockers,
        "reply_text": text,
        "logged_status": logged_status,
        "final_action": case.get("final_action"),
        "show_macro": case.get("show_macro"),
    }


def _case_specs() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "logged_estimate_states_commit_kcal_and_uncertainty",
            "family": "logged_estimate",
            "reply_text": "\u5df2\u5e6b\u4f60\u8a18\u9304\uff1a\u8336\u8449\u86cb\uff0c\u7d04 70 kcal\u3002\u9019\u662f\u4f30\u7b97\u503c\u3002",
            "logged_status": "logged",
            "final_action": "commit",
            "expected_kcal": 70,
            "must_include_kcal": True,
            "must_include_uncertainty": True,
            "required_markers": [],
            "forbidden_markers": [],
        },
        {
            "case_id": "optional_refinement_keeps_logged_status_and_next_question",
            "family": "optional_refinement",
            "reply_text": "\u5148\u5e6b\u4f60\u8a18\u4e00\u676f\u73cd\u73e0\u5976\u8336\uff0c\u7d04 450 kcal\u3002\u5982\u679c\u4f60\u8981\u66f4\u6e96\uff0c\u53ef\u4ee5\u518d\u544a\u8a34\u6211\u676f\u578b\u548c\u7cd6\u5ea6\u3002",
            "logged_status": "logged",
            "final_action": "commit_with_followup",
            "expected_kcal": 450,
            "must_include_kcal": True,
            "must_include_uncertainty": True,
            "required_markers": ["\u676f\u578b", "\u7cd6\u5ea6"],
            "forbidden_markers": ["\u5148\u4e0d\u8a18"],
        },
        {
            "case_id": "blocking_clarify_states_not_logged_and_asks_question",
            "family": "blocking_clarify",
            "reply_text": "\u9019\u7b46\u6211\u5148\u4e0d\u8a18\uff0c\u56e0\u70ba\u9084\u4e0d\u77e5\u9053\u6ef7\u5473\u6709\u54ea\u4e9b\u54c1\u9805\u3002\u4f60\u53ef\u4ee5\u544a\u8a34\u6211\u5167\u5bb9\u55ce\uff1f",
            "logged_status": "not_logged",
            "final_action": "ask_followup",
            "must_exclude_kcal": True,
            "must_include_question": True,
            "required_markers": ["\u6ef7\u5473"],
            "forbidden_markers": [],
        },
        {
            "case_id": "degraded_budget_stays_honest_without_concrete_remaining",
            "family": "degraded_budget",
            "reply_text": "\u4f60\u9084\u6c92\u5b8c\u6210\u57fa\u672c\u8a2d\u5b9a\uff0c\u6240\u4ee5\u6211\u73fe\u5728\u4e0d\u80fd\u544a\u8a34\u4f60\u4eca\u5929\u9084\u5269\u591a\u5c11\u71b1\u91cf\u3002",
            "logged_status": "",
            "final_action": "answer_only_degraded",
            "must_exclude_kcal": True,
            "required_markers": ["\u57fa\u672c\u8a2d\u5b9a", "\u9084\u5269\u591a\u5c11\u71b1\u91cf"],
            "forbidden_markers": ["500 kcal", "500"],
        },
        {
            "case_id": "macro_hidden_reply_does_not_invent_macro_numbers",
            "family": "macro_hidden",
            "reply_text": "\u5df2\u5e6b\u4f60\u8a18\u9304\u9019\u9910\uff0c\u71b1\u91cf\u7d04 520 kcal\u3002\u4e09\u5927\u71df\u990a\u7d20\u8cc7\u6599\u76ee\u524d\u4e0d\u8db3\u3002",
            "logged_status": "logged",
            "final_action": "commit",
            "expected_kcal": 520,
            "must_include_kcal": True,
            "must_include_uncertainty": True,
            "must_exclude_macro_visible": True,
            "show_macro": False,
            "required_markers": ["\u4e09\u5927\u71df\u990a\u7d20\u8cc7\u6599\u76ee\u524d\u4e0d\u8db3"],
            "forbidden_markers": [],
        },
        {
            "case_id": "correction_reply_states_update_without_debug_or_extra_claims",
            "family": "correction",
            "reply_text": "\u5df2\u628a\u525b\u525b\u90a3\u676f\u73cd\u5976\u6539\u6210\u534a\u7cd6\uff0c\u9019\u7b46\u5df2\u66f4\u65b0\u3002",
            "logged_status": "logged",
            "final_action": "correction_applied",
            "must_exclude_kcal": True,
            "required_markers": ["\u6539\u6210\u534a\u7cd6", "\u5df2\u66f4\u65b0"],
            "forbidden_markers": ["request_id", "trace", "\u4f30\u8a08"],
        },
    ]


def build_rt11_final_response_quality_artifact(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    cases = [_evaluate_case(case) for case in _case_specs()]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "claim_scope": "final_response_quality_fixture_gate",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt11_final_response_quality",
        "pass_type": "fixture",
        "runtime_backed": False,
        "live_llm_invoked": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D", "J", "K"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
        },
        "cases": cases,
        "rubric": {
            "must_include": [
                "logged or not-logged status when applicable",
                "kcal or range when the reply claims a committed estimate",
                "uncertainty language for estimated calories",
                "next-step clarification for unresolved blocking cases",
            ],
            "must_not_include": [
                "debug/provider/trace leakage",
                "concrete remaining calories in degraded budget mode",
                "visible macro grams when show_macro=false",
            ],
            "judge_type": "rule_based_fixture",
            "llm_judge_used": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT11 final response quality artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the JSON artifact.",
    )
    args = parser.parse_args(argv)
    artifact = build_rt11_final_response_quality_artifact(output_path=args.output)
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
