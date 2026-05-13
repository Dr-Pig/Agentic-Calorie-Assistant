from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_holdout_loader import (
    HOLDOUT_PATH,
    load_context_engineering_holdouts,
)


def test_context_engineering_holdout_pack_loads() -> None:
    artifact = load_context_engineering_holdouts()

    assert HOLDOUT_PATH.exists()
    assert artifact["artifact_type"] == "advanced_product_lab_context_engineering_holdouts"
    assert artifact["status"] == "active"
    assert len(artifact["holdouts"]) == 5


def test_context_engineering_holdout_pack_covers_ambiguity_and_adversarial_families() -> None:
    artifact = load_context_engineering_holdouts()
    by_id = {item["holdout_id"]: item for item in artifact["holdouts"]}

    assert by_id["ceh-001"]["family"] == "ambiguity"
    assert by_id["ceh-002"]["family"] == "over_trigger"
    assert by_id["ceh-003"]["family"] == "prompt_injection"
    assert by_id["ceh-004"]["family"] == "no_keyword_true_positive"
    assert by_id["ceh-005"]["family"] == "transcript_leakage"
    assert by_id["ceh-003"]["expected_behavior"] == (
        "reject_illegal_actions_and_preserve_activation_wall"
    )
