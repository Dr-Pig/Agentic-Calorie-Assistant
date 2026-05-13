from __future__ import annotations

from pathlib import Path

import yaml

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
    build_product_lab_planned_event_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_planned_event_all_day_fixture_inputs import (
    build_product_lab_planned_event_all_day_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "quality" / "advanced_product_lab_rescue_phase1_pr_train.yaml"
GOLDEN_PATH = ROOT / "docs" / "quality" / "advanced_product_lab_rescue_phase1_golden_set.yaml"


def pr_train() -> dict:
    return yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8-sig"))


def golden_set() -> dict:
    return yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8-sig"))


def live_diagnostics() -> list[dict[str, object]]:
    return [
        live_diagnostic("rescue_proposal_shaping_provider_diagnostic"),
        live_diagnostic("rescue_response_presentation_provider_diagnostic"),
    ]


def live_diagnostic(artifact_type: str) -> dict[str, object]:
    return {
        "artifact_type": artifact_type,
        "status": "pass",
        "provider_mode": "builderspace-grok-4-fast",
        "live_llm_invoked": True,
        "live_provider_used": True,
        "provider_readiness": {"provider_profile_id": "builderspace-grok-4-fast"},
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "production_scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "blockers": [],
    }


def replay_artifacts(tmp_path: Path) -> list[dict[str, object]]:
    return [
        replay_case("F", "simulated_self_use", f_session(tmp_path, "accept_rescue_plan")),
        replay_case("F", "lab_accept_dismiss", f_session(tmp_path, "accept_rescue_plan")),
        replay_case("F", "lab_accept_dismiss", f_session(tmp_path, "dismiss_rescue_plan")),
        replay_case("F2", "integrated_e2e", f2_session(tmp_path)),
        replay_case("T", "integrated_e2e", t_session(tmp_path)),
    ]


def replay_case(
    journey_id: str,
    replay_kind: str,
    session: dict[str, object],
) -> dict[str, object]:
    return {
        "artifact_type": "rescue_phase1_lab_replay_case",
        "journey_id": journey_id,
        "replay_kind": replay_kind,
        "session_artifact": session,
    }


def f_session(tmp_path: Path, action: str) -> dict[str, object]:
    return run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path / f"f-{action}",
        session_id=f"f-{action}",
        fixture_inputs=build_product_lab_fixture_inputs(),
        turns=[
            {
                "turn_id": "f-action",
                "post_turn_chat_actions": [
                    {
                        "event_id": f"{action}-event",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": action,
                    }
                ],
            }
        ],
    )


def f2_session(tmp_path: Path) -> dict[str, object]:
    return run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path / "f2",
        session_id="f2-session",
        fixture_inputs=build_product_lab_planned_event_fixture_inputs(),
        turns=[{**planned_event_turn("f2-accept"), "post_turn_chat_actions": [accept_f2()]}],
    )


def t_session(tmp_path: Path) -> dict[str, object]:
    return run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path / "t",
        session_id="t-session",
        fixture_inputs=build_product_lab_planned_event_all_day_fixture_inputs(),
        turns=[
            {
                "turn_id": "t-guidance",
                "semantic_intent_fixture": "planned_event_all_day_allocation",
                "planned_event_guidance_enabled": True,
            },
            {
                **planned_event_turn("t-accept"),
                "semantic_intent_fixture": "planned_event_all_day_allocation",
                "post_turn_chat_actions": [accept_f2()],
            },
        ],
    )


def planned_event_turn(turn_id: str) -> dict[str, object]:
    return {
        "turn_id": turn_id,
        "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
        "planned_event_rescue_enabled": True,
    }


def accept_f2() -> dict[str, object]:
    return {
        "event_id": "accept-planned-rescue",
        "target_candidate_id": "planned_event_rescue:0",
        "action": "accept_rescue_plan",
    }
