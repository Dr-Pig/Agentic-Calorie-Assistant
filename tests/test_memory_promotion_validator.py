from __future__ import annotations


def _scope() -> dict[str, str]:
    return {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
    }


def _record(record_id: str, **overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": record_id,
        "record_type": "pattern_memory",
        "family": "diet_product",
        "status": "pending_review",
        "summary": "User repeatedly chooses ramen.",
        "polarity": "positive",
        "strength": "boost",
        "scope_keys": _scope(),
        "source_refs": [f"message:{record_id}"],
        "consumers": ["recommendation_shadow"],
        "history": [f"feedback:{record_id}"],
    }
    record.update(overrides)
    return record


def _confirm_projection(target_id: str) -> dict[str, object]:
    return {
        "projection_type": "memory_confirmation_validator_input",
        "target_type": "memory_candidate",
        "target_id": target_id,
        "may_satisfy_memory_confirmation_gate": True,
        "validator_required": True,
        "confirmed_memory_promoted": False,
    }


def test_pattern_memory_requires_threshold_and_confirmation_projection() -> None:
    from app.memory.application.memory_promotion_validator import (
        validate_memory_record_promotion_decision,
    )

    below = validate_memory_record_promotion_decision(
        memory_record=_record("pattern-ramen", reinforcement_count=4),
        as_of="2026-05-12T00:00:00+08:00",
        feedback_projection=_confirm_projection("pattern-ramen"),
    )
    missing_confirm = validate_memory_record_promotion_decision(
        memory_record=_record("pattern-ramen", reinforcement_count=5),
        as_of="2026-05-12T00:00:00+08:00",
    )
    confirmable = validate_memory_record_promotion_decision(
        memory_record=_record("pattern-ramen", reinforcement_count=5),
        as_of="2026-05-12T00:00:00+08:00",
        feedback_projection=_confirm_projection("pattern-ramen"),
    )

    assert below["decision"] == "hold_for_more_evidence"
    assert missing_confirm["decision"] == "human_confirmation_required"
    assert confirmable["decision"] == "confirmable_after_validator"
    assert confirmable["status_after"] == "confirmed"
    assert confirmable["durable_product_memory_written"] is False
    assert confirmable["confirmed_memory_promoted"] is False


def test_temporary_preference_expiry_becomes_archive_review_only() -> None:
    from app.memory.application.memory_promotion_validator import (
        validate_memory_record_promotion_decision,
    )

    decision = validate_memory_record_promotion_decision(
        memory_record=_record(
            "temporary-low-carb",
            record_type="temporary_preference",
            status="confirmed",
            validity={"valid_until": "2026-05-01"},
        ),
        as_of="2026-05-12T00:00:00+08:00",
    )

    assert decision["decision"] == "archive_review_candidate"
    assert decision["status_after"] == "archived"
    assert decision["canonical_mutation_changed"] is False


def test_confirmed_negative_preference_conflict_requires_review_not_auto_demote() -> None:
    from app.memory.application.memory_promotion_validator import (
        validate_memory_record_promotion_decision,
    )

    decision = validate_memory_record_promotion_decision(
        memory_record=_record(
            "no-spicy",
            record_type="negative_preference",
            status="confirmed",
            summary="User does not eat spicy food.",
            polarity="negative",
            strength="block",
            conflicts_with=["pattern-spicy-ramen"],
        ),
        as_of="2026-05-12T00:00:00+08:00",
    )

    assert decision["decision"] == "contradiction_review_candidate"
    assert decision["auto_demote_allowed"] is False
    assert decision["status_after"] == "confirmed"


def test_llm_auto_promotion_claim_is_rejected_for_memory_record() -> None:
    from app.memory.application.memory_promotion_validator import (
        validate_memory_record_promotion_decision,
    )

    decision = validate_memory_record_promotion_decision(
        memory_record=_record(
            "llm-pattern",
            reinforcement_count=5,
            llm_recommended_promotion=True,
            promotion_allowed_now=True,
        ),
        as_of="2026-05-12T00:00:00+08:00",
        feedback_projection=_confirm_projection("llm-pattern"),
    )

    assert decision["decision"] == "blocked"
    assert "llm_auto_promotion_claim_blocked" in decision["blockers"]
    assert decision["status_after"] == "pending_review"


def test_validator_blocks_scope_and_feedback_target_mismatch() -> None:
    from app.memory.application.memory_promotion_validator import (
        validate_memory_record_promotion_decision,
    )

    bad_scope = validate_memory_record_promotion_decision(
        memory_record=_record("bad-scope", scope_keys={"user_id": "user-a"}),
        as_of="2026-05-12T00:00:00+08:00",
    )
    mismatch = validate_memory_record_promotion_decision(
        memory_record=_record("pattern-ramen", reinforcement_count=5),
        as_of="2026-05-12T00:00:00+08:00",
        feedback_projection=_confirm_projection("other-pattern"),
    )

    assert bad_scope["decision"] == "blocked"
    assert "scope_keys.missing:workspace_id,project_id,surface" in bad_scope[
        "blockers"
    ]
    assert mismatch["decision"] == "human_confirmation_required"
    assert "feedback_target_mismatch" in mismatch["reason_codes"]
