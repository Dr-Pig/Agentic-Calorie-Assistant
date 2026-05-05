from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)
from app.nutrition.application.grokfast_fooddb_contract_probe import (
    build_grokfast_fooddb_contract_probe,
)
from app.nutrition.application.grokfast_fooddb_packet_smoke import build_live_manager_payload
from app.nutrition.application.grokfast_fooddb_profile_schema import (
    GROKFAST_FOODDB_PROFILE_SCHEMA_NAME,
    build_grokfast_fooddb_profile_schema,
)
from app.providers.builderspace_runtime_contract import response_schema_for_stage
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from scripts.run_accurate_intake_grokfast_fooddb_packet_smoke import (
    FoodDBPacketProfileBuilderSpaceAdapter,
)


def _packet_artifact() -> dict:
    payload = json.loads(
        Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig")
    )
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    return build_fooddb_manager_packet_smoke(retrieval_records=records)


def test_fooddb_profile_schema_requires_item_results_only_for_evidence_cases() -> None:
    boba_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "boba_large_half_sugar"
    )
    bare_case = next(case for case in _packet_artifact()["cases"] if case["case_id"] == "bare_luwei")

    boba_schema = _profile_schema_for_case(boba_case)
    bare_schema = _profile_schema_for_case(bare_case)

    assert "evidence_used" not in boba_schema["properties"]
    assert "item_results" in boba_schema["required"]
    assert "evidence_used" not in bare_schema["properties"]
    assert "item_results" not in bare_schema["required"]
    assert boba_schema["x-diagnostic-profile"]["shared_manager_schema_changed"] is False


def test_fooddb_profile_schema_resolves_shared_schema_drift_for_probe() -> None:
    artifact = build_grokfast_fooddb_contract_probe(
        packet_artifact=_packet_artifact(),
        response_schema_for_constraints=_profile_schema_for_constraints,
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["issue_counts"] == {}
    assert artifact["next_recommended_slice"] == "rerun_grokfast_fooddb_packet_live_diagnostic"


def test_fooddb_profile_adapter_uses_profile_schema_name_and_overlay() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "boba_large_half_sugar"
    )
    constraints = build_live_manager_payload(packet_case=packet_case)["constraints"]
    adapter = FoodDBPacketProfileBuilderSpaceAdapter(manager_model_override="grok-4-fast")

    response_format, transport_meta = adapter._response_format_request_for_stage(
        MANAGER_LOOP_STAGE,
        constraints=constraints,
    )

    schema = response_format["json_schema"]["schema"]
    assert response_format["json_schema"]["name"] == GROKFAST_FOODDB_PROFILE_SCHEMA_NAME
    assert "evidence_used" not in schema["properties"]
    assert "item_results" in schema["required"]
    assert transport_meta["fooddb_profile_schema_applied"] is True
    assert transport_meta["shared_manager_schema_changed"] is False


def _profile_schema_for_case(packet_case: dict) -> dict:
    constraints = build_live_manager_payload(packet_case=packet_case)["constraints"]
    return _profile_schema_for_constraints(constraints) or {}


def _profile_schema_for_constraints(constraints: dict) -> dict | None:
    return build_grokfast_fooddb_profile_schema(
        stage=MANAGER_LOOP_STAGE,
        base_schema=response_schema_for_stage(MANAGER_LOOP_STAGE, constraints),
        constraints=constraints,
    )
