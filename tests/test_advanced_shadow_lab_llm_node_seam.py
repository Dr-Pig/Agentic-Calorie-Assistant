from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
)
from app.advanced_shadow_lab.vertical_proof import (
    build_fixture_vertical_proof_input,
    run_fixture_vertical_proof,
)


ROOT = Path(__file__).resolve().parents[1]


def test_advanced_shadow_llm_node_fake_provider_keeps_model_dependency_inverted(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.llm_node_contract import (
        build_recommendation_offer_synthesis_node_input,
        run_advanced_shadow_llm_node,
    )
    from app.advanced_shadow_lab.llm_node_fake_provider import (
        FakeAdvancedShadowLLMNodeProvider,
    )

    vertical = run_fixture_vertical_proof(
        build_fixture_vertical_proof_input(),
        artifact_root=tmp_path / "vertical",
    )
    node_input = build_recommendation_offer_synthesis_node_input(vertical)
    artifact = run_advanced_shadow_llm_node(
        node_input=node_input,
        provider=FakeAdvancedShadowLLMNodeProvider(),
        provider_profile={
            "provider_profile_id": "fake-advanced-shadow-node",
            "provider_family": "fake",
            "model_id": "fake-llm",
            "role": "diagnostic_live_llm",
            "live_diagnostic_allowed": False,
            "kimi_live_calls_allowed": False,
            "production_selected": False,
            "provider_specific_product_semantics_allowed": False,
        },
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert node_input["artifact_type"] == "advanced_shadow_llm_node_input_artifact"
    assert node_input["status"] == "pass"
    assert node_input["node_id"] == "recommendation_offer_synthesis_chat_first_probe"
    assert node_input["node_role"] == "offer_synthesis"
    assert node_input["source_artifact_refs"] == [
        "advanced_shadow_lab_vertical_proof_artifact",
        "advanced_shadow_chat_first_journey_proof_artifact",
    ]
    assert node_input["provider_payload"]["constraints"] == {
        "claim_scope_required": "advanced_shadow_llm_node_diagnostic_only",
        "user_facing_output_allowed": False,
        "delivery_or_notification_allowed": False,
        "mutation_or_commit_allowed": False,
    }
    assert artifact["artifact_type"] == "advanced_shadow_llm_node_diagnostic_artifact"
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["provider_invoked"] is True
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["node_id"] == node_input["node_id"]
    assert artifact["node_role"] == "offer_synthesis"
    assert artifact["structured_output_schema_id"] == (
        "advanced_shadow_llm_node_diagnostic_v1"
    )
    assert artifact["model_output_summary"] == {
        "node_output_id": "fake-recommendation-offer-synthesis",
        "selected_candidate_id": "golden-order-morning-bar-oatmeal-latte",
        "draft_text_present": True,
        "rationale_present": True,
        "reason_codes": ["chat_first", "memory_guided", "review_only"],
        "claim_scope": "advanced_shadow_llm_node_diagnostic_only",
    }
    assert artifact["provider_trace_summary"] == {
        "stage": "advanced_shadow_llm_node_diagnostic",
        "provider": "fake",
        "usage_present": False,
    }
    assert artifact["runtime_connected"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["production_selected"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["durable_product_memory_written"] is False


def test_llm_node_live_runner_blocks_without_gate_before_reading_input(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC", raising=False)
    output = tmp_path / "blocked.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_shadow_lab_llm_node_diagnostic.py",
            "--vertical-proof-json",
            str(tmp_path / "missing_vertical.json"),
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    artifact = json.loads(output.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["blockers"] == ["live_gate_not_enabled"]
    assert artifact["provider_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert "No such file" not in result.stderr


def test_llm_node_live_runner_rejects_kimi_before_reading_input(
    tmp_path: Path,
) -> None:
    output = tmp_path / "blocked_kimi.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_shadow_lab_llm_node_diagnostic.py",
            "--vertical-proof-json",
            str(tmp_path / "missing_vertical.json"),
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
    artifact = json.loads(output.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["blockers"] == [
        "profile_not_live_diagnostic_allowed;kimi_live_calls_forbidden"
    ]
    assert artifact["live_provider_used"] is False
    assert artifact["production_selected"] is False
    assert "not_kimi_activation" in artifact["non_claims"]
    assert "No such file" not in result.stderr


@pytest.mark.skipif(
    os.getenv("ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC") != "1"
    or not os.getenv("AI_BUILDER_TOKEN"),
    reason="advanced shadow Grokfast live diagnostic is manual/env-gated",
)
def test_llm_node_optional_grokfast_live_diagnostic_stays_non_claim(
    tmp_path: Path,
) -> None:
    vertical_path = tmp_path / "vertical.json"
    output = tmp_path / "live_node.json"
    vertical = run_fixture_vertical_proof(
        build_fixture_vertical_proof_input(),
        artifact_root=tmp_path / "vertical_artifacts",
    )
    vertical_path.write_text(json.dumps(vertical, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_shadow_lab_llm_node_diagnostic.py",
            "--vertical-proof-json",
            str(vertical_path),
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    artifact = json.loads(output.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert artifact["live_invoked"] is True
    assert artifact["live_provider_used"] is True
    assert artifact["provider_profile_id"].endswith("advanced-shadow-lab-live-diagnostic")
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["production_selected"] is False


def test_llm_node_app_modules_do_not_import_provider_adapters() -> None:
    for path in [
        ROOT / "app" / "advanced_shadow_lab" / "llm_node_contract.py",
        ROOT / "app" / "advanced_shadow_lab" / "llm_node_fake_provider.py",
    ]:
        imports = _absolute_imports(path)

        assert "app.providers" not in "\n".join(imports)
        assert "app.runtime.interface.provider_runtime" not in "\n".join(imports)
        assert "httpx" not in imports
        assert "requests" not in imports


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
