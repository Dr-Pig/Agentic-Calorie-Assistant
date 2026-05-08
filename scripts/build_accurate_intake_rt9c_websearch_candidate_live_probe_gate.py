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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt9c_websearch_candidate_live_probe_gate.json"
EXPECTED_PROVIDER_PROFILE_ID = "builderspace-grok-4-fast-websearch-packet-smoke"
EXPECTED_PROVIDER_MODEL = "grok-4-fast"
EXPECTED_CASE_COUNT = 6
REQUIRED_NON_CLAIMS = {
    "no_readiness_claim",
    "no_production_model_selection",
    "no_self_use_approval",
    "no_runtime_mutation",
    "no_websearch_runtime_truth",
    "no_exact_card_truth_promotion",
    "no_fooddb_truth_promotion",
    "no_kimi_call",
}
REQUIRED_FALSE_FLAGS = (
    "readiness_claimed",
    "self_use_approved",
    "production_selected",
    "runtime_mutation_attempted",
    "runtime_truth_changed",
    "manager_context_changed",
    "packetizer_format_changed",
)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def build_rt9c_websearch_candidate_live_probe_gate(
    *,
    live_packet_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    artifact = _dict(live_packet_artifact)
    blockers: list[str] = []

    if artifact.get("artifact_type") != "accurate_intake_grokfast_websearch_packet_smoke":
        blockers.append("unsupported_live_packet_artifact_type")
    if artifact.get("classification") != "live_diagnostic_only":
        blockers.append("classification_not_live_diagnostic_only")
    if artifact.get("status") != "pass":
        blockers.append(f"artifact_status_not_pass:{artifact.get('status')}")
    if artifact.get("failure_family"):
        blockers.append(f"artifact_failure_family_present:{artifact.get('failure_family')}")
    if artifact.get("live_provider_used") is not True:
        blockers.append("live_provider_not_used")

    provider_profile = _dict(artifact.get("provider_profile"))
    if provider_profile.get("provider_profile_id") != EXPECTED_PROVIDER_PROFILE_ID:
        blockers.append(
            f"unexpected_provider_profile_id:{provider_profile.get('provider_profile_id')}"
        )
    if provider_profile.get("model") != EXPECTED_PROVIDER_MODEL:
        blockers.append(f"unexpected_provider_model:{provider_profile.get('model')}")

    for flag in REQUIRED_FALSE_FLAGS:
        if artifact.get(flag) is not False:
            blockers.append(f"flag_not_false:{flag}")

    non_claims = set(str(item) for item in _list(artifact.get("non_claims")) if item)
    missing_non_claims = sorted(REQUIRED_NON_CLAIMS - non_claims)
    blockers.extend(f"missing_non_claim:{item}" for item in missing_non_claims)

    summary = _dict(artifact.get("summary"))
    observed_cases = [_dict(case) for case in _list(artifact.get("cases"))]
    if len(observed_cases) != EXPECTED_CASE_COUNT:
        blockers.append("unexpected_case_count")
    if summary.get("case_count") != EXPECTED_CASE_COUNT:
        blockers.append("summary_case_count_mismatch")
    if summary.get("pass_count") != EXPECTED_CASE_COUNT:
        blockers.append("summary_pass_count_mismatch")
    if summary.get("fail_count") != 0:
        blockers.append("summary_fail_count_not_zero")
    if _list(summary.get("failure_families")):
        blockers.append("summary_failure_families_present")

    case_summaries: list[dict[str, Any]] = []
    for case in observed_cases:
        packet_id = str(case.get("packet_id") or "")
        failure_families = [str(item) for item in _list(case.get("failure_families")) if item]
        if case.get("status") != "pass":
            blockers.append(f"case_not_pass:{packet_id}")
        if failure_families:
            blockers.append(f"case_failure_families_present:{packet_id}")
        if case.get("runtime_mutation_attempted") is not False:
            blockers.append(f"case_runtime_mutation_attempted:{packet_id}")
        if case.get("manager_action") != "final":
            blockers.append(f"case_manager_action_not_final:{packet_id}")
        final_action = case.get("final_action")
        if final_action not in (None, "answer_only"):
            blockers.append(f"case_final_action_not_candidate_review_safe:{packet_id}")
        if int(case.get("invented_evidence_ref_count") or 0) != 0:
            blockers.append(f"case_invented_evidence_refs_present:{packet_id}")
        case_summaries.append(
            {
                "packet_id": packet_id,
                "status": case.get("status"),
                "manager_action": case.get("manager_action"),
                "final_action": final_action,
                "used_evidence_ref_count": case.get("used_evidence_ref_count")
                if case.get("used_evidence_ref_count") is not None
                else len(_list(case.get("used_evidence_refs"))),
                "allowed_evidence_ref_count": case.get("allowed_evidence_ref_count")
                if case.get("allowed_evidence_ref_count") is not None
                else len(_list(case.get("allowed_evidence_refs"))),
                "invented_evidence_ref_count": case.get("invented_evidence_ref_count")
                if case.get("invented_evidence_ref_count") is not None
                else 0,
            }
        )

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt9c_websearch_candidate_live_probe_gate",
        "claim_scope": "manager_runtime_websearch_candidate_live_probe",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt9c_websearch_candidate_live_probe",
        "pass_type": "live_diagnostic",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D"],
        "status": _status(blockers),
        "blockers": blockers,
        "source_artifact_summary": {
            "status": artifact.get("status"),
            "classification": artifact.get("classification"),
            "provider_profile_id": provider_profile.get("provider_profile_id"),
            "provider_profile_model": provider_profile.get("model"),
            "failure_family": artifact.get("failure_family"),
            "live_provider_used": artifact.get("live_provider_used"),
        },
        "summary": {
            "expected_case_count": EXPECTED_CASE_COUNT,
            "required_provider_profile_id": EXPECTED_PROVIDER_PROFILE_ID,
            "required_provider_model": EXPECTED_PROVIDER_MODEL,
            "non_claim_flags_preserved": not missing_non_claims,
            "forbidden_runtime_changes_preserved": not any(
                blocker.startswith("flag_not_false:") for blocker in blockers
            ),
        },
        "cases": case_summaries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT9c WebSearch candidate live probe gate artifact."
    )
    parser.add_argument(
        "--source-artifact",
        type=Path,
        required=True,
        help="Path to an accurate_intake_grokfast_websearch_packet_smoke live artifact.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT9c gate artifact JSON.",
    )
    args = parser.parse_args(argv)

    source_artifact = json.loads(args.source_artifact.read_text(encoding="utf-8"))
    gate_artifact = build_rt9c_websearch_candidate_live_probe_gate(
        live_packet_artifact=source_artifact,
        output_path=args.output,
    )
    write_json_artifact(args.output, gate_artifact)
    print(args.output)
    return 0 if gate_artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
