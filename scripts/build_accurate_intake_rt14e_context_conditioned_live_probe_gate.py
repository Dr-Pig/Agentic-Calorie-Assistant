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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt14e_context_conditioned_live_probe_gate.json"
REQUIRED_STAGE_ID = "single_case_live_probe"
REQUIRED_NON_CLAIM_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "live_provider_used_as_truth",
    "runtime_web_activation_approved",
)
REQUIRED_CASE_EXPECTATIONS = {
    "today_consumed_query_only": {
        "remaining_status": "ready",
        "daily_target_present": True,
        "remaining_present": True,
    },
    "no_plan_consumed_without_budget_target": {
        "remaining_status": "onboarding_required",
        "daily_target_present": False,
        "remaining_present": False,
    },
}
FORBIDDEN_TOOL_NAMES = {
    "estimate_nutrition",
    "resolve_correction_target",
    "compare_against_budget",
}
ALLOWED_QUERY_WORKFLOW_EFFECTS = {"answer_only", "answer_remaining_budget"}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _tool_names(case: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for turn in _list(case.get("turns")):
        turn_item = _dict(turn)
        for round_item in _list(turn_item.get("manager_rounds")):
            round_dict = _dict(round_item)
            decision = _dict(round_dict.get("decision"))
            for call in _list(decision.get("tool_calls")):
                call_dict = _dict(call)
                name = str(call_dict.get("name") or "").strip()
                if name:
                    names.append(name)
    return names


def _case_blockers(case_id: str, case: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    expected = REQUIRED_CASE_EXPECTATIONS[case_id]
    if str(case.get("case_id") or "") != case_id:
        blockers.append(f"unexpected_case_id:{case.get('case_id')}")
        return blockers
    if str(case.get("case_contract_status") or "") != "strict_pass":
        blockers.append(f"case_not_strict_pass:{case_id}")
    if str(case.get("verdict") or "") != "pass":
        blockers.append(f"case_verdict_not_pass:{case_id}")
    if case.get("failure_layer") is not None:
        blockers.append(f"case_failure_layer_present:{case_id}")

    turns = _list(case.get("turns"))
    turn = _dict(turns[0]) if turns else {}
    state_delta = _dict(turn.get("state_delta"))
    if state_delta.get("canonical_commit") is not False:
        blockers.append(f"query_only_mutated_state:{case_id}")
    if str(turn.get("workflow_effect") or "") not in ALLOWED_QUERY_WORKFLOW_EFFECTS:
        blockers.append(f"workflow_effect_mismatch:{case_id}")

    forbidden_calls = sorted({name for name in _tool_names(case) if name in FORBIDDEN_TOOL_NAMES})
    blockers.extend(f"forbidden_tool_call:{case_id}:{name}" for name in forbidden_calls)

    same_truth = _dict(_dict(_dict(case.get("debug_surface")).get("model")).get("same_truth"))
    if same_truth and str(same_truth.get("status") or "") != "pass":
        blockers.append(f"same_truth_not_pass:{case_id}")

    remaining_budget = _dict(turn.get("remaining_budget"))
    if str(remaining_budget.get("status") or "") != expected["remaining_status"]:
        blockers.append(f"remaining_status_mismatch:{case_id}")

    daily_target_present = remaining_budget.get("daily_target_kcal") is not None
    if daily_target_present is not expected["daily_target_present"]:
        blockers.append(f"daily_target_presence_mismatch:{case_id}")

    remaining_present = remaining_budget.get("remaining_kcal") is not None
    if remaining_present is not expected["remaining_present"]:
        blockers.append(f"remaining_presence_mismatch:{case_id}")

    return blockers


def _artifact_blockers(artifact: dict[str, Any], *, expected_case_id: str) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []

    if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        blockers.append("unsupported_live_diagnostic_artifact_type")

    if artifact.get("provider_mode") != "live":
        blockers.append("provider_mode_not_live")
    if artifact.get("live_invoked") is not True:
        blockers.append("live_not_invoked")

    stages = [_dict(stage) for stage in _list(artifact.get("stages"))]
    stage = {}
    for candidate in stages:
        if str(candidate.get("stage_id") or "") == REQUIRED_STAGE_ID:
            stage = candidate
            break
    if not stage:
        blockers.append(f"missing_stage:{expected_case_id}:{REQUIRED_STAGE_ID}")
    else:
        if stage.get("status") != "pass":
            blockers.append(f"stage_not_pass:{expected_case_id}:{REQUIRED_STAGE_ID}")
        if str(stage.get("result_kind") or "") != "strict_pass_first_attempt":
            blockers.append(f"stage_not_strict_first_attempt:{expected_case_id}:{REQUIRED_STAGE_ID}")
        if _list(stage.get("case_ids")) != [expected_case_id]:
            blockers.append(f"unexpected_case_ids:{expected_case_id}:{REQUIRED_STAGE_ID}")
        failure_family = str(stage.get("failure_family") or "").strip()
        if failure_family:
            blockers.append(f"single_case_failure_family:{expected_case_id}:{failure_family}")

    cases = [_dict(case) for case in _list(artifact.get("cases"))]
    if len(cases) != 1:
        blockers.append(f"unexpected_case_count:{expected_case_id}")
        case = {}
    else:
        case = cases[0]
        blockers.extend(_case_blockers(expected_case_id, case))

    non_claim_violations = [
        flag for flag in REQUIRED_NON_CLAIM_FLAGS if artifact.get(flag) is True
    ]
    blockers.extend(f"non_claim_violation:{expected_case_id}:{flag}" for flag in non_claim_violations)

    return blockers, stage, case


def build_rt14e_context_conditioned_live_probe_gate(
    *,
    ready_case_artifact: dict[str, Any],
    no_plan_case_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    ready_blockers, ready_stage, ready_case = _artifact_blockers(
        ready_case_artifact,
        expected_case_id="today_consumed_query_only",
    )
    no_plan_blockers, no_plan_stage, no_plan_case = _artifact_blockers(
        no_plan_case_artifact,
        expected_case_id="no_plan_consumed_without_budget_target",
    )
    blockers = [*ready_blockers, *no_plan_blockers]

    ready_remaining = _dict(_dict(_list(ready_case.get("turns"))[0] if _list(ready_case.get("turns")) else {}).get("remaining_budget"))
    no_plan_remaining = _dict(_dict(_list(no_plan_case.get("turns"))[0] if _list(no_plan_case.get("turns")) else {}).get("remaining_budget"))
    if ready_remaining.get("status") == no_plan_remaining.get("status"):
        blockers.append("context_condition_not_distinguishing_status")

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt14e_context_conditioned_live_probe_gate",
        "claim_scope": "manager_runtime_context_conditioned_live_probe",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt14e_context_conditioned_live_probe",
        "pass_type": "live_diagnostic",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["A", "E", "J"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "required_stage_id": REQUIRED_STAGE_ID,
            "ready_case_id": "today_consumed_query_only",
            "no_plan_case_id": "no_plan_consumed_without_budget_target",
            "required_result_kind": "strict_pass_first_attempt",
            "forbidden_tool_names": sorted(FORBIDDEN_TOOL_NAMES),
            "context_condition_must_change_remaining_status": True,
        },
        "ready_case_stage": ready_stage,
        "ready_case": ready_case,
        "no_plan_case_stage": no_plan_stage,
        "no_plan_case": no_plan_case,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT14e context-conditioned live probe gate artifact."
    )
    parser.add_argument(
        "--ready-case-artifact",
        type=Path,
        required=True,
        help="Path to the live single-case artifact for today_consumed_query_only.",
    )
    parser.add_argument(
        "--no-plan-case-artifact",
        type=Path,
        required=True,
        help="Path to the live single-case artifact for no_plan_consumed_without_budget_target.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT14e gate artifact JSON.",
    )
    args = parser.parse_args(argv)

    ready_case_artifact = json.loads(args.ready_case_artifact.read_text(encoding="utf-8"))
    no_plan_case_artifact = json.loads(args.no_plan_case_artifact.read_text(encoding="utf-8"))
    gate_artifact = build_rt14e_context_conditioned_live_probe_gate(
        ready_case_artifact=ready_case_artifact,
        no_plan_case_artifact=no_plan_case_artifact,
        output_path=args.output,
    )
    write_json_artifact(args.output, gate_artifact)
    print(args.output)
    return 0 if gate_artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
