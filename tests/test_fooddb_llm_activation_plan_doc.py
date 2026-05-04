from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/quality/ACCURATE_INTAKE_FOODDB_WEBSEARCH_LLM_ACTIVATION_PLAN.md")


def test_fooddb_llm_activation_plan_documents_ladder_and_non_claims() -> None:
    content = DOC_PATH.read_text(encoding="utf-8-sig")

    assert "deterministic FoodDB" in content
    assert "GrokFast local packet smoke" in content
    assert "WebSearch candidate pipeline" in content
    assert "Kimi E2E diagnostic" in content
    assert "no readiness claim" in content
    assert "no self-use approval" in content
    assert "no production DB" in content
