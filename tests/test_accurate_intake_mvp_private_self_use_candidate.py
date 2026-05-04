from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def _local_web_candidate(
    *,
    candidate_prepared: bool = True,
    private_self_use_approved: bool = False,
    product_readiness_claimed: bool = False,
    live_manager_required: bool = False,
    production_selected: bool = False,
    runtime_web_activation_approved: bool = False,
    mutation_rollout_approved: bool = False,
    shadow_or_canary_approved: bool = False,
    blockers: list[str] | None = None,
) -> dict[str, object]:
    return {
        "local_web_self_use_candidate_v2": {
            "candidate_prepared": candidate_prepared,
            "private_self_use_approved": private_self_use_approved,
            "product_readiness_claimed": product_readiness_claimed,
            "live_manager_required": live_manager_required,
            "production_selected": production_selected,
            "runtime_web_activation_approved": runtime_web_activation_approved,
            "mutation_rollout_approved": mutation_rollout_approved,
            "shadow_or_canary_approved": shadow_or_canary_approved,
            "blockers": blockers if blockers is not None else [],
        }
    }


def test_private_self_use_candidate_prepares_review_artifact_without_approval() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(),
        local_web_candidate=_local_web_candidate(),
    )

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
    assert candidate["local_web_candidate_summary"]["candidate_prepared"] is True


def test_private_self_use_candidate_blocks_non_candidate_decision_pack() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(
            selected_option="offline_shadow_replay",
            selection_reason="model_diversity_missing",
            private_self_use_candidate_prepared=False,
        ),
        local_web_candidate=_local_web_candidate(),
    )

    assert candidate["candidate_prepared"] is False
    assert candidate["activation_status"] == "blocked"
    assert "decision_pack_not_candidate" in candidate["input_integrity"]["blockers"]
    assert candidate["private_self_use_approved"] is False


def test_private_self_use_candidate_blocks_overclaiming_decision_pack() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(product_readiness_claimed=True, private_self_use_approved=True),
        local_web_candidate=_local_web_candidate(),
    )

    assert candidate["candidate_prepared"] is False
    assert "decision_pack_product_readiness_claimed" in candidate["input_integrity"]["blockers"]
    assert "decision_pack_private_self_use_approved" in candidate["input_integrity"]["blockers"]
    assert candidate["private_self_use_approved"] is False


def test_private_self_use_candidate_requires_local_web_candidate_v2() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(),
        local_web_candidate={},
    )

    assert candidate["candidate_prepared"] is False
    assert candidate["activation_status"] == "blocked"
    assert "local_web_candidate_missing" in candidate["input_integrity"]["blockers"]
    assert candidate["requires_human_approval"] is False
    assert candidate["private_self_use_approved"] is False


def test_private_self_use_candidate_blocks_failed_local_web_candidate_v2() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(),
        local_web_candidate=_local_web_candidate(
            candidate_prepared=False,
            blockers=["pre-live overclaim"],
        ),
    )

    assert candidate["candidate_prepared"] is False
    assert "local_web_candidate_not_prepared" in candidate["input_integrity"]["blockers"]
    assert candidate["local_web_candidate_summary"]["blockers"] == ["pre-live overclaim"]


def test_private_self_use_candidate_blocks_local_web_candidate_overclaims() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(),
        local_web_candidate=_local_web_candidate(
            private_self_use_approved=True,
            product_readiness_claimed=True,
            live_manager_required=True,
            production_selected=True,
            runtime_web_activation_approved=True,
            mutation_rollout_approved=True,
            shadow_or_canary_approved=True,
        ),
    )

    assert candidate["candidate_prepared"] is False
    assert "local_web_candidate_private_self_use_approved" in candidate["input_integrity"]["blockers"]
    assert "local_web_candidate_product_readiness_claimed" in candidate["input_integrity"]["blockers"]
    assert "local_web_candidate_live_manager_required" in candidate["input_integrity"]["blockers"]
    assert "local_web_candidate_production_selected" in candidate["input_integrity"]["blockers"]
    assert "local_web_candidate_runtime_web_activation_approved" in candidate["input_integrity"]["blockers"]
    assert "local_web_candidate_mutation_rollout_approved" in candidate["input_integrity"]["blockers"]
    assert "local_web_candidate_shadow_or_canary_approved" in candidate["input_integrity"]["blockers"]
    assert candidate["private_self_use_approved"] is False


def test_private_self_use_candidate_blocks_local_web_candidate_with_upstream_blockers() -> None:
    candidate = build_accurate_intake_private_self_use_candidate(
        _decision_pack(),
        local_web_candidate=_local_web_candidate(
            candidate_prepared=True,
            blockers=["websearch used"],
        ),
    )

    assert candidate["candidate_prepared"] is False
    assert "local_web_candidate_has_blockers" in candidate["input_integrity"]["blockers"]
    assert candidate["local_web_candidate_summary"]["blockers"] == ["websearch used"]


def test_private_self_use_candidate_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "accurate_intake_mvp_live_decision_pack.json"
    local_web_candidate = tmp_path / "accurate_intake_local_web_self_use_candidate_v2.json"
    source.write_text(json.dumps(_decision_pack(), ensure_ascii=False), encoding="utf-8")
    local_web_candidate.write_text(json.dumps(_local_web_candidate(), ensure_ascii=False), encoding="utf-8")

    output = write_accurate_intake_private_self_use_candidate(
        decision_pack_path=source,
        local_web_candidate_path=local_web_candidate,
        output_dir=tmp_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "accurate_intake_mvp_private_self_use_candidate.json"
    assert payload["artifact_type"] == "accurate_intake_mvp_private_self_use_candidate"
    assert payload["private_self_use_approved"] is False


def test_private_self_use_candidate_writer_accepts_run_specific_output_path(tmp_path: Path) -> None:
    source = tmp_path / "accurate_intake_mvp_live_decision_pack.json"
    local_web_candidate = tmp_path / "accurate_intake_local_web_self_use_candidate_v2.json"
    output_path = tmp_path / "run_i" / "accurate_intake_mvp_private_self_use_candidate_run_i.json"
    source.write_text(json.dumps(_decision_pack(), ensure_ascii=False), encoding="utf-8")
    local_web_candidate.write_text(json.dumps(_local_web_candidate(), ensure_ascii=False), encoding="utf-8")

    output = write_accurate_intake_private_self_use_candidate(
        decision_pack_path=source,
        local_web_candidate_path=local_web_candidate,
        output_path=output_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "accurate_intake_mvp_private_self_use_candidate"
