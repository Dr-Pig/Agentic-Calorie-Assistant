from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_long_term_context_lab_stays_out_of_active_runtime_imports() -> None:
    active_surfaces = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "routes.py",
        ROOT / "app" / "schemas.py",
        ROOT / "app" / "composition" / "v2_routes.py",
        ROOT / "app" / "composition" / "intake_routes.py",
        ROOT / "app" / "runtime" / "application" / "manager_service.py",
        ROOT / "app" / "runtime" / "application" / "context_pack_builder.py",
        ROOT / "app" / "runtime" / "application" / "sidecar_service.py",
        ROOT / "app" / "runtime" / "application" / "proactive_deterministic_gate.py",
        ROOT / "app" / "runtime" / "agent" / "manager_context_payload.py",
        ROOT / "app" / "runtime" / "agent" / "manager.py",
    ]
    forbidden_imports = (
        "app.memory.application.long_term_context_shadow_lab",
        "app.memory.application.external_memory_framework_research",
        "app.memory.domain.long_term_context_candidates",
    )
    forbidden_tokens = (
        "long_term_context_shadow_lab",
        "LongTermContext",
        "manager_context_injected = True",
        '"manager_context_injected": True',
        "durable_memory_written = True",
        '"durable_memory_written": True',
    )

    violations: list[str] = []
    for path in active_surfaces:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for imported in _absolute_imports(path):
            if imported.startswith(forbidden_imports):
                violations.append(f"{path.relative_to(ROOT)} imports {imported}")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)} contains {token}")

    assert not violations, (
        "Long-term context lab must not attach to active runtime: "
        + ", ".join(violations)
    )


def test_long_term_context_lab_is_registered_as_offline_sidecar_only() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        SIDECAR_ACTIVATION_CONTRACT,
    )

    assert SIDECAR_ACTIVATION_CONTRACT.offline_only is True
    assert SIDECAR_ACTIVATION_CONTRACT.activation_blocked is True
    assert SIDECAR_ACTIVATION_CONTRACT.not_runtime_authority is True
    assert SIDECAR_ACTIVATION_CONTRACT.user_facing_activation is False
    assert SIDECAR_ACTIVATION_CONTRACT.mutation_authority is False
    assert (
        SIDECAR_ACTIVATION_CONTRACT.product_intelligence_readiness_participant is False
    )
