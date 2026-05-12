from __future__ import annotations


def _scope() -> dict[str, str]:
    return {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
    }


def _memory_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": "memory-record-strong-flavor",
        "record_type": "confirmed_preference",
        "family": "diet_product",
        "status": "candidate",
        "summary": "User prefers strong flavored meals.",
        "polarity": "positive",
        "strength": "boost",
        "scope_keys": _scope(),
        "source_refs": ["message:founder-profile-positive-002"],
        "consumers": ["recommendation_shadow"],
        "history": ["feedback:seed-001"],
    }
    record.update(overrides)
    return record


def _feedback_event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        "target_type": "memory_candidate",
        "target_id": "memory-candidate-strong-flavor",
        "action": "confirm",
        "source_turn_id": "turn-founder-profile-001",
        "scope_keys": _scope(),
    }
    event.update(overrides)
    return event


def test_memory_record_contract_accepts_minimal_envelope_without_activation() -> None:
    from app.memory.application.memory_feedback_contract import (
        validate_memory_record_contract,
    )

    result = validate_memory_record_contract(_memory_record())

    assert result["artifact_type"] == "memory_record_contract_validation"
    assert result["status"] == "pass"
    assert result["normalized_record"]["record_type"] == "confirmed_preference"
    assert result["normalized_record"]["polarity"] == "positive"
    assert result["normalized_record"]["strength"] == "boost"
    assert result["mutates_truth_directly"] is False
    assert result["durable_product_memory_written"] is False
    assert result["manager_context_packet_changed"] is False


def test_memory_record_contract_rejects_unknown_type_missing_scope_and_source() -> None:
    from app.memory.application.memory_feedback_contract import (
        validate_memory_record_contract,
    )

    bad = _memory_record(
        record_type="freeform_memory",
        scope_keys={"user_id": "user-a"},
        source_refs=[],
    )

    result = validate_memory_record_contract(bad)

    assert result["status"] == "blocked"
    assert "record_type.unsupported:freeform_memory" in result["blockers"]
    assert (
        "scope_keys.missing:workspace_id,project_id,surface"
        in result["blockers"]
    )
    assert "source_refs.missing" in result["blockers"]


def test_feedback_event_contract_validates_scope_source_and_non_mutation() -> None:
    from app.memory.application.memory_feedback_contract import (
        validate_feedback_event_contract,
    )

    result = validate_feedback_event_contract(_feedback_event())

    assert result["artifact_type"] == "feedback_event_contract_validation"
    assert result["status"] == "pass"
    assert result["normalized_event"]["target_type"] == "memory_candidate"
    assert result["normalized_event"]["action"] == "confirm"
    assert result["may_satisfy_memory_confirmation_gate"] is True
    assert result["mutates_truth_directly"] is False
    assert result["durable_product_memory_written"] is False
    assert result["manager_context_packet_changed"] is False


def test_feedback_event_contract_rejects_illegal_target_action_and_snooze_shape() -> None:
    from app.memory.application.memory_feedback_contract import (
        validate_feedback_event_contract,
    )

    illegal_confirm = validate_feedback_event_contract(
        _feedback_event(target_type="proactive_candidate", action="confirm")
    )
    missing_snooze_until = validate_feedback_event_contract(
        _feedback_event(
            target_type="proactive_candidate",
            action="snooze",
            target_id="proactive-candidate-evening-meal",
        )
    )

    assert illegal_confirm["status"] == "blocked"
    assert (
        "action.illegal_for_target:proactive_candidate.confirm"
        in illegal_confirm["blockers"]
    )
    assert missing_snooze_until["status"] == "blocked"
    assert "snooze_until.missing" in missing_snooze_until["blockers"]


def test_feedback_event_contract_rejects_missing_source_turn_and_scope() -> None:
    from app.memory.application.memory_feedback_contract import (
        validate_feedback_event_contract,
    )

    result = validate_feedback_event_contract(
        _feedback_event(source_turn_id="", scope_keys={"user_id": "user-a"})
    )

    assert result["status"] == "blocked"
    assert "source_turn_id.missing" in result["blockers"]
    assert (
        "scope_keys.missing:workspace_id,project_id,surface"
        in result["blockers"]
    )
