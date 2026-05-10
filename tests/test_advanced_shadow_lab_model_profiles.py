from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.manifest import build_advanced_shadow_lab_manifest
from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
    advanced_lab_model_profile_policy,
    resolve_advanced_lab_model_profile,
    resolve_live_diagnostic_profile,
)


ROOT = Path(__file__).resolve().parents[1]


def test_advanced_lab_model_profiles_invert_model_dependencies() -> None:
    policy = advanced_lab_model_profile_policy()
    diagnostic = policy["profiles"][ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID]
    reasoning = policy["profiles"][ADVANCED_LAB_TARGET_REASONING_PROFILE_ID]

    assert policy["provider_dependency_inversion_required"] is True
    assert policy["live_provider_calls_allowed_by_default"] is False
    assert policy["kimi_live_calls_allowed"] is False
    assert policy["production_selected"] is False
    assert policy["provider_specific_product_semantics_allowed"] is False
    assert diagnostic["role"] == "diagnostic_live_llm"
    assert diagnostic["model_id"] == "grok-4-fast"
    assert diagnostic["live_diagnostic_allowed"] is True
    assert reasoning["role"] == "target_reasoning_model"
    assert reasoning["model_id"] == "kimi-k2.5"
    assert reasoning["selection_status"] == "dormant_reference_only"
    assert reasoning["live_diagnostic_allowed"] is False
    assert reasoning["kimi_live_calls_allowed"] is False


def test_kimi_profile_cannot_be_resolved_for_live_diagnostic() -> None:
    profile, blockers = resolve_live_diagnostic_profile(
        ADVANCED_LAB_TARGET_REASONING_PROFILE_ID
    )

    assert profile["model_id"] == "kimi-k2.5"
    assert blockers == [
        "profile_not_live_diagnostic_allowed",
        "kimi_live_calls_forbidden",
    ]


def test_unknown_profile_is_rejected_before_provider_construction() -> None:
    try:
        resolve_advanced_lab_model_profile("builderspace-unknown-model")
    except ValueError as exc:
        assert str(exc) == (
            "unsupported_advanced_lab_provider_profile:builderspace-unknown-model"
        )
    else:
        raise AssertionError("unsupported profile did not raise")


def test_manual_live_script_rejects_unknown_profile_without_reading_input(
    tmp_path: Path,
) -> None:
    output = tmp_path / "blocked_unknown.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_shadow_lab_rescue_copy_live_diagnostic.py",
            "--input",
            str(tmp_path / "missing_input.json"),
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
            "--provider-profile-id",
            "builderspace-unknown-model",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "unsupported_advanced_lab_provider_profile" in output.read_text(
        encoding="utf-8"
    )
    assert "No such file" not in result.stderr


def test_boundary_manifest_embeds_profile_policy_without_activation_claims() -> None:
    manifest = build_advanced_shadow_lab_manifest()
    policy = manifest["model_profile_policy"]

    assert policy["default_live_diagnostic_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert policy["target_reasoning_profile_id"] == ADVANCED_LAB_TARGET_REASONING_PROFILE_ID
    assert manifest["live_provider_calls_allowed"] is False
    assert manifest["kimi_live_calls_allowed"] is False
    assert manifest["product_readiness_claimed"] is False
    assert "not_production_model_selection" in policy["non_claims"]


def test_model_profile_module_stays_lab_only_and_transport_free() -> None:
    path = ROOT / "app" / "advanced_shadow_lab" / "model_profiles.py"
    imports = _absolute_imports(path)

    assert "app.providers" not in "\n".join(imports)
    assert "app.runtime.interface.provider_runtime" not in "\n".join(imports)
    assert "httpx" not in imports
    assert "requests" not in imports


def test_manual_live_scripts_reject_kimi_profile_before_provider_import(tmp_path: Path) -> None:
    output = tmp_path / "blocked.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_shadow_lab_recommendation_copy_live_diagnostic.py",
            "--input",
            str(tmp_path / "missing_input.json"),
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
            "--provider-profile-id",
            ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "kimi_live_calls_forbidden" in output.read_text(encoding="utf-8")
    assert "No such file" not in result.stderr


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
