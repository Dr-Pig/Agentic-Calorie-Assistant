from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/quality/ACCURATE_INTAKE_RAKE_EVIDENCE_TRACK_SCOPE.md")


def test_rake_intake_evidence_scope_locks_track_ownership_and_boundaries() -> None:
    content = DOC_PATH.read_text(encoding="utf-8-sig")

    assert "RAKE Intake Evidence Track" in content
    assert "`FoodDB` remains an independent truth-owner track." in content
    assert "`CurrentShell` consumes this evidence through owner lanes such as `ManagerRuntime`, `AppShell`, and `SharedCurrentShell`." in content
    assert "FoodDB retrieval/ranking" in content
    assert "tool-calling evidence seam" in content
    assert "WebSearch candidate evidence" in content
    assert "does not own Webshell" in content
    assert "does not own Product Loop" in content
    assert "does not own ManagerContextPacket" in content
    assert "no runtime mutation authority" in content


def test_rake_intake_evidence_scope_maps_micro_suites_and_activation_order() -> None:
    content = DOC_PATH.read_text(encoding="utf-8-sig")

    assert "B1-001" in content
    assert "B1-004" in content
    assert "B1-005" in content
    assert "FoodEvidenceIndexPort" in content
    assert "FoodEvidenceRecallPacket" in content
    assert "deterministic FoodDB first" in content
    assert "GrokFast diagnostic after deterministic closure" in content
    assert "WebSearch after local FoodDB packet seam" in content
