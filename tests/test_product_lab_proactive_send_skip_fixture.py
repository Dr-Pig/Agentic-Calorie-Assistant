from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_proactive_send_skip import (
    run_product_lab_proactive_send_skip_fixture,
)
from tests.test_product_lab_proactive_wake_sources import (
    _memory_pack,
    _recommendation_artifact,
    _rescue_artifact,
)


def test_contextual_send_skip_fixture_accepts_llm_owned_decisions() -> None:
    proactive = _proactive_artifact()
    artifact = run_product_lab_proactive_send_skip_fixture(
        pre_delivery_review=proactive["pre_delivery_review"],
        provider_decisions=[
            {
                "candidate_id": "recommendation_prompt:0",
                "send_or_skip": "send",
                "reason_summary": "The user opened the app and asked for meal help.",
                "chat_first_copy": "要不要我幫你從現在可行的選項挑一個？",
                "skip_reason": "",
                "reason_codes": ["app_open", "qualified_offer"],
                "delivery_request": False,
                "scheduler_request": False,
                "notification_request": False,
                "mutation_request": False,
            },
            {
                "candidate_id": "rescue_nudge:1",
                "send_or_skip": "skip",
                "reason_summary": "Rescue nudges need explicit consent here.",
                "chat_first_copy": "",
                "skip_reason": "permission_posture_not_ready",
                "reason_codes": ["explicit_consent_required"],
                "delivery_request": False,
                "scheduler_request": False,
                "notification_request": False,
                "mutation_request": False,
            },
        ],
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_proactive_contextual_send_skip_fixture"
    )
    assert artifact["status"] == "pass"
    assert artifact["semantic_decision_owner"] == "fixture_llm_provider"
    assert artifact["deterministic_role"] == "validate_reject_or_omit_only"
    assert artifact["send_candidate_ids"] == ["recommendation_prompt:0"]
    assert artifact["skip_candidate_ids"] == ["rescue_nudge:1"]
    assert artifact["omission_traces"] == [
        {
            "candidate_id": "rescue_nudge:1",
            "trigger_type": "rescue_nudge",
            "omission_reason": "contextual_send_skip:permission_posture_not_ready",
            "source_refs": [
                "advanced_product_lab_rescue_runtime_artifact",
                "proposal:same_day_rescue_lab",
            ],
            "scheduler_delivery_allowed": False,
            "canonical_product_mutation_allowed": False,
        }
    ]
    assert artifact["live_provider_used"] is False
    assert artifact["notification_delivery_allowed"] is False


def test_contextual_send_skip_fixture_blocks_side_effect_requests() -> None:
    proactive = _proactive_artifact()
    artifact = run_product_lab_proactive_send_skip_fixture(
        pre_delivery_review=proactive["pre_delivery_review"],
        provider_decisions=[
            {
                "candidate_id": "recommendation_prompt:0",
                "send_or_skip": "send",
                "reason_summary": "I will notify and save this.",
                "chat_first_copy": "I sent this and updated your budget.",
                "skip_reason": "",
                "reason_codes": ["unsafe"],
                "delivery_request": True,
                "scheduler_request": True,
                "notification_request": True,
                "mutation_request": True,
            }
        ],
    )

    assert artifact["status"] == "blocked"
    assert artifact["send_candidate_ids"] == []
    assert artifact["blockers"] == [
        "provider_decision[recommendation_prompt:0].delivery_request_not_allowed",
        "provider_decision[recommendation_prompt:0].scheduler_request_not_allowed",
        "provider_decision[recommendation_prompt:0].notification_request_not_allowed",
        "provider_decision[recommendation_prompt:0].mutation_request_not_allowed",
        "provider_decision[rescue_nudge:1].decision_missing",
    ]
    assert artifact["scheduler_delivery_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def _proactive_artifact() -> dict[str, object]:
    return run_product_lab_proactive(
        turn={"session_id": "s1", "turn_id": "t1", "surface": "chat"},
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(),
        recommendation_artifact=_recommendation_artifact(),
        rescue_artifact=_rescue_artifact(),
    )
