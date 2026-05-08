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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt10e_blocking_clarify_correction_live_probe_gate.json"
REQUIRED_STAGE_ID = "single_case_live_probe"
BLOCKING_CASE_ID = "luwei_bare_to_listed_basket"
CORRECTION_CASE_ID = "chinese_chicken_rice_correction_removal_debug"
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


def _artifact_blockers(artifact: dict[str, Any], *, expected_case_id: str) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        blockers.append(f"unsupported_live_diagnostic_artifact_type:{expected_case_id}")
    if artifact.get("provider_mode") != "live":
        blockers.append(f"provider_mode_not_live:{expected_case_id}")
    if artifact.get("live_invoked") is not True:
        blockers.append(f"live_not_invoked:{expected_case_id}")
    if artifact.get("live_llm_invoked") is not True:
        blockers.append(f"live_llm_not_invoked:{expected_case_id}")

    for flag in REQUIRED_NON_CLAIM_FLAGS:
        if artifact.get(flag) is True:
            blockers.append(f"non_claim_violation:{expected_case_id}:{flag}")

    stages = [_dict(stage) for stage in _list(artifact.get("stages"))]
    stage = stages[0] if len(stages) == 1 else {}
    if not stage:
        blockers.append(f"missing_single_case_stage:{expected_case_id}")
    else:
        if stage.get("stage_id") != REQUIRED_STAGE_ID:
            blockers.append(f"unexpected_stage_id:{expected_case_id}")
        if stage.get("status") != "pass":
            blockers.append(f"single_case_stage_not_pass:{expected_case_id}")
        if stage.get("result_kind") != "strict_pass_first_attempt":
            blockers.append(f"single_case_stage_not_strict_first_attempt:{expected_case_id}")
        if _list(stage.get("case_ids")) != [expected_case_id]:
            blockers.append(f"unexpected_case_ids:{expected_case_id}")
        if stage.get("failure_family") is not None:
            blockers.append(f"single_case_failure_family_present:{expected_case_id}")

    cases = [_dict(case) for case in _list(artifact.get("cases"))]
    case = cases[0] if len(cases) == 1 else {}
    if not case:
        blockers.append(f"unexpected_case_count:{expected_case_id}")
    else:
        if case.get("case_id") != expected_case_id:
            blockers.append(f"unexpected_case_id:{expected_case_id}")
        if case.get("case_contract_status") != "strict_pass":
            blockers.append(f"case_contract_not_strict_pass:{expected_case_id}")
        if case.get("verdict") != "pass":
            blockers.append(f"case_verdict_not_pass:{expected_case_id}")
        if case.get("failure_layer") is not None:
            blockers.append(f"case_failure_layer_present:{expected_case_id}")

    return blockers, stage, case


def _blocking_case_blockers(case: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    blockers: list[str] = []
    turns = [_dict(turn) for turn in _list(case.get("turns"))]
    if len(turns) != 2:
        blockers.append("blocking_case_unexpected_turn_count")
        return blockers, {}

    first_turn, second_turn = turns
    first_state_delta = _dict(first_turn.get("state_delta"))
    second_state_delta = _dict(second_turn.get("state_delta"))

    if first_turn.get("manager_final_action") != "ask_followup":
        blockers.append("blocking_turn1_final_action_not_ask_followup")
    if first_turn.get("workflow_effect") != "ask_followup":
        blockers.append("blocking_turn1_workflow_effect_not_ask_followup")
    if first_state_delta.get("canonical_commit") is not False:
        blockers.append("blocking_turn1_canonical_commit_present")
    if first_state_delta.get("ledger_updated") is not False:
        blockers.append("blocking_turn1_ledger_updated")
    if first_state_delta.get("new_meal_version_created") is not False:
        blockers.append("blocking_turn1_unexpected_meal_version")
    if _tool_names(first_turn):
        blockers.append("blocking_turn1_unexpected_tool_calls")
    first_remaining = _dict(first_turn.get("remaining_budget"))
    if first_remaining.get("status") != "ready":
        blockers.append("blocking_turn1_remaining_budget_not_ready")
    if first_remaining.get("consumed_kcal") != 0:
        blockers.append("blocking_turn1_consumed_kcal_not_zero")
    if first_remaining.get("meal_count") != 0:
        blockers.append("blocking_turn1_meal_count_not_zero")

    if second_turn.get("manager_final_action") != "commit":
        blockers.append("blocking_turn2_final_action_not_commit")
    if second_turn.get("workflow_effect") != "canonical_write":
        blockers.append("blocking_turn2_workflow_effect_not_canonical_write")
    if second_state_delta.get("canonical_commit") is not True:
        blockers.append("blocking_turn2_canonical_commit_missing")
    if second_state_delta.get("ledger_updated") is not True:
        blockers.append("blocking_turn2_ledger_not_updated")
    if second_state_delta.get("new_meal_version_created") is not True:
        blockers.append("blocking_turn2_new_version_missing")
    if second_state_delta.get("old_version_superseded") is not False:
        blockers.append("blocking_turn2_unexpected_supersede")
    if _tool_names(second_turn) != ["estimate_nutrition"]:
        blockers.append("blocking_turn2_unexpected_tool_inventory")

    model = _dict(_dict(case.get("debug_surface")).get("model"))
    same_truth = _dict(model.get("same_truth"))
    if same_truth.get("status") != "pass":
        blockers.append("blocking_same_truth_not_pass")
    pending_drafts = _list(model.get("pending_drafts"))
    if pending_drafts:
        blockers.append("blocking_pending_drafts_not_cleared")
    threads = _list(model.get("meal_threads"))
    if len(threads) != 1:
        blockers.append("blocking_unexpected_meal_thread_count")
        return blockers, {}

    thread = _dict(threads[0])
    active_version = _dict(thread.get("active_version"))
    if active_version.get("version_reason") != "new_intake":
        blockers.append("blocking_active_version_reason_not_new_intake")
    if _list(thread.get("superseded_versions")):
        blockers.append("blocking_unexpected_superseded_versions")
    observed = {
        "final_consumed_kcal": _dict(second_turn.get("remaining_budget")).get("consumed_kcal"),
        "final_remaining_kcal": _dict(second_turn.get("remaining_budget")).get("remaining_kcal"),
    }
    if same_truth.get("debug_model_consumed_kcal") != observed["final_consumed_kcal"]:
        blockers.append("blocking_same_truth_debug_model_kcal_mismatch")
    if same_truth.get("current_budget_consumed_kcal") != observed["final_consumed_kcal"]:
        blockers.append("blocking_same_truth_budget_kcal_mismatch")
    today_summary = _dict(model.get("today_summary"))
    if today_summary.get("consumed_kcal") != observed["final_consumed_kcal"]:
        blockers.append("blocking_today_summary_consumed_kcal_mismatch")
    if today_summary.get("remaining_kcal") != observed["final_remaining_kcal"]:
        blockers.append("blocking_today_summary_remaining_kcal_mismatch")
    return blockers, observed


def _correction_case_blockers(case: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    blockers: list[str] = []
    turns = [_dict(turn) for turn in _list(case.get("turns"))]
    if len(turns) != 4:
        blockers.append("correction_case_unexpected_turn_count")
        return blockers, {}

    turn1, turn2, turn3, turn4 = turns
    turn1_state = _dict(turn1.get("state_delta"))
    turn2_state = _dict(turn2.get("state_delta"))
    turn3_state = _dict(turn3.get("state_delta"))
    turn4_state = _dict(turn4.get("state_delta"))

    if turn1.get("manager_final_action") != "commit":
        blockers.append("correction_turn1_final_action_not_commit")
    if turn1.get("workflow_effect") != "canonical_write":
        blockers.append("correction_turn1_workflow_effect_not_canonical_write")
    if turn1_state.get("canonical_commit") is not True:
        blockers.append("correction_turn1_canonical_commit_missing")

    if turn2.get("manager_final_action") != "correction_applied":
        blockers.append("correction_turn2_final_action_not_correction_applied")
    if turn2.get("workflow_effect") != "correction_write":
        blockers.append("correction_turn2_workflow_effect_not_correction_write")
    if turn2_state.get("canonical_commit") is not True:
        blockers.append("correction_turn2_canonical_commit_missing")
    if turn2_state.get("old_version_superseded") is not True:
        blockers.append("correction_turn2_expected_supersede_missing")
    if _tool_names(turn2) != ["estimate_nutrition"]:
        blockers.append("correction_turn2_unexpected_tool_inventory")

    if turn3.get("manager_final_action") != "correction_applied":
        blockers.append("correction_turn3_final_action_not_correction_applied")
    if turn3.get("workflow_effect") != "correction_write":
        blockers.append("correction_turn3_workflow_effect_not_correction_write")
    if turn3_state.get("canonical_commit") is not True:
        blockers.append("correction_turn3_canonical_commit_missing")
    if turn3_state.get("old_version_superseded") is not True:
        blockers.append("correction_turn3_expected_supersede_missing")
    if _tool_names(turn3) != ["resolve_correction_target"]:
        blockers.append("correction_turn3_unexpected_tool_inventory")

    if turn4.get("workflow_effect") != "answer_remaining_budget":
        blockers.append("correction_turn4_workflow_effect_not_answer_remaining_budget")
    if turn4_state.get("canonical_commit") is not False:
        blockers.append("correction_turn4_unexpected_commit")
    if turn4_state.get("ledger_updated") is not False:
        blockers.append("correction_turn4_unexpected_ledger_update")
    if _tool_names(turn4):
        blockers.append("correction_turn4_unexpected_tool_calls")

    model = _dict(_dict(case.get("debug_surface")).get("model"))
    same_truth = _dict(model.get("same_truth"))
    if same_truth.get("status") != "pass":
        blockers.append("correction_same_truth_not_pass")

    correction_history = _list(model.get("correction_history"))
    if len(correction_history) != 2:
        blockers.append("correction_history_count_mismatch")
    elif not _list(_dict(correction_history[-1]).get("removed_item_names")):
        blockers.append("correction_remove_item_not_recorded")

    threads = _list(model.get("meal_threads"))
    if len(threads) != 1:
        blockers.append("correction_unexpected_meal_thread_count")
        return blockers, {}

    thread = _dict(threads[0])
    active_version = _dict(thread.get("active_version"))
    if active_version.get("version_reason") != "correction":
        blockers.append("correction_active_version_reason_not_correction")
    if active_version.get("parent_version_id") in (None, ""):
        blockers.append("correction_active_version_parent_missing")
    if len(_list(thread.get("superseded_versions"))) < 2:
        blockers.append("correction_superseded_versions_missing")

    observed = {
        "final_consumed_kcal": _dict(turn4.get("remaining_budget")).get("consumed_kcal"),
        "final_remaining_kcal": _dict(turn4.get("remaining_budget")).get("remaining_kcal"),
    }
    if same_truth.get("debug_model_consumed_kcal") != observed["final_consumed_kcal"]:
        blockers.append("correction_same_truth_debug_model_kcal_mismatch")
    if same_truth.get("current_budget_consumed_kcal") != observed["final_consumed_kcal"]:
        blockers.append("correction_same_truth_budget_kcal_mismatch")
    today_summary = _dict(model.get("today_summary"))
    if today_summary.get("consumed_kcal") != observed["final_consumed_kcal"]:
        blockers.append("correction_today_summary_consumed_kcal_mismatch")
    if today_summary.get("remaining_kcal") != observed["final_remaining_kcal"]:
        blockers.append("correction_today_summary_remaining_kcal_mismatch")
    if active_version.get("total_kcal") != observed["final_consumed_kcal"]:
        blockers.append("correction_active_version_total_kcal_mismatch")
    items = _list(active_version.get("items"))
    if len(items) != 1:
        blockers.append("correction_unexpected_active_item_count")
    return blockers, observed


def build_rt10e_blocking_clarify_correction_live_probe_gate(
    *,
    blocking_clarify_artifact: dict[str, Any],
    correction_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    blocking_artifact = _dict(blocking_clarify_artifact)
    correction_artifact_dict = _dict(correction_artifact)

    blocking_blockers, blocking_stage, blocking_case = _artifact_blockers(
        blocking_artifact,
        expected_case_id=BLOCKING_CASE_ID,
    )
    correction_blockers, correction_stage, correction_case = _artifact_blockers(
        correction_artifact_dict,
        expected_case_id=CORRECTION_CASE_ID,
    )

    blocking_case_specific, blocking_observed = _blocking_case_blockers(blocking_case) if blocking_case else (["blocking_case_missing"], {})
    correction_case_specific, correction_observed = _correction_case_blockers(correction_case) if correction_case else (["correction_case_missing"], {})

    blockers = [
        *blocking_blockers,
        *blocking_case_specific,
        *correction_blockers,
        *correction_case_specific,
    ]

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt10e_blocking_clarify_correction_live_probe_gate",
        "claim_scope": "manager_runtime_blocking_clarify_correction_live_probe",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt10e_blocking_clarify_correction_live_probe",
        "pass_type": "live_diagnostic",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["D", "K"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "blocking_case_id": BLOCKING_CASE_ID,
            "correction_case_id": CORRECTION_CASE_ID,
            "required_stage_id": REQUIRED_STAGE_ID,
            "blocking_followup_must_not_commit": True,
            "blocking_resolution_requires_estimate_nutrition": True,
            "correction_remove_item_requires_target_resolution": True,
            "correction_final_budget_query_must_be_read_only": True,
            "blocking_final_consumed_kcal": blocking_observed.get("final_consumed_kcal"),
            "correction_final_consumed_kcal": correction_observed.get("final_consumed_kcal"),
        },
        "blocking_clarify_stage": blocking_stage,
        "blocking_clarify_case": blocking_case,
        "correction_stage": correction_stage,
        "correction_case": correction_case,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT10e blocking-clarify and correction live probe gate artifact."
    )
    parser.add_argument(
        "--blocking-clarify-artifact",
        type=Path,
        required=True,
        help="Path to the live single-case artifact for luwei_bare_to_listed_basket.",
    )
    parser.add_argument(
        "--correction-artifact",
        type=Path,
        required=True,
        help="Path to the live single-case artifact for chinese_chicken_rice_correction_removal_debug.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT10e gate artifact JSON.",
    )
    args = parser.parse_args(argv)

    blocking_clarify_artifact = json.loads(args.blocking_clarify_artifact.read_text(encoding="utf-8"))
    correction_artifact = json.loads(args.correction_artifact.read_text(encoding="utf-8"))
    gate_artifact = build_rt10e_blocking_clarify_correction_live_probe_gate(
        blocking_clarify_artifact=blocking_clarify_artifact,
        correction_artifact=correction_artifact,
        output_path=args.output,
    )
    write_json_artifact(args.output, gate_artifact)
    print(args.output)
    return 0 if gate_artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
