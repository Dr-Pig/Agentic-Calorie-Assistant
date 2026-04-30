from __future__ import annotations

import copy

from scripts.audit_wave1_phase_b2_local_p0_closure import audit_phase_b2_local_p0_closure
from scripts.build_wave1_phase_b2_evidence_synthesis_smoke import build_phase_b2_synthetic_smoke_report


def _b1_green_handoff_snapshot() -> dict[str, object]:
    return {
        "b1_gate_scope": "Phase B-1 minimal tool-loop full natural-probe",
        "smoke_artifact": "artifacts/phase_b1_full_smoke.json",
        "readiness_artifact": "artifacts/phase_b1_readiness.json",
        "ready_for_phase_b1_implementation": True,
        "blockers": [],
        "not_claiming": "whole Wave 1 completion",
    }


def _report() -> dict[str, object]:
    return build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())


def test_b2_local_p0_closure_audit_passes_current_runtime_backed_report() -> None:
    audit = audit_phase_b2_local_p0_closure(_report())

    assert audit["passed"] is True
    assert audit["blockers"] == []
    assert audit["runtime_web_activation_approved"] is False
    assert audit["official_runtime_backed_case_count"] == 10
    assert audit["local_evidence_provenance"]["passed"] is True
    assert audit["owner_lineage"]["passed"] is True


def test_b2_local_p0_closure_audit_blocks_synthetic_trusted_database_wording() -> None:
    report = _report()
    entry = report["trusted_source_manifest"]["entries"][0]
    entry["scope"] = "B-2 synthetic trusted database fixture"

    audit = audit_phase_b2_local_p0_closure(report)

    assert audit["passed"] is False
    assert any(item["code"] == "trusted_source_manifest_synthetic_wording" for item in audit["blockers"])


def test_b2_local_p0_closure_audit_blocks_missing_runtime_owner_lineage() -> None:
    report = _report()
    case = copy.deepcopy(report["cases"][0])
    case.pop("packet_consumption")
    report["cases"][0] = case

    audit = audit_phase_b2_local_p0_closure(report)

    assert audit["passed"] is False
    assert any(item["code"] == "runtime_owner_lineage_incomplete" for item in audit["blockers"])


def test_b2_local_p0_closure_audit_blocks_source_selection_semantic_owner() -> None:
    report = _report()
    report["cases"][0]["source_selection"]["decides_logged_or_draft"] = True

    audit = audit_phase_b2_local_p0_closure(report)

    assert audit["passed"] is False
    assert any(item["code"] == "source_selection_semantic_owner_forbidden" for item in audit["blockers"])
