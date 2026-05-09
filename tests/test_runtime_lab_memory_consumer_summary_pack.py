from __future__ import annotations

import json


def _candidate(
    candidate_id: str,
    candidate_type: str,
    review_status: str = "accepted_shadow",
    **payload: object,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "scope_keys": {
            "user_id": "user-a",
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "summary-run-001",
        },
        "source_trace_ids": [f"trace:{candidate_id}"],
        "source_object_refs": [f"message:{candidate_id}"],
        "review_status": review_status,
        "reason_codes": [f"{candidate_type}_reviewed"],
        "payload": payload,
        "promotion_allowed_now": False,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _review_contract(candidates: list[dict]) -> dict:
    return {
        "artifact_type": "runtime_lab_memory_candidate_review_contract",
        "status": "pass",
        "reviewed_shadow_candidates": candidates,
        "blockers": [],
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def test_consumer_summary_pack_uses_only_accepted_shadow_candidates() -> None:
    from app.memory.application.runtime_lab_consumer_summary_pack import (
        build_runtime_lab_memory_consumer_summary_pack,
    )

    pack = build_runtime_lab_memory_consumer_summary_pack(
        _review_contract(
            [
                _candidate("pref-1", "preference", summary="prefers tofu"),
                _candidate(
                    "neg-1",
                    "negative_preference",
                    summary="avoid sugary drinks",
                ),
                _candidate(
                    "golden-1",
                    "golden_order",
                    summary="Corner Bento chicken bento",
                    store_name="Corner Bento",
                    item_names=["chicken bento"],
                    source_kind="canonical_history_materialized_view",
                ),
                _candidate(
                    "ignored-1",
                    "interaction_preference",
                    summary="ignored meal reminder in evening",
                    trigger_type="meal_reminder",
                ),
                _candidate("rejected-1", "preference", "rejected", summary="omit me"),
            ]
        )
    )

    assert pack["artifact_type"] == "runtime_lab_memory_consumer_summary_projection"
    assert pack["status"] == "pass"
    assert pack["owner"] == "app/memory"
    assert pack["consumer"] == "recommendation_rescue_proactive_shadow_consumers"
    assert pack["retirement_trigger"] == "approved_memory_runtime_activation_plan"
    assert pack["runtime_effect_allowed"] is False
    assert pack["durable_product_memory_written"] is False
    assert pack["manager_context_packet_changed"] is False
    assert pack["recommendation_served"] is False
    assert pack["proactive_sent"] is False
    assert pack["rescue_proposal_committed"] is False

    preference = pack["preference_profile_summary"]
    assert preference["source_kind"] == "shadow_review_summary"
    assert preference["is_durable_memory_truth"] is False
    assert preference["accepted_shadow_candidate_ids"] == ["pref-1"]
    assert preference["negative_preference_blockers"] == ["neg-1"]

    golden = pack["golden_order_summary"]
    assert golden["projection_kind"] == "golden_order_projection_from_reviewed_shadow"
    assert golden["real_golden_order_materialized"] is False
    assert golden["orders"] == [
        {
            "candidate_id": "golden-1",
            "store_name": "Corner Bento",
            "item_names": ["chicken bento"],
            "summary": "Corner Bento chicken bento",
        }
    ]

    suppression = pack["suppression_summary"]
    assert suppression["suppression_blockers"] == [
        {
            "candidate_id": "ignored-1",
            "trigger_type": "meal_reminder",
            "summary": "ignored meal reminder in evening",
        }
    ]
    assert pack["omission_trace"] == [
        {"candidate_id": "rejected-1", "reason": "not_accepted_shadow"}
    ]


def test_consumer_summary_pack_blocks_raw_transcript_and_truth_leak() -> None:
    from app.memory.application.runtime_lab_consumer_summary_pack import (
        build_runtime_lab_memory_consumer_summary_pack,
    )

    pack = build_runtime_lab_memory_consumer_summary_pack(
        _review_contract(
            [
                _candidate(
                    "pref-raw",
                    "preference",
                    summary="prefers oats",
                    raw_user_input="RAW TRANSCRIPT MUST NOT LEAK",
                ),
                _candidate(
                    "pref-truth",
                    "preference",
                    summary="truth leak",
                    runtime_truth_allowed=True,
                ),
            ]
        )
    )

    serialized = json.dumps(pack, ensure_ascii=False)
    assert "RAW TRANSCRIPT MUST NOT LEAK" not in serialized
    assert pack["status"] == "blocked"
    assert pack["blockers"] == ["pref-truth.runtime_truth_allowed"]
    assert pack["durable_product_memory_written"] is False


def test_consumer_summary_pack_keeps_omitted_candidate_text_out_of_blockers() -> None:
    from app.memory.application.runtime_lab_consumer_summary_pack import (
        build_runtime_lab_memory_consumer_summary_pack,
    )

    pack = build_runtime_lab_memory_consumer_summary_pack(
        _review_contract(
            [
                _candidate(
                    "do-not-save-1",
                    "preference",
                    "rejected",
                    summary="private rejected summary must not leak",
                )
            ]
        )
    )

    serialized = json.dumps(pack, ensure_ascii=False)
    assert "private rejected summary must not leak" not in serialized
    assert pack["omission_trace"] == [
        {"candidate_id": "do-not-save-1", "reason": "not_accepted_shadow"}
    ]


def test_consumer_summary_pack_blocks_unpassed_review_contract() -> None:
    from app.memory.application.runtime_lab_consumer_summary_pack import (
        build_runtime_lab_memory_consumer_summary_pack,
    )

    pack = build_runtime_lab_memory_consumer_summary_pack(
        {
            "artifact_type": "runtime_lab_memory_candidate_review_contract",
            "status": "blocked",
            "reviewed_shadow_candidates": [],
            "blockers": ["candidate-1.missing_source_object_refs"],
        }
    )

    assert pack["status"] == "blocked"
    assert pack["blockers"] == [
        "review_contract_not_pass",
        "candidate-1.missing_source_object_refs",
    ]
    assert pack["preference_profile_summary"]["accepted_shadow_candidate_ids"] == []
