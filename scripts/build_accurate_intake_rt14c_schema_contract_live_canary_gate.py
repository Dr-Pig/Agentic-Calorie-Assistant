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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt14c_schema_contract_live_canary_gate.json"
REQUIRED_STAGE_ID = "schema_contract_probe"
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


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def build_rt14c_schema_contract_live_canary_gate(
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

    stages = [_dict(stage) for stage in list(artifact.get("stages") or [])]
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
        failure_family = str(stage.get("failure_family") or "").strip()
        if failure_family:
            blockers.append(f"schema_failure_family:{failure_family}")

    non_claim_violations = [
        flag for flag in REQUIRED_NON_CLAIM_FLAGS if artifact.get(flag) is True
    ]
    blockers.extend(f"non_claim_violation:{flag}" for flag in non_claim_violations)

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt14c_schema_contract_live_canary_gate",
        "claim_scope": "manager_runtime_schema_contract_live_canary",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt14c_schema_contract_live_canary",
        "pass_type": "live_diagnostic",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["A", "B", "C", "D", "E", "G", "H", "J", "K"],
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
            "required_stage_status": "pass",
            "required_result_kind": "strict_pass_first_attempt",
            "non_claim_flags_preserved": not non_claim_violations,
        },
        "stage": stage,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT14c schema-contract live canary gate artifact."
    )
    parser.add_argument(
        "--source-artifact",
        type=Path,
        required=True,
        help="Path to an accurate_intake_mvp_live_diagnostic schema-contract artifact.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT14c gate artifact JSON.",
    )
    args = parser.parse_args(argv)

    source_artifact = json.loads(args.source_artifact.read_text(encoding="utf-8"))
    gate_artifact = build_rt14c_schema_contract_live_canary_gate(
        live_diagnostic_artifact=source_artifact,
        output_path=args.output,
    )
    write_json_artifact(args.output, gate_artifact)
    print(args.output)
    return 0 if gate_artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
