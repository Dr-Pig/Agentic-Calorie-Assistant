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
    assert audit["official_runtime_backed_case_count"] >= 15
    assert audit["local_evidence_provenance"]["passed"] is True
    assert audit["owner_lineage"]["passed"] is True


def test_b2_local_p0_closure_report_covers_approved_local_case_law() -> None:
    report = _report()
    case_ids = {case["case_id"] for case in report["cases"]}
    seed_names = {seed["food_name"] for seed in report["minimal_db_seed_manifest"]["seeds"]}

    assert {
        "B2-011",
        "B2-012",
        "B2-013",
        "B2-014",
        "B2-015",
    }.issubset(case_ids)
    assert {
        "\u5bb6\u5e38\u83dc",
        "\u9ebb\u8fa3\u71d9",
        "\u9ebb\u8fa3\u81ed\u8c46\u8150",
        "\u9e7d\u9165\u96de",
        "\u751c\u4e0d\u8fa3",
        "\u7c73\u8840",
        "\u56db\u5b63\u8c46",
    }.issubset(seed_names)

    home = next(case for case in report["cases"] if case["case_id"] == "B2-011")
    hotpot = next(case for case in report["cases"] if case["case_id"] == "B2-012")
    spicy_tofu = next(case for case in report["cases"] if case["case_id"] == "B2-013")
    salty_item = next(case for case in report["cases"] if case["case_id"] == "B2-014")
    salty_listed = next(case for case in report["cases"] if case["case_id"] == "B2-015")

    assert home["manager_pass_2"]["item_results"][0]["final_mapping"]["external_outcome"] == "draft"
    assert hotpot["manager_pass_2"]["item_results"][0]["final_mapping"]["external_outcome"] == "draft"
    assert spicy_tofu["manager_pass_2"]["item_results"][0]["final_mapping"]["external_outcome"] == "logged"
    assert salty_item["manager_pass_2"]["item_results"][0]["final_mapping"]["external_outcome"] == "logged"
    assert all(
        item["final_mapping"]["external_outcome"] == "logged"
        for item in salty_listed["manager_pass_2"]["item_results"]
    )
    assert all(
        item["evidence_used"]
        for item in salty_listed["manager_pass_2"]["item_results"]
    )


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
