from __future__ import annotations

import json
from pathlib import Path

from scripts import build_product_pages_browser_gate_placeholders


ROOT = Path(__file__).resolve().parents[1]


def test_build_placeholders_writes_expected_fast_pass_artifacts(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path.parent / "p0"
    monkeypatch.setattr(build_product_pages_browser_gate_placeholders, "ROOT", root)

    report = build_product_pages_browser_gate_placeholders.build_placeholders(
        mode="fast_pass",
        reason="non_shell_surface_currentshell",
    )

    browser_smoke = json.loads(
        (root / "artifacts/accurate_intake_product_pages_browser_smoke_ci.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["mode"] == "fast_pass"
    assert browser_smoke["status"] == "skipped"
    assert browser_smoke["reason"] == "non_shell_surface_currentshell"
    assert (root / "artifacts/product_pages_visual_qa_ci").exists()
    canonical_current_metadata = (
        root
        / "artifacts/accurate_intake_current_shell_compatibility_current_metadata_freshness_pack_ci.json"
    )
    canonical_serial_handoff = (
        root
        / "artifacts/accurate_intake_current_shell_compatibility_serial_handoff_ci.json"
    )
    canonical_product_pages_flow = (
        root
        / "artifacts/accurate_intake_current_shell_compatibility_product_pages_self_use_flow_gate_ci.json"
    )
    canonical_browser_activation = (
        root
        / "artifacts/accurate_intake_current_shell_compatibility_browser_activation_evidence_gate_ci.json"
    )
    legacy_current_metadata = (
        root / "artifacts/accurate_intake_pl_ce_current_metadata_freshness_pack_ci.json"
    )
    legacy_serial_handoff = root / "artifacts/accurate_intake_pl_ce_serial_handoff_ci.json"
    legacy_product_pages_flow = (
        root / "artifacts/accurate_intake_pl_ce_product_pages_self_use_flow_gate_ci.json"
    )
    legacy_browser_activation = (
        root / "artifacts/accurate_intake_pl_ce_browser_activation_evidence_gate_ci.json"
    )
    assert canonical_current_metadata.exists()
    assert canonical_serial_handoff.exists()
    assert canonical_product_pages_flow.exists()
    assert canonical_browser_activation.exists()
    assert not legacy_current_metadata.exists()
    assert not legacy_serial_handoff.exists()
    assert not legacy_product_pages_flow.exists()
    assert not legacy_browser_activation.exists()


def test_build_placeholders_writes_blocked_upstream_status(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path.parent / "p1"
    monkeypatch.setattr(build_product_pages_browser_gate_placeholders, "ROOT", root)

    build_product_pages_browser_gate_placeholders.build_placeholders(
        mode="blocked_upstream",
        reason="product_pages_full_run_failed",
    )

    activation_manifest = json.loads(
        (
            root
            / "artifacts/accurate_intake_current_shell_compatibility_activation_review_manifest_ci.json"
        ).read_text(encoding="utf-8")
    )
    assert activation_manifest["status"] == "blocked_upstream"
