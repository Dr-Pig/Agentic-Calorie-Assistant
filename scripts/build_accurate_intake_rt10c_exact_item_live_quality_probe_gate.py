from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.agent.exact_item_packets import resolve_exact_item  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt10c_exact_item_live_quality_probe_gate.json"
EXPECTED_CASE_ID = "exact_item_official_label"
EXPECTED_QUERY = "\u6211\u559d\u4e86\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"
REQUIRED_NON_CLAIM_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "live_provider_used_as_truth",
    "runtime_web_activation_approved",
)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _expected_exact_truth() -> dict[str, Any]:
    candidates = resolve_exact_item(EXPECTED_QUERY, limit=1)
    if not candidates:
        raise RuntimeError("No exact-item truth candidate resolved for RT10c expected query.")
    candidate = _dict(candidates[0])
    kcal = candidate.get("kcal")
    return {
        "title": candidate.get("title"),
        "kcal": int(kcal) if isinstance(kcal, (int, float)) and float(kcal).is_integer() else kcal,
        "evidence_role": candidate.get("evidence_role"),
    }


def _tool_names(case: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for turn in _list(case.get("turns")):
        for round_item in _list(_dict(turn).get("manager_rounds")):
            for call in _list(_dict(_dict(round_item).get("decision")).get("tool_calls")):
                name = str(_dict(call).get("name") or "").strip()
                if name:
                    names.append(name)
    return names


def build_rt10c_exact_item_live_quality_probe_gate(
    *,
    live_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    expected = _expected_exact_truth()
    artifact = _dict(live_artifact)
    blockers: list[str] = []

    if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        blockers.append("unsupported_live_diagnostic_artifact_type")
    if artifact.get("provider_mode") != "live":
        blockers.append("provider_mode_not_live")
    if artifact.get("live_invoked") is not True:
        blockers.append("live_not_invoked")
    if artifact.get("live_llm_invoked") is not True:
        blockers.append("live_llm_not_invoked")

    non_claim_violations = [flag for flag in REQUIRED_NON_CLAIM_FLAGS if artifact.get(flag) is True]
    blockers.extend(f"non_claim_violation:{flag}" for flag in non_claim_violations)

    stages = [_dict(stage) for stage in _list(artifact.get("stages"))]
    stage = stages[0] if len(stages) == 1 else {}
    if not stage:
        blockers.append("missing_single_case_stage")
    else:
        if stage.get("stage_id") != "single_case_live_probe":
            blockers.append("unexpected_stage_id")
        if stage.get("status") != "pass":
            blockers.append("single_case_stage_not_pass")
        if stage.get("result_kind") != "strict_pass_first_attempt":
            blockers.append("single_case_stage_not_strict_first_attempt")
        if _list(stage.get("case_ids")) != [EXPECTED_CASE_ID]:
            blockers.append("unexpected_case_ids")

    cases = [_dict(case) for case in _list(artifact.get("cases"))]
    if len(cases) != 1:
        blockers.append("unexpected_case_count")
        case = {}
    else:
        case = cases[0]

    if case:
        if case.get("case_id") != EXPECTED_CASE_ID:
            blockers.append("unexpected_case_id")
        if case.get("case_contract_status") != "strict_pass":
            blockers.append("case_contract_not_strict_pass")
        if case.get("verdict") != "pass":
            blockers.append("case_verdict_not_pass")
        if case.get("failure_layer") is not None:
            blockers.append("case_failure_layer_present")

        turns = [_dict(turn) for turn in _list(case.get("turns"))]
        turn = turns[0] if len(turns) == 1 else {}
        if not turn:
            blockers.append("missing_single_turn")
        else:
            state_delta = _dict(turn.get("state_delta"))
            if state_delta.get("canonical_commit") is not True:
                blockers.append("canonical_commit_missing")
            if state_delta.get("draft_saved") is not False:
                blockers.append("unexpected_draft_saved")
            if state_delta.get("ledger_updated") is not True:
                blockers.append("ledger_not_updated")

            if turn.get("manager_final_action") != "commit":
                blockers.append("manager_final_action_not_commit")
            tool_names = _tool_names(case)
            if tool_names != ["estimate_nutrition"]:
                blockers.append("unexpected_tool_call_inventory")

            remaining_budget = _dict(turn.get("remaining_budget"))
            if remaining_budget.get("status") != "ready":
                blockers.append("remaining_budget_not_ready")
            if remaining_budget.get("consumed_kcal") != expected["kcal"]:
                blockers.append("consumed_kcal_mismatch")

            final_round = _dict(_list(turn.get("manager_rounds"))[-1]) if _list(turn.get("manager_rounds")) else {}
            final_decision = _dict(final_round.get("decision"))
            if final_decision.get("exactness") != "exact":
                blockers.append("final_exactness_not_exact")
            if final_decision.get("confidence") != "high":
                blockers.append("final_confidence_not_high")
            if final_decision.get("evidence_posture") != "evidence_present":
                blockers.append("final_evidence_posture_mismatch")
            followup_question = _dict(final_decision.get("semantic_decision")).get("followup_question")
            if followup_question is not None:
                blockers.append("unexpected_followup_question")

        model = _dict(_dict(case.get("debug_surface")).get("model"))
        active_threads = _list(model.get("meal_threads"))
        if len(active_threads) != 1:
            blockers.append("unexpected_meal_thread_count")
            active_version = {}
        else:
            active_version = _dict(_dict(active_threads[0]).get("active_version"))
            items = _list(active_version.get("items"))
            if len(items) != 1:
                blockers.append("unexpected_active_item_count")
            else:
                item = _dict(items[0])
                if item.get("name") != expected["title"]:
                    blockers.append("active_item_title_mismatch")
                if item.get("estimated_kcal") != expected["kcal"]:
                    blockers.append("active_item_kcal_mismatch")
            if active_version.get("total_kcal") != expected["kcal"]:
                blockers.append("active_version_total_kcal_mismatch")

        same_truth = _dict(model.get("same_truth"))
        if same_truth.get("status") != "pass":
            blockers.append("same_truth_not_pass")
        if same_truth.get("debug_model_consumed_kcal") != expected["kcal"]:
            blockers.append("same_truth_debug_model_kcal_mismatch")
        if same_truth.get("current_budget_consumed_kcal") != expected["kcal"]:
            blockers.append("same_truth_budget_kcal_mismatch")

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt10c_exact_item_live_quality_probe_gate",
        "claim_scope": "manager_runtime_exact_item_live_quality_probe",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt10c_exact_item_live_quality_probe",
        "pass_type": "live_diagnostic",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "expected_case_id": EXPECTED_CASE_ID,
            "expected_exact_title": expected["title"],
            "expected_exact_kcal": expected["kcal"],
            "required_tool_calls": ["estimate_nutrition"],
            "requires_followup_question": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT10c exact-item live quality probe gate artifact."
    )
    parser.add_argument(
        "--source-artifact",
        type=Path,
        required=True,
        help="Path to an accurate_intake_mvp_live_diagnostic artifact for exact_item_official_label.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT10c gate artifact JSON.",
    )
    args = parser.parse_args(argv)

    source_artifact = json.loads(args.source_artifact.read_text(encoding="utf-8"))
    gate_artifact = build_rt10c_exact_item_live_quality_probe_gate(
        live_artifact=source_artifact,
        output_path=args.output,
    )
    write_json_artifact(args.output, gate_artifact)
    print(args.output)
    return 0 if gate_artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
