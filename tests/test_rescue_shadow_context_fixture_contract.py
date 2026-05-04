from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TOP_LEVEL_FIELDS = {
    "user_id",
    "local_date",
    "timezone",
    "current_budget",
    "active_body_plan",
    "recent_committed_meals",
    "deficit_summary",
    "overshoot_summary",
    "calibration_posture",
    "adherence_summary",
    "rescue_history_summary",
    "open_proposals",
    "proactive_status",
}

EXPECTED_HARD_CONTEXT_BLOCKS = ["CurrentBudgetView", "OvershootSummary"]
EXPECTED_SOFT_CONTEXT_BLOCKS = [
    "AdherenceSummary",
    "RescueHistorySummary",
    "app_usage_style",
    "CalibrationPosture",
]

ACTIVE_RUNTIME_ENTRYPOINTS = [
    "app/routes.py",
    "app/schemas.py",
    "app/models.py",
    "app/composition/intake_routes.py",
    "app/composition/v2_routes.py",
    "app/composition/intake_turn_orchestrator.py",
    "app/composition/intake_execution_orchestrator.py",
    "app/runtime/application/manager_service.py",
    "app/composition/intake_manager_tool_batch.py",
    "app/runtime/interface/provider_runtime.py",
]


def _minimal_fixture_payload() -> dict[str, object]:
    return {
        "user_id": "user-rs1",
        "local_date": "2026-05-04",
        "timezone": "Asia/Taipei",
        "current_budget": {
            "active": True,
            "daily_budget_kcal": 1800,
            "consumed_kcal": 2100,
            "remaining_kcal": -300,
        },
        "active_body_plan": {
            "active": True,
            "daily_target_kcal": 1800,
            "safety_floor_kcal": 1400,
        },
        "recent_committed_meals": {},
        "deficit_summary": {},
        "overshoot_summary": {
            "today_overshoot_kcal": 300,
        },
        "calibration_posture": {},
        "adherence_summary": {},
        "rescue_history_summary": {},
        "open_proposals": {},
    }


def test_minimal_rescue_context_fixture_validates_and_dumps_required_fields() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_context")

    fixture = module.RescueContextFixture(**_minimal_fixture_payload())
    dumped = fixture.model_dump(mode="json")

    assert set(dumped) == EXPECTED_TOP_LEVEL_FIELDS
    assert dumped["local_date"] == "2026-05-04"
    assert dumped["current_budget"]["day_part"] == "unknown"
    assert dumped["recent_committed_meals"]["meal_count_today"] == 0
    assert dumped["deficit_summary"]["weekly_deficit_posture"] == "unknown"
    assert dumped["proactive_status"] is None


def test_rescue_context_hard_and_soft_blocks_match_required_classification() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_context")

    assert module.HARD_RESCUE_CONTEXT_BLOCKS == EXPECTED_HARD_CONTEXT_BLOCKS
    assert module.SOFT_RESCUE_CONTEXT_BLOCKS == EXPECTED_SOFT_CONTEXT_BLOCKS

    status = module.build_rescue_context_fixture_contract_status()

    assert status == {
        "artifact_type": "rescue_context_fixture_contract_status",
        "track": "RescueShadow",
        "slice_id": "rs1_context_fixture_contract",
        "fixture_only": True,
        "runtime_effect_allowed": False,
        "hard_context_blocks": EXPECTED_HARD_CONTEXT_BLOCKS,
        "soft_context_blocks": EXPECTED_SOFT_CONTEXT_BLOCKS,
    }


def test_calibration_posture_and_proactive_status_cannot_authorize_mutation_or_send() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_context")

    payload = _minimal_fixture_payload()
    payload["calibration_posture"] = {
        "body_plan_mutation_allowed": True,
    }
    payload["proactive_status"] = {
        "proactive_send_allowed": True,
    }

    with pytest.raises(ValidationError):
        module.RescueContextFixture(**payload)

    fixture = module.RescueContextFixture(
        **{
            **_minimal_fixture_payload(),
            "calibration_posture": {"body_plan_mutation_allowed": False},
            "proactive_status": {"proactive_send_allowed": False},
        }
    )

    assert fixture.calibration_posture.body_plan_mutation_allowed is False
    assert fixture.proactive_status.proactive_send_allowed is False


def test_rescue_context_fixture_rejects_unknown_fields() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_context")
    payload = _minimal_fixture_payload()
    payload["unexpected_runtime_field"] = "must_not_be_silently_accepted"

    with pytest.raises(ValidationError):
        module.RescueContextFixture(**payload)

    nested_payload = _minimal_fixture_payload()
    nested_payload["current_budget"] = {
        **nested_payload["current_budget"],
        "ledger_mutation_hint": "must_not_be_silently_accepted",
    }

    with pytest.raises(ValidationError):
        module.RescueContextFixture(**nested_payload)


def test_shadow_context_module_declares_offline_sidecar_activation_contract() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_context")
    contract = module.SIDECAR_ACTIVATION_CONTRACT

    assert contract.module_name == "rescue.domain.shadow_context"
    assert contract.offline_only is True
    assert contract.activation_blocked is True
    assert contract.not_runtime_authority is True
    assert contract.user_facing_activation is False
    assert contract.mutation_authority is False
    assert contract.product_intelligence_readiness_participant is False


def test_active_runtime_entrypoints_do_not_import_rescue_context_fixture() -> None:
    forbidden_tokens = [
        "app.rescue.domain.shadow_context",
        "shadow_context",
        "RescueContextFixture",
        "rescue_context_fixture_contract_status",
    ]

    for relative_path in ACTIVE_RUNTIME_ENTRYPOINTS:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} imports or references RS1 sidecar token {token!r}"
