from __future__ import annotations

import json

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from tests.test_product_lab_proactive_wake_sources import (
    _memory_pack,
    _recommendation_artifact,
    _rescue_artifact,
)


def test_pre_delivery_candidate_trace_records_wake_reason_and_interrupt_cost() -> None:
    artifact = run_product_lab_proactive(
        turn={"session_id": "s1", "turn_id": "t1", "surface": "chat"},
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(),
        recommendation_artifact=_recommendation_artifact(),
        rescue_artifact=_rescue_artifact(),
    )

    [recommendation, rescue] = artifact["candidates"]
    rec_trace = recommendation["pre_delivery_candidate_trace"]
    rescue_trace = rescue["pre_delivery_candidate_trace"]
    assert rec_trace == {
        "artifact_type": "advanced_product_lab_proactive_pre_delivery_candidate_trace",
        "artifact_schema_version": "1.0",
        "candidate_id": "recommendation_prompt:0",
        "trigger_type": "recommendation_prompt",
        "downstream_workflow_family": "recommendation",
        "candidate_quality_tier": "",
        "source_selected_candidate_id": "memory-oatmeal",
        "source_family": "recommendation",
        "wake_source": "app_open",
        "user_relevant_reason": "qualified_recommendation_offer_available",
        "interrupt_cost": "app_open_low",
        "candidate_created_before_delivery": True,
        "lab_delivery_candidate_created": True,
        "source_output_refs": [
            "advanced_product_lab_recommendation_runtime_artifact",
            "candidate:memory-oatmeal",
        ],
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
    }
    assert rescue_trace["interrupt_cost"] == "explicit_consent_required_high"
    assert artifact["delivery_packet"]["candidate_traces_by_candidate"][
        "recommendation_prompt"
    ] == rec_trace
    assert "no_send" not in json.dumps(artifact, ensure_ascii=False)
