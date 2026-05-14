from __future__ import annotations

import yaml

from app.advanced_shadow_lab.proactive_deterministic_gate import (
    evaluate_proactive_deterministic_trigger_gate,
)
from app.advanced_shadow_lab.product_lab_proactive_gate import (
    review_product_lab_proactive_candidates,
)


def test_deterministic_trigger_gate_passes_before_llm_send_skip() -> None:
    result = evaluate_proactive_deterministic_trigger_gate(
        trigger_type="recommendation_prompt",
        turn={"surface": "chat", "lab_now_minute": 780},
        context={
            "local_time": "12:30",
            "max_recent_send_count": 2,
            "recent_send_count": 0,
            "delivery_surface_by_trigger": {"recommendation_prompt": "app_open"},
            "onboarding_ready_by_trigger": {"recommendation_prompt": True},
            "data_sufficiency_by_trigger": {"recommendation_prompt": True},
        },
    )

    assert result["status"] == "pass"
    assert result["llm_contextual_send_skip_allowed"] is True
    assert result["checks"] == {
        "quiet_hours_passed": True,
        "recent_send_cap_passed": True,
        "cooldown_passed": True,
        "surface_passed": True,
        "permission_posture_passed": True,
        "onboarding_gate_passed": True,
        "data_sufficiency_passed": True,
    }
    assert result["suppression_reasons"] == []


def test_deterministic_trigger_gate_blocks_context_before_llm() -> None:
    result = evaluate_proactive_deterministic_trigger_gate(
        trigger_type="rescue_nudge",
        turn={"surface": "chat", "lab_now_minute": 50},
        context={
            "local_time": "23:10",
            "max_recent_send_count": 2,
            "recent_send_count": 2,
            "last_sent_minute_by_trigger": {"rescue_nudge": 40},
            "cooldown_minutes_by_trigger": {"rescue_nudge": 30},
            "explicit_consent_ready_by_trigger": {"rescue_nudge": False},
            "onboarding_ready_by_trigger": {"rescue_nudge": False},
            "data_sufficiency_by_trigger": {"rescue_nudge": False},
        },
    )

    assert result["status"] == "blocked"
    assert result["llm_contextual_send_skip_allowed"] is False
    assert result["checks"] == {
        "quiet_hours_passed": False,
        "recent_send_cap_passed": False,
        "cooldown_passed": False,
        "surface_passed": True,
        "permission_posture_passed": False,
        "onboarding_gate_passed": False,
        "data_sufficiency_passed": False,
    }
    assert result["suppression_reasons"] == [
        "quiet_hours",
        "recent_send_cap",
        "cooldown_active",
        "permission_explicit_consent_required",
        "onboarding_gate_not_ready",
        "data_sufficiency_missing",
    ]


def test_product_lab_pre_delivery_review_exposes_deterministic_gate_result() -> None:
    artifact = review_product_lab_proactive_candidates(
        turn={"surface": "chat", "lab_now_minute": 780},
        candidates=[
            {
                "candidate_id": "recommendation_prompt:0",
                "trigger_type": "recommendation_prompt",
                "status": "pass",
                "source_output_refs": ["recommendation:offer-1"],
            }
        ],
        memory_context_pack={},
        prior_control_journal=[],
    )

    [review] = artifact["candidate_reviews"]
    assert review["deterministic_gate_result"]["status"] == "pass"
    assert review["deterministic_gate_result"]["llm_contextual_send_skip_allowed"] is True
    assert review["review_decision"]["status"] == "candidate_for_human_review"


def test_proactive_train_records_pr4_completion_and_next_active_slice() -> None:
    with open(
        "docs/quality/advanced_product_lab_proactive_chat_first_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 20
    assert plan["last_completed_pr_number"] >= 4
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 5
    assert {
        "pr_number": 4,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "deterministic_trigger_gate_core_completed_locally",
        "dynamic_remaining_pr_count_after": 20,
    } in plan["last_merge_evidence"]["completed_prs"]
