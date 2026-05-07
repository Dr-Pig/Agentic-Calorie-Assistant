from __future__ import annotations

import json
from pathlib import Path

from scripts import build_product_pages_browser_gate_placeholders


ROOT = Path(__file__).resolve().parents[1]


def test_build_placeholders_writes_expected_fast_pass_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(build_product_pages_browser_gate_placeholders, "ROOT", tmp_path)

    report = build_product_pages_browser_gate_placeholders.build_placeholders(
        mode="fast_pass",
        reason="non_shell_surface_currentshell",
    )

    browser_smoke = json.loads(
        (tmp_path / "artifacts/accurate_intake_product_pages_browser_smoke_ci.json").read_text(encoding="utf-8")
    )
    assert report["mode"] == "fast_pass"
    assert browser_smoke["status"] == "skipped"
    assert browser_smoke["reason"] == "non_shell_surface_currentshell"
    assert (tmp_path / "artifacts/product_pages_visual_qa_ci").exists()


def test_build_placeholders_writes_blocked_upstream_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(build_product_pages_browser_gate_placeholders, "ROOT", tmp_path)

    build_product_pages_browser_gate_placeholders.build_placeholders(
        mode="blocked_upstream",
        reason="product_pages_full_run_failed",
    )

    activation_manifest = json.loads(
        (tmp_path / "artifacts/accurate_intake_pl_ce_activation_review_manifest_ci.json").read_text(
            encoding="utf-8"
        )
    )
    assert activation_manifest["status"] == "blocked_upstream"
