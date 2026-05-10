from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_live_bundle_inputs_feed_existing_bundle_runner(tmp_path: Path) -> None:
    from app.advanced_shadow_lab.live_bundle_inputs import write_live_bundle_inputs
    from scripts import run_advanced_shadow_lab_live_bundle as runner

    bundle_inputs = write_live_bundle_inputs(tmp_path / "inputs")
    output = tmp_path / "advanced_shadow_comparison.json"

    exit_code = runner.main(
        [
            "--memory-dogfood-replay-review",
            str(bundle_inputs["memory_review_path"]),
            "--chain-payload",
            str(bundle_inputs["chain_payload_path"]),
            "--artifact-dir",
            str(tmp_path / "intermediate"),
            "--output",
            str(output),
        ]
    )

    terminal = json.loads(output.read_text(encoding="utf-8"))
    preflight = json.loads(bundle_inputs["preflight_path"].read_text(encoding="utf-8"))

    assert exit_code == 0
    assert terminal["status"] == "pass"
    assert terminal["live_diagnostic_signals"]["recommendation_copy_live_diagnostic"][
        "output_guard_status"
    ] == "pass"
    assert terminal["live_diagnostic_signals"]["rescue_copy_live_diagnostic"][
        "output_guard_status"
    ] == "pass"
    assert terminal["live_diagnostic_signals"]["proactive_copy_live_diagnostic"][
        "output_guard_status"
    ] == "pass"
    assert preflight["artifact_type"] == "advanced_shadow_live_bundle_input_preflight"
    assert preflight["status"] == "pass"
    assert preflight["input_artifacts"] == {
        "memory_review": "runtime_lab_memory_dogfood_replay_review",
        "chain_payload": "advanced_shadow_live_bundle_chain_payload",
    }
    assert preflight["live_provider_invoked"] is False
    assert preflight["product_readiness_claimed"] is False
    assert preflight["user_facing_behavior_changed"] is False


def test_live_bundle_inputs_preflight_reports_live_gate_without_secrets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.advanced_shadow_lab.live_bundle_inputs import build_live_bundle_preflight

    monkeypatch.setenv("AI_BUILDER_TOKEN", "secret-token-that-must-not-leak")
    monkeypatch.setenv("BUILDERSPACE_MANAGER_MODEL", "legacy-env-model-not-used")
    monkeypatch.delenv("ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC", raising=False)

    preflight = build_live_bundle_preflight(
        provider_mode="live",
        allow_live_provider=True,
    )

    serialized = json.dumps(preflight, ensure_ascii=False)
    assert preflight["status"] == "blocked"
    assert preflight["blockers"] == ["live_gate_not_enabled"]
    assert preflight["environment_presence"]["AI_BUILDER_TOKEN"] is True
    assert preflight["environment_presence"]["BUILDERSPACE_MANAGER_MODEL"] is True
    assert preflight["environment_presence"][
        "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
    ] is False
    assert "secret-token-that-must-not-leak" not in serialized
    assert "legacy-env-model-not-used" not in serialized
    assert preflight["live_provider_invoked"] is False
    assert preflight["provider_specific_product_semantics_allowed"] is False


def test_live_bundle_input_builder_script_writes_runner_inputs_without_live_call(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "inputs"
    env = dict(os.environ)
    env["AI_BUILDER_TOKEN"] = "script-secret-that-must-not-leak"
    env.pop("ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC", None)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_advanced_shadow_lab_live_bundle_inputs.py"),
            "--output-dir",
            str(output_dir),
            "--provider-mode",
            "live",
            "--allow-live-provider",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "script-secret-that-must-not-leak" not in result.stdout
    memory_review = json.loads(
        (output_dir / "memory_dogfood_replay_review.json").read_text(
            encoding="utf-8"
        )
    )
    chain_payload = json.loads(
        (output_dir / "chain_payload.json").read_text(encoding="utf-8")
    )
    preflight = json.loads(
        (output_dir / "live_bundle_input_preflight.json").read_text(
            encoding="utf-8"
        )
    )

    assert memory_review["status"] == "pass"
    assert chain_payload["artifact_type"] == "advanced_shadow_live_bundle_chain_payload"
    assert preflight["status"] == "blocked"
    assert preflight["blockers"] == ["live_gate_not_enabled"]
    assert preflight["live_provider_invoked"] is False
    assert preflight["mainline_runtime_connected"] is False


def test_live_bundle_input_builder_does_not_import_test_or_runtime_surfaces() -> None:
    module_source = (ROOT / "app" / "advanced_shadow_lab" / "live_bundle_inputs.py").read_text(
        encoding="utf-8-sig"
    )
    script_source = (
        ROOT / "scripts" / "build_advanced_shadow_lab_live_bundle_inputs.py"
    ).read_text(encoding="utf-8-sig")

    for source in (module_source, script_source):
        assert "tests." not in source
        assert "tests\\" not in source
        assert "app.routes" not in source
        assert "app.database" not in source
        assert "app.models" not in source
        assert "FastAPI" not in source
        assert "APIRouter" not in source
        assert "send_notification" not in source
        assert "create_engine" not in source
        assert "ManagerContextPacket" not in source
