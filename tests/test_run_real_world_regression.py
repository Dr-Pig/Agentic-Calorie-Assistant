from __future__ import annotations

from scripts.run_real_world_regression import _build_wave_summary


def test_build_wave_summary_aggregates_stage_and_verdict_signals() -> None:
    summary = _build_wave_summary(
        [
            {
                "category": "buffet",
                "best_answer_source": "reference_card",
                "failed_layer": "grounding",
                "north_star_verdict": "loss",
                "failure_family": "exact_item_shadowed_by_generic_anchor",
                "followup_decision": "must_ask",
                "db_hit_type": "exact_truth",
            },
            {
                "category": "buffet",
                "best_answer_source": "initial",
                "failed_layer": "layer3_primary_llm",
                "north_star_verdict": "loss",
                "failure_family": "portion_missing_overestimate",
                "followup_decision": "should_ask",
                "db_hit_type": "none",
            },
            {
                "category": "common_foods",
                "best_answer_source": "with_local_knowledge",
                "failed_layer": None,
                "north_star_verdict": "win",
                "failure_family": None,
                "followup_decision": "not_needed",
                "db_hit_type": "reference_anchor",
            },
        ]
    )

    assert summary["total_cases"] == 3
    assert summary["by_category"]["buffet"] == 2
    assert summary["by_failed_layer"]["grounding"] == 1
    assert summary["by_failed_layer"]["layer3_primary_llm"] == 1
    assert summary["by_north_star_verdict"]["loss"] == 2
    assert summary["by_north_star_verdict"]["win"] == 1
    assert summary["by_db_hit_type"]["exact_truth"] == 1
    assert summary["by_db_hit_type"]["reference_anchor"] == 1
