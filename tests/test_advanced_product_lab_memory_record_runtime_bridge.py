from __future__ import annotations

from app.memory.application.memory_record_context_pack import (
    build_memory_record_context_pack,
)
from tests.test_advanced_product_lab_runtime import _fixture_inputs, _turn


def _scope() -> dict[str, str]:
    return {
        "user_id": "advanced-product-lab-user",
        "workspace_id": "advanced-product-lab-workspace",
        "project_id": "advanced-product-lab",
        "surface": "chat",
    }


def _record(record_id: str, **overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": record_id,
        "record_type": "golden_order",
        "family": "diet_product",
        "status": "confirmed",
        "summary": "Morning Bar oatmeal is reliable before meetings.",
        "polarity": "positive",
        "strength": "boost",
        "scope_keys": _scope(),
        "source_refs": [f"source:{record_id}"],
        "consumers": ["recommendation_shadow", "proactive_shadow"],
        "history": [f"feedback:{record_id}"],
        "subject_keys": ["oatmeal"],
        "store_name": "Morning Bar",
        "item_names": ["oatmeal"],
        "estimated_kcal": 420,
    }
    record.update(overrides)
    return record


def _shadow_pack() -> dict[str, object]:
    return build_memory_record_context_pack(
        memory_records=[
            _record("memory-oatmeal"),
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


def test_memory_record_context_pack_drives_product_lab_runtime() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_runtime import (
        run_advanced_product_lab_turn_with_memory_records,
    )

    artifact = run_advanced_product_lab_turn_with_memory_records(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("memory-record-runtime-turn"),
        fixture_inputs=_fixture_inputs(),
        shadow_memory_context_pack=_shadow_pack(),
        enable_lab_memory_record_bridge=True,
    )

    bridge = artifact["memory_record_runtime_bridge"]
    recommendation = artifact["product_lab_recommendation_artifact"]

    assert artifact["status"] == "pass"
    assert bridge["status"] == "pass"
    assert bridge["memory_manager_lab_bridge"]["lab_manager_context_attached"] is True
    assert artifact["lab_memory_context_pack"]["selected_record_ids"] == [
        "no-spicy",
        "memory-oatmeal",
    ]
    assert artifact["lab_memory_context_pack"]["memory_context_injected"] is True
    assert recommendation["planning"]["candidate_spec"]["memory_record_refs"] == [
        "no-spicy",
        "memory-oatmeal",
    ]
    assert recommendation["offer_synthesis"]["selected_primary"]["candidate_id"] == (
        "memory-oatmeal"
    )
    assert artifact["lab_chat_response_packet"]["memory_context_applied"] is True
    assert artifact["memory_record_context_pack_used"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["durable_product_memory_written"] is False


def test_memory_record_runtime_bridge_blocks_unsafe_manager_packet_claim() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_runtime import (
        run_advanced_product_lab_turn_with_memory_records,
    )

    pack = dict(_shadow_pack(), manager_context_packet_changed=True)

    artifact = run_advanced_product_lab_turn_with_memory_records(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("memory-record-runtime-blocked"),
        fixture_inputs=_fixture_inputs(),
        shadow_memory_context_pack=pack,
        enable_lab_memory_record_bridge=True,
    )

    assert artifact["status"] == "blocked"
    assert "memory_record_runtime_bridge.shadow_memory_context_pack.manager_context_packet_changed" in artifact[
        "blockers"
    ]
    assert artifact["memory_record_context_pack_used"] is False
    assert artifact["lab_memory_context_pack"]["selected_record_ids"] == []
    assert artifact["manager_context_packet_changed"] is False
