from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402

REQUIRED_PRODUCT_LOOP_EVIDENCE = (
    "browser_shell_smoke",
    "local_web_candidate",
    "browser_fixture_dogfood",
    "local_dogfood_hygiene",
    "browser_realistic_dogfood",
    "operator_review",
    "mvp_gate",
)

REALISTIC_BROWSER_STATUSES = {
    "browser_diagnostic_pass_with_fixture_evidence_gap",
    "browser_diagnostic_pass_with_evidence_gap",
}
OPERATOR_REVIEW_STATUSES = {
    "browser_diagnostic_review_with_fixture_evidence_gap",
    "browser_diagnostic_review_with_evidence_gap",
    "diagnostic_review_with_evidence_gap",
}
ALLOWED_SOURCE_QUALITY = {
    "approved",
    "human_approved",
    "packet_ready_approved",
}
FOODDB_METADATA_FIELDS = (
    "path",
    "schema_version",
    "fixture_or_real",
    "source_quality",
    "ready_for_product_loop",
)
REQUIRED_FOODDB_MACRO_PACKET_FIELDS = {
    "protein_g",
    "carbs_g",
    "fat_g",
    "macro_visibility_status",
    "macro_source_basis",
    "macro_confidence",
}
FOODDB_MACRO_TRUTH_OWNER = "fooddb_approved_packet"
FOODDB_MISSING_MACRO_POLICY = "preserve_null_do_not_invent"


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(value: dict[str, Any]) -> str:
    return str(value.get("status") or "")


def _local_web_candidate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return _object_dict(payload.get("local_web_self_use_candidate_v2"))


def _local_web_candidate_status(payload: dict[str, Any]) -> str:
    candidate = _local_web_candidate_payload(payload)
    if candidate.get("candidate_prepared") is True:
        return "candidate_prepared"
    if payload:
        return "blocked"
    return ""


def _appshell_chain(payload: dict[str, Any]) -> dict[str, Any]:
    return _object_dict(
        _local_web_candidate_payload(payload).get("appshell_browser_evidence_chain")
    )


def _local_web_candidate_blockers(payload: dict[str, Any]) -> list[str]:
    candidate = _local_web_candidate_payload(payload)
    chain = _appshell_chain(payload)
    blockers: list[str] = []
    if not payload:
        return ["missing_product_loop_evidence:local_web_candidate"]
    if candidate.get("candidate_prepared") is not True:
        blockers.append("local_web_candidate_not_prepared")
    if candidate.get("blockers") not in (None, []):
        blockers.append("local_web_candidate_upstream_blockers_present")
    if chain.get("browser_artifact_count") != 6 or chain.get("browser_executed_count") != 6:
        blockers.append("local_web_candidate_browser_artifact_count_mismatch")
    for field, blocker in (
        (
            "all_required_browser_artifacts_executed",
            "local_web_candidate_browser_artifacts_not_all_executed",
        ),
        ("product_pages_self_use_flow_checked", "local_web_candidate_self_use_flow_missing"),
        ("today_macro_runtime_mirror_checked", "local_web_candidate_today_macro_missing"),
        ("renderer_source_closure_checked", "local_web_candidate_renderer_source_missing"),
        (
            "context_target_browser_closure_checked",
            "local_web_candidate_context_target_browser_closure_missing",
        ),
        ("body_noplan_degraded_checked", "local_web_candidate_body_noplan_missing"),
    ):
        if chain.get(field) is not True:
            blockers.append(blocker)
    for field, blocker in (
        ("live_llm_invoked", "local_web_candidate_live_llm_invoked"),
        ("fooddb_evidence_used", "local_web_candidate_fooddb_evidence_used"),
        ("websearch_evidence_used", "local_web_candidate_websearch_evidence_used"),
        ("runtime_truth_changed", "local_web_candidate_runtime_truth_changed"),
        ("mutation_changed", "local_web_candidate_mutation_changed"),
        ("frontend_semantic_owner", "local_web_candidate_frontend_semantic_owner"),
    ):
        if chain.get(field) is True:
            blockers.append(blocker)
    return blockers


def _pl_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    status = _status(payload)
    blockers: list[str] = []
    if not payload:
        return [f"missing_product_loop_evidence:{group_id}"]
    if group_id == "browser_shell_smoke":
        if status != "pass" or payload.get("browser_executed") is not True:
            blockers.append("browser_shell_smoke_not_browser_executed_pass")
    elif group_id == "local_web_candidate":
        blockers.extend(_local_web_candidate_blockers(payload))
    elif group_id == "browser_fixture_dogfood":
        if status != "browser_fixture_pass":
            blockers.append("browser_fixture_dogfood_not_fixture_pass")
        if payload.get("fixture_evidence_used") is not True:
            blockers.append("browser_fixture_dogfood_fixture_scope_missing")
        if payload.get("real_fooddb_pass_claimed") is not False:
            blockers.append("browser_fixture_dogfood_real_fooddb_overclaim")
    elif group_id == "local_dogfood_hygiene":
        if status not in {"pass", "generated"}:
            blockers.append("local_dogfood_hygiene_not_clean")
    elif group_id == "browser_realistic_dogfood":
        if status not in REALISTIC_BROWSER_STATUSES:
            blockers.append("browser_realistic_dogfood_not_diagnostic_gap")
        if payload.get("fixture_evidence_used") is not True:
            blockers.append("browser_realistic_dogfood_fixture_scope_missing")
        if payload.get("real_fooddb_pass_claimed") is not False:
            blockers.append("browser_realistic_dogfood_real_fooddb_overclaim")
    elif group_id == "operator_review":
        if status not in OPERATOR_REVIEW_STATUSES:
            blockers.append("operator_review_not_diagnostic_review")
        if payload.get("real_fooddb_pass_claimed") is not False:
            blockers.append("operator_review_real_fooddb_overclaim")
    elif group_id == "mvp_gate":
        if status != "pass":
            blockers.append("mvp_gate_not_pass")
    return blockers


def _product_loop_evidence_status(evidence: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    statuses: dict[str, Any] = {}
    blockers: list[str] = []
    for group_id in REQUIRED_PRODUCT_LOOP_EVIDENCE:
        payload = _object_dict(evidence.get(group_id))
        group_blockers = _pl_blockers(group_id, payload)
        status = (
            _local_web_candidate_status(payload)
            if group_id == "local_web_candidate"
            else _status(payload)
        )
        statuses[group_id] = {
            "present": bool(payload),
            "status": status,
            "blockers": group_blockers,
        }
        blockers.extend(group_blockers)
    return statuses, blockers


def _fooddb_validation(fooddb_artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not fooddb_artifact:
        return {
            "present": False,
            "status": "blocked_waiting_for_fdb_artifact",
            "ready_for_fdb_integration": False,
            "blockers": ["fooddb_artifact_missing"],
            "metadata": {},
        }

    metadata = _object_dict(
        _object_dict(fooddb_artifact).get("approved_packet_ready_evidence_artifact")
    )
    missing = [
        field
        for field in FOODDB_METADATA_FIELDS
        if field not in metadata or metadata.get(field) in (None, "")
    ]
    if missing:
        return {
            "present": True,
            "status": "blocked_invalid_fooddb_metadata",
            "ready_for_fdb_integration": False,
            "blockers": [f"fooddb_metadata_missing:{field}" for field in missing],
            "metadata": _json_safe(metadata),
        }

    if metadata.get("fixture_or_real") != "real":
        return {
            "present": True,
            "status": "fixture_not_real_fooddb",
            "ready_for_fdb_integration": False,
            "blockers": ["fooddb_artifact_is_fixture"],
            "metadata": _json_safe(metadata),
        }

    if metadata.get("source_quality") not in ALLOWED_SOURCE_QUALITY:
        return {
            "present": True,
            "status": "blocked_invalid_fooddb_metadata",
            "ready_for_fdb_integration": False,
            "blockers": ["fooddb_source_quality_not_approved"],
            "metadata": _json_safe(metadata),
        }

    if metadata.get("ready_for_product_loop") is not True:
        return {
            "present": True,
            "status": "blocked_fooddb_not_ready_for_product_loop",
            "ready_for_fdb_integration": False,
            "blockers": ["fooddb_artifact_not_ready_for_product_loop"],
            "metadata": _json_safe(metadata),
        }

    macro_blockers = _fooddb_macro_contract_blockers(metadata)
    if macro_blockers:
        return {
            "present": True,
            "status": "blocked_invalid_fooddb_macro_contract",
            "ready_for_fdb_integration": False,
            "blockers": macro_blockers,
            "metadata": _json_safe(metadata),
        }

    return {
        "present": True,
        "status": "approved_packet_ready_evidence_metadata_valid",
        "ready_for_fdb_integration": True,
        "blockers": [],
        "metadata": _json_safe(metadata),
    }


def _fooddb_macro_contract_blockers(metadata: dict[str, Any]) -> list[str]:
    macro_contract = _object_dict(metadata.get("macro_contract"))
    if not macro_contract:
        return ["fooddb_macro_contract_missing"]

    blockers: list[str] = []
    packet_fields = macro_contract.get("packet_fields")
    if not isinstance(packet_fields, list):
        blockers.append("fooddb_macro_packet_fields_invalid")
        packet_field_set: set[str] = set()
    else:
        packet_field_set = {str(field) for field in packet_fields}

    for field in sorted(REQUIRED_FOODDB_MACRO_PACKET_FIELDS - packet_field_set):
        blockers.append(f"fooddb_macro_packet_field_missing:{field}")

    if macro_contract.get("macro_truth_owner") != FOODDB_MACRO_TRUTH_OWNER:
        blockers.append("fooddb_macro_truth_owner_invalid")
    if macro_contract.get("missing_macro_policy") != FOODDB_MISSING_MACRO_POLICY:
        blockers.append("fooddb_macro_missing_policy_invalid")
    return blockers


def build_product_loop_handoff_v3(
    evidence: dict[str, Any],
    *,
    fooddb_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_status, product_loop_blockers = _product_loop_evidence_status(evidence)
    fooddb = _fooddb_validation(fooddb_artifact)
    local_web_candidate = _object_dict(evidence.get("local_web_candidate"))
    blockers = [*product_loop_blockers]
    if fooddb["status"] in {
        "blocked_invalid_fooddb_metadata",
        "blocked_invalid_fooddb_macro_contract",
    }:
        blockers.extend(fooddb["blockers"])

    if product_loop_blockers:
        status = "blocked"
        selected_next_step = "fix_product_loop_evidence"
    elif fooddb["status"] in {
        "blocked_invalid_fooddb_metadata",
        "blocked_invalid_fooddb_macro_contract",
    }:
        status = "blocked"
        selected_next_step = "wait_for_valid_fdb_metadata"
    elif fooddb["ready_for_fdb_integration"]:
        status = "product_loop_handoff_ready_for_fdb_integration_validation"
        selected_next_step = "run_cross_track_validation_with_approved_fdb_artifact"
    else:
        status = "product_loop_handoff_waiting_for_fdb_artifact"
        selected_next_step = "wait_for_fdb_approved_packet_ready_artifact"

    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_product_loop_handoff_v3",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "product_loop_to_fooddb_handoff_metadata_gate",
            "status": status,
            "selected_next_step": selected_next_step,
            "product_loop_required_evidence": list(REQUIRED_PRODUCT_LOOP_EVIDENCE),
            "product_loop_evidence_status": evidence_status,
            "appshell_browser_evidence_chain": _appshell_chain(local_web_candidate),
            "fooddb_input_mode": "approved_packet_ready_metadata_validation_only",
            "fooddb_artifact_status": fooddb["status"],
            "fooddb_validation": fooddb,
            "ready_for_fdb_integration": fooddb["ready_for_fdb_integration"]
            and not product_loop_blockers
            and not blockers,
            "blockers": blockers,
            "local_only": True,
            "shared_contract_changed": False,
            "autofix_attempted": False,
            "fooddb_truth_updated": False,
            "non_approved_fooddb_inputs_consumed": False,
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "web_readiness_claimed": False,
            "production_db_used": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "not_claiming": [
                "product_ready",
                "web_ready",
                "private_self_use_approved",
                "real_fooddb_pass",
                "dogfood_pass",
                "production_ready",
            ],
        }
    )


def _load_optional(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    return read_json_artifact(Path(path))


def _load_evidence_from_args(args: argparse.Namespace) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    if args.evidence_json:
        evidence.update(read_json_artifact(Path(args.evidence_json)))
    for group_id, path in (
        ("browser_shell_smoke", args.browser_shell_smoke),
        ("local_web_candidate", args.local_web_candidate),
        ("browser_fixture_dogfood", args.browser_fixture_dogfood),
        ("local_dogfood_hygiene", args.local_dogfood_hygiene),
        ("browser_realistic_dogfood", args.browser_realistic_dogfood),
        ("operator_review", args.operator_review),
        ("mvp_gate", args.mvp_gate),
    ):
        if path:
            loaded = read_json_artifact(Path(path))
            if group_id == "mvp_gate" and "local_deterministic_mvp_gate" in loaded:
                loaded = _object_dict(loaded.get("local_deterministic_mvp_gate"))
            evidence[group_id] = loaded
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an Accurate Intake Product Loop handoff metadata gate."
    )
    parser.add_argument("--evidence-json")
    parser.add_argument("--browser-shell-smoke")
    parser.add_argument("--local-web-candidate")
    parser.add_argument("--browser-fixture-dogfood")
    parser.add_argument("--local-dogfood-hygiene")
    parser.add_argument("--browser-realistic-dogfood")
    parser.add_argument("--operator-review")
    parser.add_argument("--mvp-gate")
    parser.add_argument("--fooddb-artifact")
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_product_loop_handoff_v3.json",
    )
    args = parser.parse_args(argv)

    pack = build_product_loop_handoff_v3(
        _load_evidence_from_args(args),
        fooddb_artifact=_load_optional(args.fooddb_artifact),
    )
    write_json_artifact(Path(args.output), pack)
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 1 if pack["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
