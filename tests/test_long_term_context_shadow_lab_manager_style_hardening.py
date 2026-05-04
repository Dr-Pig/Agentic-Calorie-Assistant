from __future__ import annotations

import ast
from pathlib import Path

from tests.long_term_context_shadow_fixture import _fixture_payload


ROOT = Path(__file__).resolve().parents[1]


def _imports_symbol(path: Path, symbol_names: set[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            if alias.name in symbol_names:
                imports.append(alias.name)
    return imports


def test_active_manager_never_imports_future_memory_contract_symbols() -> None:
    future_contract_symbols = {
        "MemoryIngressRequest",
        "MemoryContextPack",
        "MemoryUseDecisionTrace",
    }
    active_manager_paths = [
        *(ROOT / "app" / "runtime").rglob("*.py"),
        ROOT / "app" / "composition" / "manager_context_runtime.py",
        ROOT / "app" / "composition" / "intake_turn_orchestrator.py",
        ROOT / "app" / "composition" / "intake_execution_orchestrator.py",
    ]

    violations: list[str] = []
    for path in active_manager_paths:
        if not path.exists():
            continue
        imported = _imports_symbol(path, future_contract_symbols)
        if imported:
            violations.append(f"{path.relative_to(ROOT)} imports {sorted(imported)}")

    assert violations == []


def test_manager_memory_contract_artifact_is_offline_only() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "manager_memory_contract_shadow_plan"
    ]

    assert artifact["active_manager_import_allowed"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["runtime_tool_registered"] is False
    assert artifact["contract_symbols"] == [
        "MemoryIngressRequest",
        "MemoryContextPack",
        "MemoryUseDecisionTrace",
    ]


def test_semantic_extraction_flags_prevent_runtime_readiness_claim() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "semantic_pattern_extraction_shadow_plan"
    ]

    assert artifact["semantic_extraction_flags"] == {
        "fixture_llm_output_used": True,
        "live_provider_used": False,
        "semantic_extraction_runtime_ready": False,
    }


def test_promotion_ladder_separates_candidate_confirmed_and_runtime_injectable() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_promotion_demotion_shadow_eval"
    ]

    assert artifact["memory_states"] == {
        "candidate": {"runtime_use_allowed": False},
        "confirmed_memory": {
            "runtime_use_allowed": False,
            "still_false_until_injection_gate": True,
        },
        "runtime_injectable_memory": {
            "runtime_use_allowed": False,
            "requires_future_gate": True,
        },
    }


def test_proactive_evaluator_records_high_value_silence_cases() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "proactive_intelligence_shadow_eval"
    ]

    assert artifact["proactive_silence_cases"]
    for silence_case in artifact["proactive_silence_cases"]:
        assert silence_case["why_system_should_stay_silent"]
        assert silence_case["potential_trigger_suppressed"]
        assert silence_case["user_annoyance_risk"]
        assert silence_case["future_data_needed"]
        assert silence_case["runtime_effect_allowed"] is False


def test_long_term_context_module_boundaries_are_named_and_guarded() -> None:
    shadow_dir = ROOT / "app" / "memory" / "application" / "long_term_context_shadow"
    expected_modules = {
        "contracts.py",
        "manager_memory_contracts.py",
        "semantic_pattern_artifacts.py",
        "memory_action_artifacts.py",
        "memory_architecture_artifacts.py",
        "context_pack_artifacts.py",
        "shadow_evaluators.py",
        "review_queue_reducer.py",
    }

    assert expected_modules <= {path.name for path in shadow_dir.glob("*.py")}
