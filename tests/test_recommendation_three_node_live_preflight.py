from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
)
from app.recommendation.application.three_node_live_preflight import (
    build_recommendation_three_node_live_preflight,
)
from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
)


ROOT = Path(__file__).resolve().parents[1]


def test_three_node_live_preflight_builds_fixed_node_inputs_without_live_call() -> None:
    artifact = build_recommendation_three_node_live_preflight()

    assert artifact["artifact_type"] == "recommendation_three_node_live_preflight"
    assert artifact["status"] == "pass"
    assert artifact["canonical_recommendation_graph"] == "three_node"
    assert artifact["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert artifact["provider_dependency_inversion_required"] is True
    assert artifact["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert artifact["profile_model_id"] == "grok-4-fast"
    assert artifact["target_reasoning_model_id"] == "kimi-k2.5"
    assert artifact["target_reasoning_live_calls_allowed"] is False
    assert artifact["provider_call_ready"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["candidate_guard"]["allowed_candidate_ids"] == ["golden-1"]
    assert [node["physical_node"] for node in artifact["provider_inputs"]] == [
        "recommendation_planning",
        "offer_synthesis",
    ]
    assert artifact["provider_inputs"][0]["logical_outputs_required"] == [
        "recommendation_context_result",
        "candidate_spec",
    ]
    assert artifact["provider_inputs"][1]["logical_outputs_required"] == [
        "ranking_result",
        "recommendation_response_result",
    ]
    assert all(node["response_schema"]["strict"] is True for node in artifact["provider_inputs"])
    assert all(node["live_provider_invoked"] is False for node in artifact["provider_inputs"])
    assert artifact["activation_flags"] == _false_activation_flags()
    assert "not_kimi_activation" in artifact["non_claims"]
    assert "not_recommendation_serving" in artifact["non_claims"]


def test_three_node_live_preflight_blocks_kimi_and_unknown_profiles() -> None:
    kimi = build_recommendation_three_node_live_preflight(
        provider_profile_id=ADVANCED_LAB_TARGET_REASONING_PROFILE_ID
    )
    unknown = build_recommendation_three_node_live_preflight(
        provider_profile_id="builderspace-unknown-model"
    )

    assert kimi["status"] == "blocked"
    assert kimi["provider_call_ready"] is False
    assert kimi["blockers"] == [
        "profile.profile_not_live_diagnostic_allowed",
        "profile.kimi_live_calls_forbidden",
    ]
    assert kimi["activation_flags"] == _false_activation_flags()
    assert unknown["status"] == "blocked"
    assert unknown["blockers"] == [
        "profile.unsupported_advanced_lab_provider_profile:builderspace-unknown-model"
    ]
    assert unknown["live_provider_invoked"] is False


def test_three_node_live_preflight_blocks_three_node_claim_drift() -> None:
    payload = build_fixture_recommendation_three_node_input()
    payload["shadow_offer_packet_fixture"]["recommendation_served"] = True
    payload["shadow_offer_packet_fixture"]["intake_commit_requested"] = True

    artifact = build_recommendation_three_node_live_preflight(payload=payload)

    assert artifact["status"] == "blocked"
    assert "three_node_artifact.status_not_pass" in artifact["blockers"]
    assert "shadow_offer_packet_fixture.recommendation_served_not_allowed" in artifact["blockers"]
    assert "shadow_offer_packet_fixture.intake_commit_requested_not_allowed" in artifact["blockers"]
    assert artifact["provider_inputs"] == []
    assert artifact["activation_flags"] == _false_activation_flags()


def test_three_node_live_preflight_script_writes_artifact_without_provider_call(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "recommendation-three-node-live-preflight.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_three_node_live_preflight.py",
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "recommendation_three_node_live_preflight"
    assert payload["status"] == "pass"
    assert payload["live_provider_invoked"] is False
    assert payload["provider_call_ready"] is False


def test_three_node_live_preflight_source_stays_dormant_and_provider_free() -> None:
    paths = [
        ROOT / "app" / "recommendation" / "application" / "three_node_live_preflight.py",
        ROOT / "scripts" / "build_recommendation_three_node_live_preflight.py",
    ]
    forbidden_imports = (
        "app.providers",
        "app.runtime.interface.provider_runtime",
        "app.runtime.application.manager_service",
        "httpx",
        "requests",
        "sqlalchemy",
    )
    forbidden_text = (
        "BuilderSpaceAdapter",
        "AI_BUILDER_TOKEN",
        "FastAPI",
        "APIRouter",
        "Scheduler(",
        "send_notification",
        "recommendation_served=True",
        "live_provider_invoked=True",
        "manager_context_packet_changed=True",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        imports = "\n".join(_absolute_imports(path))
        for prefix in forbidden_imports:
            assert prefix not in imports
        for token in forbidden_text:
            assert token not in text


def _false_activation_flags() -> dict[str, bool]:
    return {
        "runtime_effect_allowed": False,
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "live_provider_used": False,
        "live_provider_invoked": False,
        "live_llm_invoked": False,
        "recommendation_served": False,
        "intake_committed": False,
        "product_readiness_claimed": False,
    }


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
