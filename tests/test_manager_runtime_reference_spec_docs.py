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


def test_bootstrap_requires_code_reference_first_for_mechanism_sensitive_work() -> None:
    agents = _read("AGENTS.md")
    edd = _read("docs/quality/CURRENT_SHELL_AGENTIC_EDD_STANDARD.md")

    bootstrap_required = [
        "Code-reference-first bootstrap",
        "repo truth first",
        "implementation code references before official-doc-only best-practice claims",
        "official docs are normative API/framework evidence, not mechanism implementation proof",
        "inspected reference paths",
        "adopted_or_rejected_rationale",
    ]
    for phrase in bootstrap_required:
        assert phrase in agents

    edd_required = [
        "Code-Reference-First Bootstrap",
        "repo truth first",
        "implementation code references",
        "official docs are normative API/framework evidence",
        "code_references_inspected",
        "reference_mechanisms_compared",
        "adopted_mechanisms",
        "rejected_mechanisms",
        "product_variant_rationale",
    ]
    for phrase in edd_required:
        assert phrase in edd


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


def test_ab_mechanism_specs_capture_current_code_reference_findings() -> None:
    prompt = _read("docs/specs/MANAGER_RUNTIME_PROMPT_ARCHITECTURE_AND_OWNERSHIP_SPEC.md")
    context = _read("docs/specs/L4C_CONTEXT_PACKING_SPEC.md")
    intake = _read("docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md")
    edd = _read("docs/quality/CURRENT_SHELL_AGENTIC_EDD_STANDARD.md")
    fooddb = _read("docs/quality/FOODDB_SELF_USE_V1_1000_PACKET_READY_COVERAGE_PLAN.md")

    reference_paths = [
        "codex-rs/core/src/state/session.rs",
        "codex-rs/core/src/tools/registry.rs",
        "cc-haha-main/src/utils/messageQueueManager.ts",
        "hermes-agent-main/agent/context_references.py",
        "hermes-agent-main/agent/memory_manager.py",
    ]
    combined_reference_text = "\n".join([prompt, context, edd])
    for path in reference_paths:
        assert path in combined_reference_text

    prompt_required = [
        "manager-owned evidence target",
        "targetless estimate_nutrition",
        "tool_schema_hash",
        "output_schema_hash",
        "provider_profile",
        "cached_tokens",
        "unknown",
    ]
    for phrase in prompt_required:
        assert phrase in prompt

    context_required = [
        "post-tool context compaction",
        "preserve compact target candidates",
        "selection_owner: manager",
        "mutation_authority: false",
    ]
    for phrase in context_required:
        assert phrase in context

    intake_required = [
        "estimate_nutrition requires a Manager-owned evidence target",
        "raw user text must not be the retrieval query",
        "Manager-owned retrieval query",
        "active committed version",
    ]
    for phrase in intake_required:
        assert phrase in intake

    edd_required = [
        "L9_ui_same_truth",
        "trace repair router",
        "isolated pass cannot be reported as full suite pass",
    ]
    for phrase in edd_required:
        assert phrase in edd

    fooddb_required = [
        "DB rows are packet-ready storage",
        "not prompt-shaped evidence packets",
        "raw user text must not be a retrieval query",
        "Manager-owned evidence target",
    ]
    for phrase in fooddb_required:
        assert phrase in fooddb
