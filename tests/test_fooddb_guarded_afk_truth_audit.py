from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_guarded_afk_truth_audit import (
    build_fooddb_guarded_afk_truth_audit,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _tfda_source_payload() -> dict:
    return json.loads(
        Path("app/knowledge/tfda_per100g_source_evidence_tw.json").read_text(encoding="utf-8-sig")
    )


def _exact_card_payload() -> dict:
    return json.loads(Path("app/knowledge/exact_item_cards_tw.json").read_text(encoding="utf-8-sig"))


def test_truth_audit_reports_current_fooddb_boundaries_without_runtime_change() -> None:
    audit = build_fooddb_guarded_afk_truth_audit(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
    )

    assert audit["artifact_type"] == "accurate_intake_fooddb_guarded_afk_truth_audit"
    assert audit["runtime_truth_changed"] is False
    assert audit["stop_gate_status"] == "pass"
    assert audit["summary"]["runtime_common_serving_anchor_count"] == 40
    assert audit["summary"]["tfda_source_evidence_only_count"] == 848
    assert audit["summary"]["semantic_only_basket_count"] == 4
    assert audit["summary"]["exact_card_count"] == 5
    assert audit["summary"]["blocker_count"] == 0
    assert audit["non_claims"] == [
        "no_product_loop_integration",
        "no_manager_context_change",
        "no_packetizer_format_change",
        "no_live_provider_call",
        "no_readiness_claim",
    ]


def test_truth_audit_blocks_runtime_anchor_missing_required_metadata() -> None:
    payload = _small_anchor_payload()
    runtime_anchor = next(item for item in payload["anchors"] if item.get("runtime_truth_allowed") is True)
    runtime_anchor.pop("portion_basis", None)

    audit = build_fooddb_guarded_afk_truth_audit(
        small_anchor_payload=payload,
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
    )

    assert audit["stop_gate_status"] == "blocked"
    assert "runtime_anchor_missing_required_metadata" in audit["blockers"]
    failed = [
        item for item in audit["runtime_anchor_audit"] if item["anchor_id"] == runtime_anchor["anchor_id"]
    ][0]
    assert failed["status"] == "blocked"
    assert failed["missing_required_fields"] == ["portion_basis"]


def test_truth_audit_blocks_tfda_per100g_runtime_estimate_leakage() -> None:
    tfda = _tfda_source_payload()
    tfda["records"][0]["runtime_estimate_allowed"] = True

    audit = build_fooddb_guarded_afk_truth_audit(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=tfda,
        exact_card_payload=_exact_card_payload(),
    )

    assert audit["stop_gate_status"] == "blocked"
    assert "tfda_per100g_runtime_estimate_leakage" in audit["blockers"]
    assert audit["source_evidence_audit"]["tfda_per100g_violation_count"] == 1


def test_truth_audit_blocks_tfda_source_ref_role_leakage_from_runtime_anchor() -> None:
    payload = _small_anchor_payload()
    runtime_anchor = next(
        item for item in payload["anchors"] if item.get("anchor_id") == "custom_drink_boba_milk_tea"
    )
    runtime_anchor["source_refs"][0]["external_source_role"] = "common_serving_anchor"

    audit = build_fooddb_guarded_afk_truth_audit(
        small_anchor_payload=payload,
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
    )

    assert audit["stop_gate_status"] == "blocked"
    assert "runtime_anchor_source_ref_role_leakage" in audit["blockers"]


def test_truth_audit_manager_evidence_catalog_is_compact_and_runtime_only() -> None:
    audit = build_fooddb_guarded_afk_truth_audit(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
    )

    catalog = audit["manager_evidence_catalog"]
    assert catalog["claim_scope"] == "compact_runtime_evidence_catalog_not_raw_source"
    assert catalog["raw_source_rows_included"] is False
    assert catalog["candidate_only_records_included"] is False
    assert len(catalog["runtime_common_serving_anchors"]) == 40
    for anchor in catalog["runtime_common_serving_anchors"]:
        assert set(anchor) == {
            "anchor_id",
            "canonical_name",
            "aliases",
            "dish_type",
            "kcal_point",
            "kcal_range",
            "serving_basis",
            "portion_basis",
            "variance_level",
            "followup_hints",
            "runtime_usage_boundary",
        }


def test_truth_audit_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "truth_audit.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_guarded_afk_truth_audit import main

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["stop_gate_status"] == "pass"
    assert artifact["summary"]["runtime_common_serving_anchor_count"] == 40
