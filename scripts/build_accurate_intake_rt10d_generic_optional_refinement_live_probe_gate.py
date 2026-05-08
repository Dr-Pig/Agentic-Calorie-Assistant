from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt10d_generic_optional_refinement_live_probe_gate.json"
EXPECTED_CASE_ID = "bubble_milk_tea_refinement"
EXPECTED_TOTAL_KCAL = 400
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


def _tool_names(turn: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for round_item in _list(turn.get("manager_rounds")):
        decision = _dict(_dict(round_item).get("decision"))
        for call in _list(decision.get("tool_calls")):
            name = str(_dict(call).get("name") or "").strip()
            if name:
                names.append(name)
    return names


def _final_round(turn: dict[str, Any]) -> dict[str, Any]:
    rounds = _list(turn.get("manager_rounds"))
    return _dict(rounds[-1]) if rounds else {}


def _workflow_effect_ok(value: Any) -> bool:
    return str(value or "").strip() in {"commit", "canonical_write"}


def _targets_existing_thread(semantic_decision: dict[str, Any]) -> bool:
    target_attachment = _dict(semantic_decision.get("target_attachment"))
    mode = str(target_attachment.get("mode") or "").strip()
    return mode == "target_committed_thread" or target_attachment.get("meal_thread_id") not in (None, "")


def build_rt10d_generic_optional_refinement_live_probe_gate(
    *,
    live_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
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

    for flag in REQUIRED_NON_CLAIM_FLAGS:
        if artifact.get(flag) is True:
            blockers.append(f"non_claim_violation:{flag}")

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
    case = cases[0] if len(cases) == 1 else {}
    if not case:
        blockers.append("unexpected_case_count")
    else:
        if case.get("case_id") != EXPECTED_CASE_ID:
            blockers.append("unexpected_case_id")
        if case.get("case_contract_status") != "strict_pass":
            blockers.append("case_contract_not_strict_pass")
        if case.get("verdict") != "pass":
            blockers.append("case_verdict_not_pass")
        if case.get("failure_layer") is not None:
            blockers.append("case_failure_layer_present")

    turns = [_dict(turn) for turn in _list(case.get("turns"))] if case else []
    if len(turns) != 2:
        blockers.append("unexpected_turn_count")
        first_turn = {}
        second_turn = {}
    else:
        first_turn, second_turn = turns

    for prefix, turn in (("turn1", first_turn), ("turn2", second_turn)):
        if not turn:
            blockers.append(f"{prefix}_missing")
            continue
        state_delta = _dict(turn.get("state_delta"))
        if state_delta.get("canonical_commit") is not True:
            blockers.append(f"{prefix}_canonical_commit_missing")
        if state_delta.get("draft_saved") is not False:
            blockers.append(f"{prefix}_unexpected_draft_saved")
        if state_delta.get("ledger_updated") is not True:
            blockers.append(f"{prefix}_ledger_not_updated")
        if turn.get("manager_final_action") != "commit":
            blockers.append(f"{prefix}_manager_final_action_not_commit")
        if not _workflow_effect_ok(turn.get("workflow_effect")):
            blockers.append(f"{prefix}_workflow_effect_not_commit_family")
        if _tool_names(turn) != ["estimate_nutrition"]:
            blockers.append(f"{prefix}_unexpected_tool_inventory")

    if first_turn:
        first_state_delta = _dict(first_turn.get("state_delta"))
        if first_state_delta.get("new_meal_version_created") is not True:
            blockers.append("turn1_new_version_missing")
        if first_state_delta.get("old_version_superseded") is not False:
            blockers.append("turn1_unexpected_supersede")
        first_remaining = _dict(first_turn.get("remaining_budget"))
        if first_remaining.get("status") != "ready":
            blockers.append("turn1_remaining_budget_not_ready")
        if first_remaining.get("consumed_kcal") != EXPECTED_TOTAL_KCAL:
            blockers.append("turn1_consumed_kcal_mismatch")

        first_final_decision = _dict(_final_round(first_turn).get("decision"))
        first_semantic = _dict(first_final_decision.get("semantic_decision"))
        if not _dict(first_semantic.get("target_attachment")):
            blockers.append("turn1_target_attachment_missing")

    if second_turn:
        second_state_delta = _dict(second_turn.get("state_delta"))
        if second_state_delta.get("new_meal_version_created") is not True:
            blockers.append("turn2_new_version_missing")
        if second_state_delta.get("old_version_superseded") is not True:
            blockers.append("turn2_expected_supersede_missing")
        second_remaining = _dict(second_turn.get("remaining_budget"))
        if second_remaining.get("status") != "ready":
            blockers.append("turn2_remaining_budget_not_ready")
        if second_remaining.get("consumed_kcal") != EXPECTED_TOTAL_KCAL:
            blockers.append("turn2_consumed_kcal_mismatch")

        second_final_decision = _dict(_final_round(second_turn).get("decision"))
        second_semantic = _dict(second_final_decision.get("semantic_decision"))
        if not _targets_existing_thread(second_semantic):
            blockers.append("turn2_target_existing_thread_missing")

    model = _dict(_dict(case.get("debug_surface")).get("model")) if case else {}
    same_truth = _dict(model.get("same_truth"))
    if same_truth.get("status") != "pass":
        blockers.append("same_truth_not_pass")
    if same_truth.get("debug_model_consumed_kcal") != EXPECTED_TOTAL_KCAL:
        blockers.append("same_truth_debug_model_kcal_mismatch")
    if same_truth.get("current_budget_consumed_kcal") != EXPECTED_TOTAL_KCAL:
        blockers.append("same_truth_budget_kcal_mismatch")

    today_summary = _dict(model.get("today_summary"))
    if today_summary.get("consumed_kcal") != EXPECTED_TOTAL_KCAL:
        blockers.append("today_summary_consumed_kcal_mismatch")
    if today_summary.get("remaining_kcal") != 912:
        blockers.append("today_summary_remaining_kcal_mismatch")

    meal_threads = _list(model.get("meal_threads"))
    if len(meal_threads) != 1:
        blockers.append("unexpected_meal_thread_count")
    else:
        thread = _dict(meal_threads[0])
        active_version = _dict(thread.get("active_version"))
        if active_version.get("version_reason") != "correction":
            blockers.append("active_version_reason_not_correction")
        if active_version.get("parent_version_id") != 1:
            blockers.append("active_version_parent_missing")
        if active_version.get("total_kcal") != EXPECTED_TOTAL_KCAL:
            blockers.append("active_version_total_kcal_mismatch")
        items = _list(active_version.get("items"))
        if len(items) != 1:
            blockers.append("unexpected_active_item_count")
        elif _dict(items[0]).get("estimated_kcal") != EXPECTED_TOTAL_KCAL:
            blockers.append("active_item_kcal_mismatch")

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt10d_generic_optional_refinement_live_probe_gate",
        "claim_scope": "manager_runtime_generic_optional_refinement_live_probe",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt10d_generic_optional_refinement_live_probe",
        "pass_type": "live_diagnostic",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "expected_case_id": EXPECTED_CASE_ID,
            "expected_total_kcal": EXPECTED_TOTAL_KCAL,
            "required_tool_calls": ["estimate_nutrition"],
            "required_turn_count": 2,
            "requires_supersede_on_refinement": True,
            "requires_same_truth_pass": True,
            "locks_response_wording": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT10d generic optional-refinement live probe gate artifact."
    )
    parser.add_argument(
        "--source-artifact",
        type=Path,
        required=True,
        help="Path to an accurate_intake_mvp_live_diagnostic artifact for bubble_milk_tea_refinement.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT10d gate artifact JSON.",
    )
    args = parser.parse_args(argv)

    source_artifact = json.loads(args.source_artifact.read_text(encoding="utf-8"))
    gate_artifact = build_rt10d_generic_optional_refinement_live_probe_gate(
        live_artifact=source_artifact,
        output_path=args.output,
    )
    write_json_artifact(args.output, gate_artifact)
    print(args.output)
    return 0 if gate_artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
