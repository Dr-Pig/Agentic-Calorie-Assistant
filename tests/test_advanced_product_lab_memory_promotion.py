from __future__ import annotations

import json
from pathlib import Path


def test_product_lab_memory_review_decisions_promote_only_confirmed_items(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        ProductLabMemoryStore,
        apply_product_lab_memory_review_decisions,
        build_product_lab_memory_review_queue,
        extract_product_lab_memory_candidates,
    )

    store = ProductLabMemoryStore(tmp_path)
    queue = build_product_lab_memory_review_queue(
        session_id="promotion-session",
        turn_id="t1",
        extraction_artifact=extract_product_lab_memory_candidates(
            session_id="promotion-session",
            turn_id="t1",
            memory_signal_events=[
                _signal("explicit-low-sugar", "explicit_preference", "Low sugar."),
                _signal(
                    "golden-oatmeal",
                    "golden_order",
                    "Morning Bar oatmeal is reliable.",
                    store_name="Morning Bar",
                    item_names=["oatmeal"],
                    estimated_kcal=420,
                ),
                _signal("negative-cilantro", "negative_preference", "Avoid cilantro."),
                _signal(
                    "temp-soup",
                    "temporary_preference",
                    "Soup only today.",
                    valid_until_minute=1440,
                ),
            ],
        ),
    )

    promotion = apply_product_lab_memory_review_decisions(
        store=store,
        session_id="promotion-session",
        turn_id="t2",
        review_queue=queue,
        review_decisions=[
            _decision("explicit-low-sugar", "promote", confirmed=True),
            _decision("golden-oatmeal", "promote", confirmed=True),
            _decision("negative-cilantro", "reject", reason="too_specific"),
            _decision("temp-soup", "hold", reason="wait_for_second_signal"),
        ],
    )

    assert promotion["artifact_type"] == (
        "advanced_product_lab_memory_promotion_artifact"
    )
    assert promotion["status"] == "pass"
    assert promotion["promoted_record_ids"] == [
        "explicit-low-sugar",
        "golden-oatmeal",
    ]
    assert promotion["rejected_candidate_ids"] == ["negative-cilantro"]
    assert promotion["held_candidate_ids"] == ["temp-soup"]
    assert promotion["lab_memory_store_written"] is True
    assert promotion["durable_product_memory_written"] is False
    assert promotion["canonical_product_mutation_allowed"] is False
    assert promotion["manager_context_packet_changed"] is False

    records = store.list_records("promotion-session")
    assert [record["record_id"] for record in records] == [
        "explicit-low-sugar",
        "golden-oatmeal",
    ]
    assert {record["review_status"] for record in records} == {"accepted_lab"}
    assert records[1]["payload"]["store_name"] == "Morning Bar"
    assert "RAW SHOULD NOT LEAK" not in json.dumps(records, ensure_ascii=False)


def test_product_lab_memory_promotion_blocks_unconfirmed_promotion(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        ProductLabMemoryStore,
        apply_product_lab_memory_review_decisions,
        build_product_lab_memory_review_queue,
        extract_product_lab_memory_candidates,
    )

    store = ProductLabMemoryStore(tmp_path)
    queue = build_product_lab_memory_review_queue(
        session_id="promotion-session",
        turn_id="t1",
        extraction_artifact=extract_product_lab_memory_candidates(
            session_id="promotion-session",
            turn_id="t1",
            memory_signal_events=[
                _signal("explicit-low-sugar", "explicit_preference", "Low sugar.")
            ],
        ),
    )

    promotion = apply_product_lab_memory_review_decisions(
        store=store,
        session_id="promotion-session",
        turn_id="t2",
        review_queue=queue,
        review_decisions=[_decision("explicit-low-sugar", "promote")],
    )

    assert promotion["status"] == "blocked"
    assert promotion["blockers"] == [
        "decision.explicit-low-sugar.confirmation_required"
    ]
    assert promotion["promoted_record_ids"] == []
    assert store.list_records("promotion-session") == []


def _signal(
    signal_id: str,
    signal_type: str,
    summary: str,
    **payload: object,
) -> dict[str, object]:
    return {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "summary": summary,
        "source_object_refs": [f"turn:t1:{signal_id}"],
        "raw_user_utterance": "RAW SHOULD NOT LEAK",
        **payload,
    }


def _decision(
    candidate_id: str,
    decision: str,
    *,
    confirmed: bool = False,
    reason: str = "reviewed",
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "decision": decision,
        "confirmed": confirmed,
        "reviewer": "lab-human",
        "reason": reason,
    }
