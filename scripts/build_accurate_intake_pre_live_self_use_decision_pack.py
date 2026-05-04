from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

REQUIRED_PRE_LIVE_EVIDENCE = (
    "phase_c_gate",
    "accurate_intake_mvp_gate",
    "browser_shell_smoke",
    "chat_history_reload_gate",
    "free_text_manual_target_gate",
    "dogfood_review_queue",
    "local_dogfood_data_hygiene",
    "local_operator_data_hygiene_bundle",
    "pl_ce_local_review_decision_pack",
)

_EXPECTED_STATUS_BY_GROUP = {
    "phase_c_gate": "pass",
    "accurate_intake_mvp_gate": "pass",
    "browser_shell_smoke": "pass",
    "chat_history_reload_gate": "pass",
    "free_text_manual_target_gate": "pass",
    "dogfood_review_queue": "generated",
    "local_dogfood_data_hygiene": "pass",
    "local_operator_data_hygiene_bundle": "local_operator_data_hygiene_ready",
    "pl_ce_local_review_decision_pack": "ready_for_human_pl_ce_review",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _evidence_missing(group_id: str, payload: dict[str, Any]) -> bool:
    if str(payload.get("status") or "") != _EXPECTED_STATUS_BY_GROUP[group_id]:
        return True
    if group_id == "browser_shell_smoke" and payload.get("browser_executed") is not True:
        return True
    return False


def _evidence_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in (
        "shared_contract_changed",
        "manager_context_packet_schema_changed",
        "manager_context_packet_changed",
        "nutrition_evidence_store_port_changed",
        "food_evidence_record_schema_changed",
        "packet_ready_anchor_schema_changed",
        "packetizer_format_changed",
        "packetizer_contract_changed",
        "basket_semantics_changed",
        "estimate_output_format_changed",
        "food_evidence_promotion_policy_changed",
        "runtime_truth_changed",
        "mutation_changed",
        "production_db_touched",
        "production_db_ready_claimed",
        "runtime_web_activation_approved",
        "live_canary_approved",
        "kimi_active_runtime_default_allowed",
        "kimi_activated",
        "grokfast_activated",
        "web_ready",
        "product_ready",
        "production_selected",
        "rollout_approved",
        "live_manager_required",
        "websearch_evidence_used",
        "web_tavily",
        "fooddb_evidence_used",
        "fooddb_schema_changed",
        "writes_performed",
        "import_allowed",
        "production_db_used",
        "fooddb_truth_updated",
        "live_llm_invoked",
        "web_tavily_used",
        "web_tavily_invoked",
        "private_self_use_approved",
        "product_readiness_claimed",
        "ready_for_live_diagnostic_decision",
        "ready_for_fdb_integration",
        "real_fooddb_pass_claimed",
    ):
        if payload.get(flag) is True:
            blockers.append(f"{group_id}_{flag}")
    return blockers


def build_pre_live_self_use_decision_pack(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_status = {
        group_id: dict(evidence.get(group_id) or {})
        for group_id in REQUIRED_PRE_LIVE_EVIDENCE
    }
    missing_evidence = [
        group_id
        for group_id, payload in evidence_status.items()
        if _evidence_missing(group_id, payload)
    ]
    blockers: list[str] = []
    for group_id, payload in evidence_status.items():
        blockers.extend(_evidence_blockers(group_id, payload))
    selected_option = (
        "stay_local_self_use"
        if missing_evidence or blockers
        else "ready_for_human_limited_live_canary_decision"
    )
    ready_for_pl_ce_local_review = (
        not _evidence_missing(
            "pl_ce_local_review_decision_pack",
            evidence_status["pl_ce_local_review_decision_pack"],
        )
        and not any(
            blocker.startswith("pl_ce_local_review_decision_pack_")
            for blocker in blockers
        )
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pre_live_self_use_decision_pack",
            "status": "generated",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pre_live_local_web_self_use_decision_pack",
            "required_evidence": list(REQUIRED_PRE_LIVE_EVIDENCE),
            "evidence_status": evidence_status,
            "missing_evidence": missing_evidence,
            "blockers": blockers,
            "selected_option": selected_option,
            "selection_reason": (
                "pre_live_evidence_missing"
                if missing_evidence
                else "pre_live_evidence_blocked"
                if blockers
                else "local_web_self_use_evidence_ready_for_human_live_decision"
            ),
            "ready_for_pl_ce_local_review": ready_for_pl_ce_local_review,
            "ready_for_live_diagnostic_decision": False,
            "live_llm_invoked": False,
            "web_tavily_invoked": False,
            "live_canary_approved": False,
            "kimi_active_runtime_default_allowed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "runtime_web_activation_approved": False,
            "production_db_ready_claimed": False,
            "not_claiming": [
                "product_ready",
                "rollout_ready",
                "live_llm_ready",
                "web_ready",
                "production_db_ready",
                "kimi_ready",
            ],
        }
    )


def _load_evidence(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _write_output(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a pre-live Accurate Intake local web self-use decision pack."
    )
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_pre_live_self_use_decision_pack.json",
    )
    args = parser.parse_args(argv)

    pack = build_pre_live_self_use_decision_pack(_load_evidence(Path(args.evidence_json)))
    _write_output(Path(args.output), pack)
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
