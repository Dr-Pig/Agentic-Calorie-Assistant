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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt14a_live_ladder_foundation_gate.json"
REQUIRED_STAGE_IDS = ("provider_health_smoke", "schema_contract_probe")
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


def build_rt14a_live_ladder_foundation_gate(
    *,
    live_diagnostic_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    artifact = _dict(live_diagnostic_artifact)
    blockers: list[str] = []

    if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        blockers.append("unsupported_live_diagnostic_artifact_type")

    stages = [_dict(stage) for stage in list(artifact.get("stages") or [])]
    stage_by_id = {
        str(stage.get("stage_id") or ""): stage for stage in stages if stage.get("stage_id")
    }

    missing_stage_ids = [stage_id for stage_id in REQUIRED_STAGE_IDS if stage_id not in stage_by_id]
    blockers.extend(f"missing_stage:{stage_id}" for stage_id in missing_stage_ids)

    foundation_failure_families: list[str] = []
    for stage_id in REQUIRED_STAGE_IDS:
        stage = stage_by_id.get(stage_id, {})
        if stage and stage.get("status") != "pass":
            blockers.append(f"stage_not_pass:{stage_id}")
            failure_family = str(stage.get("failure_family") or "").strip()
            if failure_family:
                foundation_failure_families.append(failure_family)
    blockers.extend(
        f"foundation_failure_family:{failure_family}"
        for failure_family in foundation_failure_families
    )

    non_claim_violations = [
        flag for flag in REQUIRED_NON_CLAIM_FLAGS if artifact.get(flag) is True
    ]
    blockers.extend(f"non_claim_violation:{flag}" for flag in non_claim_violations)

    provider_mode = str(artifact.get("provider_mode") or "")
    live_invoked = bool(artifact.get("live_invoked"))
    pass_type = "live_diagnostic" if live_invoked else "contract"

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt14a_live_ladder_foundation_gate",
        "claim_scope": "manager_runtime_limited_live_foundation_gate",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt14a_provider_health_schema_live_foundation",
        "pass_type": pass_type,
        "runtime_backed": False,
        "live_llm_invoked": live_invoked,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D", "E", "J", "K"],
        "status": _status(blockers),
        "blockers": blockers,
        "source_artifact_summary": {
            "provider_mode": provider_mode,
            "live_invoked": live_invoked,
            "provider_profile_id": artifact.get("provider_profile_id"),
            "provider_profile_model": artifact.get("provider_profile_model"),
            "failure_family": artifact.get("failure_family"),
        },
        "summary": {
            "required_stage_ids": list(REQUIRED_STAGE_IDS),
            "present_stage_ids": [stage_id for stage_id in REQUIRED_STAGE_IDS if stage_id in stage_by_id],
            "passed_stage_ids": [
                stage_id
                for stage_id in REQUIRED_STAGE_IDS
                if stage_by_id.get(stage_id, {}).get("status") == "pass"
            ],
            "non_claim_flags_preserved": not non_claim_violations,
        },
        "stages": [stage_by_id[stage_id] for stage_id in REQUIRED_STAGE_IDS if stage_id in stage_by_id],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT14a provider-health/schema live foundation gate artifact."
    )
    parser.add_argument(
        "--source-artifact",
        type=Path,
        required=True,
        help="Path to an accurate_intake_mvp_live_diagnostic artifact.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT14a gate artifact JSON.",
    )
    args = parser.parse_args(argv)

    source_artifact = json.loads(args.source_artifact.read_text(encoding="utf-8"))
    artifact = build_rt14a_live_ladder_foundation_gate(
        live_diagnostic_artifact=source_artifact,
        output_path=args.output,
    )
    write_json_artifact(args.output, artifact)
    print(args.output)
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
