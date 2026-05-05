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
from app.composition.accurate_intake_fake_provider_tool_loop_smoke import (
    build_fake_provider_tool_loop_smoke_artifact,
)
from app.composition.accurate_intake_fixture_evidence_packet_emulator import (
    build_fixture_evidence_packet_emulator_artifact,
)
from app.composition.accurate_intake_review_eval_candidate_pipeline import (
    build_review_eval_candidate_pipeline_artifact,
)
from app.composition.accurate_intake_short_term_context_runtime_replay import (
    build_short_term_context_runtime_replay_artifact,
)
from app.composition.accurate_intake_ui_same_truth_render_contract import (
    build_ui_same_truth_render_contract,
)
from scripts import build_accurate_intake_review_eval_candidate_pipeline as module


def _context_quality() -> dict[str, object]:
    return build_context_quality_pack_artifact(
        context_review={
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
        },
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
        short_term_context_runtime_replay=build_short_term_context_runtime_replay_artifact(),
    )


def _product_loop_e2e() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_fixture_full_product_loop_e2e",
        "status": "fixture_product_loop_e2e_diagnostic_pass",
        "fixture_evidence_used": True,
        "fooddb_evidence_used": False,
        "websearch_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


def _ui_contract() -> dict[str, object]:
    return build_ui_same_truth_render_contract(
        Path("static/accurate-intake-local-shell.html").read_text(encoding="utf-8")
    )


def test_review_eval_candidate_pipeline_converts_diagnostics_to_review_candidates_only() -> None:
    fixture_packets = build_fixture_evidence_packet_emulator_artifact()
    artifact = build_review_eval_candidate_pipeline_artifact(
        product_loop_e2e=_product_loop_e2e(),
        ui_same_truth_contract=_ui_contract(),
        context_quality_pack=_context_quality(),
        fixture_packet_emulator=fixture_packets,
        fake_provider_tool_loop_smoke=build_fake_provider_tool_loop_smoke_artifact(
            context_smoke=build_fake_provider_context_smoke_artifact(),
            fixture_packet_emulator=fixture_packets,
        ),
    )

    assert artifact["artifact_type"] == "accurate_intake_review_eval_candidate_pipeline"
    assert artifact["status"] == "review_eval_candidate_pipeline_ready"
    assert artifact["review_candidate_count"] == 5
    assert artifact["canonical_eval_promoted"] is False
    assert artifact["human_approval_required"] is True
    assert artifact["raw_traces_review_input_only"] is True
    assert artifact["fooddb_truth_updated"] is False
    assert artifact["contains_personal_diet_logs"] is True
    assert artifact["do_not_commit"] is True
    for candidate in artifact["review_candidates"]:
        assert candidate["human_approval_required"] is True
        assert candidate["canonical_eval_promoted"] is False
        assert candidate["fooddb_truth_updated"] is False


def test_review_eval_candidate_pipeline_rejects_readiness_or_truth_overclaims() -> None:
    fixture_packets = build_fixture_evidence_packet_emulator_artifact()
    product_loop = {**_product_loop_e2e(), "dogfood_pass": True}
    context_quality = {**_context_quality(), "private_self_use_approved": True}

    artifact = build_review_eval_candidate_pipeline_artifact(
        product_loop_e2e=product_loop,
        ui_same_truth_contract=_ui_contract(),
        context_quality_pack=context_quality,
        fixture_packet_emulator=fixture_packets,
        fake_provider_tool_loop_smoke=build_fake_provider_tool_loop_smoke_artifact(
            context_smoke=build_fake_provider_context_smoke_artifact(),
            fixture_packet_emulator=fixture_packets,
        ),
    )

    assert artifact["status"] == "fail"
    assert "product_loop_e2e.dogfood_pass" in artifact["blockers"]
    assert "context_quality_pack.private_self_use_approved" in artifact["blockers"]


def test_review_eval_candidate_pipeline_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "review-pipeline.json"

    exit_code = module.main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "review_eval_candidate_pipeline_ready"


def test_review_eval_candidate_pipeline_script_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/build_accurate_intake_review_eval_candidate_pipeline.py").read_text(encoding="utf-8")

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
    ):
        assert fragment not in source
