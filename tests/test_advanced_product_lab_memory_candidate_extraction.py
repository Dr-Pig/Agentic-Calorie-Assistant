from __future__ import annotations

import json


def test_product_lab_memory_candidate_extraction_builds_reviewable_candidates() -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        build_product_lab_memory_review_queue,
        extract_product_lab_memory_candidates,
    )

    extraction = extract_product_lab_memory_candidates(
        session_id="candidate-session",
        turn_id="t1",
        memory_signal_events=[
            _signal(
                "explicit-low-sugar",
                "explicit_preference",
                "User prefers low sugar breakfast options.",
                preferred_attributes=["low_sugar"],
            ),
            _signal(
                "negative-cilantro",
                "negative_preference",
                "User wants cilantro avoided.",
                blocks_candidate_types=["recommendation_candidate"],
            ),
            _signal(
                "temp-soup",
                "temporary_preference",
                "User wants lighter soup only today.",
                valid_until_minute=1440,
            ),
            _signal(
                "golden-oatmeal",
                "golden_order",
                "Morning Bar oatmeal is a reliable breakfast option.",
                store_name="Morning Bar",
                item_names=["oatmeal"],
                estimated_kcal=420,
            ),
            _signal(
                "tone-brief",
                "interaction_preference",
                "User prefers proactive meal suggestions to be brief.",
                intended_consumers=["proactive"],
            ),
            _signal(
                "meal-correction",
                "correction_not_memory",
                "User corrected a single meal estimate.",
            ),
        ],
    )

    assert extraction["artifact_type"] == (
        "advanced_product_lab_memory_candidate_extraction_artifact"
    )
    assert extraction["status"] == "pass"
    assert extraction["candidate_count"] == 5
    assert extraction["rejected_signal_ids"] == ["meal-correction"]
    assert extraction["lab_memory_store_written"] is False
    assert extraction["durable_product_memory_written"] is False
    assert extraction["canonical_product_mutation_allowed"] is False
    assert extraction["semantic_inference_used"] is False

    candidates_by_type = {
        candidate["candidate_type"]: candidate
        for candidate in extraction["memory_candidates"]
    }
    assert candidates_by_type["explicit_preference"]["memory_type"] == "preference"
    assert candidates_by_type["explicit_preference"]["review_action"] == (
        "promote_with_confirmation"
    )
    assert candidates_by_type["negative_preference"]["requires_confirmation"] is True
    assert candidates_by_type["temporary_preference"]["valid_until_minute"] == 1440
    assert candidates_by_type["golden_order"]["payload"]["store_name"] == "Morning Bar"
    assert candidates_by_type["interaction_preference"]["intended_consumers"] == [
        "proactive"
    ]
    assert all(
        candidate["scope_keys"]["session_id"] == "candidate-session"
        for candidate in extraction["memory_candidates"]
    )

    serialized = json.dumps(extraction, ensure_ascii=False)
    assert "RAW SHOULD NOT LEAK" not in serialized

    queue = build_product_lab_memory_review_queue(
        session_id="candidate-session",
        turn_id="t1",
        extraction_artifact=extraction,
    )

    assert queue["artifact_type"] == "advanced_product_lab_memory_review_queue"
    assert queue["status"] == "pass"
    assert queue["review_item_count"] == 5
    assert queue["queue_status"] == "pending_human_review"
    assert queue["memory_write_allowed"] is False
    assert queue["durable_product_memory_written"] is False
    assert queue["review_items"][0]["allowed_review_actions"] == [
        "promote_with_confirmation",
        "reject",
        "edit_summary",
    ]


def test_product_lab_memory_candidate_extraction_blocks_missing_source_scope() -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        extract_product_lab_memory_candidates,
    )

    missing_source = extract_product_lab_memory_candidates(
        session_id="candidate-session",
        turn_id="t1",
        memory_signal_events=[
            {
                "signal_id": "bad-source",
                "signal_type": "explicit_preference",
                "summary": "User prefers warm breakfasts.",
            }
        ],
    )
    missing_scope = extract_product_lab_memory_candidates(
        session_id="",
        turn_id="t1",
        memory_signal_events=[_signal("bad-scope", "explicit_preference", "x")],
    )

    assert missing_source["status"] == "blocked"
    assert missing_source["blockers"] == ["signal.bad-source.source_object_refs.missing"]
    assert missing_source["memory_candidates"] == []
    assert missing_scope["status"] == "blocked"
    assert missing_scope["blockers"] == ["session_id.unsafe_path_segment"]


def test_product_lab_memory_review_queue_blocks_cross_scope_candidates() -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        build_product_lab_memory_review_queue,
        extract_product_lab_memory_candidates,
    )

    extraction = extract_product_lab_memory_candidates(
        session_id="scope-a",
        turn_id="t1",
        memory_signal_events=[
            _signal("scope-a-pref", "explicit_preference", "Scope A preference.")
        ],
    )
    extraction["memory_candidates"][0]["scope_keys"]["session_id"] = "scope-b"

    queue = build_product_lab_memory_review_queue(
        session_id="scope-a",
        turn_id="t1",
        extraction_artifact=extraction,
    )

    assert queue["status"] == "blocked"
    assert queue["blockers"] == ["candidate.scope-a-pref.scope_keys.session_mismatch"]
    assert queue["review_items"] == []
    assert queue["memory_write_allowed"] is False


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
