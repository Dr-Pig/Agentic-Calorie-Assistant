from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_active_intake_callers_do_not_import_runtime_phase_a_facade() -> None:
    active_callers = [
        "app/intake/interface/intake_routes.py",
        "app/intake/interface/v2_routes.py",
        "app/intake/application/intake_turn_orchestrator.py",
        "app/intake/application/intake_execution_orchestrator.py",
        "app/intake/application/workflow_routing.py",
    ]

    for rel_path in active_callers:
        content = _read(rel_path)
        assert "runtime.application.phase_a_context" not in content, rel_path


def test_runtime_manager_does_not_assemble_phase_a_context() -> None:
    content = _read("app/runtime/agent/manager.py")

    assert "build_manager_context_pack" not in content
    assert "build_current_turn_context_v1" not in content
    assert "runtime.application.phase_a_context" not in content


def test_runtime_phase_a_context_is_a_facade_for_active_core_symbols() -> None:
    content = _read("app/runtime/application/phase_a_context.py")

    assert "from ...intake.application.current_turn_context_assembler import" in content
    assert "from ...intake.application.attachment_resolver import" in content
    assert "from ...intake.application.transition_guard import" in content
    assert "from ...intake.application.context_injection_policy import" in content
    assert "from ...intake.application.history_expansion_policy import" in content
    assert "from ...intake.application.phase_a_trace import" in content
    assert "from ...intake.application.shadow_hypothesis import" in content
    assert "def build_current_turn_context_v1(" not in content
    assert "def resolve_attachment_decision(" not in content
    assert "def resolve_transition_guard(" not in content
    assert "def build_manager_context_pack(" not in content
    assert "def build_history_expansion_request(" not in content
    assert "def build_history_expansion_result(" not in content
    assert "def build_shadow_hypothesis(" not in content
    assert "def advance_shadow_hypothesis(" not in content


def test_history_expansion_policy_is_policy_only() -> None:
    content = _read("app/intake/application/history_expansion_policy.py")

    assert "resolve_v2_bundle1_state" not in content
    assert "search_port" not in content
    assert "extract_port" not in content
    assert "tool_executor" not in content
    assert "vector" not in content.lower()
    assert "transcript search" not in content.lower()


def test_shadow_hypothesis_is_lifecycle_only() -> None:
    content = _read("app/intake/application/shadow_hypothesis.py")

    assert "reply_text" not in content
    assert "assistant_message" not in content
    assert "render_bundle1_reply" not in content
    assert "tentative phrasing" not in content.lower()


def test_only_one_dedicated_compatibility_shim_test_imports_runtime_phase_a_facade() -> None:
    importing_tests = []
    for path in (REPO_ROOT / "tests").glob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        imports_runtime_facade = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "app.runtime.application.phase_a_context":
                imports_runtime_facade = True
                break
            if isinstance(node, ast.Import):
                imported_names = {alias.name for alias in node.names}
                if "app.runtime.application.phase_a_context" in imported_names:
                    imports_runtime_facade = True
                    break
        if imports_runtime_facade:
            importing_tests.append(path.name)

    assert importing_tests == ["test_phase_a_compatibility_shim.py"]
