from __future__ import annotations

import json


def _scope(**overrides: str) -> dict[str, str]:
    scope = {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
    }
    scope.update(overrides)
    return scope


def _record(record_id: str, **overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": record_id,
        "record_type": "confirmed_preference",
        "family": "diet_product",
        "status": "confirmed",
        "summary": f"{record_id} summary",
        "polarity": "positive",
        "strength": "boost",
        "scope_keys": _scope(),
        "source_refs": [f"source:{record_id}"],
        "consumers": ["recommendation_shadow"],
        "history": [f"feedback:{record_id}"],
        "subject_keys": [record_id],
    }
    record.update(overrides)
    return record


def _pack() -> dict[str, object]:
    from app.memory.application.memory_record_context_pack import (
        build_memory_record_context_pack,
    )

    return build_memory_record_context_pack(
        memory_records=[
            _record("likes-ramen", subject_keys=["ramen"]),
            _record(
                "no-spicy",
                record_type="negative_preference",
                summary="User does not eat spicy food.",
                polarity="negative",
                strength="block",
                subject_keys=["spicy_food"],
            ),
        ],
        scope_keys=_scope(),
        consumer="recommendation_shadow",
        token_budget=120,
    )


def _manager_input() -> dict[str, object]:
    return {
        "request_id": "manager-memory-bridge-001",
        "user_message": "help me choose dinner",
        "manager_context_packet_v1": {"recent_chat_window": {"loaded_message_count": 2}},
    }


def test_bridge_attaches_memory_only_to_lab_context_block() -> None:
    from app.memory.application.memory_manager_lab_bridge import (
        build_memory_manager_lab_bridge,
    )

    artifact = build_memory_manager_lab_bridge(
        manager_input=_manager_input(),
        shadow_memory_context_pack=_pack(),
        enable_lab_memory_context=True,
    )

    augmented = artifact["memory_augmented_manager_input"]
    context_block = augmented["lab_memory_context_block"]

    assert artifact["status"] == "pass"
    assert artifact["lab_enabled"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["shadow_memory_context_pack_used"] is True
    assert artifact["lab_manager_context_attached"] is True
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["manager_context_injected"] is False
    assert augmented["manager_context_packet_v1"] == _manager_input()["manager_context_packet_v1"]
    assert context_block["selected_record_ids"] == ["no-spicy", "likes-ramen"]
    assert context_block["negative_preference_blockers"] == ["no-spicy"]
    assert context_block["entries"][0]["summary"] == "User does not eat spicy food."
    assert artifact["paired_trace"]["baseline_has_lab_memory_context"] is False
    assert artifact["paired_trace"]["memory_run_has_lab_memory_context"] is True


def test_bridge_flag_off_keeps_manager_input_baseline_only() -> None:
    from app.memory.application.memory_manager_lab_bridge import (
        build_memory_manager_lab_bridge,
    )

    artifact = build_memory_manager_lab_bridge(
        manager_input=_manager_input(),
        shadow_memory_context_pack=_pack(),
        enable_lab_memory_context=False,
    )

    assert artifact["status"] == "pass"
    assert artifact["shadow_memory_context_pack_used"] is False
    assert artifact["lab_manager_context_attached"] is False
    assert artifact["memory_augmented_manager_input"] == artifact["baseline_manager_input"]
    assert "lab_memory_context_block" not in artifact["memory_augmented_manager_input"]


def test_bridge_blocks_pack_that_claims_manager_context_packet_change() -> None:
    from app.memory.application.memory_manager_lab_bridge import (
        build_memory_manager_lab_bridge,
    )

    pack = dict(_pack(), manager_context_packet_changed=True)
    artifact = build_memory_manager_lab_bridge(
        manager_input=_manager_input(),
        shadow_memory_context_pack=pack,
        enable_lab_memory_context=True,
    )

    assert artifact["status"] == "blocked"
    assert "shadow_memory_context_pack.manager_context_packet_changed" in artifact["blockers"]
    assert artifact["lab_manager_context_attached"] is False
    assert "lab_memory_context_block" not in artifact["memory_augmented_manager_input"]


def test_bridge_never_copies_raw_transcript_or_evidence_fields() -> None:
    from app.memory.application.memory_manager_lab_bridge import (
        build_memory_manager_lab_bridge,
    )

    pack = _pack()
    pack["entries"] = [
        {
            **pack["entries"][0],  # type: ignore[index]
            "raw_transcript": "RAW TRANSCRIPT SHOULD NOT LEAK",
            "evidence_text": "raw source evidence should stay behind source lookup",
        }
    ]
    artifact = build_memory_manager_lab_bridge(
        manager_input=_manager_input(),
        shadow_memory_context_pack=pack,
        enable_lab_memory_context=True,
    )
    serialized = json.dumps(artifact["memory_augmented_manager_input"])

    assert "RAW TRANSCRIPT SHOULD NOT LEAK" not in serialized
    assert "raw source evidence should stay behind source lookup" not in serialized
    assert artifact["memory_augmented_manager_input"]["lab_memory_context_block"][
        "source_lookup_required_for_evidence"
    ] is True
