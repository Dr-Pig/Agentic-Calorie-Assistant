from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE = (
    "browser_shell_smoke",
    "chat_history_reload",
    "free_text_manual_target",
    "dogfood_review_queue",
    "local_dogfood_data_hygiene",
    "pre_live_decision_pack",
    "mvp_gate",
    "phase_c_gate",
)

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))

def build_local_web_self_use_candidate_v2(evidence: dict[str, Any]) -> dict[str, Any]:
    required_evidence_output = {}
    blockers = []

    # 1. Check all required evidence is present and clean
    for group_id in REQUIRED_EVIDENCE:
        payload = dict(evidence.get(group_id) or {})
        present = bool(payload)
        status = str(payload.get("status") or "")
        
        entry = {"present": present, "status": status}
        if group_id not in ("mvp_gate", "phase_c_gate"):
            entry["source"] = payload.get("source")
            
        required_evidence_output[group_id] = entry

        if not present:
            blockers.append(f"missing evidence: {group_id}")
        else:
            expected_status = "generated" if group_id in ("dogfood_review_queue", "pre_live_decision_pack") else "pass"
            if status != expected_status:
                blockers.append(f"failed evidence: {group_id} status={status}")

    # 2. Check for blockers in any artifact claims
    for group_id, payload in evidence.items():
        if not isinstance(payload, dict):
            continue
        
        if payload.get("private_self_use_approved") is True:
            blockers.append("private self-use approval attempted")
        
        if payload.get("product_readiness_claimed") is True or payload.get("product_ready") is True:
            blockers.append("readiness overclaim")
            
        if payload.get("web_ready") is True:
            blockers.append("readiness overclaim")

        if payload.get("live_provider_called") is True or payload.get("live_provider_used") is True:
            blockers.append("live provider used")
            
        if payload.get("kimi_activated") is True:
            blockers.append("Kimi activated")
            
        if payload.get("production_db_touched") is True:
            blockers.append("production DB touched")

        if payload.get("production_selected") is True:
            blockers.append("readiness overclaim")

        if payload.get("rollout_approved") is True:
            blockers.append("readiness overclaim")

        if payload.get("live_manager_required") is True:
            blockers.append("readiness overclaim")

    blockers = sorted(list(set(blockers)))
    candidate_prepared = len(blockers) == 0

    return _json_safe({
        "local_web_self_use_candidate_v2": {
            "candidate_prepared": candidate_prepared,
            "private_self_use_approved": False,
            "product_readiness_claimed": False,
            "live_manager_required": False,
            "production_selected": False,
            "rollout_approved": False,
            "kimi_activated": False,
            "live_provider_called": False,
            "required_evidence": required_evidence_output,
            "blockers": blockers,
            "next_recommended_slice": (
                ["one_day_realistic_web_dogfood_scenario"]
                if candidate_prepared
                else blockers
            ),
        }
    })

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument(
        "--output", 
        default="artifacts/accurate_intake_local_web_self_use_candidate_v2.json"
    )
    args = parser.parse_args(argv)

    evidence_str = Path(args.evidence_json).read_text(encoding="utf-8")
    evidence = dict(json.loads(evidence_str))
    
    pack = build_local_web_self_use_candidate_v2(evidence)
    
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
