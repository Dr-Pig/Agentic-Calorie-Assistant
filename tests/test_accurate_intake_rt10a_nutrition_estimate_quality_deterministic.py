from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_rt10a_nutrition_estimate_quality_artifact() -> None:
    module = importlib.import_module(
        "scripts.run_accurate_intake_rt10a_nutrition_estimate_quality_deterministic"
    )

    artifact = module.build_rt10a_nutrition_estimate_quality_deterministic_artifact()

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt10a_nutrition_estimate_quality_deterministic"
    assert artifact["pass_type"] == "fixture"
    assert artifact["runtime_backed"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["supports_journeys"] == ["B", "C", "D"]
    assert artifact["summary"] == {"case_count": 6, "passed_case_count": 6}

    by_id = {case["case_id"]: case for case in artifact["cases"]}
    assert by_id["exact_item_keeps_exact_posture_with_official_card"]["exactness_posture"] == "exact"
    assert by_id["generic_single_item_uses_honest_estimate_not_fake_exactness"]["exactness_posture"] == "estimated"
    assert (
        by_id["optional_refinement_commits_estimate_and_keeps_refinement_posture"]["followup_role"]
        == "precision_refinement"
    )
    assert (
        by_id["blocking_clarify_stays_unresolved_without_canonical_truth"]["mapping_external_outcome"]
        == "draft"
    )
    assert (
        by_id["macro_visibility_stays_honest_when_display_data_is_missing_or_explicit"][
            "visible_guard_reason"
        ]
        == "committed_and_aligned"
    )


def test_rt10a_nutrition_estimate_quality_main_writes_artifact(tmp_path: Path) -> None:
    module = importlib.import_module(
        "scripts.run_accurate_intake_rt10a_nutrition_estimate_quality_deterministic"
    )
    output_path = tmp_path / "accurate_intake_rt10a_nutrition_estimate_quality_deterministic.json"

    exit_code = module.main(["--output", str(output_path)])

    assert exit_code == 0
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["status"] == "pass"
    assert written["artifact_name"] == output_path.name
