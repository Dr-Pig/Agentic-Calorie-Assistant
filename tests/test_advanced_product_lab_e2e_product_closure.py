from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_live_diagnostic import (
    run_product_lab_live_diagnostic,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (
    build_product_lab_simulated_turns,
)
from app.advanced_shadow_lab.product_lab_simulated_summary import (
    build_simulated_dogfood_summary,
)
from tests.test_advanced_product_lab_runtime import _turn


def test_product_lab_e2e_surface_uses_product_outputs_and_controls(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("product-closure-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )
    messages = artifact["lab_chat_surface"]["messages"]
    serialized = json.dumps(artifact["lab_chat_surface"], ensure_ascii=False)

    assert artifact["status"] == "pass"
    assert artifact["product_lab_recommendation_artifact"]["offer_synthesis"][
        "selected_primary"
    ]["candidate_id"] == "memory-oatmeal"
    assert messages[0]["workflow_family"] == "recommendation"
    assert "Morning Bar oatmeal" in messages[0]["copy"]
    assert messages[0]["product_runtime_output_refs"] == [
        "advanced_product_lab_recommendation_runtime_artifact",
        "advanced_product_lab_proactive_runtime_artifact",
    ]
    assert messages[1]["workflow_family"] == "rescue"
    assert "Smooth today over 2 days" in messages[1]["copy"]
    assert messages[1]["product_runtime_output_refs"] == [
        "advanced_product_lab_rescue_runtime_artifact",
        "advanced_product_lab_proactive_runtime_artifact",
    ]
    assert all(message["controls_visible"] is True for message in messages)
    assert artifact["product_lab_proactive_artifact"]["candidate_count"] == 2
    assert artifact["lab_chat_response_packet"]["product_outputs_applied"] is True
    assert "no_send" not in serialized


def test_product_lab_final_loop_closes_with_live_diagnostic_dormant_wall(
    tmp_path: Path,
) -> None:
    session = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path / "final-loop",
        session_id="product-lab-final-loop",
        fixture_inputs=build_product_lab_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    summary = build_simulated_dogfood_summary(session)
    live_diagnostic = run_product_lab_live_diagnostic(
        summary_artifact=summary,
        provider=_FinalLoopProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert summary["status"] == "pass"
    assert summary["advanced_product_lab_product_loop_closed"] is True
    assert summary["product_runtime_capabilities_exercised"] == [
        "long_term_memory",
        "recommendation",
        "rescue",
        "proactive",
        "chat_surface",
    ]
    assert summary["lab_chat_action_outcome_types"] == [
        "recommendation_intake_draft",
        "rescue_commit_confirmation",
        "pending_intake_confirmed_lab",
    ]
    assert live_diagnostic["status"] == "pass"
    assert live_diagnostic["source_product_loop_closed"] is True
    assert live_diagnostic["live_provider_used"] is False
    assert live_diagnostic["user_facing_behavior_changed"] is False
    assert live_diagnostic["mainline_runtime_connected"] is False
    assert live_diagnostic["canonical_product_mutation_allowed"] is False
    assert live_diagnostic["durable_product_memory_written"] is False


def _memory_pack(tmp_path: Path) -> dict[str, object]:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="closure-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is reliable before meetings.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "store_name": "Morning Bar",
                "item_names": ["oatmeal"],
                "estimated_kcal": 420,
                "intended_consumers": ["recommendation", "proactive"],
            }
        ],
    )
    return build_product_lab_memory_context_pack(
        store=store,
        session_id="closure-session",
        turn_id="t2",
        consumers=["recommendation", "proactive"],
        token_budget=120,
    )


class _FinalLoopProvider:
    def readiness(self) -> dict[str, object]:
        return {"provider": "final-loop-fake", "configured": True}

    async def complete_with_trace(
        self,
        **_: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "diagnostic_notes": "Final lab loop closes inside the isolated lab.",
            "risk_notes": "Diagnostic only; no outside-lab delivery or mutation.",
            "claim_scope": "diagnostic_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["final_loop_contract"],
        }, {"stage": "advanced_product_lab_live_diagnostic", "provider": "fake"}
