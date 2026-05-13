from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
from tests.support_rescue_phase1_decision_pack import (
    GOLDEN_PATH,
    PLAN_PATH,
    ROOT,
    golden_set,
    live_diagnostics,
    pr_train,
    replay_artifacts,
)


SCRIPT = "scripts/build_rescue_phase1_e2e_decision_pack.py"


def test_rescue_phase1_decision_pack_closes_lab_without_mainline_activation(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_rescue_phase1_decision_pack import (
        build_rescue_phase1_e2e_decision_pack,
    )

    pack = build_rescue_phase1_e2e_decision_pack(
        pr_train=pr_train(),
        golden_set=golden_set(),
        replay_artifacts=replay_artifacts(tmp_path),
        live_diagnostic_artifacts=live_diagnostics(),
    )

    assert pack["artifact_type"] == "advanced_product_lab_rescue_phase1_e2e_decision_pack"
    assert pack["status"] == "pass"
    assert pack["lab_enabled"] is True
    assert pack["lab_product_loop_complete"] is True
    assert pack["ready_for_lab_dogfood_feedback"] is True
    assert pack["ready_for_mainline_activation"] is False
    assert pack["mainline_activation_enabled"] is False
    assert pack["production_scheduler_delivery_allowed"] is False
    assert pack["canonical_product_mutation_allowed"] is False
    assert pack["dynamic_estimate"]["remaining_pr_count_before_this_pr"] == 1
    assert pack["dynamic_estimate"]["remaining_pr_count_after_pr24_merge"] == 0
    assert pack["milestone_statuses"] == {
        "fixture_golden_set_replay": "satisfied_fixture",
        "simulated_self_use_trace_replay": "satisfied_fixture",
        "grokfast_rescue_proposal_shaping_diagnostic": "satisfied_live_grokfast",
        "grokfast_rescue_response_presentation_diagnostic": "satisfied_live_grokfast",
        "lab_accept_dismiss_e2e": "satisfied_fixture",
        "integrated_f_f2_t_e2e_decision_pack": "satisfied_integrated_e2e",
    }
    assert pack["journey_statuses"] == {"F": "pass", "F2": "pass", "T": "pass"}
    assert pack["lab_accept_dismiss_e2e"] == {
        "accept_seen": True,
        "dismiss_seen": True,
        "canonical_product_mutation_allowed": False,
    }
    assert pack["blockers"] == []


def test_rescue_phase1_decision_pack_blocks_missing_live_grokfast(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_rescue_phase1_decision_pack import (
        build_rescue_phase1_e2e_decision_pack,
    )

    diagnostics = [
        item
        for item in live_diagnostics()
        if item["artifact_type"] != "rescue_response_presentation_provider_diagnostic"
    ]
    pack = build_rescue_phase1_e2e_decision_pack(
        pr_train=pr_train(),
        golden_set=golden_set(),
        replay_artifacts=replay_artifacts(tmp_path),
        live_diagnostic_artifacts=diagnostics,
    )

    assert pack["status"] == "blocked"
    assert "milestone.grokfast_rescue_response_presentation_diagnostic.missing" in pack[
        "blockers"
    ]
    assert pack["lab_product_loop_complete"] is False
    assert pack["ready_for_lab_dogfood_feedback"] is False


def test_rescue_phase1_decision_pack_cli_roundtrip(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay.json"
    diagnostics_path = tmp_path / "diagnostics.json"
    output = tmp_path / "decision-pack.json"
    write_json_artifact(replay_path, {"replay_artifacts": replay_artifacts(tmp_path)})
    write_json_artifact(diagnostics_path, {"diagnostic_artifacts": live_diagnostics()})

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--pr-train-yaml",
            str(PLAN_PATH),
            "--golden-set-yaml",
            str(GOLDEN_PATH),
            "--replay-artifacts-json",
            str(replay_path),
            "--live-diagnostics-json",
            str(diagnostics_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == read_json_artifact(output)
    assert read_json_artifact(output)["status"] == "pass"
