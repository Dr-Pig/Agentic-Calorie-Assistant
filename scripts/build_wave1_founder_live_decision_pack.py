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


DEFAULT_FOUNDER_LIVE_ARTIFACT = ROOT / "artifacts" / "wave1_founder_e2e_live_diagnostic.json"
DEFAULT_OFFLINE_SHADOW_REPLAY_ARTIFACT = ROOT / "artifacts" / "wave1_founder_offline_shadow_replay.json"
DEFAULT_PROVIDER_ROBUSTNESS_MATRIX_ARTIFACT = ROOT / "artifacts" / "wave1_founder_provider_robustness_matrix.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
MINIMUM_STRICT_REPLAY_RUNS_FOR_SHADOW_CANDIDATE = 3
REPAIR_FAILURE_INVARIANT_BY_FAMILY = {
    "commit_without_evidence": "commit_requires_evidence",
    "correction_without_target": "correction_requires_valid_target",
    "mutation_without_final_mapping": "mutation_requires_final_mapping",
    "manager_output_contract_violation": "manager_contract_schema_adherence",
}
DECISION_OPTION_IDS = (
    "stay_diagnostic",
    "offline_shadow_replay",
    "narrow_live_contract_followup",
    "defer_until_product_decision",
    "prepare_shadow_candidate",
)


def build_founder_live_decision_pack(
    founder_live_artifact: dict[str, Any],
    *,
    offline_shadow_replay_artifact: dict[str, Any] | None = None,
    provider_robustness_matrix_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = _dict(founder_live_artifact.get("summary"))
    input_integrity = _input_integrity(founder_live_artifact)
    repaired_cases = _repaired_cases(founder_live_artifact)
    offline_shadow_replay_summary = _offline_shadow_replay_summary(offline_shadow_replay_artifact)
    provider_robustness_summary = _provider_robustness_summary(provider_robustness_matrix_artifact)
    evidence_summary = {
        "live_invoked": founder_live_artifact.get("live_invoked") is True,
        "case_count": _case_count(summary, founder_live_artifact),
        "pass_count": int(summary.get("pass_count") or 0),
        "fail_count": int(summary.get("fail_count") or 0),
        "product_decision_required_count": int(summary.get("product_decision_required_count") or 0),
        "failure_layers": _string_list(summary.get("failure_layers")),
        "strict_pass_count": int(summary.get("strict_pass_count") or 0),
        "repaired_pass_count": int(summary.get("repaired_pass_count") or 0),
        "contract_fail_count": int(summary.get("contract_fail_count") or 0),
        "repaired_case_ids": [str(item["case_id"]) for item in repaired_cases],
        "repaired_cases": repaired_cases,
        "minimum_strict_replay_runs_for_shadow_candidate": MINIMUM_STRICT_REPLAY_RUNS_FOR_SHADOW_CANDIDATE,
    }
    selected_option, selection_reason = _select_option(
        input_integrity=input_integrity,
        evidence_summary=evidence_summary,
        offline_shadow_replay_summary=offline_shadow_replay_summary,
        provider_robustness_summary=provider_robustness_summary,
    )
    return _json_safe(
        {
            "artifact_type": "wave1_founder_live_decision_pack",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_artifact_type": founder_live_artifact.get("artifact_type"),
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "input_integrity": input_integrity,
            "evidence_summary": evidence_summary,
            "offline_shadow_replay_summary": offline_shadow_replay_summary,
            "provider_robustness_summary": provider_robustness_summary,
            "decision_options_ordered": list(DECISION_OPTION_IDS),
            "decision_options": _decision_options(),
            "selected_option": selected_option,
            "selection_reason": selection_reason,
            "requires_human_decision": selected_option == "defer_until_product_decision",
            "shadow_or_canary_approved": False,
            "production_rollout_approved": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "decision_boundary": {
                "live_diagnostic_is_product_readiness": False,
                "repaired_pass_unlocks_shadow": False,
                "single_profile_stability_is_shadow_ready": False,
                "model_diversity_required_for_shadow_candidate": True,
                "timeout_evidence_excluded_from_strict_claim": True,
                "strict_pass_allows_decision_pack_only": True,
                "mutation_allowed": False,
                "product_readiness_claim_allowed": False,
            },
        }
    )


def write_founder_live_decision_pack(
    *,
    founder_live_artifact_path: Path = DEFAULT_FOUNDER_LIVE_ARTIFACT,
    offline_shadow_replay_artifact_path: Path | None = None,
    provider_robustness_matrix_artifact_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    founder_live_artifact = json.loads(founder_live_artifact_path.read_text(encoding="utf-8"))
    offline_shadow_replay_artifact = None
    if offline_shadow_replay_artifact_path is not None and offline_shadow_replay_artifact_path.exists():
        offline_shadow_replay_artifact = json.loads(offline_shadow_replay_artifact_path.read_text(encoding="utf-8"))
    provider_robustness_matrix_artifact = None
    if provider_robustness_matrix_artifact_path is not None and provider_robustness_matrix_artifact_path.exists():
        provider_robustness_matrix_artifact = json.loads(
            provider_robustness_matrix_artifact_path.read_text(encoding="utf-8")
        )
    pack = build_founder_live_decision_pack(
        founder_live_artifact,
        offline_shadow_replay_artifact=offline_shadow_replay_artifact,
        provider_robustness_matrix_artifact=provider_robustness_matrix_artifact,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "wave1_founder_live_decision_pack.json"
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _select_option(
    *,
    input_integrity: dict[str, Any],
    evidence_summary: dict[str, Any],
    offline_shadow_replay_summary: dict[str, Any],
    provider_robustness_summary: dict[str, Any],
) -> tuple[str, str]:
    if input_integrity.get("passed") is not True:
        return "stay_diagnostic", "input_integrity_blocked"
    if evidence_summary.get("product_decision_required_count", 0) > 0:
        return "defer_until_product_decision", "product_decision_required"
    if evidence_summary.get("fail_count", 0) > 0 or evidence_summary.get("contract_fail_count", 0) > 0:
        failure_layers = set(evidence_summary.get("failure_layers") or [])
        if "provider_contract_non_adherence" in failure_layers:
            return "narrow_live_contract_followup", "provider_contract_non_adherence"
        return "stay_diagnostic", "live_diagnostic_has_failures"
    if evidence_summary.get("repaired_pass_count", 0) > 0:
        return "offline_shadow_replay", "live_clean_but_repair_dependent"
    if evidence_summary.get("strict_pass_count", 0) == evidence_summary.get("case_count", 0) and evidence_summary.get("case_count", 0) > 0:
        if offline_shadow_replay_summary.get("present") is not True:
            return "offline_shadow_replay", "offline_shadow_replay_required_before_shadow_candidate"
        if offline_shadow_replay_summary.get("integrity_passed") is not True:
            return "offline_shadow_replay", "offline_shadow_replay_integrity_blocked"
        if offline_shadow_replay_summary.get("strict_replay_ready") is not True:
            return "offline_shadow_replay", "offline_shadow_replay_not_all_strict"
        if offline_shadow_replay_summary.get("model_diversity_status") == "model_diversity_missing":
            return "offline_shadow_replay", "model_diversity_missing"
        if provider_robustness_summary.get("present") is not True:
            return "offline_shadow_replay", "provider_robustness_matrix_required_before_shadow_candidate"
        if provider_robustness_summary.get("integrity_passed") is not True:
            return "offline_shadow_replay", "provider_robustness_matrix_integrity_blocked"
        if provider_robustness_summary.get("contract_overfit_risk") is True:
            return "narrow_live_contract_followup", "contract_overfit_risk"
        if provider_robustness_summary.get("model_inversion_evidence_passed") is True:
            return "prepare_shadow_candidate", "repeated_all_strict_with_model_inversion_evidence"
        status = str(provider_robustness_summary.get("provider_diversity_status") or "model_diversity_missing")
        if status:
            return "offline_shadow_replay", status
        return "offline_shadow_replay", "offline_shadow_replay_not_all_strict"
    return "stay_diagnostic", "insufficient_live_evidence"


def _offline_shadow_replay_summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {
            "present": False,
            "integrity_passed": False,
            "eligible_for_shadow_candidate": False,
            "strict_replay_ready": False,
            "single_profile_stability": False,
            "model_diversity_status": "missing_offline_replay",
            "sample_run_count": 0,
            "repaired_pass_count": 0,
            "repaired_case_ids": [],
        }
    summary = _dict(artifact.get("summary"))
    integrity = _dict(artifact.get("input_integrity"))
    gate = _dict(artifact.get("strictness_gate"))
    return {
        "present": artifact.get("artifact_type") == "wave1_founder_offline_shadow_replay",
        "integrity_passed": integrity.get("passed") is True,
        "eligible_for_shadow_candidate": summary.get("eligible_for_shadow_candidate") is True,
        "strict_replay_ready": summary.get("strict_replay_ready") is True
        or (
            summary.get("all_sampled_runs_7_strict") is True
            and int(summary.get("sample_run_count") or 0) >= MINIMUM_STRICT_REPLAY_RUNS_FOR_SHADOW_CANDIDATE
            and int(summary.get("repaired_pass_count") or 0) == 0
        ),
        "single_profile_stability": summary.get("single_profile_stability") is True,
        "model_diversity_status": str(summary.get("model_diversity_status") or "unknown"),
        "sample_run_count": int(summary.get("sample_run_count") or 0),
        "minimum_strict_replay_runs": int(
            summary.get("minimum_strict_replay_runs_for_shadow_candidate")
            or gate.get("minimum_strict_replay_runs")
            or MINIMUM_STRICT_REPLAY_RUNS_FOR_SHADOW_CANDIDATE
        ),
        "all_sampled_runs_7_strict": summary.get("all_sampled_runs_7_strict") is True,
        "repaired_pass_count": int(summary.get("repaired_pass_count") or 0),
        "repaired_case_ids": _string_list(summary.get("repaired_case_ids")),
        "shadow_or_canary_approved": artifact.get("shadow_or_canary_approved") is True,
    }


def _provider_robustness_summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {
            "present": False,
            "integrity_passed": False,
            "provider_diversity_status": "missing_provider_robustness_matrix",
            "model_inversion_evidence_passed": False,
            "contract_overfit_risk": False,
            "strict_pass_rate": 0.0,
            "repaired_pass_rate": 0.0,
            "timeout_rate": 0.0,
        }
    summary = _dict(artifact.get("matrix_summary"))
    integrity = _dict(artifact.get("input_integrity"))
    return {
        "present": artifact.get("artifact_type") == "wave1_founder_provider_robustness_matrix",
        "integrity_passed": integrity.get("passed") is True,
        "provider_diversity_status": str(summary.get("provider_diversity_status") or "unknown"),
        "model_inversion_evidence_passed": summary.get("model_inversion_evidence_passed") is True,
        "contract_overfit_risk": summary.get("contract_overfit_risk") is True,
        "strict_pass_rate": float(summary.get("strict_pass_rate") or 0.0),
        "repaired_pass_rate": float(summary.get("repaired_pass_rate") or 0.0),
        "timeout_rate": float(summary.get("timeout_rate") or 0.0),
    }


def _repaired_cases(founder_live_artifact: dict[str, Any]) -> list[dict[str, str | None]]:
    repaired: list[dict[str, str | None]] = []
    for case in _list(founder_live_artifact.get("cases")):
        item = _dict(case)
        if str(item.get("case_contract_status") or "") != "repaired_pass":
            continue
        repair_family = _optional_string(item.get("repair_failure_family")) or _extract_repair_failure_family(item)
        failed_invariant = _optional_string(item.get("failed_invariant"))
        if not failed_invariant and repair_family:
            failed_invariant = REPAIR_FAILURE_INVARIANT_BY_FAMILY.get(repair_family)
        repaired.append(
            {
                "case_id": str(item.get("case_id") or ""),
                "repair_failure_family": repair_family,
                "failed_invariant": failed_invariant,
            }
        )
    return repaired


def _extract_repair_failure_family(case: dict[str, Any]) -> str | None:
    traces = _case_manager_traces(case)
    for trace in traces:
        repair_contract = _find_nested_key(trace, "x-repair-contract")
        if isinstance(repair_contract, dict):
            repair_family = str(repair_contract.get("failure_family") or "")
            if repair_family:
                return repair_family
        request_family = str(trace.get("request_failure_family") or "")
        if request_family:
            return request_family
    for trace in traces:
        family = _find_nested_key(trace, "failure_family")
        if isinstance(family, str) and family in REPAIR_FAILURE_INVARIANT_BY_FAMILY:
            return family
    return None


def _case_manager_traces(case: dict[str, Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    actual = _dict(case.get("actual_behavior"))
    for round_item in actual.get("manager_rounds") or []:
        if isinstance(round_item, dict):
            traces.append(_dict(round_item.get("trace")))
    trace = _dict(actual.get("manager_trace"))
    if trace:
        traces.append(trace)
    return traces


def _find_nested_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_nested_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_nested_key(child, key)
            if found is not None:
                return found
    return None


def _input_integrity(founder_live_artifact: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if founder_live_artifact.get("artifact_type") != "wave1_founder_e2e_live_diagnostic":
        blockers.append("input_artifact_type_invalid")
    if founder_live_artifact.get("readiness_claimed") is True:
        blockers.append("input_readiness_claimed")
    if founder_live_artifact.get("production_selected") is True:
        blockers.append("input_production_selected")
    if founder_live_artifact.get("runtime_web_activation_approved") is True:
        blockers.append("input_runtime_web_activation_approved")
    if founder_live_artifact.get("mutation_enabled") is True:
        blockers.append("input_mutation_enabled")
    return {
        "passed": not blockers,
        "blockers": sorted(set(blockers)),
    }


def _case_count(summary: dict[str, Any], founder_live_artifact: dict[str, Any]) -> int:
    counted = (
        int(summary.get("pass_count") or 0)
        + int(summary.get("fail_count") or 0)
        + int(summary.get("product_decision_required_count") or 0)
        + int(summary.get("deferred_count") or 0)
    )
    return counted or len(_list(founder_live_artifact.get("cases")))


def _decision_options() -> list[dict[str, Any]]:
    return [
        {
            "option_id": "stay_diagnostic",
            "description": "Keep Founder live as diagnostic-only evidence collection.",
            "auto_activation_allowed": True,
            "blocked_claims": ["product_ready", "user_facing_ready", "mutation_ready"],
        },
        {
            "option_id": "offline_shadow_replay",
            "description": "Compare live candidate outputs against deterministic truth offline before any shadow/canary stage.",
            "auto_activation_allowed": True,
            "blocked_claims": ["product_ready", "user_facing_ready", "mutation_ready"],
        },
        {
            "option_id": "narrow_live_contract_followup",
            "description": "Continue provider/model contract repair without changing product semantics.",
            "auto_activation_allowed": True,
            "blocked_claims": ["product_ready", "production_manager", "mutation_ready"],
        },
        {
            "option_id": "defer_until_product_decision",
            "description": "Stop because the next fix requires product semantic decision.",
            "auto_activation_allowed": False,
            "blocked_claims": ["runtime_semantic_change_without_approval"],
        },
        {
            "option_id": "prepare_shadow_candidate",
            "description": (
                "Prepare a separate human-reviewable shadow-mode plan after repeated all-strict offline replay."
            ),
            "auto_activation_allowed": False,
            "blocked_claims": ["automatic_shadow_rollout", "user_facing_ready", "mutation_ready"],
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
            "artifacts": ["artifacts/wave1_founder_e2e_live_diagnostic.json"],
            "producers": ["scripts/build_wave1_founder_live_decision_pack.py"],
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=[
            "product_ready",
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
    parser = argparse.ArgumentParser(description="Build Wave 1 Founder live decision pack.")
    parser.add_argument("--founder-live-artifact", default=str(DEFAULT_FOUNDER_LIVE_ARTIFACT))
    parser.add_argument("--offline-shadow-replay-artifact", default=str(DEFAULT_OFFLINE_SHADOW_REPLAY_ARTIFACT))
    parser.add_argument("--provider-robustness-matrix-artifact", default=str(DEFAULT_PROVIDER_ROBUSTNESS_MATRIX_ARTIFACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_founder_live_decision_pack(
        founder_live_artifact_path=Path(args.founder_live_artifact),
        offline_shadow_replay_artifact_path=(
            Path(args.offline_shadow_replay_artifact) if args.offline_shadow_replay_artifact else None
        ),
        provider_robustness_matrix_artifact_path=(
            Path(args.provider_robustness_matrix_artifact) if args.provider_robustness_matrix_artifact else None
        ),
        output_dir=Path(args.output_dir),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
