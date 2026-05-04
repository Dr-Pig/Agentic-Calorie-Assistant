from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rescue.domain.shadow_context import RescueContextFixture


ROOT = Path(__file__).resolve().parents[1]

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
    "app/composition/manager_context_runtime.py",
    "app/intake/application/manager_context_policy.py",
    "app/runtime/agent/manager_context_payload.py",
]

REQUIRED_FALSE_FLAGS = [
    "real_runtime_effect",
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "manager_context_injected",
    "proactive_sent",
    "recommendation_served",
    "live_provider_used",
    "product_readiness_claimed",
    "private_self_use_approved",
]


def _context_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "user_id": "user-rs5",
        "local_date": "2026-05-04",
        "timezone": "Asia/Taipei",
        "current_budget": {
            "active": True,
            "daily_budget_kcal": 1800,
            "consumed_kcal": 1800,
            "remaining_kcal": 0,
            "day_part": "evening",
        },
        "active_body_plan": {
            "active": True,
            "daily_target_kcal": 1800,
            "safety_floor_kcal": 1400,
        },
        "recent_committed_meals": {
            "meal_count_today": 3,
            "logging_coverage": 0.9,
        },
        "deficit_summary": {
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        "overshoot_summary": {
            "today_overshoot_kcal": 650,
            "weekly_overshoot_kcal": 0,
            "recent_overshoot_days": 0,
        },
        "calibration_posture": {},
        "adherence_summary": {
            "logging_quality": "high",
            "adherence_score": 0.8,
        },
        "rescue_history_summary": {},
        "open_proposals": {},
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key] = {**payload[key], **value}  # type: ignore[index]
        else:
            payload[key] = value
    return payload


def _context(**overrides: object) -> RescueContextFixture:
    return RescueContextFixture(**_context_payload(**overrides))


def test_shadow_candidate_artifact_contains_required_fields_flags_and_selected_option() -> None:
    from app.rescue.application.shadow_candidate_artifact import (
        build_rescue_shadow_candidate_artifact,
    )

    candidate = build_rescue_shadow_candidate_artifact(
        scenario_id="rs5_large_overshoot_fixture",
        context=_context(),
    )
    payload = candidate.model_dump(mode="json")

    assert payload["scenario_id"] == "rs5_large_overshoot_fixture"
    assert payload["shadow_mode"] is True
    assert payload["runtime_effect_allowed"] is False
    for flag in REQUIRED_FALSE_FLAGS:
        assert payload[flag] is False

    assert payload["input_context_summary"]["user_id"] == "user-rs5"
    assert payload["overshoot_summary"]["today_overshoot_kcal"] == 650
    assert payload["trigger_candidate"] == "today_overshoot"
    assert payload["rescue_viability_score"] > 0
    assert payload["viability_band"] == "medium"
    assert payload["option_candidates"][0]["option_type"] == "multi_day_spread_candidate"
    assert payload["selected_shadow_option"]["option_id"] == payload["option_candidates"][0]["option_id"]
    assert "CurrentBudgetView" in payload["context_candidates_used"]
    assert "OvershootSummary" in payload["context_candidates_used"]
    assert "ManagerContextPacket" in payload["context_candidates_ignored"]
    assert "formal_proposal_contract" in payload["future_required_gate_before_runtime"]


def test_shadow_candidates_batch_artifact_is_json_safe_and_non_claiming() -> None:
    from app.rescue.application.shadow_candidate_artifact import (
        build_rescue_shadow_candidates_artifact,
    )

    artifact = build_rescue_shadow_candidates_artifact(
        scenarios=[
            ("rs5_large_overshoot_fixture", _context()),
            (
                "rs5_small_overshoot_fixture",
                _context(
                    overshoot_summary={"today_overshoot_kcal": 80},
                    deficit_summary={
                        "weekly_deficit_gap_kcal": -250,
                        "weekly_deficit_posture": "on_track",
                    },
                ),
            ),
        ]
    )
    payload = artifact.model_dump(mode="json")

    assert payload["artifact_type"] == "rescue_shadow_candidates"
    assert payload["track"] == "RescueShadow"
    assert payload["shadow_mode"] is True
    for flag in REQUIRED_FALSE_FLAGS:
        assert payload[flag] is False
    assert payload["summary"]["candidate_count"] == 2
    assert len(payload["rescue_shadow_candidates"]) == 2
    json.dumps(payload, ensure_ascii=False)


def test_shadow_candidate_contract_rejects_unknown_fields() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_artifact")

    with pytest.raises(ValidationError):
        module.RescueShadowCandidateArtifact(
            scenario_id="bad-extra-field",
            input_context_summary={},
            overshoot_summary={},
            trigger_candidate="no_rescue_needed",
            rescue_viability_score=0,
            viability_band="not_needed",
            option_candidates=[],
            options_rejected=[],
            reason_codes=[],
            confidence=0.5,
            harm_if_wrong="low",
            recommended_action="discard",
            context_candidates_used=[],
            context_candidates_ignored=[],
            future_required_gate_before_runtime=[],
            unexpected_runtime_field="must_not_be_silently_accepted",
        )


def test_shadow_candidate_summary_contracts_are_typed_frozen_and_json_safe() -> None:
    from app.rescue.application.shadow_candidate_artifact import (
        build_rescue_shadow_candidate_artifact,
    )

    candidate = build_rescue_shadow_candidate_artifact(
        scenario_id="rs5_typed_summary_fixture",
        context=_context(),
    )
    payload = candidate.model_dump(mode="python")
    payload["input_context_summary"]["unexpected_nested_field"] = "blocked"

    module = importlib.import_module("app.rescue.domain.shadow_artifact")
    with pytest.raises(ValidationError):
        module.RescueShadowCandidateArtifact(**payload)

    with pytest.raises(ValidationError):
        candidate.input_context_summary.user_id = "mutated"  # type: ignore[misc]


def test_shadow_candidate_selected_option_must_exactly_match_candidate() -> None:
    from app.rescue.application.shadow_candidate_artifact import (
        build_rescue_shadow_candidate_artifact,
    )

    candidate = build_rescue_shadow_candidate_artifact(
        scenario_id="rs5_selected_divergence_fixture",
        context=_context(),
    )
    payload = candidate.model_dump(mode="python")
    payload["selected_shadow_option"] = dict(payload["selected_shadow_option"])
    payload["selected_shadow_option"]["rationale"] = "Diverged selected option payload."

    module = importlib.import_module("app.rescue.domain.shadow_artifact")
    with pytest.raises(ValidationError):
        module.RescueShadowCandidateArtifact(**payload)


def test_shadow_batch_summary_must_match_candidate_payload() -> None:
    from app.rescue.application.shadow_candidate_artifact import (
        build_rescue_shadow_candidates_artifact,
    )

    artifact = build_rescue_shadow_candidates_artifact(
        scenarios=[("rs5_summary_consistency_fixture", _context())]
    )
    payload = artifact.model_dump(mode="python")
    payload["summary"]["candidate_count"] = 99

    module = importlib.import_module("app.rescue.domain.shadow_artifact")
    with pytest.raises(ValidationError):
        module.RescueShadowCandidatesArtifact(**payload)


def test_rescue_shadow_artifact_script_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_rescue_shadow_candidates import main

    output_path = tmp_path / "rescue_shadow_candidates.json"
    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "rescue_shadow_candidates"
    assert payload["shadow_mode"] is True
    assert payload["real_runtime_effect"] is False
    assert payload["summary"]["candidate_count"] >= 1
    assert payload["rescue_shadow_candidates"][0]["rescue_committed"] is False


def test_active_runtime_entrypoints_do_not_import_shadow_artifact_builder() -> None:
    forbidden_tokens = [
        "app.rescue.domain.shadow_artifact",
        "app.rescue.application.shadow_candidate_artifact",
        "shadow_artifact",
        "shadow_candidate_artifact",
        "RescueShadowCandidateArtifact",
        "build_rescue_shadow_candidate_artifact",
    ]

    for relative_path in ACTIVE_RUNTIME_ENTRYPOINTS:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} imports or references RS5 sidecar token {token!r}"
