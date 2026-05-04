from __future__ import annotations

from pathlib import Path


RUNBOOK = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md")


def test_foundation_train_runbook_mentions_context_policy_harness_and_fooddb_plan() -> None:
    text = RUNBOOK.read_text(encoding="utf-8-sig")

    assert "Manager Context Policy v1" in text
    assert "LocalSQLiteRouteHarness" in text
    assert "write_json_artifact" in text
    assert "build_accurate_intake_fooddb_quality_plan.py" in text
    assert "build_accurate_intake_food_evidence_candidates.py" in text
    assert "build_accurate_intake_food_evidence_validation.py" in text
    assert "FoodEvidenceCandidate" in text
    assert "validator_passed" in text
    assert "FoodDB truth" in text
    assert "review packets only" in text
