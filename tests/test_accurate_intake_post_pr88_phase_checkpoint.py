from __future__ import annotations

import json
from pathlib import Path


def test_post_pr88_checkpoint_locks_return_to_product_mainline() -> None:
    checkpoint_path = Path("docs/quality/accurate_intake_post_pr88_phase_checkpoint.json")

    assert checkpoint_path.exists()

    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["checkpoint_id"] == "accurate_intake_post_pr88_phase_checkpoint"
    assert checkpoint["current_mainline"] == "Accurate Intake MVP local self-use shell"
    assert checkpoint["return_to_product_mainline"] is True
    assert checkpoint["grokfast_role"] == "diagnostic_contract_probe_only"
    assert checkpoint["do_not_continue_grokfast_full_suite_hardening"] is True
    assert checkpoint["next_pr_train"] == [
        "PR89_post_pr88_phase_checkpoint",
        "PR90_one_day_self_use_scenario_wall",
        "PR91_local_self_use_operator_shell",
        "PR92_local_self_use_candidate_packet",
    ]
    assert checkpoint["completed_baseline"] == [
        "PR85_contract_hardening_guard_and_drift_audit",
        "PR86_basket_holdout_anti_overfit_regression",
        "PR87_remove_item_target_evidence_boundary",
        "PR88_live_cost_summary_and_replay_hygiene",
    ]
    assert checkpoint["not_claiming"] == [
        "product_readiness",
        "private_self_use_approval",
        "model_portability",
        "production_model_selection",
        "shadow_or_canary",
        "mutation_rollout",
    ]
    assert checkpoint["claim_flags"] == {
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "model_portability_claimed": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
    }


def test_post_pr88_guidance_is_present_in_runbook_and_bootstrap() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )
    current_plan = Path("docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md").read_text(
        encoding="utf-8-sig"
    )

    required_fragments = [
        "Post-PR88 phase checkpoint",
        "GrokFast remains a diagnostic contract probe only",
        "stop GrokFast full-suite hardening",
        "return to the Accurate Intake local self-use shell",
        "future target-model diagnostic slice",
        "not a private self-use approval",
    ]
    for fragment in required_fragments:
        assert fragment in runbook
    assert "Current Shell self-use MVP local desktop dogfood" in current_plan
    assert "legacy Product Loop / PLCE planning prose" in current_plan
