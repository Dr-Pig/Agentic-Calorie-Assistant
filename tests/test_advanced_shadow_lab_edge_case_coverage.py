from __future__ import annotations


def test_edge_case_coverage_contract_maps_domains_without_semantic_authority() -> None:
    from app.advanced_shadow_lab.edge_case_coverage import (
        load_edge_case_coverage_contract,
    )

    artifact = load_edge_case_coverage_contract()

    assert artifact["artifact_type"] == "advanced_shadow_edge_case_coverage_contract"
    assert artifact["status"] == "pass"
    assert artifact["coverage_role"] == "evidence_index_not_product_semantic_authority"
    assert artifact["new_report_family_created"] is False
    assert artifact["live_diagnostics_required"] is False
    assert artifact["raw_keyword_semantic_oracle_allowed"] is False
    assert artifact["required_domains"] == [
        "long_term_memory",
        "recommendation",
        "rescue",
        "proactive",
        "chat_ux_packet",
    ]
    assert artifact["missing_domains"] == []
    assert artifact["domain_summary"] == {
        "chat_ux_packet": {"covered_count": 1},
        "long_term_memory": {"covered_count": 2},
        "proactive": {"covered_count": 2},
        "recommendation": {"covered_count": 2},
        "rescue": {"covered_count": 2},
    }
    for entry in artifact["coverage_entries"]:
        assert entry["claim_boundary"] == "non_claim"
        assert entry["raw_keyword_semantic_oracle_allowed"] is False
        assert entry["product_contract_refs"]
        assert entry["trace_fields"]
        assert entry["guard_or_rubric_refs"]


def test_edge_case_coverage_contract_maps_advanced_ux_journeys_without_readiness_claim() -> None:
    from app.advanced_shadow_lab.edge_case_coverage import (
        load_edge_case_coverage_contract,
    )

    artifact = load_edge_case_coverage_contract()

    assert artifact["ux_acceptance_role"] == (
        "acceptance_map_not_product_readiness_authority"
    )
    assert artifact["ux_acceptance_summary"] == {
        "required_journey_ids": ["F", "F2", "I", "L", "M", "N"],
        "mapped_journey_count": 6,
        "missing_journey_ids": [],
        "existing_shadow_chain_mapped_count": 6,
        "gap_requires_next_slice_count": 0,
        "stale_next_slice_journey_ids": [],
        "closure_next_build_slice": "advanced_capability_gap_review",
        "mapped_chain_closure_status": "closed_for_gap_review",
        "new_report_family_created": False,
        "mainline_activation_allowed": False,
    }
    assert [entry["journey_id"] for entry in artifact["ux_acceptance_entries"]] == [
        "F",
        "F2",
        "I",
        "L",
        "M",
        "N",
    ]
    for entry in artifact["ux_acceptance_entries"]:
        assert entry["claim_boundary"] == "non_claim"
        assert entry["mainline_activation_allowed"] is False
        assert entry["product_contract_refs"]
        assert entry["existing_shadow_artifacts"]
        assert entry["required_trace_fields"]
        assert entry["acceptance_status"] in {
            "existing_shadow_chain_mapped",
            "gap_requires_next_slice",
        }
        assert entry["next_build_slice"]


def test_edge_case_coverage_blocks_orphan_ux_acceptance_entries() -> None:
    from app.advanced_shadow_lab.edge_case_coverage import (
        load_edge_case_coverage_contract,
        validate_edge_case_coverage_contract,
    )

    artifact = load_edge_case_coverage_contract()
    contract = dict(artifact["source_contract"])
    entries = [dict(entry) for entry in contract["ux_acceptance_entries"]]
    entries[0]["existing_shadow_artifacts"] = []
    entries[0]["claim_boundary"] = "product_readiness"
    entries[0]["mainline_activation_allowed"] = True
    contract["ux_acceptance_entries"] = entries

    blocked = validate_edge_case_coverage_contract(contract)

    assert blocked["status"] == "blocked"
    assert "ux_acceptance[F].existing_shadow_artifacts_missing" in blocked["blockers"]
    assert "ux_acceptance[F].claim_boundary_not_non_claim" in blocked["blockers"]
    assert "ux_acceptance[F].mainline_activation_allowed" in blocked["blockers"]


def test_edge_case_coverage_blocks_stale_gap_and_next_slice_pointers() -> None:
    from app.advanced_shadow_lab.edge_case_coverage import (
        load_edge_case_coverage_contract,
        validate_edge_case_coverage_contract,
    )

    artifact = load_edge_case_coverage_contract()
    contract = dict(artifact["source_contract"])
    entries = [dict(entry) for entry in contract["ux_acceptance_entries"]]
    entries[0]["acceptance_status"] = "gap_requires_next_slice"
    entries[0]["next_build_slice"] = "rescue_missing_slice"
    entries[1]["next_build_slice"] = "memory_review_forget_confirmation_shadow"
    contract["ux_acceptance_entries"] = entries

    blocked = validate_edge_case_coverage_contract(contract)

    assert blocked["status"] == "blocked"
    assert blocked["ux_acceptance_summary"]["mapped_chain_closure_status"] == (
        "open_gap_requires_next_slice"
    )
    assert blocked["ux_acceptance_summary"]["gap_requires_next_slice_count"] == 1
    assert blocked["ux_acceptance_summary"]["stale_next_slice_journey_ids"] == [
        "F",
        "F2",
    ]
    assert "ux_acceptance[F].gap_requires_next_slice_not_closed" in blocked["blockers"]
    assert "ux_acceptance[F].stale_next_build_slice:rescue_missing_slice" in blocked[
        "blockers"
    ]
    assert (
        "ux_acceptance[F2].stale_next_build_slice:"
        "memory_review_forget_confirmation_shadow"
    ) in blocked["blockers"]


def test_edge_case_coverage_blocks_orphan_and_keyword_owned_entries() -> None:
    from app.advanced_shadow_lab.edge_case_coverage import (
        load_edge_case_coverage_contract,
        validate_edge_case_coverage_contract,
    )

    artifact = load_edge_case_coverage_contract()
    contract = dict(artifact["source_contract"])
    entries = [dict(entry) for entry in contract["coverage_entries"]]
    entries[0]["product_contract_refs"] = []
    entries[0]["raw_keyword_semantic_oracle_allowed"] = True
    entries[0]["claim_boundary"] = "product_truth"
    contract["coverage_entries"] = entries

    blocked = validate_edge_case_coverage_contract(contract)

    assert blocked["status"] == "blocked"
    assert blocked["blockers"] == [
        "memory_scope_leak_rejected.product_contract_refs_missing",
        "memory_scope_leak_rejected.claim_boundary_not_non_claim",
        "memory_scope_leak_rejected.raw_keyword_semantic_oracle_allowed",
    ]
    assert blocked["new_report_family_created"] is False


def test_shadow_comparison_exposes_edge_coverage_without_readiness_claim() -> None:
    from app.advanced_shadow_lab.shadow_comparison import (
        build_advanced_shadow_comparison_artifact,
    )
    from tests.test_advanced_shadow_lab_shadow_comparison import (
        _dogfood_replay,
        _fixture_chain,
        _live_diagnostic,
        _proactive_live_diagnostic,
        _rescue_live_diagnostic,
    )

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
        proactive_copy_live_diagnostic_artifact=_proactive_live_diagnostic(),
    )

    assert artifact["status"] == "pass"
    assert artifact["edge_case_coverage_summary"] == {
        "status": "pass",
        "covered_domain_count": 5,
        "coverage_entry_count": 9,
        "missing_domains": [],
        "new_report_family_created": False,
        "coverage_role": "evidence_index_not_product_semantic_authority",
        "ux_acceptance_summary": {
            "required_journey_ids": ["F", "F2", "I", "L", "M", "N"],
            "mapped_journey_count": 6,
            "missing_journey_ids": [],
            "existing_shadow_chain_mapped_count": 6,
            "gap_requires_next_slice_count": 0,
            "stale_next_slice_journey_ids": [],
            "closure_next_build_slice": "advanced_capability_gap_review",
            "mapped_chain_closure_status": "closed_for_gap_review",
            "new_report_family_created": False,
            "mainline_activation_allowed": False,
        },
    }
    assert artifact["surface_status_rows"][3] == {
        "surface": "cross_domain_edge_case_coverage",
        "fixture_status": "pass",
        "dogfood_status": "not_applicable",
        "live_status": "not_required",
        "finding": "edge_case_contract_linkage_passed",
    }
    assert artifact["product_readiness_claimed"] is False
