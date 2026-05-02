from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.contracts.readiness_claim import build_readiness_claim


DEFAULT_LIVE_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic.json"
DEFAULT_OFFLINE_REPLAY_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_offline_shadow_replay.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"

DECISION_OPTION_IDS = (
    "stay_diagnostic",
    "repeat_single_profile_diagnostic",
    "offline_shadow_replay",
    "prepare_private_self_use_candidate",
    "defer_to_local_mvp",
)


def build_accurate_intake_live_decision_pack(
    live_artifact: dict[str, Any],
    *,
    offline_replay_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_integrity = _input_integrity(live_artifact)
    evidence_summary = _evidence_summary(live_artifact)
    offline_replay_summary = _offline_replay_summary(offline_replay_artifact)
    selected_option, selection_reason = _select_option(
        input_integrity=input_integrity,
        evidence_summary=evidence_summary,
        offline_replay_summary=offline_replay_summary,
    )
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_live_decision_pack",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_artifact_type": live_artifact.get("artifact_type"),
            "claim_scope": "live_diagnostic_decision_pack",
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "private_self_use_candidate_prepared": selected_option == "prepare_private_self_use_candidate",
            "production_selected": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "shadow_or_canary_approved": False,
            "input_integrity": input_integrity,
            "evidence_summary": evidence_summary,
            "offline_replay_summary": offline_replay_summary,
            "decision_options_ordered": list(DECISION_OPTION_IDS),
            "decision_options": _decision_options(),
            "selected_option": selected_option,
            "selection_reason": selection_reason,
            "requires_human_approval_for_private_self_use": selected_option == "prepare_private_self_use_candidate",
            "decision_boundary": {
                "live_diagnostic_is_product_readiness": False,
                "repaired_pass_unlocks_private_self_use": False,
                "single_live_run_unlocks_private_self_use": False,
                "runtime_web_activation_allowed": False,
                "mutation_rollout_allowed": False,
                "production_manager_selected": False,
                "raw_text_routing_allowed": False,
            },
        }
    )


def write_accurate_intake_live_decision_pack(
    *,
    live_artifact_path: Path = DEFAULT_LIVE_ARTIFACT,
    offline_replay_artifact_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    live_artifact = json.loads(live_artifact_path.read_text(encoding="utf-8"))
    offline_replay_artifact = None
    if offline_replay_artifact_path is not None and offline_replay_artifact_path.exists():
        offline_replay_artifact = json.loads(offline_replay_artifact_path.read_text(encoding="utf-8"))
    pack = build_accurate_intake_live_decision_pack(
        live_artifact,
        offline_replay_artifact=offline_replay_artifact,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "accurate_intake_mvp_live_decision_pack.json"
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _select_option(
    *,
    input_integrity: dict[str, Any],
    evidence_summary: dict[str, Any],
    offline_replay_summary: dict[str, Any],
) -> tuple[str, str]:
    if input_integrity.get("passed") is not True:
        return "stay_diagnostic", "input_integrity_blocked"
    if evidence_summary.get("environment_or_provider_blocker") is True:
        return "stay_diagnostic", "environment_or_provider_blocker"
    if evidence_summary.get("timeout_count", 0) > 0:
        return "repeat_single_profile_diagnostic", "timeout_evidence_incomplete"
    if evidence_summary.get("contract_fail_count", 0) > 0:
        return "repeat_single_profile_diagnostic", "live_diagnostic_contract_failures"
    if evidence_summary.get("repaired_pass_count", 0) > 0:
        return "repeat_single_profile_diagnostic", "live_clean_but_repair_dependent"
    if evidence_summary.get("strict_pass_count", 0) == evidence_summary.get("case_count", 0) and evidence_summary.get("case_count", 0) > 0:
        if offline_replay_summary.get("present") is not True:
            return "offline_shadow_replay", "single_live_run_requires_offline_replay_before_private_self_use_candidate"
        if offline_replay_summary.get("integrity_passed") is not True:
            return "offline_shadow_replay", "offline_replay_integrity_blocked"
        if offline_replay_summary.get("strict_replay_ready") is True:
            return "prepare_private_self_use_candidate", "strict_live_diagnostic_with_replay_evidence"
        return "offline_shadow_replay", "offline_replay_not_strict"
    return "defer_to_local_mvp", "live_diagnostic_not_clean"


def _input_integrity(live_artifact: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if live_artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        blockers.append("input_artifact_type_invalid")
    for key in (
        "readiness_claimed",
        "product_readiness_claimed",
        "private_self_use_approved",
        "production_selected",
        "mutation_rollout_approved",
        "runtime_web_activation_approved",
        "live_provider_used_as_truth",
    ):
        if live_artifact.get(key) is True:
            blockers.append(f"input_{key}")
    return {"passed": not blockers, "blockers": sorted(set(blockers))}


def _evidence_summary(live_artifact: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(live_artifact.get("summary"))
    repaired_cases = _repaired_cases(live_artifact)
    failure_families = _string_list(summary.get("failure_families"))
    root_failure_family = str(live_artifact.get("failure_family") or "")
    if root_failure_family:
        failure_families = sorted(set([*failure_families, root_failure_family]))
    return {
        "live_invoked": live_artifact.get("live_invoked") is True,
        "case_count": int(summary.get("case_count") or len(_list(live_artifact.get("cases")))),
        "strict_pass_count": int(summary.get("strict_pass_count") or 0),
        "repaired_pass_count": int(summary.get("repaired_pass_count") or 0),
        "contract_fail_count": int(summary.get("contract_fail_count") or 0),
        "timeout_count": int(summary.get("timeout_count") or 0),
        "provider_timeout_count": int(summary.get("provider_timeout_count") or 0),
        "failure_layers": _string_list(summary.get("failure_layers")),
        "failure_families": failure_families,
        "environment_or_provider_blocker": "environment_or_provider_blocker" in failure_families,
        "repaired_case_ids": [str(item["case_id"]) for item in repaired_cases],
        "repaired_cases": repaired_cases,
    }


def _offline_replay_summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {
            "present": False,
            "integrity_passed": False,
            "strict_replay_ready": False,
            "sample_run_count": 0,
            "repaired_pass_count": 0,
            "timeout_count": 0,
        }
    summary = _dict(artifact.get("summary"))
    integrity = _dict(artifact.get("input_integrity"))
    return {
        "present": artifact.get("artifact_type") == "accurate_intake_mvp_offline_shadow_replay",
        "integrity_passed": integrity.get("passed") is True,
        "strict_replay_ready": (
            summary.get("strict_replay_ready") is True
            and int(summary.get("sample_run_count") or 0) >= 3
            and int(summary.get("repaired_pass_count") or 0) == 0
            and int(summary.get("timeout_count") or 0) == 0
        ),
        "sample_run_count": int(summary.get("sample_run_count") or 0),
        "repaired_pass_count": int(summary.get("repaired_pass_count") or 0),
        "timeout_count": int(summary.get("timeout_count") or 0),
    }


def _repaired_cases(live_artifact: dict[str, Any]) -> list[dict[str, str | None]]:
    repaired: list[dict[str, str | None]] = []
    for case in _list(live_artifact.get("cases")):
        item = _dict(case)
        if str(item.get("case_contract_status") or "") != "repaired_pass":
            continue
        repaired.append(
            {
                "case_id": str(item.get("case_id") or ""),
                "repair_failure_family": _optional_string(item.get("repair_failure_family")),
                "failed_invariant": _optional_string(item.get("failed_invariant")),
            }
        )
    return repaired


def _decision_options() -> list[dict[str, Any]]:
    return [
        {
            "option_id": "stay_diagnostic",
            "description": "Keep Accurate Intake live as diagnostic-only evidence collection.",
            "auto_activation_allowed": True,
            "blocked_claims": ["product_ready", "private_self_use_ready", "mutation_ready"],
        },
        {
            "option_id": "repeat_single_profile_diagnostic",
            "description": "Repeat the same diagnostic profile because the current run has repair, timeout, or contract instability.",
            "auto_activation_allowed": True,
            "blocked_claims": ["private_self_use_ready", "production_manager", "mutation_ready"],
        },
        {
            "option_id": "offline_shadow_replay",
            "description": "Collect replay evidence before preparing a private self-use candidate.",
            "auto_activation_allowed": True,
            "blocked_claims": ["automatic_self_use", "product_ready", "mutation_ready"],
        },
        {
            "option_id": "prepare_private_self_use_candidate",
            "description": "Prepare a separate human-reviewable private self-use candidate; do not approve it here.",
            "auto_activation_allowed": False,
            "blocked_claims": ["automatic_private_self_use", "user_facing_ready", "mutation_rollout_ready"],
        },
        {
            "option_id": "defer_to_local_mvp",
            "description": "Return to deterministic/local MVP closure when live output exposes unresolved local gaps.",
            "auto_activation_allowed": True,
            "blocked_claims": ["live_ready", "product_ready"],
        },
    ]


def _readiness_claim() -> dict[str, Any]:
    return build_readiness_claim(
        claim_scope="live_diagnostic",
        activation_stage="live_diagnostic",
        semantic_authority_source="deterministic_validator",
        producer_honesty={
            "runner_inferred_semantics": False,
            "fake_provider_simulated_manager": False,
            "final_mapping_fabricated": False,
            "mutation_fabricated": False,
        },
        evidence_lineage={
            "artifacts": ["artifacts/accurate_intake_mvp_live_diagnostic.json"],
            "producers": ["scripts/build_accurate_intake_mvp_live_decision_pack.py"],
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=[
            "product_ready",
            "private_self_use_ready",
            "user_facing_ready",
            "mutation_ready",
            "production_ready",
            "runtime_web_activation_ready",
        ],
        readiness_claimed=False,
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if str(item)]


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Accurate Intake MVP live diagnostic decision pack.")
    parser.add_argument("--live-artifact", default=str(DEFAULT_LIVE_ARTIFACT))
    parser.add_argument("--offline-replay-artifact", default=str(DEFAULT_OFFLINE_REPLAY_ARTIFACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_accurate_intake_live_decision_pack(
        live_artifact_path=Path(args.live_artifact),
        offline_replay_artifact_path=Path(args.offline_replay_artifact) if args.offline_replay_artifact else None,
        output_dir=Path(args.output_dir),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
