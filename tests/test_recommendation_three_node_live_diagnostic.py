from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_TARGET_REASONING_PROFILE_ID
from app.recommendation.application.three_node_live_diagnostic import (
    FakeRecommendationThreeNodeDiagnosticProvider,
    run_recommendation_three_node_live_diagnostic,
)
from app.recommendation.application.three_node_live_preflight import (
    build_recommendation_three_node_live_preflight,
)


ROOT = Path(__file__).resolve().parents[1]


def test_three_node_live_diagnostic_runs_fake_provider_contract_without_serving() -> None:
    preflight = build_recommendation_three_node_live_preflight()

    artifact = run_recommendation_three_node_live_diagnostic(
        preflight=preflight,
        provider=FakeRecommendationThreeNodeDiagnosticProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["artifact_type"] == "recommendation_three_node_live_diagnostic"
    assert artifact["status"] == "pass"
    assert artifact["diagnostic_only"] is True
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["provider_profile_id"] == preflight["provider_profile_id"]
    assert artifact["fixed_case_matrix_used"] is True
    assert artifact["semantic_quality_claimed"] is False
    assert artifact["node_status_by_physical_node"] == {
        "recommendation_planning": "pass",
        "offer_synthesis": "pass",
    }
    assert artifact["node_provider_used_by_physical_node"] == {
        "recommendation_planning": False,
        "offer_synthesis": False,
    }
    assert artifact["candidate_guard"]["allowed_candidate_ids"] == ["golden-1"]
    assert artifact["deterministic_guard_replayed"] is True
    assert artifact["recommendation_response"]["candidate_id"] == "golden-1"
    assert artifact["recommendation_response"]["recommendation_served"] is False
    assert artifact["activation_flags"] == _false_activation_flags()
    assert "not_recommendation_serving" in artifact["non_claims"]


def test_three_node_live_diagnostic_blocks_bad_offer_claims() -> None:
    preflight = build_recommendation_three_node_live_preflight()

    artifact = run_recommendation_three_node_live_diagnostic(
        preflight=preflight,
        provider=_BadOfferProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert "offer_synthesis.output.recommendation_served_not_allowed" in artifact["blockers"]
    assert "offer_synthesis.output.intake_commit_requested_not_allowed" in artifact["blockers"]
    assert artifact["recommendation_response"] is None
    assert artifact["activation_flags"] == _false_activation_flags()


def test_three_node_live_diagnostic_blocks_blocked_preflight_before_provider_invocation() -> None:
    preflight = build_recommendation_three_node_live_preflight(
        provider_profile_id=ADVANCED_LAB_TARGET_REASONING_PROFILE_ID
    )
    provider = _CountingProvider()

    artifact = run_recommendation_three_node_live_diagnostic(
        preflight=preflight,
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "preflight.status_not_pass",
        "profile.profile_not_live_diagnostic_allowed",
        "profile.kimi_live_calls_forbidden",
    ]
    assert provider.calls == []
    assert artifact["node_outputs"] == []
    assert artifact["activation_flags"] == _false_activation_flags()


def test_three_node_live_diagnostic_script_writes_fake_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "recommendation-three-node-live-diagnostic.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_recommendation_three_node_live_diagnostic.py",
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["live_provider_invoked"] is False
    assert artifact["recommendation_served"] is False


def test_three_node_live_diagnostic_source_stays_manual_and_provider_free() -> None:
    paths = [
        ROOT / "app" / "recommendation" / "application" / "three_node_diagnostic_fake_provider.py",
        ROOT / "app" / "recommendation" / "application" / "three_node_diagnostic_policy.py",
        ROOT / "app" / "recommendation" / "application" / "three_node_live_diagnostic.py",
        ROOT / "scripts" / "run_recommendation_three_node_live_diagnostic.py",
    ]
    forbidden_imports = (
        "app.providers",
        "app.runtime.interface.provider_runtime",
        "app.runtime.application.manager_service",
        "sqlalchemy",
    )
    forbidden_text = (
        "BuilderSpaceAdapter",
        "FastAPI",
        "APIRouter",
        "Scheduler(",
        "send_notification",
        "recommendation_served=True",
        "manager_context_packet_changed=True",
        "--model",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        imports = "\n".join(_absolute_imports(path))
        for prefix in forbidden_imports:
            assert prefix not in imports
        for token in forbidden_text:
            assert token not in text


class _BadOfferProvider(FakeRecommendationThreeNodeDiagnosticProvider):
    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        output, trace = await super().complete_with_trace(**kwargs)
        if kwargs["user_payload"]["physical_node"] == "offer_synthesis":
            output["recommendation_response_result"]["recommendation_served"] = True
            output["recommendation_response_result"]["intake_commit_requested"] = True
        return output, trace


class _CountingProvider(FakeRecommendationThreeNodeDiagnosticProvider):
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.calls.append(str(kwargs["user_payload"]["physical_node"]))
        return await super().complete_with_trace(**kwargs)


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
