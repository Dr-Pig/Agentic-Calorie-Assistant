from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_conditioned_intent_wall import (
    build_context_conditioned_intent_wall_artifact,
)
from app.composition.accurate_intake_context_quality_pack import (
    build_context_quality_pack_artifact,
)
from app.composition.accurate_intake_context_replay_pack import (
    build_context_replay_pack_artifact,
)
from app.composition.accurate_intake_context_review import build_context_review_artifact
from app.composition.accurate_intake_context_target_candidate_eval import (
    build_context_target_candidate_eval_artifact,
)
from app.composition.accurate_intake_context_window_diagnostic import (
    build_context_window_diagnostic_artifact,
)
from app.composition.accurate_intake_fake_provider_context_smoke import (
    build_fake_provider_context_smoke_artifact,
)
from app.composition.accurate_intake_short_term_context_runtime_replay import (
    build_short_term_context_runtime_replay_artifact,
)


def _context_review() -> dict[str, object]:
    return build_context_review_artifact(
        traces=[
            {
                "request_id": "coverage-matrix-fixture-trace",
                "context_policy_version": "manager_context_policy_v1",
                "loaded_context_summary": {
                    "pending_followup_present": True,
                    "pending_draft_present": True,
                    "target_candidate_count": 2,
                },
                "omitted_context_summary": {
                    "policy_excluded_context_ids": [
                        "raw_trace_dump",
                        "long_term_memory",
                        "proactive_context",
                        "rescue_context",
                    ]
                },
                "manager_context_packet_v1": {
                    "hard_pins": {
                        "pending_followup": {"is_open": True},
                        "pending_draft": {"draft_id": "coverage-matrix-draft"},
                    },
                    "target_candidates": {
                        "for_correction_or_removal": [
                            {"meal_item_id": 1, "display_name": "tofu"},
                            {"meal_item_id": 2, "display_name": "rice"},
                        ]
                    },
                },
            }
        ]
    )


def _context_quality_pack() -> dict[str, object]:
    return build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
    )


def _inputs() -> dict[str, dict[str, object]]:
    return {
        "context_conditioned_intent_wall": build_context_conditioned_intent_wall_artifact(),
        "short_term_context_runtime_replay": build_short_term_context_runtime_replay_artifact(),
        "fake_provider_context_smoke": build_fake_provider_context_smoke_artifact(),
        "context_quality_pack": _context_quality_pack(),
    }


def test_context_coverage_matrix_reports_supported_short_term_capabilities() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    artifact = build_pl_ce_context_coverage_matrix_artifact(**_inputs())
    coverage = artifact["coverage_matrix"]

    assert artifact["artifact_type"] == "accurate_intake_pl_ce_context_coverage_matrix"
    assert artifact["status"] == "context_coverage_matrix_ready_for_human_review"
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["mutation_authority"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["fooddb_truth_updated"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["summary"]["covered_capability_count"] >= 8
    assert coverage["pending_followup_carryover"]["coverage_status"] == (
        "fixture_runtime_and_fake_provider_checked"
    )
    assert coverage["correction_target_candidates"]["coverage_status"] == (
        "fixture_runtime_and_fake_provider_checked"
    )
    assert coverage["removal_target_candidates"]["coverage_status"] == (
        "fixture_runtime_and_fake_provider_checked"
    )
    assert coverage["ambiguity_preserved"]["coverage_status"] == (
        "fixture_runtime_and_fake_provider_checked"
    )
    assert coverage["query_no_mutation"]["coverage_status"] == "fixture_and_fake_provider_checked"
    assert coverage["target_update_boundary"]["coverage_status"] == (
        "fixture_and_fake_provider_checked"
    )
    assert coverage["long_session_bounded_context"]["coverage_status"] == (
        "fixture_runtime_checked"
    )
    assert coverage["forbidden_context_exclusion"]["coverage_status"] == (
        "runtime_and_fake_provider_checked"
    )
    assert coverage["semantic_owner_boundary"]["coverage_status"] == (
        "fixture_runtime_and_fake_provider_checked"
    )


def test_context_coverage_matrix_preserves_known_runtime_gaps_without_fault_claim() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    inputs = _inputs()
    runtime_replay = dict(inputs["short_term_context_runtime_replay"])
    runtime_replay["status"] = "diagnostic_has_known_context_gaps"
    runtime_replay["summary"] = {
        **dict(runtime_replay["summary"]),
        "current_gap_scenarios": 1,
        "known_gap_signals": ["runtime_back_reference_heuristic_attached_target"],
    }
    inputs["short_term_context_runtime_replay"] = runtime_replay

    artifact = build_pl_ce_context_coverage_matrix_artifact(**inputs)

    assert artifact["status"] == "context_coverage_matrix_ready_with_known_runtime_gaps"
    assert artifact["summary"]["known_runtime_gap_count"] == 1
    assert artifact["known_runtime_gap_signals"] == [
        "runtime_back_reference_heuristic_attached_target"
    ]
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["blockers"] == []


def test_context_coverage_matrix_keeps_known_gap_status_when_count_is_missing() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    inputs = _inputs()
    runtime_replay = dict(inputs["short_term_context_runtime_replay"])
    runtime_replay["status"] = "diagnostic_has_known_context_gaps"
    runtime_replay["summary"] = {
        **dict(runtime_replay["summary"]),
        "current_gap_scenarios": 0,
        "known_gap_signals": ["runtime_back_reference_heuristic_attached_target"],
    }
    inputs["short_term_context_runtime_replay"] = runtime_replay

    artifact = build_pl_ce_context_coverage_matrix_artifact(**inputs)

    assert artifact["status"] == "context_coverage_matrix_ready_with_known_runtime_gaps"
    assert artifact["summary"]["known_runtime_gap_count"] == 1
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["blockers"] == []


def test_context_coverage_matrix_blocks_missing_required_capability() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    inputs = _inputs()
    wall = dict(inputs["context_conditioned_intent_wall"])
    wall["scenarios"] = [
        scenario
        for scenario in wall["scenarios"]
        if scenario["scenario_id"] != "explicit_daily_target_1800"
    ]
    inputs["context_conditioned_intent_wall"] = wall

    artifact = build_pl_ce_context_coverage_matrix_artifact(**inputs)

    assert artifact["status"] == "blocked"
    assert "coverage.target_update_boundary.missing_intent_wall" in artifact["blockers"]
    assert artifact["coverage_matrix"]["target_update_boundary"]["coverage_status"] == "not_checked"


def test_context_coverage_matrix_blocks_missing_fake_provider_semantic_posture() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    inputs = _inputs()
    fake_provider = dict(inputs["fake_provider_context_smoke"])
    fake_provider["manager_handoff_scenarios"] = [
        scenario
        for scenario in fake_provider["manager_handoff_scenarios"]
        if scenario["scenario_id"]
        not in {
            "previous_drink_calorie_query",
            "explicit_daily_target_1800",
            "meal_estimate_800_not_target",
        }
    ]
    inputs["fake_provider_context_smoke"] = fake_provider

    artifact = build_pl_ce_context_coverage_matrix_artifact(**inputs)

    assert artifact["status"] == "blocked"
    assert "coverage.query_no_mutation.missing_fake_provider" in artifact["blockers"]
    assert "coverage.target_update_boundary.missing_fake_provider" in artifact["blockers"]
    assert artifact["coverage_matrix"]["query_no_mutation"]["coverage_status"] == "fixture_checked"
    assert artifact["coverage_matrix"]["target_update_boundary"]["coverage_status"] == "fixture_checked"


def test_context_coverage_matrix_blocks_overclaims_and_schema_change() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    inputs = _inputs()
    fake_provider = dict(inputs["fake_provider_context_smoke"])
    fake_provider["live_llm_invoked"] = {"claimed": True}
    fake_provider["web_tavily_invoked"] = True
    fake_provider["live_websearch_used"] = True
    fake_provider["writes_performed"] = True
    fake_provider["import_allowed"] = True
    quality_pack = dict(inputs["context_quality_pack"])
    quality_pack["manager_context_packet_schema_changed"] = True
    quality_pack["runtime_truth_changed"] = True
    quality_pack["mutation_changed"] = True
    quality_pack["dogfood_pass"] = "pass"
    quality_pack["private_self_use_approved"] = "approved"
    quality_pack["ready_for_fdb_integration"] = "ready"
    quality_pack["fooddb_evidence_used"] = "used"
    inputs["fake_provider_context_smoke"] = fake_provider
    inputs["context_quality_pack"] = quality_pack

    artifact = build_pl_ce_context_coverage_matrix_artifact(**inputs)

    assert artifact["status"] == "blocked"
    assert "fake_provider_context_smoke.live_llm_invoked" in artifact["blockers"]
    assert "fake_provider_context_smoke.web_tavily_invoked" in artifact["blockers"]
    assert "fake_provider_context_smoke.live_websearch_used" in artifact["blockers"]
    assert "fake_provider_context_smoke.writes_performed" in artifact["blockers"]
    assert "fake_provider_context_smoke.import_allowed" in artifact["blockers"]
    assert "context_quality_pack.manager_context_packet_schema_changed" in artifact["blockers"]
    assert "context_quality_pack.runtime_truth_changed" in artifact["blockers"]
    assert "context_quality_pack.mutation_changed" in artifact["blockers"]
    assert "context_quality_pack.dogfood_pass" in artifact["blockers"]
    assert "context_quality_pack.private_self_use_approved" in artifact["blockers"]
    assert "context_quality_pack.ready_for_fdb_integration" in artifact["blockers"]
    assert "context_quality_pack.fooddb_evidence_used" in artifact["blockers"]
    assert artifact["live_llm_invoked"] is False
    assert artifact["manager_context_packet_schema_changed"] is False


def test_context_coverage_matrix_blocks_nested_overclaims() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    inputs = _inputs()
    fake_provider = dict(inputs["fake_provider_context_smoke"])
    fake_provider["provider_input_summary"] = {
        **dict(fake_provider["provider_input_summary"]),
        "manager_context_packet_schema_changed": True,
    }
    scenarios = list(fake_provider["manager_handoff_scenarios"])
    scenarios[0] = {**dict(scenarios[0]), "mutation_authority": {"claimed": True}}
    fake_provider["manager_handoff_scenarios"] = scenarios
    inputs["fake_provider_context_smoke"] = fake_provider

    artifact = build_pl_ce_context_coverage_matrix_artifact(**inputs)

    assert artifact["status"] == "blocked"
    assert (
        "fake_provider_context_smoke.provider_input_summary.manager_context_packet_schema_changed"
        in artifact["blockers"]
    )
    assert (
        "fake_provider_context_smoke.manager_handoff_scenarios[0].mutation_authority"
        in artifact["blockers"]
    )
    assert artifact["mutation_authority"] is False


def test_context_coverage_matrix_blocks_missing_upstream_invariants() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    inputs = _inputs()
    runtime_replay = dict(inputs["short_term_context_runtime_replay"])
    runtime_replay["runtime_trace_backed"] = False
    runtime_replay["scenario_count"] = 0
    fake_provider = dict(inputs["fake_provider_context_smoke"])
    fake_provider["manager_handoff_matrix_checked"] = False
    quality_pack = dict(inputs["context_quality_pack"])
    quality_pack["short_term_context_runtime_replay_checked"] = False
    inputs["short_term_context_runtime_replay"] = runtime_replay
    inputs["fake_provider_context_smoke"] = fake_provider
    inputs["context_quality_pack"] = quality_pack

    artifact = build_pl_ce_context_coverage_matrix_artifact(**inputs)

    assert artifact["status"] == "blocked"
    assert "short_term_context_runtime_replay.runtime_trace_backed_not_true" in artifact["blockers"]
    assert "short_term_context_runtime_replay.scenario_count_too_low" in artifact["blockers"]
    assert "fake_provider_context_smoke.manager_handoff_matrix_missing" in artifact["blockers"]
    assert "context_quality_pack.runtime_replay_not_checked" in artifact["blockers"]


def test_context_coverage_matrix_blocks_partial_fake_provider_handoff_matrix() -> None:
    from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (
        build_pl_ce_context_coverage_matrix_artifact,
    )

    inputs = _inputs()
    fake_provider = dict(inputs["fake_provider_context_smoke"])
    fake_provider["summary"] = {
        **dict(fake_provider["summary"]),
        "manager_handoff_scenario_count": 5,
    }
    quality_pack = dict(inputs["context_quality_pack"])
    quality_pack["summary"] = {
        **dict(quality_pack["summary"]),
        "fake_provider_handoff_scenario_count": 5,
    }
    inputs["fake_provider_context_smoke"] = fake_provider
    inputs["context_quality_pack"] = quality_pack

    artifact = build_pl_ce_context_coverage_matrix_artifact(**inputs)

    assert artifact["status"] == "blocked"
    assert "fake_provider_context_smoke.manager_handoff_scenario_count_too_low" in artifact["blockers"]
    assert "context_quality_pack.fake_provider_handoff_scenario_count_too_low" in artifact["blockers"]


def test_context_coverage_matrix_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    from scripts.build_accurate_intake_pl_ce_context_coverage_matrix import main

    inputs = _inputs()
    paths: dict[str, Path] = {}
    for group_id, payload in inputs.items():
        path = tmp_path / f"{group_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        paths[group_id] = path
    output_path = tmp_path / "coverage-matrix.json"

    exit_code = main(
        [
            "--artifact",
            f"context_conditioned_intent_wall={paths['context_conditioned_intent_wall']}",
            "--artifact",
            f"short_term_context_runtime_replay={paths['short_term_context_runtime_replay']}",
            "--artifact",
            f"fake_provider_context_smoke={paths['fake_provider_context_smoke']}",
            "--artifact",
            f"context_quality_pack={paths['context_quality_pack']}",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "context_coverage_matrix_ready_for_human_review"


def test_context_coverage_matrix_cli_blocks_missing_input_without_autofix(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.build_accurate_intake_pl_ce_context_coverage_matrix import main

    output_path = tmp_path / "coverage-matrix.json"

    exit_code = main(
        [
            "--artifact",
            f"context_conditioned_intent_wall={tmp_path / 'missing-wall.json'}",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["status"] == "blocked"
    assert artifact["status"] == "blocked"
    assert "context_conditioned_intent_wall.missing" in artifact["blockers"]
    assert artifact["autofix_attempted"] is False


def test_context_coverage_matrix_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_context_coverage_matrix.py"),
        Path("scripts/build_accurate_intake_pl_ce_context_coverage_matrix.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "openai",
        "requests",
        "httpx",
        "ready_for_live_diagnostic_decision = True",
        "fooddb_evidence_used = True",
        "mutation_authority = True",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for fragment in forbidden:
        assert fragment not in combined_source


def test_context_coverage_matrix_cli_defaults_use_local_artifact_names() -> None:
    source = Path("scripts/build_accurate_intake_pl_ce_context_coverage_matrix.py").read_text(
        encoding="utf-8"
    )

    assert "accurate_intake_context_conditioned_intent_wall.json" in source
    assert "accurate_intake_context_conditioned_intent_wall_ci.json" not in source
