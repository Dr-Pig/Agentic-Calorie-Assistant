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
from app.composition.accurate_intake_short_term_context_runtime_replay import (
    build_short_term_context_runtime_replay_artifact,
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


def _short_term_context_smoke() -> dict[str, object]:
    loaded = {
        "recent_chat_messages": 0,
        "pending_followup_present": False,
        "pending_draft_present": False,
        "target_candidate_count": 0,
        "interaction_event_present": True,
    }
    omitted = {
        "policy_excluded_context_ids": [
            "debug_artifacts",
            "dogfood_review_artifacts",
            "raw_trace_dump",
            "food_gap_candidates_as_truth",
            "full_day_transcript_by_default",
            "long_term_memory",
            "proactive_context",
            "rescue_context",
            "recommendation_context",
        ],
        "recent_chat_messages_omitted": 0,
        "omitted_by_message_limit": 0,
        "omitted_by_char_cap": 0,
    }
    return {
        "smoke_id": "accurate_intake_product_pages_short_term_context_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "fixture_manager_used": True,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "browser": {
            "chat_history_payload": {
                "source": "accurate_intake_chat_history_read_model",
                "long_term_memory_used": False,
                "proactive_or_rescue_used": False,
                "messages": [
                    {
                        "trace_id": "runtime-trace-user-1",
                        "context_policy_version": "accurate_intake_mvp_context_policy_v1",
                        "loaded_context_summary": loaded,
                        "omitted_context_summary": omitted,
                        "pending_followup_linkage_present": True,
                        "pending_pins_present": True,
                        "target_candidate_count": 0,
                    },
                    {
                        "trace_id": "runtime-trace-assistant-1",
                        "context_policy_version": "accurate_intake_mvp_context_policy_v1",
                        "loaded_context_summary": loaded,
                        "omitted_context_summary": omitted,
                        "pending_followup_linkage_present": True,
                        "pending_pins_present": True,
                        "target_candidate_count": 0,
                    },
                ],
            }
        },
        "fake_provider_calls": [
            {
                "stage": "execution_after_followup",
                "context_policy_version_present": True,
                "loaded_context_summary_present": True,
                "omitted_context_summary_present": True,
                "pending_followup_pin_present": True,
                "raw_user_input_used_for_fixture_selection": False,
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
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
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
    assert pack["summary"]["short_term_runtime_replay_scenario_count"] == 7
    assert pack["summary"]["fake_provider_handoff_scenario_count"] >= 6
    assert pack["short_term_context_runtime_replay_checked"] is True
    assert pack["short_term_context_current_gap_scenarios"] == 0
    assert pack["short_term_context_known_gap_signals"] == []
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
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
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
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
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
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
    )

    assert pack["status"] == "fail"
    assert "context_replay.scenario_count_too_low" in pack["blockers"]
    assert "context_replay.pending_pin_scenarios_too_low" in pack["blockers"]
    assert "context_replay.manager_semantic_required_missing" in pack["blockers"]
    assert "context_replay.outside_current_day_omitted_missing" in pack["blockers"]


def test_context_quality_pack_rejects_missing_fake_provider_handoff_matrix() -> None:
    fake_provider = build_fake_provider_context_smoke_artifact()
    fake_provider.pop("manager_handoff_matrix_checked", None)
    fake_provider["summary"] = {}

    pack = build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=fake_provider,
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
    )

    assert pack["status"] == "fail"
    assert "fake_provider_context_smoke.manager_handoff_matrix_missing" in pack["blockers"]
    assert "fake_provider_context_smoke.manager_handoff_scenario_count_too_low" in pack["blockers"]
    assert "fake_provider_context_smoke.ambiguous_back_reference_missing" in pack["blockers"]


def test_context_quality_pack_rejects_partial_fake_provider_handoff_matrix() -> None:
    fake_provider = build_fake_provider_context_smoke_artifact()
    fake_provider["summary"] = {
        **fake_provider["summary"],
        "manager_handoff_scenario_count": 5,
    }

    pack = build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=fake_provider,
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
    )

    assert pack["status"] == "fail"
    assert "fake_provider_context_smoke.manager_handoff_scenario_count_too_low" in pack["blockers"]


def test_context_quality_pack_rejects_inconsistent_fake_provider_handoff_count() -> None:
    fake_provider = build_fake_provider_context_smoke_artifact()
    fake_provider["manager_handoff_scenarios"] = list(fake_provider["manager_handoff_scenarios"])[:5]

    pack = build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=fake_provider,
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
    )

    assert pack["status"] == "fail"
    assert "fake_provider_context_smoke.manager_handoff_scenario_count_mismatch" in pack["blockers"]


def test_context_quality_pack_propagates_fake_provider_handoff_blockers() -> None:
    fake_provider = build_fake_provider_context_smoke_artifact()
    fake_provider["blockers"] = [
        "named_item_correction.candidate_supported_preselected_target",
        "named_item_correction.deterministic_selected_target",
    ]

    pack = build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=fake_provider,
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
    )

    assert pack["status"] == "fail"
    assert (
        "fake_provider_context_smoke.named_item_correction.candidate_supported_preselected_target"
        in pack["blockers"]
    )
    assert (
        "fake_provider_context_smoke.named_item_correction.deterministic_selected_target"
        in pack["blockers"]
    )


def test_context_quality_pack_rejects_missing_short_term_runtime_replay() -> None:
    pack = build_context_quality_pack_artifact(
        context_review=_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
    )

    assert pack["status"] == "fail"
    assert "short_term_context_runtime_replay.not_generated" in pack["blockers"]
    assert pack["short_term_context_runtime_replay_checked"] is False


def test_context_quality_pack_cli_writes_artifact(tmp_path: Path, capsys, monkeypatch) -> None:
    output_path = tmp_path / "context-quality.json"
    monkeypatch.setattr(module, "DEFAULT_SHORT_TERM_CONTEXT_SMOKE_PATHS", (tmp_path / "missing.json",))

    exit_code = module.main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "context_quality_diagnostic_pass"
    assert artifact["short_term_context_runtime_replay_checked"] is True
    assert artifact["runtime_trace_input_used"] is False


def test_context_quality_pack_cli_autoloads_default_runtime_trace_smoke(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    smoke_path = tmp_path / "default-short-term-context-smoke.json"
    output_path = tmp_path / "context-quality.json"
    smoke_path.write_text(json.dumps(_short_term_context_smoke()), encoding="utf-8")
    monkeypatch.setattr(module, "DEFAULT_SHORT_TERM_CONTEXT_SMOKE_PATHS", (smoke_path,))

    exit_code = module.main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "context_quality_diagnostic_pass"
    assert artifact["runtime_trace_input_used"] is True
    assert artifact["context_review_source"] == "product_pages_short_term_context_smoke"
    assert artifact["runtime_trace_source_artifact"] == (
        "accurate_intake_product_pages_short_term_context_smoke_v1"
    )


def test_context_quality_pack_cli_requires_autoloaded_runtime_trace_when_flagged(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    output_path = tmp_path / "context-quality.json"
    monkeypatch.setattr(module, "DEFAULT_SHORT_TERM_CONTEXT_SMOKE_PATHS", (tmp_path / "missing.json",))

    exit_code = module.main(["--require-runtime-trace-input", "--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert artifact == printed
    assert artifact["runtime_trace_input_used"] is False
    assert "runtime_trace_input.required_missing" in artifact["blockers"]


def test_context_quality_pack_can_be_backed_by_product_page_runtime_trace() -> None:
    artifact = module.build_context_quality_pack_report(
        short_term_context_smoke=_short_term_context_smoke(),
        require_runtime_trace_input=True,
    )

    assert artifact["status"] == "context_quality_diagnostic_pass"
    assert artifact["runtime_trace_input_used"] is True
    assert artifact["runtime_trace_source_artifact"] == "accurate_intake_product_pages_short_term_context_smoke_v1"
    assert artifact["runtime_trace_context_review"]["summary"]["present_context_trace_count"] == 2
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["raw_text_intent_router_used"] is False


def test_context_quality_pack_rejects_fixture_only_when_runtime_trace_is_required() -> None:
    artifact = module.build_context_quality_pack_report(require_runtime_trace_input=True)

    assert artifact["status"] == "fail"
    assert artifact["runtime_trace_input_used"] is False
    assert "runtime_trace_input.required_missing" in artifact["blockers"]
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["product_readiness_claimed"] is False


def test_context_quality_pack_cli_accepts_runtime_trace_smoke_artifact(tmp_path: Path, capsys) -> None:
    smoke_path = tmp_path / "short-term-context-smoke.json"
    output_path = tmp_path / "context-quality.json"
    smoke_path.write_text(json.dumps(_short_term_context_smoke()), encoding="utf-8")

    exit_code = module.main(
        [
            "--short-term-context-smoke",
            str(smoke_path),
            "--require-runtime-trace-input",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["runtime_trace_input_used"] is True
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
