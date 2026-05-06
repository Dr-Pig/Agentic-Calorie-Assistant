from __future__ import annotations

import json
from pathlib import Path


def test_free_text_manual_target_gate_cli_writes_pass_artifact(tmp_path: Path) -> None:
    from scripts.run_accurate_intake_free_text_manual_target_gate import main

    output_path = tmp_path / "free-text-manual-target-gate.json"

    exit_code = main(["--output", str(output_path)])
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["gate_id"] == "accurate_intake_free_text_manual_target_gate"
    assert artifact["status"] == "pass"
    assert artifact["manual_target_updated"] is True
    assert artifact["unsafe_target_blocked"] is True
    assert artifact["ambiguous_target_blocked"] is True
    assert artifact["meal_mutation_performed"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["blockers"] == []


def test_free_text_manual_target_gate_source_stays_out_of_fooddb_live_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_free_text_manual_target_gate.py").read_text(
        encoding="utf-8"
    )
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "Kimi",
        "GrokFast",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "fooddb_evidence_used = True",
        "private_self_use_approved = True",
    ]

    for fragment in forbidden:
        assert fragment not in source


def test_local_dogfood_inspect_manifest_is_pre_live_gate_compatible(tmp_path: Path) -> None:
    from scripts.manage_accurate_intake_local_dogfood_data import main

    output_path = tmp_path / "local-dogfood-data-hygiene.json"

    exit_code = main(
        [
            "--operation",
            "inspect",
            "--db-path",
            str(tmp_path / "local_dogfood" / "accurate_intake.sqlite3"),
            "--output",
            str(output_path),
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["artifact_type"] == "accurate_intake_local_dogfood_data_hygiene"
    assert artifact["status"] == "pass"
    assert artifact["operation"] == "inspect"
    assert artifact["local_only"] is True
    assert artifact["contains_personal_diet_logs"] is True
    assert artifact["do_not_commit"] is True
    assert artifact["writes_performed"] is False
    assert artifact["import_allowed"] is False
    assert artifact["production_db_used"] is False
    assert artifact["fooddb_truth_updated"] is False
