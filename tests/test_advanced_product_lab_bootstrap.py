from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agents_bootstrap_records_two_layer_advanced_product_lab_strategy() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8-sig")

    assert "Advanced Product Lab Branch Bootstrap" in text
    assert "codex/advanced-product-lab" in text
    assert "complete advanced product" in text
    assert "complete product build" in text
    assert "full runtime lab integration" in text
    assert "live Grokfast diagnostics" in text
    assert "control state loop" in text
    assert "recommendation/rescue/proactive loop" in text
    assert "self-use V1 remains isolated" in text
    assert "merge back to main" in text
    assert "activation wall" in text
    assert "do not reduce lab behavior to no-send/dormant-only constraints" in text
    assert "Lab runtime capability flags may be `true`" in text
    assert "Do not keep memory tools" in text
    assert "context injection" in text
    assert "do not delete this branch unless the user explicitly asks" in text
    assert "`user.md`" in text
    assert "`source.md`" in text
    assert "not raw transcript dumps" in text
    assert "`lab_enabled=true`" in text
    assert "`mainline_activation_enabled=false`" in text


def test_docs_index_records_advanced_product_lab_runtime_closure_contract() -> None:
    index = (ROOT / "docs" / "DOC_INDEX.md").read_text(encoding="utf-8-sig")
    build_spec = (
        ROOT / "docs" / "quality" / "ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md"
    ).read_text(encoding="utf-8-sig")

    assert "advanced product lab runtime closure" in index
    assert "ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md" in index
    assert "Advanced Product Lab Runtime Closure Record" in build_spec
    assert "chat action outcome replay" in build_spec
    assert "product loop closure" in build_spec
    assert "live Grokfast diagnostic payload" in build_spec
    assert "merge-back activation wall regression" in build_spec
