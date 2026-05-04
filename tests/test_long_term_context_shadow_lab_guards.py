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
        ROOT / "app" / "composition" / "manager_context_runtime.py",
        ROOT / "app" / "composition" / "intake_execution_orchestrator.py",
        ROOT / "app" / "composition" / "intake_turn_orchestrator.py",
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
        "app.memory",
    )
    forbidden_tokens = (
        "long_term_context_shadow_lab",
        "LongTermContext",
        "artifact_registry_manifest",
        "conversation_recall.search",
        "memory.application.long_term_context_shadow_lab",
        "manager_context_injected = True",
        '"manager_context_injected": True',
        "durable_memory_written = True",
        '"durable_memory_written": True',
        "runtime_effect_allowed = True",
        '"runtime_effect_allowed": True',
        "BodyPlan mutation allowed",
        "DayBudgetLedger mutation allowed",
        "MealThread mutation allowed",
        "FoodDB truth mutation allowed",
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


def test_long_term_context_artifact_contract_blocks_unowned_outputs() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifacts = build_shadow_lab_artifacts(
        {
            "user_id": "fixture-user",
            "meal_logs": [
                {
                    "trace_id": "meal-1",
                    "meal_id": "m1",
                    "logged_at": "2026-04-01T08:15:00+08:00",
                    "item_names": ["oatmeal"],
                    "item_kinds": ["staple"],
                    "staple_types": ["oats"],
                }
            ],
        }
    )

    manifest = artifacts["artifact_registry_manifest"]
    assert manifest["artifacts_without_consumers"] == []
    assert manifest["pseudo_runtime_truth_risks"] == []

    for artifact_key, artifact in artifacts.items():
        assert artifact["intended_consumers"], artifact_key
        assert artifact["consumer_use_hints"], artifact_key
        assert artifact["risk_if_wrong"], artifact_key
        assert artifact["promotion_path"], artifact_key
        assert artifact["why_this_is_not_runtime_truth"], artifact_key
        assert artifact["runtime_effect_allowed"] is False, artifact_key
