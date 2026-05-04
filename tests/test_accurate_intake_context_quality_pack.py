from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_quality_pack import (
    build_context_quality_pack_artifact,
)
from app.composition.accurate_intake_context_replay_pack import (
    build_context_replay_pack_artifact,
)
from app.composition.accurate_intake_context_target_candidate_eval import (
    build_context_target_candidate_eval_artifact,
)
from app.composition.accurate_intake_context_window_diagnostic import (
    build_context_window_diagnostic_artifact,
)
from app.composition.accurate_intake_fake_provider_context_smoke import (
    build_fake_provider_context_smoke_artifact,
)
from scripts import build_accurate_intake_context_quality_pack as module


def _context_review() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_context_review_artifact",
        "status": "generated",
        "context_engineering_fault_claimed": False,
        "manager_context_packet_schema_changed": False,
        "summary": {
            "trace_count": 1,
            "present_context_trace_count": 1,
            "missing_context_trace_count": 0,
            "forbidden_context_trace_count": 0,
        },
        "trace_reviews": [
            {
                "status": "present",
                "pending_followup_present": True,
                "pending_draft_present": True,
                "target_candidate_count": 2,
                "forbidden_context_detected": False,
            }
        ],
    }


def test_context_quality_pack_combines_ce_diagnostics_without_fault_claims() -> None:
    pack = build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
    )

    assert pack["artifact_type"] == "accurate_intake_context_quality_pack"
    assert pack["status"] == "context_quality_diagnostic_pass"
    assert pack["context_engineering_fault_claimed"] is False
    assert pack["manager_context_packet_schema_changed"] is False
    assert pack["deterministic_selected_target"] is False
    assert pack["deterministic_semantic_inference_used"] is False
    assert pack["mutation_authority"] is False
    assert pack["summary"]["context_replay_scenario_count"] == 12
    assert pack["summary"]["target_candidate_scenario_count"] == 5
    assert pack["summary"]["ambiguous_target_scenarios"] >= 2
    assert pack["summary"]["pending_pin_scenarios"] >= 2
    assert pack["summary"]["manager_semantic_required_scenarios"] == 1
    assert pack["summary"]["outside_current_day_omitted_scenarios"] == 1
    assert pack["ready_for_live_diagnostic_decision"] is False
    assert pack["private_self_use_approved"] is False


def test_context_quality_pack_rejects_deterministic_target_selection_or_mutation_authority() -> None:
    target_eval = build_context_target_candidate_eval_artifact()
    target_eval["deterministic_selected_target"] = True
    target_eval["mutation_authority"] = True

    pack = build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=target_eval,
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
    )

    assert pack["status"] == "fail"
    assert "target_candidate_eval.deterministic_selected_target" in pack["blockers"]
    assert "target_candidate_eval.mutation_authority" in pack["blockers"]


def test_context_quality_pack_rejects_forbidden_context_or_schema_change() -> None:
    context_review = _context_review()
    context_review["manager_context_packet_schema_changed"] = True
    context_review["summary"] = {**context_review["summary"], "forbidden_context_trace_count": 1}

    pack = build_context_quality_pack_artifact(
        context_review=context_review,
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
    )

    assert pack["status"] == "fail"
    assert "context_review.manager_context_packet_schema_changed" in pack["blockers"]
    assert "context_review.forbidden_context_detected" in pack["blockers"]


def test_context_quality_pack_rejects_stale_context_replay_coverage() -> None:
    stale_replay = build_context_replay_pack_artifact()
    stale_replay["scenario_count"] = 7
    stale_replay["summary"] = {
        **stale_replay["summary"],
        "scenario_count": 7,
        "pending_pin_scenarios": 2,
        "manager_semantic_required_scenarios": 0,
        "outside_current_day_omitted_scenarios": 0,
    }

    pack = build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=stale_replay,
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
    )

    assert pack["status"] == "fail"
    assert "context_replay.scenario_count_too_low" in pack["blockers"]
    assert "context_replay.pending_pin_scenarios_too_low" in pack["blockers"]
    assert "context_replay.manager_semantic_required_missing" in pack["blockers"]
    assert "context_replay.outside_current_day_omitted_missing" in pack["blockers"]


def test_context_quality_pack_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "context-quality.json"

    exit_code = module.main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "context_quality_diagnostic_pass"


def test_context_quality_pack_script_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/build_accurate_intake_context_quality_pack.py").read_text(encoding="utf-8")

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
    ):
        assert fragment not in source
