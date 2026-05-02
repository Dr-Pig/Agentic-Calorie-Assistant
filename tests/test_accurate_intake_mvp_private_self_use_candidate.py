from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_private_self_use_candidate import (
    build_accurate_intake_private_self_use_candidate,
    write_accurate_intake_private_self_use_candidate,
)


def _decision_pack(
    *,
    selected_option: str = "prepare_private_self_use_candidate",
    selection_reason: str = "strict_live_diagnostic_with_replay_evidence",
    private_self_use_candidate_prepared: bool = True,
    private_self_use_approved: bool = False,
    product_readiness_claimed: bool = False,
    production_selected: bool = False,
    mutation_rollout_approved: bool = False,
) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_decision_pack",
        "claim_scope": "live_diagnostic_decision_pack",
        "selected_option": selected_option,
        "selection_reason": selection_reason,
        "private_self_use_candidate_prepared": private_self_use_candidate_prepared,
        "requires_human_approval_for_private_self_use": private_self_use_candidate_prepared,
        "private_self_use_approved": private_self_use_approved,
        "product_readiness_claimed": product_readiness_claimed,
        "production_selected": production_selected,
        "mutation_rollout_approved": mutation_rollout_approved,
        "runtime_web_activation_approved": False,
        "model_portability_claimed": False,
        "max_model_claim": "multi_profile_live_diagnostic_observed",
        "offline_replay_summary": {
            "present": True,
            "strict_replay_ready": True,
            "sample_run_count": 3,
            "timeout_count": 0,
            "model_diversity_status": "provider_diversity_present",
        },
        "provider_robustness_summary": {
            "present": True,
            "model_inversion_evidence_passed": True,
            "contract_overfit_risk": False,
            "model_diversity_status": "provider_diversity_present",
        },
        "stage_summary": {"full_suite_status": "pass", "has_timeout_stage": False},
    }


def test_private_self_use_candidate_prepares_review_artifact_without_approval() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(_decision_pack())

    assert candidate["artifact_type"] == "accurate_intake_mvp_private_self_use_candidate"
    assert candidate["claim_scope"] == "private_self_use_candidate_review"
    assert candidate["candidate_prepared"] is True
    assert candidate["private_self_use_approved"] is False
    assert candidate["product_readiness_claimed"] is False
    assert candidate["production_selected"] is False
    assert candidate["mutation_rollout_approved"] is False
    assert candidate["requires_human_approval"] is True
    assert candidate["input_integrity"]["passed"] is True
    assert candidate["activation_status"] == "candidate_review_required"


def test_private_self_use_candidate_blocks_non_candidate_decision_pack() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(
            selected_option="offline_shadow_replay",
            selection_reason="model_diversity_missing",
            private_self_use_candidate_prepared=False,
        )
    )

    assert candidate["candidate_prepared"] is False
    assert candidate["activation_status"] == "blocked"
    assert "decision_pack_not_candidate" in candidate["input_integrity"]["blockers"]
    assert candidate["private_self_use_approved"] is False


def test_private_self_use_candidate_blocks_overclaiming_decision_pack() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(product_readiness_claimed=True, private_self_use_approved=True)
    )

    assert candidate["candidate_prepared"] is False
    assert "decision_pack_product_readiness_claimed" in candidate["input_integrity"]["blockers"]
    assert "decision_pack_private_self_use_approved" in candidate["input_integrity"]["blockers"]
    assert candidate["private_self_use_approved"] is False


def test_private_self_use_candidate_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "accurate_intake_mvp_live_decision_pack.json"
    source.write_text(json.dumps(_decision_pack(), ensure_ascii=False), encoding="utf-8")

    output = write_accurate_intake_private_self_use_candidate(decision_pack_path=source, output_dir=tmp_path)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "accurate_intake_mvp_private_self_use_candidate.json"
    assert payload["artifact_type"] == "accurate_intake_mvp_private_self_use_candidate"
    assert payload["private_self_use_approved"] is False
