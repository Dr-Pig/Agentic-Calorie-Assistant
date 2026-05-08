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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt14d_single_case_tool_choice_live_probe_gate.json"
REQUIRED_STAGE_ID = "single_case_live_probe"
REQUIRED_CASE_ID = "today_consumed_query_only"
REQUIRED_NON_CLAIM_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "live_provider_used_as_truth",
    "runtime_web_activation_approved",
)
FORBIDDEN_TOOL_NAMES = {
    "estimate_nutrition",
    "resolve_correction_target",
    "compare_against_budget",
}


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


def build_rt14d_single_case_tool_choice_live_probe_gate(
    *,
    live_diagnostic_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    artifact = _dict(live_diagnostic_artifact)
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
        blockers.append(f"missing_stage:{REQUIRED_STAGE_ID}")
    else:
        if stage.get("status") != "pass":
            blockers.append(f"stage_not_pass:{REQUIRED_STAGE_ID}")
        if str(stage.get("result_kind") or "") != "strict_pass_first_attempt":
            blockers.append(f"stage_not_strict_first_attempt:{REQUIRED_STAGE_ID}")
        if _list(stage.get("case_ids")) != [REQUIRED_CASE_ID]:
            blockers.append(f"unexpected_case_ids:{REQUIRED_STAGE_ID}")
        failure_family = str(stage.get("failure_family") or "").strip()
        if failure_family:
            blockers.append(f"single_case_failure_family:{failure_family}")

    cases = [_dict(case) for case in _list(artifact.get("cases"))]
    if len(cases) != 1:
        blockers.append("unexpected_case_count")
        case = {}
    else:
        case = cases[0]
        if str(case.get("case_id") or "") != REQUIRED_CASE_ID:
            blockers.append(f"unexpected_case_id:{case.get('case_id')}")
        if str(case.get("case_contract_status") or "") != "strict_pass":
            blockers.append("case_not_strict_pass")
        if str(case.get("verdict") or "") != "pass":
            blockers.append("case_verdict_not_pass")
        if case.get("failure_layer") is not None:
            blockers.append("case_failure_layer_present")
        turn = _dict(_list(case.get("turns"))[0]) if _list(case.get("turns")) else {}
        if _dict(turn.get("state_delta")).get("canonical_commit") is not False:
            blockers.append("query_only_mutated_state")
        if str(turn.get("workflow_effect") or "") != "answer_only":
            blockers.append("workflow_effect_not_answer_only")
        forbidden_calls = sorted({name for name in _tool_names(case) if name in FORBIDDEN_TOOL_NAMES})
        blockers.extend(f"forbidden_tool_call:{name}" for name in forbidden_calls)
        same_truth = _dict(_dict(_dict(case.get("debug_surface")).get("model")).get("same_truth"))
        if same_truth and str(same_truth.get("status") or "") != "pass":
            blockers.append("same_truth_not_pass")

    non_claim_violations = [
        flag for flag in REQUIRED_NON_CLAIM_FLAGS if artifact.get(flag) is True
    ]
    blockers.extend(f"non_claim_violation:{flag}" for flag in non_claim_violations)

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt14d_single_case_tool_choice_live_probe_gate",
        "claim_scope": "manager_runtime_single_case_tool_choice_live_probe",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt14d_single_case_tool_choice_live_probe",
        "pass_type": "live_diagnostic",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["E"],
        "status": _status(blockers),
        "blockers": blockers,
        "source_artifact_summary": {
            "provider_mode": artifact.get("provider_mode"),
            "live_invoked": artifact.get("live_invoked"),
            "provider_profile_id": artifact.get("provider_profile_id"),
            "provider_profile_model": artifact.get("provider_profile_model"),
            "failure_family": artifact.get("failure_family"),
        },
        "summary": {
            "required_stage_id": REQUIRED_STAGE_ID,
            "required_case_id": REQUIRED_CASE_ID,
            "required_stage_status": "pass",
            "required_result_kind": "strict_pass_first_attempt",
            "non_claim_flags_preserved": not non_claim_violations,
            "forbidden_tool_names": sorted(FORBIDDEN_TOOL_NAMES),
        },
        "stage": stage,
        "case": case,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT14d single-case tool-choice live probe gate artifact."
    )
    parser.add_argument(
        "--source-artifact",
        type=Path,
        required=True,
        help="Path to an accurate_intake_mvp_live_diagnostic single-case artifact.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT14d gate artifact JSON.",
    )
    args = parser.parse_args(argv)

    source_artifact = json.loads(args.source_artifact.read_text(encoding="utf-8"))
    gate_artifact = build_rt14d_single_case_tool_choice_live_probe_gate(
        live_diagnostic_artifact=source_artifact,
        output_path=args.output,
    )
    write_json_artifact(args.output, gate_artifact)
    print(args.output)
    return 0 if gate_artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
