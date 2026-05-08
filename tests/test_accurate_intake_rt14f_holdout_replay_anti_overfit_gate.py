from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_accurate_intake_rt14f_holdout_replay_anti_overfit_gate as module  # noqa: E402


def _anti_overfit_guard() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_context_live_diagnostic_anti_overfit_guard",
        "status": "pass",
        "live_provider_invoked": False,
        "fooddb_used": False,
        "mutation_changed": False,
        "summary": {
            "fixed_case_matrix_used": True,
            "case_count": 11,
            "holdout_utterance_variant_count": 24,
            "compound_cases": 2,
            "ambiguity_cases": 2,
            "pending_pin_cases": 2,
            "target_candidate_cases": 2,
        },
    }


def _holdout_plan() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_context_live_diagnostic_holdout_plan",
        "status": "pass",
        "fixed_case_matrix_used": True,
        "holdout_variants_withheld_from_default_live_prompt": True,
        "ad_hoc_live_case_selection_allowed": False,
        "provider_optimized_case_selection_allowed": False,
        "live_provider_invoked": False,
        "fooddb_used": False,
        "mutation_changed": False,
        "summary": {
            "fixed_case_count": 11,
            "holdout_variant_count": 24,
            "withheld_holdout_variant_count": 24,
            "cases_with_holdouts": 11,
        },
    }


def _offline_replay() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
        "claim_scope": "offline_shadow_replay",
        "input_integrity": {"passed": True, "blockers": []},
        "summary": {
            "sample_run_count": 3,
            "strict_replay_ready": True,
            "full_suite_replay_ready": False,
            "pass_after_retry_count": 0,
            "timeout_count": 0,
            "retry_dependent_count": 0,
            "failed_stage_count": 0,
            "eligible_for_private_self_use_candidate": False,
            "max_model_claim": "single_profile_live_diagnostic_observed",
        },
    }


def _robustness_matrix() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_robustness_matrix",
        "input_integrity": {"passed": True, "blockers": []},
        "single_profile_only": True,
        "model_diversity_status": "model_diversity_missing",
        "model_inversion_evidence_passed": False,
        "contract_overfit_risk": False,
        "has_retry_dependent_evidence": False,
        "has_timeout_evidence": False,
        "has_error_evidence": False,
        "private_self_use_candidate_blocked": True,
        "max_model_claim": "single_profile_live_diagnostic_observed",
    }


def _rt13b_artifact() -> dict[str, object]:
    return {
        "target_manager_runtime_gate": "rt13b_latency_cost_cache_budget_pack",
        "status": "pass",
    }


def _build(**overrides: object) -> dict[str, object]:
    payloads: dict[str, object] = {
        "anti_overfit_guard": _anti_overfit_guard(),
        "holdout_plan": _holdout_plan(),
        "offline_shadow_replay": _offline_replay(),
        "live_robustness_matrix": _robustness_matrix(),
        "rt13b_artifact": _rt13b_artifact(),
    }
    payloads.update(overrides)
    return module.build_rt14f_holdout_replay_anti_overfit_gate(**payloads)


def test_rt14f_gate_passes_with_withheld_holdouts_and_strict_replay() -> None:
    artifact = _build()

    assert artifact["artifact_type"] == "accurate_intake_rt14f_holdout_replay_anti_overfit_gate"
    assert artifact["target_manager_runtime_gate"] == "rt14f_holdout_replay_anti_overfit_gate"
    assert artifact["status"] == "pass"
    assert artifact["pass_type"] == "runtime_backed"
    assert artifact["runtime_backed"] is True
    assert artifact["live_llm_invoked"] is True
    assert artifact["summary"] == {
        "fixed_case_count": 11,
        "withheld_holdout_variant_count": 24,
        "strict_replay_ready": True,
        "full_suite_replay_ready": False,
        "sample_run_count": 3,
        "retry_dependent_evidence_present": False,
        "timeout_evidence_present": False,
        "contract_overfit_risk": False,
        "model_diversity_status": "model_diversity_missing",
        "model_diversity_required_before_private_candidate": True,
    }
    assert artifact["semantic_boundary"]["deterministic_role"] == "validate_selection_replay_and_overfit_risk"
    assert artifact["semantic_boundary"]["llm_role"] == "future_live_manager_provider"
    assert artifact["non_claims"]["private_self_use_approved"] is False


def test_rt14f_gate_blocks_ad_hoc_or_provider_optimized_holdout_selection() -> None:
    holdout = _holdout_plan()
    holdout["ad_hoc_live_case_selection_allowed"] = True
    holdout["provider_optimized_case_selection_allowed"] = True

    artifact = _build(holdout_plan=holdout)

    assert artifact["status"] == "fail"
    assert "holdout_selection.ad_hoc_live_case_selection_allowed" in artifact["blockers"]
    assert "holdout_selection.provider_optimized_case_selection_allowed" in artifact["blockers"]


def test_rt14f_gate_blocks_retry_timeout_or_failed_replay_window() -> None:
    replay = _offline_replay()
    replay["summary"]["strict_replay_ready"] = False
    replay["summary"]["pass_after_retry_count"] = 1
    replay["summary"]["timeout_count"] = 1

    artifact = _build(offline_shadow_replay=replay)

    assert artifact["status"] == "fail"
    assert "shadow_replay.strict_replay_not_ready" in artifact["blockers"]
    assert "shadow_replay.retry_dependent_evidence_present" in artifact["blockers"]
    assert "shadow_replay.timeout_evidence_present" in artifact["blockers"]


def test_rt14f_gate_blocks_contract_overfit_but_allows_model_diversity_missing_as_nonclaim() -> None:
    robustness = _robustness_matrix()
    robustness["contract_overfit_risk"] = True

    artifact = _build(live_robustness_matrix=robustness)

    assert artifact["status"] == "fail"
    assert "live_robustness.contract_overfit_risk" in artifact["blockers"]
    assert artifact["summary"]["model_diversity_status"] == "model_diversity_missing"
    assert artifact["summary"]["model_diversity_required_before_private_candidate"] is True


def test_rt14f_gate_blocks_missing_budget_dependency() -> None:
    rt13b = _rt13b_artifact()
    rt13b["status"] = "fail"

    artifact = _build(rt13b_artifact=rt13b)

    assert artifact["status"] == "fail"
    assert "dependencies.rt13b_latency_cost_cache_budget_pack_not_pass" in artifact["blockers"]


def test_rt14f_cli_writes_artifact(tmp_path: Path) -> None:
    paths = {
        "anti": tmp_path / "anti.json",
        "holdout": tmp_path / "holdout.json",
        "replay": tmp_path / "replay.json",
        "robustness": tmp_path / "robustness.json",
        "rt13b": tmp_path / "rt13b.json",
    }
    payloads = {
        "anti": _anti_overfit_guard(),
        "holdout": _holdout_plan(),
        "replay": _offline_replay(),
        "robustness": _robustness_matrix(),
        "rt13b": _rt13b_artifact(),
    }
    for key, path in paths.items():
        path.write_text(json.dumps(payloads[key], ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "rt14f.json"

    rc = module.main(
        [
            "--anti-overfit-artifact",
            str(paths["anti"]),
            "--holdout-plan-artifact",
            str(paths["holdout"]),
            "--offline-replay-artifact",
            str(paths["replay"]),
            "--live-robustness-artifact",
            str(paths["robustness"]),
            "--rt13b-artifact",
            str(paths["rt13b"]),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
