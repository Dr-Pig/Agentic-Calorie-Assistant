from __future__ import annotations

from pathlib import Path


def test_product_lab_memory_lifecycle_policy_archives_stale_but_keeps_negative(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        ProductLabMemoryStore,
        apply_product_lab_memory_lifecycle_policy,
        build_product_lab_memory_context_pack,
    )

    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="policy-session",
        turn_id="t1",
        events=[
            _memory(
                "pattern-lunch",
                "pattern_memory",
                "User often picks lunch bowls.",
                last_observed_day=0,
            ),
            _memory(
                "golden-oatmeal",
                "golden_order",
                "Morning Bar oatmeal is reliable.",
                last_observed_day=0,
                is_active=True,
            ),
            _memory(
                "negative-cilantro",
                "negative_preference",
                "Avoid cilantro.",
                last_observed_day=0,
            ),
            _memory(
                "temp-soup",
                "temporary_preference",
                "Soup only today.",
                valid_until_minute=30,
            ),
        ],
    )

    policy = apply_product_lab_memory_lifecycle_policy(
        store=store,
        session_id="policy-session",
        turn_id="t2",
        lab_now_day=65,
        lab_now_minute=60,
    )

    assert policy["status"] == "pass"
    assert policy["applied_actions"] == [
        {"record_id": "golden-oatmeal", "action": "deactivate"},
        {"record_id": "pattern-lunch", "action": "archive"},
        {"record_id": "temp-soup", "action": "expire"},
    ]
    by_id = {record["record_id"]: record for record in store.list_records("policy-session")}
    assert by_id["pattern-lunch"]["record_state"] == "archived_lab"
    assert by_id["golden-oatmeal"]["payload"]["is_active"] is False
    assert by_id["negative-cilantro"]["record_state"] == "active_lab"
    assert by_id["temp-soup"]["review_status"] == "expired_lab"

    pack = build_product_lab_memory_context_pack(
        store=store,
        session_id="policy-session",
        turn_id="t3",
        consumers=["recommendation"],
        token_budget=120,
        lab_now_minute=60,
    )

    assert pack["selected_record_ids"] == ["negative-cilantro"]
    assert {item["record_id"]: item["reason"] for item in pack["omission_trace"]} == {
        "golden-oatmeal": "stale_or_expired",
        "pattern-lunch": "archived_lab",
        "temp-soup": "archived_lab",
    }


def _memory(
    memory_id: str,
    memory_type: str,
    summary: str,
    **payload: object,
) -> dict[str, object]:
    return {
        "memory_id": memory_id,
        "memory_type": memory_type,
        "summary": summary,
        "review_status": "accepted_lab",
        "source_object_refs": [f"turn:t1:{memory_id}"],
        "intended_consumers": ["recommendation"],
        **payload,
    }
