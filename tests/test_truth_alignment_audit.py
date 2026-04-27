from __future__ import annotations

from scripts.active_code_inventory import build_active_code_inventory
from scripts.truth_alignment_audit import build_truth_alignment_audit


def test_truth_alignment_audit_flags_rescue_proposal_as_premature_active() -> None:
    report = build_truth_alignment_audit()
    rescue = report["short_audit_notes"]["app/rescue/application/proposal.py"]

    assert rescue is not None
    assert rescue["classification"] == "later_wave_premature_active"
    assert rescue["recommended_action"] == "deactivate_from_active_wiring"


def test_truth_alignment_audit_flags_builderspace_as_workaround_residue() -> None:
    report = build_truth_alignment_audit()
    builderspace = report["short_audit_notes"]["app/providers/builderspace_adapter.py"]

    assert builderspace is not None
    assert builderspace["classification"] == "historical_workaround_residue"
    assert builderspace["recommended_action"] == "keep_and_deflate"


def test_active_code_inventory_has_no_unmapped_active_python_files() -> None:
    report = build_active_code_inventory()
    assert not report["unmapped_files"]
