from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def test_reference_informed_prompt_architecture_spec_exists_and_cites_code_refs() -> None:
    text = _read("docs/specs/MANAGER_RUNTIME_PROMPT_ARCHITECTURE_AND_OWNERSHIP_SPEC.md")

    assert "a2802480211a6b28f3c00c0ca9bbb2838503eba4" in text
    assert "C:\\Users\\User\\Desktop\\agent runtime\\cc-haha-main.zip" in text
    assert "codex-rs/core/src/context_manager/history.rs" in text
    assert "codex-rs/core/src/context_manager/updates.rs" in text
    assert "codex-rs/core/src/tools/orchestrator.rs" in text
    assert "codex-rs/core/src/tools/tool_dispatch_trace.rs" in text
    assert "cc-haha-main/src/constants/systemPromptSections.ts" in text
    assert "cc-haha-main/src/constants/prompts.ts" in text
    assert "SYSTEM_PROMPT_DYNAMIC_BOUNDARY" in text
    assert "DANGEROUS_uncachedSystemPromptSection" in text
    assert "case-style patch" in text
    assert "provider-reported cached tokens" in text


def test_agentic_edd_standard_exists_and_blocks_fake_pass_patterns() -> None:
    text = _read("docs/quality/CURRENT_SHELL_AGENTIC_EDD_STANDARD.md")

    required_phrases = [
        "Golden Set is a measuring instrument, not an architecture source",
        "classify failure family",
        "inspect trace owner",
        "fix capability mechanism",
        "add holdout",
        "rerun targeted E2E",
        "rerun full E2E",
        "isolated pass",
        "browser/UI flag",
        "live LLM flag",
        "live tool flag",
        "artifact path",
        "fixture label",
        "literal case",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_shared_llm_deterministic_boundary_is_copied_to_active_owner_docs() -> None:
    required_phrases = [
        "LLM / Manager owns",
        "composition sufficiency",
        "estimability",
        "whether to call WebSearch",
        "Deterministic code may only",
        "validate source eligibility",
        "must not inspect raw user text",
        "create fallback kcal/macros",
        "rewrite Manager action to make a test pass",
    ]
    for path in (
        "docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md",
        "docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md",
        "docs/quality/CURRENT_SHELL_SELF_USE_GOLDEN_SET_SPEC.md",
    ):
        text = _read(path)
        for phrase in required_phrases:
            assert phrase in text


def test_doc_index_points_agents_to_reference_runtime_specs() -> None:
    text = _read("docs/DOC_INDEX.md")

    assert "MANAGER_RUNTIME_PROMPT_ARCHITECTURE_AND_OWNERSHIP_SPEC.md" in text
    assert "CURRENT_SHELL_AGENTIC_EDD_STANDARD.md" in text
