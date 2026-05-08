from __future__ import annotations

import importlib
import json
from pathlib import Path

from scripts.build_accurate_intake_rt14a_live_ladder_foundation_gate import (
    build_rt14a_live_ladder_foundation_gate,
)


def _build_fake_foundation_report(tmp_path: Path) -> dict:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    return module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )


def test_rt14a_live_ladder_foundation_gate_passes_for_fake_foundation_report(tmp_path: Path) -> None:
    source = _build_fake_foundation_report(tmp_path)

    artifact = build_rt14a_live_ladder_foundation_gate(
        live_diagnostic_artifact=source,
    )

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt14a_provider_health_schema_live_foundation"
    assert artifact["pass_type"] == "contract"
    assert artifact["summary"]["required_stage_ids"] == [
        "provider_health_smoke",
        "schema_contract_probe",
    ]
    assert artifact["summary"]["passed_stage_ids"] == [
        "provider_health_smoke",
        "schema_contract_probe",
    ]
    assert artifact["summary"]["non_claim_flags_preserved"] is True


def test_rt14a_live_ladder_foundation_gate_blocks_schema_probe_failure(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    class SchemaFailingProvider:
        def __init__(self) -> None:
            self.calls = 0

        def readiness(self) -> dict[str, object]:
            return {"provider": "schema-fail", "configured": True}

        async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
            self.calls += 1
            if self.calls == 1:
                return module.ScriptedAccurateIntakeLiveProvider()._entry_decision(), {"stage": "health"}  # noqa: SLF001
            return {"intent": "log_meal"}, {"stage": "schema"}

    source = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=SchemaFailingProvider(),
        provider_mode="fake_schema_contract_test",
        live_invoked=False,
    )

    artifact = build_rt14a_live_ladder_foundation_gate(
        live_diagnostic_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "stage_not_pass:schema_contract_probe" in artifact["blockers"]
    assert "foundation_failure_family:schema_contract_blocked" in artifact["blockers"]


def test_rt14a_live_ladder_foundation_gate_cli_writes_json(tmp_path: Path) -> None:
    source = _build_fake_foundation_report(tmp_path)
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "accurate_intake_rt14a_live_ladder_foundation_gate.json"

    from scripts.build_accurate_intake_rt14a_live_ladder_foundation_gate import main

    exit_code = main(
        [
            "--source-artifact",
            str(source_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "accurate_intake_rt14a_live_ladder_foundation_gate"
    assert payload["status"] == "pass"
