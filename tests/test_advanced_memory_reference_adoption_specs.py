from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "docs" / "specs"


def _spec(name: str) -> str:
    return (SPECS / name).read_text(encoding="utf-8-sig")


def test_l4a_records_memory_substrate_and_reference_adoption() -> None:
    text = _spec("L4A_MEMORY_MODEL_SPEC.md")

    assert "V1 Memory Substrate And Reference Adoption" in text
    assert "`user.md`" in text
    assert "`memory.md`" in text
    assert "`sources.jsonl` / `source.md`" in text
    assert "`daily/YYYY-MM-DD.md`" in text
    assert "`review.md`" in text
    assert "Hermes、OpenClaw、Mem0、Hindsight、Graphiti、Letta、memU" in text
    assert "不是產品 truth owner" in text
    assert "不在 V1 直接啟動外部 memory framework server" in text
    assert "codex/advanced-product-lab" in text


def test_l4b_records_memory_tool_facade_and_selection_policy() -> None:
    text = _spec("L4B_RETRIEVAL_POLICY_SPEC.md")

    assert "Memory Tool Facade And Retrieval Selection" in text
    assert "`memory.search`" in text
    assert "`memory.get`" in text
    assert "`conversation_recall.search`" in text
    assert "`memory.propose`" in text
    assert "`memory.review`" in text
    assert "`canonical_state_first`" in text
    assert "`semantic_or_vector_retrieval`" in text
    assert "V1 不預設大型 RAG 或 graph retrieval" in text


def test_l4c_records_lab_enabled_context_injection_boundary() -> None:
    text = _spec("L4C_CONTEXT_PACKING_SPEC.md")

    assert "Lab-Enabled Memory Context Injection Boundary" in text
    assert "`lab_enabled=true`" in text
    assert "`memory_context_injected=true|false`" in text
    assert "`mainline_activation_enabled=false`" in text
    assert "`self_use_v1_affected=false`" in text
    assert "`user.md` compact profile block" in text
    assert "`conversation_recall.search` 的結果必須 summary-first" in text


def test_l4d_records_framework_informed_promotion_guardrails() -> None:
    text = _spec("L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md")

    assert "Framework-Informed Promotion Guardrails" in text
    assert "retain / recall / reflect" in text
    assert "review.md" in text
    assert "缺少 scope keys 時，promotion 必須拒絕" in text
    assert "`add/update/delete` 在本產品對應 propose/review/forget" in text
    assert "`lab_promotion_executed=true`" in text
    assert "`mainline_promotion_enabled=false`" in text
