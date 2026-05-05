from __future__ import annotations

import json
from pathlib import Path

from scripts import run_accurate_intake_pl_ce_artifact_refresh as module


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _payload_for_step(step: module.RefreshStep) -> dict[str, object]:
    if step.step_id == "pl_ce_local_review_gate":
        return {
            "artifact_type": "accurate_intake_pl_ce_local_review_decision_pack",
            "status": "ready_for_human_pl_ce_review",
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
        }
    if step.step_id == "pl_ce_metadata_freshness_pack":
        return {
            "artifact_type": "accurate_intake_pl_ce_metadata_freshness_pack",
            "status": "metadata_freshness_ready_for_pl_ce_local_review",
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
        }
    return {
        "artifact_type": f"fixture_{step.step_id}",
        "status": next(iter(step.expected_statuses)),
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_truth_updated": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


def test_pl_ce_artifact_refresh_runner_orders_runtime_context_before_quality_and_gates(
    tmp_path: Path,
) -> None:
    calls: list[module.RefreshStep] = []

    def fake_run(step: module.RefreshStep) -> module.StepRunResult:
        calls.append(step)
        _write(step.output_path, _payload_for_step(step))
        return module.StepRunResult(returncode=0, stdout="{}", stderr="")

    report = module.run_pl_ce_artifact_refresh(
        artifact_dir=tmp_path / "artifacts",
        run_step=fake_run,
        require_browser_execution=True,
    )

    step_ids = [step["step_id"] for step in report["steps"]]
    assert report["status"] == "pl_ce_artifact_refresh_ready_for_human_review"
    assert report["ready_for_human_pl_ce_review"] is True
    assert report["ready_for_live_diagnostic_decision"] is False
    assert report["ready_for_fdb_integration"] is False
    assert step_ids.index("product_pages_short_term_context_smoke") < step_ids.index(
        "context_quality_pack"
    )
    assert step_ids.index("pl_ce_local_review_gate") < step_ids.index(
        "pl_ce_metadata_freshness_pack"
    )
    context_quality_command = " ".join(
        next(step.command for step in calls if step.step_id == "context_quality_pack")
    )
    assert "--short-term-context-smoke" in context_quality_command
    assert "--require-runtime-trace-input" in context_quality_command
    browser_commands = [
        " ".join(step.command)
        for step in calls
        if step.browser_required
    ]
    assert browser_commands
    assert all("--require-browser-execution" in command for command in browser_commands)


def test_pl_ce_artifact_refresh_runner_blocks_when_browser_step_blocks(tmp_path: Path) -> None:
    def fake_run(step: module.RefreshStep) -> module.StepRunResult:
        if step.step_id == "product_pages_short_term_context_smoke":
            _write(
                step.output_path,
                {
                    "artifact_type": "accurate_intake_product_pages_short_term_context_smoke",
                    "status": "blocked",
                    "browser_executed": False,
                    "live_llm_invoked": False,
                    "web_tavily_used": False,
                    "product_readiness_claimed": False,
                    "private_self_use_approved": False,
                },
            )
            return module.StepRunResult(returncode=1, stdout="{}", stderr="playwright_not_installed")
        _write(step.output_path, _payload_for_step(step))
        return module.StepRunResult(returncode=0, stdout="{}", stderr="")

    report = module.run_pl_ce_artifact_refresh(
        artifact_dir=tmp_path / "artifacts",
        run_step=fake_run,
        require_browser_execution=True,
    )

    assert report["status"] == "blocked"
    assert report["ready_for_human_pl_ce_review"] is False
    assert report["ready_for_live_diagnostic_decision"] is False
    assert report["ready_for_fdb_integration"] is False
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_used"] is False
    assert report["fooddb_truth_updated"] is False
    assert "product_pages_short_term_context_smoke.returncode_1" in report["blockers"]
    failed_step = report["steps"][0]
    assert failed_step["stderr_excerpt"] == "playwright_not_installed"
    assert failed_step["artifact_blockers"] == []


def test_pl_ce_artifact_refresh_runner_blocks_if_local_review_gate_is_not_ready(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_run(step: module.RefreshStep) -> module.StepRunResult:
        calls.append(step.step_id)
        if step.step_id == "pl_ce_local_review_gate":
            _write(
                step.output_path,
                {
                    "artifact_type": "accurate_intake_pl_ce_local_review_decision_pack",
                    "status": "blocked",
                    "missing_evidence": ["browser_shell_smoke"],
                    "ready_for_live_diagnostic_decision": False,
                    "ready_for_fdb_integration": False,
                },
            )
            return module.StepRunResult(returncode=1, stdout="{}", stderr="")
        _write(step.output_path, _payload_for_step(step))
        return module.StepRunResult(returncode=0, stdout="{}", stderr="")

    report = module.run_pl_ce_artifact_refresh(
        artifact_dir=tmp_path / "artifacts",
        run_step=fake_run,
    )

    assert report["status"] == "blocked"
    assert "pl_ce_local_review_gate.unexpected_status:blocked" in report["blockers"]
    failed_step = report["steps"][-1]
    assert failed_step["artifact_blockers"] == []
    assert "pl_ce_metadata_freshness_pack" not in calls


def test_pl_ce_artifact_refresh_runner_blocks_if_metadata_freshness_is_not_ready(
    tmp_path: Path,
) -> None:
    def fake_run(step: module.RefreshStep) -> module.StepRunResult:
        if step.step_id == "pl_ce_metadata_freshness_pack":
            _write(
                step.output_path,
                {
                    "artifact_type": "accurate_intake_pl_ce_metadata_freshness_pack",
                    "status": "blocked",
                    "blockers": ["context_quality_pack.stale_metadata"],
                    "ready_for_live_diagnostic_decision": False,
                    "ready_for_fdb_integration": False,
                },
            )
            return module.StepRunResult(returncode=1, stdout="{}", stderr="")
        _write(step.output_path, _payload_for_step(step))
        return module.StepRunResult(returncode=0, stdout="{}", stderr="")

    report = module.run_pl_ce_artifact_refresh(
        artifact_dir=tmp_path / "artifacts",
        run_step=fake_run,
        fail_fast=False,
    )

    assert report["status"] == "blocked"
    assert "pl_ce_metadata_freshness_pack.returncode_1" in report["blockers"]
    assert "pl_ce_metadata_freshness_pack.unexpected_status:blocked" in report["blockers"]
    failed_step = report["steps"][-1]
    assert failed_step["artifact_blockers"] == ["context_quality_pack.stale_metadata"]
    assert report["ready_for_human_pl_ce_review"] is False


def test_pl_ce_artifact_refresh_runner_defaults_required_browser_output_path(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    captured: dict[str, object] = {}

    def fake_refresh(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "status": module.READY_STATUS,
            "completed_step_count": 20,
            "required_step_count": 20,
            "blockers": [],
        }

    monkeypatch.setattr(module, "run_pl_ce_artifact_refresh", fake_refresh)

    exit_code = module.main([
        "--artifact-dir",
        str(tmp_path / "artifacts"),
        "--require-browser-execution",
    ])
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert captured["require_browser_execution"] is True
    assert str(captured["output_path"]).endswith("accurate_intake_pl_ce_artifact_refresh_required_browser.json")
    assert printed["artifact"].endswith("accurate_intake_pl_ce_artifact_refresh_required_browser.json")


def test_pl_ce_artifact_refresh_runner_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_pl_ce_artifact_refresh.py").read_text(
        encoding="utf-8"
    )
    forbidden = [
        "requests",
        "httpx",
        "urllib",
        "openai",
        "app.providers",
        "Tavily",
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "runtime_truth_allowed = True",
        "fooddb_truth_updated = True",
    ]

    for fragment in forbidden:
        assert fragment not in source
