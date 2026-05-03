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
from scripts.build_accurate_intake_mvp_live_stage_manifest import stage_summary_from_stages


DEFAULT_LIVE_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic.json"
DEFAULT_STAGE_MANIFEST_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_live_stage_manifest.json"
DEFAULT_OFFLINE_REPLAY_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_offline_shadow_replay.json"
DEFAULT_PROVIDER_ROBUSTNESS_MATRIX_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_live_robustness_matrix.json"
DEFAULT_CONTRACT_HARDENING_GUARD_ARTIFACT = ROOT / "artifacts" / "accurate_intake_contract_hardening_guard.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"

DECISION_OPTION_IDS = (
    "provider_health_blocked",
    "schema_contract_blocked",
    "single_case_probe_required",
    "stay_diagnostic",
    "repeat_single_profile_diagnostic",
    "offline_shadow_replay",
    "full_suite_blocked",
    "prepare_private_self_use_candidate",
    "defer_to_local_mvp",
)


def build_accurate_intake_live_decision_pack(
    live_artifact: dict[str, Any],
    *,
    stage_manifest_artifact: dict[str, Any] | None = None,
    offline_replay_artifact: dict[str, Any] | None = None,
    provider_robustness_artifact: dict[str, Any] | None = None,
    contract_hardening_guard_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_integrity = _input_integrity(live_artifact, stage_manifest_artifact=stage_manifest_artifact)
    evidence_summary = _evidence_summary(live_artifact)
    stage_summary = _stage_summary(live_artifact, stage_manifest_artifact=stage_manifest_artifact)
    offline_replay_summary = _offline_replay_summary(offline_replay_artifact)
    provider_robustness_summary = _provider_robustness_summary(provider_robustness_artifact)
    contract_hardening_summary = _contract_hardening_summary(contract_hardening_guard_artifact)
    selected_option, selection_reason = _select_option(
        input_integrity=input_integrity,
        evidence_summary=evidence_summary,
        stage_summary=stage_summary,
        offline_replay_summary=offline_replay_summary,
        provider_robustness_summary=provider_robustness_summary,
        contract_hardening_summary=contract_hardening_summary,
    )
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_live_decision_pack",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_artifact_type": live_artifact.get("artifact_type"),
            "source_stage_manifest_type": (
                stage_manifest_artifact.get("artifact_type") if isinstance(stage_manifest_artifact, dict) else None
            ),
            "source_provider_robustness_matrix_type": (
                provider_robustness_artifact.get("artifact_type")
                if isinstance(provider_robustness_artifact, dict)
                else None
            ),
            "source_contract_hardening_guard_type": (
                contract_hardening_guard_artifact.get("artifact_type")
                if isinstance(contract_hardening_guard_artifact, dict)
                else None
            ),
            "claim_scope": "live_diagnostic_decision_pack",
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "private_self_use_candidate_prepared": selected_option == "prepare_private_self_use_candidate",
            "production_selected": False,
            "model_portability_claimed": False,
            "max_model_claim": _max_model_claim(
                live_artifact,
                stage_manifest_artifact=stage_manifest_artifact,
                provider_robustness_summary=provider_robustness_summary,
            ),
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "shadow_or_canary_approved": False,
            "input_integrity": input_integrity,
            "stage_summary": stage_summary,
            "evidence_summary": evidence_summary,
            "offline_replay_summary": offline_replay_summary,
            "provider_robustness_summary": provider_robustness_summary,
            "contract_hardening_summary": contract_hardening_summary,
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
    stage_manifest_artifact_path: Path | None = None,
    offline_replay_artifact_path: Path | None = None,
    provider_robustness_artifact_path: Path | None = None,
    contract_hardening_guard_artifact_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    output_path: Path | None = None,
) -> Path:
    live_artifact = json.loads(live_artifact_path.read_text(encoding="utf-8"))
    stage_manifest_artifact = None
    if stage_manifest_artifact_path is not None and stage_manifest_artifact_path.exists():
        stage_manifest_artifact = json.loads(stage_manifest_artifact_path.read_text(encoding="utf-8"))
    offline_replay_artifact = None
    if offline_replay_artifact_path is not None and offline_replay_artifact_path.exists():
        offline_replay_artifact = json.loads(offline_replay_artifact_path.read_text(encoding="utf-8"))
    provider_robustness_artifact = None
    if provider_robustness_artifact_path is not None and provider_robustness_artifact_path.exists():
        provider_robustness_artifact = json.loads(provider_robustness_artifact_path.read_text(encoding="utf-8"))
    contract_hardening_guard_artifact = None
    if contract_hardening_guard_artifact_path is not None and contract_hardening_guard_artifact_path.exists():
        contract_hardening_guard_artifact = json.loads(
            contract_hardening_guard_artifact_path.read_text(encoding="utf-8")
        )
    pack = build_accurate_intake_live_decision_pack(
        live_artifact,
        stage_manifest_artifact=stage_manifest_artifact,
        offline_replay_artifact=offline_replay_artifact,
        provider_robustness_artifact=provider_robustness_artifact,
        contract_hardening_guard_artifact=contract_hardening_guard_artifact,
    )
    path = output_path or output_dir / "accurate_intake_mvp_live_decision_pack.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _select_option(
    *,
    input_integrity: dict[str, Any],
    evidence_summary: dict[str, Any],
    stage_summary: dict[str, Any],
    offline_replay_summary: dict[str, Any],
    provider_robustness_summary: dict[str, Any],
    contract_hardening_summary: dict[str, Any],
) -> tuple[str, str]:
    if input_integrity.get("passed") is not True:
        if input_integrity.get("stage_manifest_integrity_blocked") is True:
            return "stay_diagnostic", "stage_manifest_integrity_blocked"
        return "stay_diagnostic", "input_integrity_blocked"
    if contract_hardening_summary.get("present") is True:
        if contract_hardening_summary.get("integrity_passed") is not True:
            return "stay_diagnostic", "contract_hardening_guard_integrity_blocked"
        if contract_hardening_summary.get("debt_present") is True:
            return "offline_shadow_replay", "contract_hardening_debt"
    if stage_summary.get("provider_health_blocked") is True:
        return "provider_health_blocked", "environment_or_provider_blocker"
    if stage_summary.get("schema_contract_blocked") is True:
        return "schema_contract_blocked", "schema_contract_blocked"
    if stage_summary.get("full_suite_without_single_case_probe") is True:
        return "single_case_probe_required", "single_case_probe_missing"
    full_suite_blocker = _full_suite_blocker(stage_summary)
    if full_suite_blocker:
        return "full_suite_blocked", full_suite_blocker
    if stage_summary.get("has_timeout_stage") is True:
        return "stay_diagnostic", "timeout_evidence_incomplete"
    if stage_summary.get("has_failed_stage") is True:
        return "stay_diagnostic", "live_diagnostic_contract_failures"
    if stage_summary.get("has_retry_dependent_stage") is True:
        return "repeat_single_profile_diagnostic", "retry_dependent_evidence"
    if stage_summary.get("source") == "stage_manifest" and stage_summary.get("has_missing_required_stage") is True:
        if stage_summary.get("missing_required_stage_ids"):
            return "stay_diagnostic", "stage_evidence_missing"
        if stage_summary.get("missing_required_single_case_ids"):
            return "single_case_probe_required", "single_case_probe_missing"
    if stage_summary.get("source") == "stage_manifest" and stage_summary.get("present") is True:
        if offline_replay_summary.get("present") is not True:
            return "offline_shadow_replay", "clean_stage_manifest_requires_replay_before_private_self_use_candidate"
        if offline_replay_summary.get("integrity_passed") is not True:
            return "offline_shadow_replay", "offline_replay_integrity_blocked"
        if offline_replay_summary.get("strict_replay_ready") is not True:
            return "offline_shadow_replay", "offline_replay_not_strict"
        if _full_suite_strict_ready(stage_summary) is not True:
            return "full_suite_blocked", "full_suite_diagnostic_required"
        if offline_replay_summary.get("model_diversity_status") == "model_diversity_missing":
            return "offline_shadow_replay", "model_diversity_missing"
        if offline_replay_summary.get("full_suite_replay_ready") is not True:
            return "offline_shadow_replay", "full_suite_replay_window_required"
        if provider_robustness_summary.get("present") is not True:
            return "offline_shadow_replay", "provider_robustness_matrix_required"
        if provider_robustness_summary.get("integrity_passed") is not True:
            return "offline_shadow_replay", "provider_robustness_matrix_integrity_blocked"
        if provider_robustness_summary.get("contract_overfit_risk") is True:
            return "offline_shadow_replay", "contract_overfit_risk"
        if provider_robustness_summary.get("model_inversion_evidence_passed") is not True:
            return "offline_shadow_replay", "model_inversion_evidence_missing"
        return "prepare_private_self_use_candidate", "strict_live_diagnostic_with_replay_evidence"
    if evidence_summary.get("environment_or_provider_blocker") is True:
        return "stay_diagnostic", "environment_or_provider_blocker"
    if evidence_summary.get("timeout_count", 0) > 0:
        return "stay_diagnostic", "timeout_evidence_incomplete"
    if evidence_summary.get("contract_fail_count", 0) > 0:
        return "stay_diagnostic", "live_diagnostic_contract_failures"
    if evidence_summary.get("repaired_pass_count", 0) > 0:
        return "repeat_single_profile_diagnostic", "live_clean_but_repair_dependent"
    if evidence_summary.get("strict_pass_count", 0) == evidence_summary.get("case_count", 0) and evidence_summary.get("case_count", 0) > 0:
        if offline_replay_summary.get("present") is not True:
            return "offline_shadow_replay", "single_live_run_requires_offline_replay_before_private_self_use_candidate"
        if offline_replay_summary.get("integrity_passed") is not True:
            return "offline_shadow_replay", "offline_replay_integrity_blocked"
        if offline_replay_summary.get("strict_replay_ready") is True:
            if offline_replay_summary.get("model_diversity_status") == "model_diversity_missing":
                return "offline_shadow_replay", "model_diversity_missing"
            if provider_robustness_summary.get("present") is not True:
                return "offline_shadow_replay", "provider_robustness_matrix_required"
            if provider_robustness_summary.get("integrity_passed") is not True:
                return "offline_shadow_replay", "provider_robustness_matrix_integrity_blocked"
            if provider_robustness_summary.get("contract_overfit_risk") is True:
                return "offline_shadow_replay", "contract_overfit_risk"
            if provider_robustness_summary.get("model_inversion_evidence_passed") is not True:
                return "offline_shadow_replay", "model_inversion_evidence_missing"
            if _full_suite_strict_ready(stage_summary) is not True:
                return "full_suite_blocked", "full_suite_diagnostic_required"
            if offline_replay_summary.get("full_suite_replay_ready") is not True:
                return "offline_shadow_replay", "full_suite_replay_window_required"
            return "prepare_private_self_use_candidate", "strict_live_diagnostic_with_replay_evidence"
        return "offline_shadow_replay", "offline_replay_not_strict"
    return "defer_to_local_mvp", "live_diagnostic_not_clean"


def _input_integrity(
    live_artifact: dict[str, Any],
    *,
    stage_manifest_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    stage_manifest_integrity_blocked = False
    if stage_manifest_artifact is not None:
        if stage_manifest_artifact.get("artifact_type") != "accurate_intake_mvp_live_stage_manifest":
            blockers.append("stage_manifest_artifact_type_invalid")
            stage_manifest_integrity_blocked = True
        manifest_integrity = _dict(stage_manifest_artifact.get("input_integrity"))
        if manifest_integrity.get("passed") is not True:
            stage_manifest_integrity_blocked = True
            for blocker in _string_list(manifest_integrity.get("blockers")):
                blockers.append(f"stage_manifest_{blocker}")
        for key in (
            "readiness_claimed",
            "product_readiness_claimed",
            "private_self_use_approved",
            "production_selected",
            "mutation_rollout_approved",
            "runtime_web_activation_approved",
        ):
            if stage_manifest_artifact.get(key) is True:
                blockers.append(f"stage_manifest_{key}")
                stage_manifest_integrity_blocked = True
    return {
        "passed": not blockers,
        "blockers": sorted(set(blockers)),
        "stage_manifest_integrity_blocked": stage_manifest_integrity_blocked,
    }


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


def _stage_summary(
    live_artifact: dict[str, Any],
    *,
    stage_manifest_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        isinstance(stage_manifest_artifact, dict)
        and stage_manifest_artifact.get("artifact_type") == "accurate_intake_mvp_live_stage_manifest"
        and _dict(stage_manifest_artifact.get("input_integrity")).get("passed") is True
    ):
        stages = [_dict(stage) for stage in _list(stage_manifest_artifact.get("stages"))]
        summary = stage_summary_from_stages(stages)
        summary["source"] = "stage_manifest"
        summary["manifest_stage_count"] = len(stages)
        summary["has_timeout_stage"] = any(str(stage.get("status") or "") == "timeout" for stage in stages)
        summary["has_failed_stage"] = any(
            str(stage.get("status") or "") in {"fail", "blocked"} for stage in stages
        )
        summary["has_retry_dependent_stage"] = any(
            stage.get("retry_policy_applied") is True or str(stage.get("result_kind") or "") == "pass_after_retry"
            for stage in stages
        )
        return summary
    stages = [_dict(stage) for stage in _list(live_artifact.get("stages"))]
    by_id = {str(stage.get("stage_id") or ""): stage for stage in stages}
    provider_health = by_id.get("provider_health_smoke", {})
    schema_probe = by_id.get("schema_contract_probe", {})
    provider_health_blocked = (
        not stages
        and "environment_or_provider_blocker" in _evidence_summary(live_artifact).get("failure_families", [])
    ) or (
        bool(provider_health)
        and provider_health.get("status") != "pass"
    )
    schema_contract_blocked = bool(schema_probe) and schema_probe.get("status") != "pass"
    result = stage_summary_from_stages(stages)
    result["source"] = "live_artifact"
    result["provider_health_blocked"] = provider_health_blocked
    result["schema_contract_blocked"] = schema_contract_blocked
    result["has_timeout_stage"] = any(str(stage.get("status") or "") == "timeout" for stage in stages)
    result["has_failed_stage"] = any(str(stage.get("status") or "") in {"fail", "blocked"} for stage in stages)
    result["has_retry_dependent_stage"] = any(
        stage.get("retry_policy_applied") is True or str(stage.get("result_kind") or "") == "pass_after_retry"
        for stage in stages
    )
    return result


def _max_model_claim(
    live_artifact: dict[str, Any],
    *,
    stage_manifest_artifact: dict[str, Any] | None = None,
    provider_robustness_summary: dict[str, Any] | None = None,
) -> str:
    if (
        isinstance(provider_robustness_summary, dict)
        and provider_robustness_summary.get("model_diversity_status") == "provider_diversity_present"
    ):
        return "multi_profile_live_diagnostic_observed"
    profile_ids: set[str] = set()
    model_ids: set[str] = set()
    if isinstance(stage_manifest_artifact, dict):
        for stage in _list(stage_manifest_artifact.get("stages")):
            stage_dict = _dict(stage)
            profile_id = _optional_string(stage_dict.get("provider_profile_id"))
            model_id = _optional_string(stage_dict.get("model"))
            if profile_id:
                profile_ids.add(profile_id)
            if model_id:
                model_ids.add(model_id)
    profile_id = _optional_string(live_artifact.get("provider_profile_id"))
    model_id = _optional_string(live_artifact.get("provider_profile_model"))
    if profile_id:
        profile_ids.add(profile_id)
    if model_id:
        model_ids.add(model_id)
    if len(profile_ids) <= 1 and len(model_ids) <= 1:
        return "single_profile_live_diagnostic_observed"
    return "multi_profile_live_diagnostic_observed"


def _offline_replay_summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {
            "present": False,
            "integrity_passed": False,
            "strict_replay_ready": False,
            "sample_run_count": 0,
            "repaired_pass_count": 0,
            "timeout_count": 0,
            "full_suite_replay_ready": False,
            "full_suite_run_count": 0,
            "full_suite_strict_first_attempt_count": 0,
            "full_suite_timeout_count": 0,
            "full_suite_pass_after_retry_count": 0,
            "model_diversity_status": "missing_offline_replay",
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
        "full_suite_replay_ready": summary.get("full_suite_replay_ready") is True,
        "full_suite_run_count": int(summary.get("full_suite_run_count") or 0),
        "full_suite_strict_first_attempt_count": int(
            summary.get("full_suite_strict_first_attempt_count") or 0
        ),
        "full_suite_timeout_count": int(summary.get("full_suite_timeout_count") or 0),
        "full_suite_pass_after_retry_count": int(summary.get("full_suite_pass_after_retry_count") or 0),
        "model_diversity_status": str(summary.get("model_diversity_status") or "unknown"),
    }


def _provider_robustness_summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {
            "present": False,
            "integrity_passed": False,
            "model_inversion_evidence_passed": False,
            "contract_overfit_risk": False,
            "model_diversity_status": "missing_provider_robustness_matrix",
            "single_profile_only": True,
        }
    integrity = _dict(artifact.get("input_integrity"))
    return {
        "present": artifact.get("artifact_type") == "accurate_intake_mvp_live_robustness_matrix",
        "integrity_passed": integrity.get("passed") is True,
        "model_inversion_evidence_passed": artifact.get("model_inversion_evidence_passed") is True,
        "contract_overfit_risk": artifact.get("contract_overfit_risk") is True,
        "model_diversity_status": str(artifact.get("model_diversity_status") or "unknown"),
        "single_profile_only": artifact.get("single_profile_only") is True,
        "has_retry_dependent_evidence": artifact.get("has_retry_dependent_evidence") is True,
        "has_timeout_evidence": artifact.get("has_timeout_evidence") is True,
        "has_error_evidence": artifact.get("has_error_evidence") is True,
    }


def _contract_hardening_summary(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {
            "present": False,
            "integrity_passed": True,
            "debt_present": False,
            "merge_allowed": True,
            "blockers": [],
            "fixed_case_ids": [],
            "legal_flows_broken": [],
        }
    integrity = _dict(artifact.get("input_integrity"))
    debt = _dict(artifact.get("contract_hardening_debt"))
    blockers = _string_list(artifact.get("blockers"))
    artifact_type_valid = artifact.get("artifact_type") == "accurate_intake_contract_hardening_guard"
    integrity_passed = artifact_type_valid and integrity.get("passed") is True
    return {
        "present": True,
        "artifact_type_valid": artifact_type_valid,
        "integrity_passed": integrity_passed,
        "debt_present": debt.get("present") is True or artifact.get("merge_allowed") is False,
        "merge_allowed": artifact.get("merge_allowed") is True,
        "blockers": blockers,
        "fixed_case_ids": _string_list(artifact.get("fixed_case_ids")),
        "legal_flows_broken": _string_list(artifact.get("legal_flows_broken")),
        "provider_overfit_risk": _optional_string(artifact.get("provider_overfit_risk")),
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
            "option_id": "provider_health_blocked",
            "description": "Provider health smoke failed or timed out; do not run or trust product-loop live evidence.",
            "auto_activation_allowed": True,
            "blocked_claims": ["private_self_use_ready", "product_ready", "production_manager"],
        },
        {
            "option_id": "schema_contract_blocked",
            "description": "Provider responded but failed the manager schema/transport contract probe.",
            "auto_activation_allowed": True,
            "blocked_claims": ["private_self_use_ready", "product_ready", "mutation_ready"],
        },
        {
            "option_id": "single_case_probe_required",
            "description": "Full suite evidence is invalid until an independent single-case live probe is green.",
            "auto_activation_allowed": True,
            "blocked_claims": ["private_self_use_ready", "product_ready", "live_ready"],
        },
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
            "option_id": "full_suite_blocked",
            "description": "Full-suite diagnostic evidence is blocked by missing, incomplete, or retry/timeout-bearing replay evidence.",
            "auto_activation_allowed": True,
            "blocked_claims": ["private_self_use_ready", "product_ready", "live_ready"],
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


def _full_suite_blocker(stage_summary: dict[str, Any]) -> str | None:
    for item in _list(stage_summary.get("stage_failures")):
        failure = _dict(item)
        if failure.get("stage_id") != "full_suite_live_diagnostic":
            continue
        family = str(failure.get("failure_family") or "")
        if family.startswith("offline_replay"):
            return family
    return None


def _full_suite_strict_ready(stage_summary: dict[str, Any]) -> bool:
    if stage_summary.get("full_suite_status") != "pass":
        return False
    result_kind_counts = _dict(stage_summary.get("result_kind_counts"))
    if "pass_after_retry" in result_kind_counts:
        return False
    full_suite_result_kind = None
    for item in _list(stage_summary.get("stages")):
        stage = _dict(item)
        if stage.get("stage_id") == "full_suite_live_diagnostic":
            full_suite_result_kind = _optional_string(stage.get("result_kind"))
            break
    return full_suite_result_kind in {None, "strict_pass_first_attempt"}


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
    parser.add_argument("--stage-manifest", default=str(DEFAULT_STAGE_MANIFEST_ARTIFACT))
    parser.add_argument("--offline-replay-artifact", default=str(DEFAULT_OFFLINE_REPLAY_ARTIFACT))
    parser.add_argument("--provider-robustness-matrix", default=str(DEFAULT_PROVIDER_ROBUSTNESS_MATRIX_ARTIFACT))
    parser.add_argument("--contract-hardening-guard-artifact", default=str(DEFAULT_CONTRACT_HARDENING_GUARD_ARTIFACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output")
    args = parser.parse_args()
    path = write_accurate_intake_live_decision_pack(
        live_artifact_path=Path(args.live_artifact),
        stage_manifest_artifact_path=Path(args.stage_manifest) if args.stage_manifest else None,
        offline_replay_artifact_path=Path(args.offline_replay_artifact) if args.offline_replay_artifact else None,
        provider_robustness_artifact_path=(
            Path(args.provider_robustness_matrix) if args.provider_robustness_matrix else None
        ),
        contract_hardening_guard_artifact_path=(
            Path(args.contract_hardening_guard_artifact) if args.contract_hardening_guard_artifact else None
        ),
        output_dir=Path(args.output_dir),
        output_path=Path(args.output) if args.output else None,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
