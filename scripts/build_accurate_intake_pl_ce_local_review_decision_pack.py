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

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact

REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE = (
    "browser_shell_smoke",
    "browser_fixture_dogfood",
    "browser_realistic_dogfood",
    "pl_ce_review_bundle",
    "context_review",
    "context_target_candidate_eval",
    "context_window_diagnostic",
    "mvp_gate",
)

_PASS_STATUSES = {
    "pass",
    "generated",
    "browser_fixture_pass",
    "browser_diagnostic_pass_with_fixture_evidence_gap",
    "browser_diagnostic_pass_with_evidence_gap",
    "product_loop_context_diagnostic_ready_for_human_review",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _missing(group_id: str, payload: dict[str, Any]) -> bool:
    if not payload or _status(payload) not in _PASS_STATUSES:
        return True
    if group_id == "browser_shell_smoke" and payload.get("browser_executed") is not True:
        return True
    if group_id == "pl_ce_review_bundle" and payload.get("ready_for_fdb_integration") is not False:
        return True
    return False


def _overclaim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("real_fooddb_pass_claimed") is True:
        blockers.append(f"{group_id}_real_fooddb_overclaim")
    if payload.get("dogfood_pass") is True:
        blockers.append(f"{group_id}_dogfood_pass_overclaim")
    if payload.get("product_readiness_claimed") is True:
        blockers.append(f"{group_id}_product_readiness_overclaim")
    if payload.get("private_self_use_approved") is True:
        blockers.append(f"{group_id}_private_self_use_overclaim")
    if payload.get("live_llm_invoked") is True:
        blockers.append(f"{group_id}_live_llm_invoked")
    if payload.get("web_tavily_used") is True or payload.get("web_tavily_invoked") is True:
        blockers.append(f"{group_id}_web_tavily_used")
    return blockers


def build_pl_ce_local_review_decision_pack(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_status = {
        group_id: _object_dict(evidence.get(group_id))
        for group_id in REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE
    }
    missing_evidence = [
        group_id
        for group_id, payload in evidence_status.items()
        if _missing(group_id, payload)
    ]
    blockers: list[str] = []
    for group_id, payload in evidence_status.items():
        blockers.extend(_overclaim_blockers(group_id, payload))
    status = "blocked" if missing_evidence or blockers else "ready_for_human_pl_ce_review"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_local_review_decision_pack",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_local_review_decision_pack",
            "status": status,
            "required_evidence": list(REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE),
            "evidence_status": evidence_status,
            "missing_evidence": missing_evidence,
            "blockers": blockers,
            "selected_next_step": (
                "human_review_pl_ce_checkpoint"
                if status == "ready_for_human_pl_ce_review"
                else "fix_pl_ce_local_evidence"
            ),
            "review_required_before_provider_call": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "local_only": True,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local PL+CE review decision pack."
    )
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_pl_ce_local_review_decision_pack.json",
    )
    args = parser.parse_args(argv)

    pack = build_pl_ce_local_review_decision_pack(read_json_artifact(Path(args.evidence_json)))
    write_json_artifact(Path(args.output), pack)
    print(json.dumps({"artifact": args.output, "status": pack["status"]}, ensure_ascii=False))
    return 1 if pack["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
