from __future__ import annotations

import json
from pathlib import Path


def test_context_live_diagnostic_gate_default_writes_review_pack_without_live(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.run_accurate_intake_context_live_diagnostic_gate import main

    monkeypatch.setenv("AI_BUILDER_TOKEN", "token-that-must-not-be-used")
    artifact_dir = tmp_path / "artifacts"
    output_path = tmp_path / "context-live-diagnostic-gate.json"

    exit_code = main(["--artifact-dir", str(artifact_dir), "--output", str(output_path)])

    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert artifact["artifact_type"] == "accurate_intake_context_live_diagnostic_gate"
    assert artifact["status"] == "context_live_diagnostic_gate_ready_without_live_canary"
    assert artifact["review_pack_status"] == "context_live_diagnostic_review_ready_without_live_canary"
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["live_provider_allowed"] is False
    assert artifact["full_matrix_live_probe_required"] is True
    assert artifact["ad_hoc_live_case_selection_allowed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    for path_text in artifact["artifact_paths"].values():
        assert Path(path_text).exists()


def test_context_live_diagnostic_gate_can_require_live_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.run_accurate_intake_context_live_diagnostic_gate import main

    monkeypatch.delenv("AI_BUILDER_TOKEN", raising=False)
    output_path = tmp_path / "context-live-diagnostic-gate.json"

    exit_code = main(
        [
            "--artifact-dir",
            str(tmp_path / "artifacts"),
            "--output",
            str(output_path),
            "--allow-live-provider",
            "--require-live-provider",
        ]
    )

    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert artifact["status"] == "blocked"
    assert artifact["live_provider_allowed"] is True
    assert artifact["live_llm_invoked"] is False
    assert "live_provider_required_but_not_invoked" in artifact["blockers"]
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_context_live_diagnostic_gate_source_stays_out_of_fooddb_truth_and_runtime_mutation() -> None:
    source = Path("scripts/run_accurate_intake_context_live_diagnostic_gate.py").read_text(
        encoding="utf-8"
    )
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "from app.nutrition",
        "import app.nutrition",
        "fooddb_used = True",
        "web_tavily_used = True",
        "mutation_changed = True",
        "manager_context_packet_schema_changed = True",
        "private_self_use_approved = True",
    ]

    for fragment in forbidden:
        assert fragment not in source
