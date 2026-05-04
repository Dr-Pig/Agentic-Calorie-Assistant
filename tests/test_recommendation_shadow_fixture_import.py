from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.recommendation.application.shadow_artifact_gate import (
    evaluate_recommendation_shadow_artifact_quality,
)
from app.recommendation.application.shadow_evaluator import (
    build_recommendation_shadow_eval_artifact,
)
from app.recommendation.application.shadow_fixture_import import (
    OPTIONAL_SCENARIO_FIELDS,
    REQUIRED_CANDIDATE_FIELDS,
    REQUIRED_CANDIDATE_SPEC_FIELDS,
    REQUIRED_SCENARIO_FIELDS,
    RecommendationShadowFixtureImportError,
    load_recommendation_shadow_context_fixtures,
)
from app.recommendation.domain.shadow import (
    CandidateSpec,
    RecommendationCandidateFixture,
    RecommendationShadowContextFixture,
)


ROOT = Path(__file__).resolve().parents[1]


def test_fixture_import_loads_explicit_scenario_bundle_without_runtime_effect() -> None:
    scenario = _scenario("fixture-import-1")
    result = load_recommendation_shadow_context_fixtures(
        {
            "fixture_bundle_type": "recommendation_shadow_context_fixtures",
            "scenarios": [scenario.model_dump(mode="json")],
        }
    )

    artifact = build_recommendation_shadow_eval_artifact(result.scenarios)
    gate_result = evaluate_recommendation_shadow_artifact_quality(artifact)

    assert len(result.scenarios) == 1
    assert result.source_summary == {
        "input_shape": "scenario_bundle",
        "scenario_count": 1,
        "scenario_ids": ["fixture-import-1"],
    }
    assert artifact.evals[0].scenario_id == "fixture-import-1"
    assert artifact.evals[0].runtime_effect_allowed is False
    assert artifact.evals[0].shadow_leading_candidate is not None
    assert artifact.evals[0].candidate_hint_packet_drafts
    assert artifact.evals[0].candidate_hint_packet_drafts[0].is_canonical_truth is False
    assert gate_result.passed is False
    assert "artifact:missing_required_scenario:cold_start_lunch" in gate_result.failure_codes


def test_fixture_import_field_gate_stays_in_sync_with_fixture_models() -> None:
    assert set(REQUIRED_SCENARIO_FIELDS) | set(OPTIONAL_SCENARIO_FIELDS) == set(
        RecommendationShadowContextFixture.model_fields
    )
    assert set(REQUIRED_CANDIDATE_SPEC_FIELDS) == set(CandidateSpec.model_fields)
    assert set(REQUIRED_CANDIDATE_FIELDS) == set(
        RecommendationCandidateFixture.model_fields
    )


def test_fixture_import_rejects_missing_required_context_field_before_defaults() -> None:
    payload = _scenario("missing-candidate-spec").model_dump(mode="json")
    del payload["candidate_spec"]

    try:
        load_recommendation_shadow_context_fixtures(payload)
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == [
            "scenario:missing-candidate-spec:missing_field:candidate_spec"
        ]
    else:
        raise AssertionError("fixture import should reject missing explicit candidate_spec")


def test_fixture_import_rejects_raw_dogfood_log_shape_without_semantic_inference() -> None:
    raw_log_payload = {
        "dogfood_logs": [
            {
                "user_text": "中午想吃輕一點，不要太油",
                "recorded_at": "2026-05-04T12:00:00+08:00",
            }
        ]
    }

    try:
        load_recommendation_shadow_context_fixtures(raw_log_payload)
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == ["payload:unsupported_fixture_shape"]
    else:
        raise AssertionError("raw logs must not be inferred into recommendation fixtures")


def test_fixture_import_rejects_eval_artifact_as_context_input() -> None:
    payload = {
        "artifact_type": "recommendation_shadow_eval",
        "evals": [],
    }

    try:
        load_recommendation_shadow_context_fixtures(payload)
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == ["payload:eval_artifact_not_context_fixture"]
    else:
        raise AssertionError("eval artifacts must not be re-imported as context fixtures")


def test_fixture_import_runs_fixture_governance_validation() -> None:
    payload = _scenario("bad-budget").model_dump(mode="json")
    payload["current_budget_view"]["remaining_kcal"] = True

    try:
        load_recommendation_shadow_context_fixtures({"scenarios": [payload]})
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == [
            "scenario:bad-budget:missing_current_budget_remaining_kcal"
        ]
    else:
        raise AssertionError("fixture import should run hard context validation")


def test_fixture_import_rejects_candidate_missing_explicit_kcal_range() -> None:
    payload = _scenario("missing-candidate-kcal").model_dump(mode="json")
    del payload["candidate_source_fixture"][0]["estimated_kcal_range"]

    try:
        load_recommendation_shadow_context_fixtures({"scenarios": [payload]})
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == [
            "scenario:missing-candidate-kcal:candidate_index:0:missing_field:estimated_kcal_range"
        ]
    else:
        raise AssertionError("fixture import should reject missing explicit candidate kcal")


def test_fixture_import_rejects_candidate_spec_missing_explicit_nested_fields() -> None:
    payload = _scenario("missing-candidate-spec-nested").model_dump(mode="json")
    payload["candidate_spec"] = {
        "desired_meal_style": "light",
        "acceptable_cuisine_families": ["generic"],
    }

    try:
        load_recommendation_shadow_context_fixtures({"scenarios": [payload]})
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == [
            "scenario:missing-candidate-spec-nested:candidate_spec:missing_field:excluded_item_patterns",
            "scenario:missing-candidate-spec-nested:candidate_spec:missing_field:soft_target_kcal_band",
            "scenario:missing-candidate-spec-nested:candidate_spec:missing_field:venue_posture",
            "scenario:missing-candidate-spec-nested:candidate_spec:missing_field:swaps_allowed",
            "scenario:missing-candidate-spec-nested:candidate_spec:missing_field:priority_signals",
            "scenario:missing-candidate-spec-nested:candidate_spec:missing_field:avoid_repeat_from_today",
            "scenario:missing-candidate-spec-nested:candidate_spec:missing_field:protein_posture",
            "scenario:missing-candidate-spec-nested:candidate_spec:missing_field:budget_fit_posture",
        ]
    else:
        raise AssertionError("fixture import should reject implicit candidate_spec defaults")


def test_fixture_import_rejects_candidate_missing_explicit_defaulted_fields() -> None:
    payload = _scenario("missing-candidate-nested").model_dump(mode="json")
    candidate_payload = payload["candidate_source_fixture"][0]
    del candidate_payload["cuisine_family"]
    del candidate_payload["protein_posture"]
    del candidate_payload["confidence"]

    try:
        load_recommendation_shadow_context_fixtures({"scenarios": [payload]})
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == [
            "scenario:missing-candidate-nested:candidate_index:0:missing_field:protein_posture",
            "scenario:missing-candidate-nested:candidate_index:0:missing_field:cuisine_family",
            "scenario:missing-candidate-nested:candidate_index:0:missing_field:confidence",
        ]
    else:
        raise AssertionError("fixture import should reject implicit candidate defaults")


def test_fixture_import_rejects_extra_raw_or_live_context_fields() -> None:
    payload = _scenario("extra-raw-fields").model_dump(mode="json")
    payload["raw_dogfood_event"] = {"user_text": "想吃輕的"}
    payload["location_api_payload"] = {"lat": 25.0, "lng": 121.5}
    payload["candidate_source_fixture"][0]["live_provider_payload"] = {
        "provider": "maps"
    }

    try:
        load_recommendation_shadow_context_fixtures({"scenarios": [payload]})
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == [
            "scenario:extra-raw-fields:unexpected_field:location_api_payload",
            "scenario:extra-raw-fields:unexpected_field:raw_dogfood_event",
            "scenario:extra-raw-fields:candidate_index:0:unexpected_field:live_provider_payload",
        ]
    else:
        raise AssertionError("fixture import should reject extra raw/live fields")


def test_fixture_import_rejects_extra_raw_or_live_bundle_fields() -> None:
    payload = {
        "fixture_bundle_type": "recommendation_shadow_context_fixtures",
        "scenarios": [_scenario("extra-bundle-fields").model_dump(mode="json")],
        "raw_dogfood_event": {"user_text": "想吃輕的"},
        "live_provider_payload": {"provider": "maps"},
    }

    try:
        load_recommendation_shadow_context_fixtures(payload)
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == [
            "payload:unexpected_field:live_provider_payload",
            "payload:unexpected_field:raw_dogfood_event",
        ]
    else:
        raise AssertionError("fixture import should reject extra bundle fields")


def test_fixture_import_rejects_wrong_bundle_type() -> None:
    payload = {
        "fixture_bundle_type": "some_other_fixture",
        "scenarios": [_scenario("wrong-bundle-type").model_dump(mode="json")],
    }

    try:
        load_recommendation_shadow_context_fixtures(payload)
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == ["payload:wrong_fixture_bundle_type"]
    else:
        raise AssertionError("fixture import should reject ambiguous bundle type")


def test_fixture_import_rejects_empty_scenario_bundle() -> None:
    try:
        load_recommendation_shadow_context_fixtures({"scenarios": []})
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == ["payload:scenarios_empty"]
    else:
        raise AssertionError("fixture import should reject empty bundles")


def test_fixture_import_rejects_empty_top_level_scenario_list() -> None:
    try:
        load_recommendation_shadow_context_fixtures([])
    except RecommendationShadowFixtureImportError as exc:
        assert exc.failure_codes == ["payload:scenarios_empty"]
    else:
        raise AssertionError("fixture import should reject empty scenario lists")


def test_fixture_import_cli_builds_shadow_artifact_from_fixture_file(tmp_path: Path) -> None:
    fixture_path = tmp_path / "recommendation_shadow_context_fixtures.json"
    artifact_path = tmp_path / "recommendation_shadow_eval.json"
    report_path = tmp_path / "recommendation_shadow_eval_gate_report.json"
    fixture_path.write_text(
        json.dumps(
            {
                "fixture_bundle_type": "recommendation_shadow_context_fixtures",
                "scenarios": [_scenario("fixture-cli-1").model_dump(mode="json")],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_eval_from_fixtures.py",
            "--fixtures",
            str(fixture_path),
            "--output",
            str(artifact_path),
            "--gate-report",
            str(report_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "wrote" in result.stdout
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert artifact_payload["artifact_type"] == "recommendation_shadow_eval"
    assert artifact_payload["evals"][0]["scenario_id"] == "fixture-cli-1"
    assert artifact_payload["evals"][0]["recommendation_served"] is False
    assert "hint_packet" not in artifact_payload["evals"][0]
    assert (
        artifact_payload["evals"][0]["candidate_hint_packet_drafts"][0][
            "is_canonical_truth"
        ]
        is False
    )
    assert report_payload["passed"] is False
    assert "artifact:missing_required_scenario:cold_start_lunch" in report_payload[
        "failure_codes"
    ]


def test_fixture_import_cli_accepts_utf8_bom_fixture_file(tmp_path: Path) -> None:
    fixture_path = tmp_path / "recommendation_shadow_context_fixtures_bom.json"
    artifact_path = tmp_path / "recommendation_shadow_eval.json"
    fixture_path.write_text(
        json.dumps(
            {"scenarios": [_scenario("fixture-cli-bom").model_dump(mode="json")]},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8-sig",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_eval_from_fixtures.py",
            "--fixtures",
            str(fixture_path),
            "--output",
            str(artifact_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["evals"][0]["scenario_id"] == "fixture-cli-bom"


def test_fixture_import_cli_returns_nonzero_for_invalid_fixture_file(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "raw_logs.json"
    artifact_path = tmp_path / "recommendation_shadow_eval.json"
    fixture_path.write_text(
        json.dumps({"dogfood_logs": [{"user_text": "想吃輕的"}]}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_eval_from_fixtures.py",
            "--fixtures",
            str(fixture_path),
            "--output",
            str(artifact_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "payload:unsupported_fixture_shape" in result.stderr
    assert not artifact_path.exists()


def test_fixture_import_cli_returns_nonzero_for_malformed_json(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "malformed.json"
    artifact_path = tmp_path / "recommendation_shadow_eval.json"
    fixture_path.write_text("{not-json", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_eval_from_fixtures.py",
            "--fixtures",
            str(fixture_path),
            "--output",
            str(artifact_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "payload:invalid_json" in result.stderr
    assert "Traceback" not in result.stderr
    assert not artifact_path.exists()


def test_fixture_import_cli_returns_nonzero_for_invalid_utf8(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "invalid_utf8.json"
    artifact_path = tmp_path / "recommendation_shadow_eval.json"
    fixture_path.write_bytes(b"\xff\xfe\x00\x00")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_eval_from_fixtures.py",
            "--fixtures",
            str(fixture_path),
            "--output",
            str(artifact_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "payload:invalid_json" in result.stderr
    assert "Traceback" not in result.stderr
    assert not artifact_path.exists()


def _scenario(scenario_id: str) -> RecommendationShadowContextFixture:
    return RecommendationShadowContextFixture(
        scenario_id=scenario_id,
        user_id="dogfood-user",
        local_date="2026-05-04",
        channel="chat",
        recorded_at="2026-05-04T12:00:00+08:00",
        timezone="Asia/Taipei",
        current_budget_view={
            "remaining_kcal": 700,
            "budget_kcal": 1600,
            "consumed_kcal": 900,
        },
        active_body_plan_view={
            "daily_budget_kcal": 1600,
            "goal_type": "lose_weight",
            "plan_status": "active",
        },
        recent_committed_meals_view={"meals": []},
        open_proposals_view={"proposals": []},
        proactive_status_view={"status": "inactive"},
        preference_profile_summary={"event_count": 1},
        negative_preference_summary={"items": []},
        golden_order_summary={"orders": []},
        candidate_spec=CandidateSpec(
            desired_meal_style="light",
            acceptable_cuisine_families=["generic"],
            soft_target_kcal_band={"min": 250, "max": 650},
            priority_signals=["budget_fit"],
        ),
        candidate_source_fixture=[
            RecommendationCandidateFixture(
                candidate_id="fixture-candidate-1",
                title="tofu bento",
                source_type="safe_fallback",
                estimated_kcal_range={"min": 360, "max": 520},
                cuisine_family="generic",
                source_refs=["fixture:fixture-candidate-1"],
            )
        ],
    )
