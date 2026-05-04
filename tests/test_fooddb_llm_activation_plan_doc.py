from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/quality/ACCURATE_INTAKE_FOODDB_WEBSEARCH_LLM_ACTIVATION_PLAN.md")


def test_fooddb_llm_activation_plan_documents_ladder_and_non_claims() -> None:
    content = DOC_PATH.read_text(encoding="utf-8-sig")

    assert "deterministic FoodDB" in content
    assert "GrokFast local packet smoke" in content
    assert "WebSearch candidate pipeline" in content
    assert "Kimi E2E diagnostic" in content
    assert "coverage_stop_rule" in content
    assert "common_serving_anchor_max_before_activation: 80" in content
    assert "listed_basket_components_max_before_activation: 60" in content
    assert "modifier_priority" in content
    assert "P0: sugar_level, cup_size, rice_portion" in content
    assert "exact_card_candidate.runtime_truth_allowed == false" in content
    assert "selected_extract.runtime_truth_allowed == false" in content
    assert "no_ledger_mutation_from_exact_candidate" in content
    assert "activation can proceed with known bounded gaps" in content
    assert "no readiness claim" in content
    assert "no self-use approval" in content
    assert "no production DB" in content
