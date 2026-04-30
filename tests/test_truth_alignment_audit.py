from __future__ import annotations

from scripts.active_code_inventory import build_active_code_inventory
from scripts.truth_alignment_audit import build_truth_alignment_audit


def test_truth_alignment_audit_has_no_archive_focus_modules() -> None:
    report = build_truth_alignment_audit()
    assert report["short_audit_notes"]["archive_surface_count"] == 0


def test_truth_alignment_audit_flags_builderspace_as_workaround_residue() -> None:
    report = build_truth_alignment_audit()
    builderspace = report["short_audit_notes"]["app/providers/builderspace_adapter.py"]

    assert builderspace is not None
    assert builderspace["classification"] == "historical_workaround_residue"
    assert builderspace["recommended_action"] == "keep_and_deflate"


def test_active_code_inventory_has_no_unmapped_active_python_files() -> None:
    report = build_active_code_inventory()
    assert not report["unmapped_files"]
