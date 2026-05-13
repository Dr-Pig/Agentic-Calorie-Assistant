from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/run_advanced_product_lab_recommendation_planning_grokfast_diagnostic.py"


def test_recommendation_planning_grokfast_fake_provider_contract(tmp_path: Path) -> None:
    from app.advanced_shadow_lab.recommendation_planning_grokfast_diagnostic import (
        run_recommendation_planning_grokfast_diagnostic,
    )
    from app.recommendation.application.planning_fixture_provider import (
        FixtureRecommendationPlanningProvider,
    )

    planning_seed = FixtureRecommendationPlanningProvider(
        model_profile="fast_router_model"
    ).plan(
        turn={"semantic_intent_fixture": "pre_meal_planning"},
        fixture_inputs=_fixture_inputs(),
        memory_context_pack={"selected_record_ids": ["golden-bento-1"], "entries": []},
    )
    artifact = run_recommendation_planning_grokfast_diagnostic(
        planning_seed=planning_seed,
        provider=_FakePlanningProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        output_path=tmp_path / "planning.json",
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_recommendation_planning_grokfast_diagnostic"
    )
    assert artifact["status"] == "pass"
    assert artifact["diagnostic_evidence_class"] == "fixture_provider_contract"
    assert artifact["provider_invoked"] is True
    assert artifact["live_invoked"] is False
    assert artifact["live_grokfast_diagnostic_pass"] is False
    assert artifact["output_guard"]["status"] == "pass"
    assert artifact["provider_result"]["recommendation_context_result"]["user_goal"] == (
        "pre_meal_planning"
    )
    assert artifact["provider_result"]["candidate_spec"]["desired_source_types"] == [
        "golden_order",
        "memory_golden_order",
    ]
    assert artifact["blockers"] == []


def test_recommendation_planning_grokfast_payload_is_bounded_seed_summary() -> None:
    from app.advanced_shadow_lab.recommendation_planning_grokfast_diagnostic import (
        recommendation_planning_live_provider_payload,
    )

    payload = recommendation_planning_live_provider_payload(
        {
            "artifact_type": "recommendation_planning_fixture_output",
            "recommendation_context_result": {"user_goal": "pre_meal_planning"},
            "candidate_spec": {"desired_source_types": ["golden_order"]},
            "raw_user_input": "must not be forwarded",
            "messages": [{"role": "user", "content": "must not be forwarded"}],
        }
    )
    serialized = json.dumps(payload)

    assert payload["stage"] == "advanced_product_lab_recommendation_planning_diagnostic"
    assert payload["planning_seed_summary"] == {
        "artifact_type": "recommendation_planning_fixture_output",
        "recommendation_context_result": {"user_goal": "pre_meal_planning"},
        "candidate_spec": {"desired_source_types": ["golden_order"]},
    }
    assert "raw_user_input" not in serialized
    assert "messages" not in serialized
    assert payload["constraints"]["mutation_or_commit_allowed"] is False
    assert payload["constraints"]["serve_to_mainline_allowed"] is False


def test_recommendation_planning_grokfast_accepts_live_style_non_serve_flags(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.recommendation_planning_grokfast_diagnostic import (
        run_recommendation_planning_grokfast_diagnostic,
    )
    from app.recommendation.application.planning_fixture_provider import (
        FixtureRecommendationPlanningProvider,
    )

    planning_seed = FixtureRecommendationPlanningProvider(
        model_profile="fast_router_model"
    ).plan(
        turn={"semantic_intent_fixture": "pre_meal_planning"},
        fixture_inputs=_fixture_inputs(),
        memory_context_pack={"selected_record_ids": ["golden-bento-1"], "entries": []},
    )
    artifact = run_recommendation_planning_grokfast_diagnostic(
        planning_seed=planning_seed,
        provider=_FakePlanningProviderLiveStyleFlags(),
        provider_mode="fake_live_style_flags",
        live_invoked=True,
        output_path=tmp_path / "planning.json",
    )

    assert artifact["status"] == "pass"
    assert artifact["live_grokfast_diagnostic_pass"] is True
    assert artifact["blockers"] == []


def test_recommendation_planning_grokfast_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "blocked.json"
    completed = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--provider-mode",
            "live",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    artifact = json.loads(output.read_text(encoding="utf-8"))

    assert summary["status"] == "blocked"
    assert artifact["provider_invoked"] is False
    assert artifact["live_invoked"] is False
    assert artifact["blockers"] == ["live_gate_not_enabled"]


def test_recommendation_train_records_pr5_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 19
    assert plan["last_completed_pr_number"] == 5
    assert plan["active_pr_number"] == 6
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 5,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_planning_grokfast_live_diagnostic_completed_locally",
        "live_artifact": (
            "artifacts/advanced_product_lab_recommendation_planning_grokfast_"
            "diagnostic_pr5_live.json"
        ),
    }


class _FakePlanningProvider:
    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-recommendation-planning-grokfast", "configured": True}

    async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "claim_scope": "diagnostic_only",
            "recommendation_context_result": {"user_goal": "pre_meal_planning"},
            "candidate_spec": {
                "desired_source_types": ["golden_order", "memory_golden_order"],
                "hard_blockers_must_be_deterministic": True,
            },
            "non_serve_flags": {
                "mainline_activation_enabled": False,
                "canonical_product_mutation_allowed": False,
            },
        }, {
            "stage": "advanced_product_lab_recommendation_planning_diagnostic",
            "provider": "fake",
        }


class _FakePlanningProviderLiveStyleFlags(_FakePlanningProvider):
    async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
        result, trace = await super().complete_with_trace()
        flags = result["non_serve_flags"]  # type: ignore[index]
        flags.pop("mainline_activation_enabled")  # type: ignore[union-attr]
        flags.pop("canonical_product_mutation_allowed")  # type: ignore[union-attr]
        flags["serve_to_mainline_allowed"] = False  # type: ignore[index]
        flags["mutation_or_commit_allowed"] = False  # type: ignore[index]
        return result, trace


def _fixture_inputs() -> dict[str, object]:
    return {
        "recommendation_payload": {
            "current_budget_view": {"remaining_kcal": 700},
        },
        "current_budget_view": {"meal_consumption_total_kcal": 600},
    }
