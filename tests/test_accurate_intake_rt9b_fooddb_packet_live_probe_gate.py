from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_manager_packet_smoke import (  # noqa: E402
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_retrieval_policy import (  # noqa: E402
    build_runtime_retrieval_records_from_small_anchor_payload,
)
from app.nutrition.application.grokfast_fooddb_packet_smoke import (  # noqa: E402
    build_fixture_manager_outputs,
    build_grokfast_fooddb_packet_diagnostic,
)
from scripts.build_accurate_intake_rt9b_fooddb_packet_live_probe_gate import (  # noqa: E402
    build_rt9b_fooddb_packet_live_probe_gate,
)


def _build_live_fooddb_packet_smoke_artifact() -> dict:
    payload = json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    packet_artifact = build_fooddb_manager_packet_smoke(retrieval_records=records)
    artifact = build_grokfast_fooddb_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=build_fixture_manager_outputs(packet_artifact=packet_artifact),
        live_provider_used=True,
    )
    return artifact


def test_rt9b_fooddb_packet_live_probe_gate_passes_for_live_packet_smoke_shape() -> None:
    source = _build_live_fooddb_packet_smoke_artifact()

    artifact = build_rt9b_fooddb_packet_live_probe_gate(
        live_packet_artifact=source,
    )

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt9b_fooddb_packet_live_probe"
    assert artifact["summary"]["required_provider_profile_id"] == (
        "builderspace-grok-4-fast-fooddb-packet-smoke"
    )
    assert artifact["summary"]["non_claim_flags_preserved"] is True


def test_rt9b_fooddb_packet_live_probe_gate_blocks_non_live_artifact() -> None:
    source = _build_live_fooddb_packet_smoke_artifact()
    source["live_provider_used"] = False

    artifact = build_rt9b_fooddb_packet_live_probe_gate(
        live_packet_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "live_provider_not_used" in artifact["blockers"]


def test_rt9b_fooddb_packet_live_probe_gate_blocks_missing_case_coverage() -> None:
    source = _build_live_fooddb_packet_smoke_artifact()
    source["cases"] = source["cases"][:-1]
    source["summary"]["case_count"] = len(source["cases"])
    source["summary"]["pass_count"] = len(source["cases"])

    artifact = build_rt9b_fooddb_packet_live_probe_gate(
        live_packet_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "unexpected_case_inventory" in artifact["blockers"]
    assert "summary_case_count_mismatch" in artifact["blockers"]


def test_rt9b_fooddb_packet_live_probe_gate_cli_writes_json(tmp_path: Path) -> None:
    source = _build_live_fooddb_packet_smoke_artifact()
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "accurate_intake_rt9b_fooddb_packet_live_probe_gate.json"

    from scripts.build_accurate_intake_rt9b_fooddb_packet_live_probe_gate import main

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
    assert payload["artifact_type"] == "accurate_intake_rt9b_fooddb_packet_live_probe_gate"
    assert payload["status"] == "pass"
