from __future__ import annotations

from pathlib import Path

from app.nutrition.application.food_evidence_retriever_execution_smoke import (
    RetrieverExecutionCase,
    build_food_evidence_retriever_execution_smoke,
)
from app.nutrition.application.food_evidence_retriever_router import (
    RetrieverBackendAvailability,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (
    SQLiteFtsFoodEvidenceIndex,
)

SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _sqlite_index(tmp_path: Path) -> SQLiteFtsFoodEvidenceIndex:
    local = LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE)
    return SQLiteFtsFoodEvidenceIndex.rebuild_from_records(
        tmp_path / "food_evidence.sqlite",
        local.load_records(),
    )


def test_retriever_execution_smoke_unifies_fooddb_and_websearch_candidate_paths(
    tmp_path: Path,
) -> None:
    artifact = build_food_evidence_retriever_execution_smoke(
        index=_sqlite_index(tmp_path),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
    )

    assert artifact["artifact_type"] == "accurate_intake_food_evidence_retriever_execution_smoke_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_retriever_execution_smoke_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["case_count"] == 4
    assert artifact["summary"]["fail_count"] == 0
    assert artifact["summary"]["blocked_no_execution_case_count"] == 1
    assert artifact["next_required_slice"] == "grokfast_fooddb_diagnostic_preflight"


def test_retriever_execution_smoke_keeps_fooddb_backend_manager_invisible(
    tmp_path: Path,
) -> None:
    artifact = build_food_evidence_retriever_execution_smoke(
        index=_sqlite_index(tmp_path),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
    )
    cases = {case["case_id"]: case for case in artifact["cases"]}
    fooddb = cases["generic_boba_fooddb"]

    assert fooddb["status"] == "pass"
    assert fooddb["route_plan"]["backend_sequence"] == [
        "sqlite_fts_index",
        "local_fooddb_index",
    ]
    assert fooddb["route_plan"]["retrieval_intent_source"] == "manager_decision"
    assert fooddb["route_plan"]["manager_owned_intent_required"] is True
    assert fooddb["route_plan"]["raw_text_hint_executed"] is False
    assert fooddb["tool_evidence_result"]["tool_name"] == "lookup_food_evidence"
    assert fooddb["tool_evidence_result"]["runtime_mutation_allowed"] is False
    assert fooddb["tool_evidence_result"]["source_implementation_visible"] is False
    assert "sqlite_fts" not in str(fooddb["tool_evidence_result"])
    assert "local_json" not in str(fooddb["tool_evidence_result"])
    assert fooddb["manager_owned_query"] == "boba"
    assert fooddb["tool_evidence_result"]["evidence_packets"][0]["evidence_items"][0][
        "anchor_id"
    ] == "custom_drink_boba_milk_tea"


def test_retriever_execution_smoke_keeps_websearch_candidate_only(tmp_path: Path) -> None:
    artifact = build_food_evidence_retriever_execution_smoke(
        index=_sqlite_index(tmp_path),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
    )
    cases = {case["case_id"]: case for case in artifact["cases"]}
    exact = cases["exact_brand_websearch_candidate"]

    assert exact["status"] == "pass"
    assert exact["route_plan"]["backend_sequence"] == [
        "sqlite_fts_index",
        "local_fooddb_index",
        "websearch_candidate_lane",
    ]
    assert exact["tool_evidence_result"]["tool_name"] == "search_official_nutrition"
    assert exact["tool_evidence_result"]["runtime_truth_changed"] is False
    assert exact["websearch_runtime_truth_allowed"] is False
    assert exact["tool_evidence_result"]["trace"]["packet_count"] == 1
    assert all(
        packet["truth_level"] == "candidate"
        for packet in exact["tool_evidence_result"]["evidence_packets"]
    )
    assert exact["tool_evidence_result"]["evidence_packets"][0]["title"] == (
        "Milksha pearl black tea latte"
    )
    assert all(
        "runtime_truth_allowed" not in packet
        for packet in exact["tool_evidence_result"]["evidence_packets"]
    )


def test_retriever_execution_smoke_composition_clarification_does_not_call_tools(
    tmp_path: Path,
) -> None:
    artifact = build_food_evidence_retriever_execution_smoke(
        index=_sqlite_index(tmp_path),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
    )
    cases = {case["case_id"]: case for case in artifact["cases"]}
    clarification = cases["composition_clarification"]

    assert clarification["status"] == "pass"
    assert clarification["route_plan"]["primary_backend"] == "ask_followup"
    assert clarification["tool_evidence_result"] is None
    assert clarification["runtime_mutation_allowed"] is False
    assert clarification["truth_selection_forbidden"] is True


def test_retriever_execution_smoke_blocks_raw_text_hint_before_backend_execution(
    tmp_path: Path,
) -> None:
    artifact = build_food_evidence_retriever_execution_smoke(
        index=_sqlite_index(tmp_path),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
    )
    cases = {case["case_id"]: case for case in artifact["cases"]}
    raw_hint = cases["raw_text_hint_does_not_execute_backend"]

    assert raw_hint["status"] == "pass"
    assert raw_hint["route_plan"]["primary_backend"] == "blocked_no_execution"
    assert raw_hint["route_plan"]["backend_sequence"] == []
    assert raw_hint["route_plan"]["retrieval_intent_source"] == "raw_text_hint"
    assert raw_hint["route_plan"]["manager_owned_intent_required"] is True
    assert raw_hint["route_plan"]["raw_text_hint_executed"] is False
    assert raw_hint["tool_evidence_result"] is None


def test_retriever_execution_smoke_uses_manager_owned_intent_not_raw_query(
    tmp_path: Path,
) -> None:
    artifact = build_food_evidence_retriever_execution_smoke(
        index=_sqlite_index(tmp_path),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
        cases=(
            RetrieverExecutionCase(
                case_id="raw_query_mismatch_does_not_drive_retrieval",
                raw_query="kelp",
                expected_primary_backend="sqlite_fts_index",
                intent=RetrievalIntent(
                    base_dish="bubble milk tea",
                    aliases=["boba"],
                    brand_hint=None,
                    size_hint=None,
                    modifier_hints=[],
                    listed_items=[],
                    retrieval_goal="generic_anchor_lookup",
                ),
            ),
        ),
    )

    case = artifact["cases"][0]
    assert case["status"] == "pass"
    assert case["raw_query"] == "kelp"
    assert case["manager_owned_query"] == "boba"
    assert case["tool_evidence_result"]["evidence_packets"][0]["evidence_items"][0][
        "anchor_id"
    ] == "custom_drink_boba_milk_tea"


def test_retriever_execution_smoke_fails_closed_when_websearch_scope_is_empty(
    tmp_path: Path,
) -> None:
    artifact = build_food_evidence_retriever_execution_smoke(
        index=_sqlite_index(tmp_path),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
        cases=(
            RetrieverExecutionCase(
                case_id="unmatched_exact_brand_websearch_candidate",
                raw_query="Unknown Brand mystery drink",
                expected_primary_backend="sqlite_fts_index",
                intent=RetrievalIntent(
                    base_dish="mystery drink",
                    aliases=["Unknown Brand mystery drink"],
                    brand_hint="Unknown Brand",
                    size_hint=None,
                    modifier_hints=[],
                    listed_items=[],
                    retrieval_goal="exact_brand_lookup",
                ),
            ),
        ),
    )

    assert artifact["status"] == "blocked"
    assert artifact["cases"][0]["status"] == "fail"
    assert artifact["cases"][0]["checks"]["websearch_candidate_packet_present"] is False
    assert artifact["cases"][0]["tool_evidence_result"]["trace"]["packet_count"] == 0
    assert artifact["next_required_slice"] == "inspect_food_evidence_retriever_execution_blockers"


def test_retriever_execution_smoke_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_food_evidence_retriever_execution_smoke import (
        main,
    )

    output = tmp_path / "retriever_execution.json"
    sqlite_db = tmp_path / "food.sqlite"

    assert (
        main(
            [
                "--small-anchor-store",
                str(SMALL_ANCHOR_STORE),
                "--sqlite-db",
                str(sqlite_db),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_food_evidence_retriever_execution_smoke_v1"
    assert artifact["status"] == "pass"
