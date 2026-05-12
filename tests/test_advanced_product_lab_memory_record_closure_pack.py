from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_record_dogfood_summary import (
    build_memory_record_dogfood_summary,
)
from app.advanced_shadow_lab.product_lab_memory_record_holdout import (
    build_memory_record_holdout_report,
    build_memory_record_holdout_turns,
)
from app.advanced_shadow_lab.product_lab_memory_record_integrated_e2e import (
    run_memory_record_integrated_e2e_chain,
)
from app.advanced_shadow_lab.product_lab_memory_record_live_diagnostic import (
    run_memory_record_live_diagnostic,
)
from app.advanced_shadow_lab.product_lab_memory_record_readiness import (
    build_memory_record_readiness_report,
)
from app.advanced_shadow_lab.product_lab_memory_record_session import (
    run_advanced_product_lab_memory_record_session,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (
    build_product_lab_simulated_turns,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


ROOT = Path(__file__).resolve().parents[1]


class FakeDiagnosticProvider:
    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-memory-record-diagnostic", "configured": True}

    async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "diagnostic_notes": "The MemoryRecord integrated lab chain is reviewable.",
            "risk_notes": "Diagnostic only; no outside-lab delivery or mutation.",
            "claim_scope": "diagnostic_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["memory_record_integrated_e2e"],
        }, {"stage": "memory_record_live_diagnostic", "provider": "fake"}


def test_memory_record_closure_pack_aggregates_complete_lab_chain(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_closure_pack import (
        build_memory_record_closure_pack,
    )

    chain = _complete_chain(tmp_path)

    pack = build_memory_record_closure_pack(**chain)

    assert pack["artifact_type"] == "advanced_product_lab_memory_record_closure_pack"
    assert pack["status"] == "pass"
    assert pack["lab_enabled"] is True
    assert pack["lab_product_loop_closed"] is True
    assert pack["mainline_activation_enabled"] is False
    assert pack["self_use_v1_affected"] is False
    assert pack["durable_product_memory_written"] is False
    assert pack["canonical_product_mutation_allowed"] is False
    assert pack["production_scheduler_delivery_allowed"] is False
    assert pack["stage_statuses"] == {
        "memory_record_dogfood_summary": "pass",
        "memory_record_readiness": "pass",
        "integrated_e2e": "pass",
        "provider_contract_diagnostic": "pass",
        "negative_preference_holdout": "pass",
    }
    assert pack["capabilities_closed"] == [
        "long_term_memory",
        "recommendation",
        "rescue",
        "calibration",
        "proactive",
        "chat_surface",
    ]
    assert pack["next_allowed_slices"] == [
        "activation_wall_audit",
        "lab_debt_retirement_plan",
    ]
    assert pack["provider_contract_diagnostic"]["diagnostic_evidence_class"] == (
        "fake_contract"
    )
    assert pack["provider_contract_diagnostic"]["fake_contract_pass"] is True
    assert pack["provider_contract_diagnostic"]["live_grokfast_diagnostic_pass"] is False
    assert pack["provider_contract_diagnostic"]["live_milestone_status"] == (
        "not_satisfied_fake_contract"
    )
    assert "raw_user_utterance" not in json.dumps(pack, ensure_ascii=False)


def test_memory_record_closure_pack_blocks_activation_or_upstream_drift(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_closure_pack import (
        build_memory_record_closure_pack,
    )

    chain = _complete_chain(tmp_path)
    chain["readiness_report"] = {
        **chain["readiness_report"],
        "status": "blocked",
        "blockers": ["memory_record_context_pack_used.missing_or_false"],
    }
    chain["live_diagnostic_artifact"] = {
        **chain["live_diagnostic_artifact"],
        "mainline_activation_enabled": True,
    }

    pack = build_memory_record_closure_pack(**chain)

    assert pack["status"] == "blocked"
    assert pack["lab_product_loop_closed"] is False
    assert pack["next_allowed_slices"] == []
    assert pack["blockers"] == [
        "memory_record_readiness.status_blocked",
        "memory_record_readiness.memory_record_context_pack_used.missing_or_false",
        "provider_contract_diagnostic.mainline_activation_enabled.claim_drift",
    ]


def test_memory_record_closure_pack_cli_writes_artifact(tmp_path: Path) -> None:
    chain = _complete_chain(tmp_path)
    paths = _write_chain(tmp_path, chain)
    output = tmp_path / "closure-pack.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_advanced_product_lab_memory_record_closure_pack.py",
            "--summary-json",
            str(paths["summary"]),
            "--readiness-json",
            str(paths["readiness"]),
            "--integrated-e2e-json",
            str(paths["integrated"]),
            "--live-diagnostic-json",
            str(paths["live"]),
            "--holdout-json",
            str(paths["holdout"]),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout_pack = json.loads(result.stdout)
    file_pack = read_json_artifact(output)
    assert stdout_pack == file_pack
    assert file_pack["status"] == "pass"
    assert file_pack["source_paths"]["integrated_e2e"] == str(paths["integrated"])


def _complete_chain(tmp_path: Path) -> dict[str, object]:
    base_session = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path / "session",
        session_id="closure-pack-session",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    summary = build_memory_record_dogfood_summary(base_session)
    readiness = build_memory_record_readiness_report(summary)
    integrated = run_memory_record_integrated_e2e_chain(
        summary_artifact=summary,
        readiness_report=readiness,
    )
    live = run_memory_record_live_diagnostic(
        integrated_e2e_artifact=integrated,
        provider=FakeDiagnosticProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )
    holdout_session = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path / "holdout-session",
        session_id="closure-pack-holdout",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=[*build_product_lab_simulated_turns(), *build_memory_record_holdout_turns()],
    )
    holdout = build_memory_record_holdout_report(holdout_session)
    return {
        "summary_artifact": summary,
        "readiness_report": readiness,
        "integrated_e2e_artifact": integrated,
        "live_diagnostic_artifact": live,
        "holdout_report": holdout,
    }


def _write_chain(
    tmp_path: Path,
    chain: dict[str, object],
) -> dict[str, Path]:
    paths = {
        "summary": tmp_path / "summary.json",
        "readiness": tmp_path / "readiness.json",
        "integrated": tmp_path / "integrated.json",
        "live": tmp_path / "live.json",
        "holdout": tmp_path / "holdout.json",
    }
    write_json_artifact(paths["summary"], chain["summary_artifact"])
    write_json_artifact(paths["readiness"], chain["readiness_report"])
    write_json_artifact(paths["integrated"], chain["integrated_e2e_artifact"])
    write_json_artifact(paths["live"], chain["live_diagnostic_artifact"])
    write_json_artifact(paths["holdout"], chain["holdout_report"])
    return paths
