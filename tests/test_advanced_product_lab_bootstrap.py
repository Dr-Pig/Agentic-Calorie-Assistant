from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_agents_defers_advanced_product_lab_branch_bootstrap() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8-sig")

    assert "Advanced Product Lab Branch Bootstrap" not in text
    assert "`main` does not own branch-local bootstrap" in text
    assert "codex/advanced-product-lab" in text
    assert "self-use V1 remains isolated" in text
    assert "default runtime connection" in text
    assert "full runtime lab integration" not in text
    assert "live Grokfast diagnostics" not in text
    assert "recommendation/rescue/proactive loop" not in text


def test_docs_index_records_advanced_product_lab_runtime_closure_contract() -> None:
    index = (ROOT / "docs" / "DOC_INDEX.md").read_text(encoding="utf-8-sig")
    build_spec = (
        ROOT / "docs" / "quality" / "ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md"
    ).read_text(encoding="utf-8-sig")

    assert "branch-local bootstrap lives in `codex/advanced-product-lab` `AGENTS.md`" in index
    assert "advanced product lab runtime closure" in index
    assert "ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md" in index
    assert "Advanced Product Lab Runtime Closure Record" in build_spec
    assert "chat action outcome replay" in build_spec
    assert "product loop closure" in build_spec
    assert "live Grokfast diagnostic payload" in build_spec
    assert "merge-back activation wall regression" in build_spec
