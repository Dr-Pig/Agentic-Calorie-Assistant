from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
)
from app.recommendation.application.three_node_live_provider_gate import (
    LIVE_DIAGNOSTIC_ENV,
    LIVE_DIAGNOSTIC_ENV_VALUE,
    build_recommendation_three_node_live_provider_gate,
)


ROOT = Path(__file__).resolve().parents[1]


def test_live_provider_gate_requires_explicit_grokfast_env() -> None:
    gate = build_recommendation_three_node_live_provider_gate(
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        env={},
    )

    assert gate["live_requested"] is False
    assert gate["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert gate["model_id"] == "grok-4-fast"
    assert gate["accepted_live_env_value"] == LIVE_DIAGNOSTIC_ENV_VALUE
    assert f"live_env_not_enabled:{LIVE_DIAGNOSTIC_ENV}" in gate["blockers"]
    assert gate["live_provider_invoked"] is False
    assert gate["kimi_live_calls_allowed"] is False


def test_live_provider_gate_accepts_only_grokfast_profile_with_env() -> None:
    gate = build_recommendation_three_node_live_provider_gate(
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        env={LIVE_DIAGNOSTIC_ENV: LIVE_DIAGNOSTIC_ENV_VALUE},
    )

    assert gate["status"] == "pass"
    assert gate["live_requested"] is True
    assert gate["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert gate["model_id"] == "grok-4-fast"
    assert gate["blockers"] == []
    assert gate["live_provider_invoked"] is False


def test_live_provider_gate_blocks_kimi_even_when_env_enabled() -> None:
    gate = build_recommendation_three_node_live_provider_gate(
        provider_profile_id=ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
        env={LIVE_DIAGNOSTIC_ENV: LIVE_DIAGNOSTIC_ENV_VALUE},
    )

    assert gate["live_requested"] is True
    assert gate["model_id"] == "kimi-k2.5"
    assert "profile.profile_not_live_diagnostic_allowed" in gate["blockers"]
    assert "profile.kimi_live_calls_forbidden" in gate["blockers"]
    assert "profile.model_not_grok_4_fast" in gate["blockers"]
    assert gate["live_provider_invoked"] is False


def test_live_script_with_live_flag_without_env_writes_blocked_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "recommendation-three-node-live-gate.json"
    env = dict(os.environ)
    env.pop(LIVE_DIAGNOSTIC_ENV, None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_recommendation_three_node_live_diagnostic.py",
            "--live",
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "live_provider_diagnostic_blocked"
    assert artifact["live_requested"] is True
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert f"live_env_not_enabled:{LIVE_DIAGNOSTIC_ENV}" in artifact["blockers"]
    assert artifact["recommendation_served"] is False
    assert artifact["intake_committed"] is False
    assert artifact["activation_flags"]["user_facing_behavior_changed"] is False


def test_live_script_blocks_kimi_profile_before_provider_invocation(tmp_path: Path) -> None:
    output_path = tmp_path / "recommendation-three-node-kimi-blocked.json"
    env = dict(os.environ)
    env[LIVE_DIAGNOSTIC_ENV] = LIVE_DIAGNOSTIC_ENV_VALUE

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_recommendation_three_node_live_diagnostic.py",
            "--live",
            "--provider-profile-id",
            ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "blocked"
    assert artifact["live_requested"] is True
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert "profile.kimi_live_calls_forbidden" in artifact["blockers"]
    assert "profile.model_not_grok_4_fast" in artifact["blockers"]
    assert artifact["provider_gate"]["model_id"] == "kimi-k2.5"


def test_live_script_stays_manual_only() -> None:
    path = ROOT / "scripts" / "run_recommendation_three_node_live_diagnostic.py"
    text = path.read_text(encoding="utf-8")
    assert "BuilderSpaceAdapter" in text
    assert "FastAPI" not in text
    assert "APIRouter" not in text
    assert "Scheduler(" not in text
    assert "send_notification" not in text
    assert "recommendation_served=True" not in text
    assert "manager_context_packet_changed=True" not in text
    assert "--model" not in text
