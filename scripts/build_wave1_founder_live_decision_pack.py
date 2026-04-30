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

from app.shared.contracts.readiness_claim import build_readiness_claim


DEFAULT_FOUNDER_LIVE_ARTIFACT = ROOT / "artifacts" / "wave1_founder_e2e_live_diagnostic.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
DECISION_OPTION_IDS = (
    "stay_diagnostic",
    "offline_shadow_replay",
    "narrow_live_contract_followup",
    "defer_until_product_decision",
    "prepare_shadow_candidate",
)


def build_founder_live_decision_pack(founder_live_artifact: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(founder_live_artifact.get("summary"))
    input_integrity = _input_integrity(founder_live_artifact)
    evidence_summary = {
        "live_invoked": founder_live_artifact.get("live_invoked") is True,
        "case_count": _case_count(summary, founder_live_artifact),
        "pass_count": int(summary.get("pass_count") or 0),
        "fail_count": int(summary.get("fail_count") or 0),
        "product_decision_required_count": int(summary.get("product_decision_required_count") or 0),
        "failure_layers": _string_list(summary.get("failure_layers")),
        "strict_pass_count": int(summary.get("strict_pass_count") or 0),
        "repaired_pass_count": int(summary.get("repaired_pass_count") or 0),
        "contract_fail_count": int(summary.get("contract_fail_count") or 0),
    }
    selected_option, selection_reason = _select_option(
        input_integrity=input_integrity,
        evidence_summary=evidence_summary,
    )
    return _json_safe(
        {
            "artifact_type": "wave1_founder_live_decision_pack",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_artifact_type": founder_live_artifact.get("artifact_type"),
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "input_integrity": input_integrity,
            "evidence_summary": evidence_summary,
            "decision_options_ordered": list(DECISION_OPTION_IDS),
            "decision_options": _decision_options(),
            "selected_option": selected_option,
            "selection_reason": selection_reason,
            "requires_human_decision": selected_option == "defer_until_product_decision",
            "shadow_or_canary_approved": False,
            "production_rollout_approved": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "decision_boundary": {
                "live_diagnostic_is_product_readiness": False,
                "repaired_pass_unlocks_shadow": False,
                "strict_pass_allows_decision_pack_only": True,
                "mutation_allowed": False,
                "product_readiness_claim_allowed": False,
            },
        }
    )


def write_founder_live_decision_pack(
    *,
    founder_live_artifact_path: Path = DEFAULT_FOUNDER_LIVE_ARTIFACT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    founder_live_artifact = json.loads(founder_live_artifact_path.read_text(encoding="utf-8"))
    pack = build_founder_live_decision_pack(founder_live_artifact)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "wave1_founder_live_decision_pack.json"
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _select_option(
    *,
    input_integrity: dict[str, Any],
    evidence_summary: dict[str, Any],
) -> tuple[str, str]:
    if input_integrity.get("passed") is not True:
        return "stay_diagnostic", "input_integrity_blocked"
    if evidence_summary.get("product_decision_required_count", 0) > 0:
        return "defer_until_product_decision", "product_decision_required"
    if evidence_summary.get("fail_count", 0) > 0 or evidence_summary.get("contract_fail_count", 0) > 0:
        failure_layers = set(evidence_summary.get("failure_layers") or [])
        if "provider_contract_non_adherence" in failure_layers:
            return "narrow_live_contract_followup", "provider_contract_non_adherence"
        return "stay_diagnostic", "live_diagnostic_has_failures"
    if evidence_summary.get("repaired_pass_count", 0) > 0:
        return "offline_shadow_replay", "live_clean_but_repair_dependent"
    if evidence_summary.get("strict_pass_count", 0) == evidence_summary.get("case_count", 0) and evidence_summary.get("case_count", 0) > 0:
        return "prepare_shadow_candidate", "all_live_cases_strict_pass_diagnostic_only"
    return "stay_diagnostic", "insufficient_live_evidence"


def _input_integrity(founder_live_artifact: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if founder_live_artifact.get("artifact_type") != "wave1_founder_e2e_live_diagnostic":
        blockers.append("input_artifact_type_invalid")
    if founder_live_artifact.get("readiness_claimed") is True:
        blockers.append("input_readiness_claimed")
    if founder_live_artifact.get("production_selected") is True:
        blockers.append("input_production_selected")
    if founder_live_artifact.get("runtime_web_activation_approved") is True:
        blockers.append("input_runtime_web_activation_approved")
    if founder_live_artifact.get("mutation_enabled") is True:
        blockers.append("input_mutation_enabled")
    return {
        "passed": not blockers,
        "blockers": sorted(set(blockers)),
    }


def _case_count(summary: dict[str, Any], founder_live_artifact: dict[str, Any]) -> int:
    counted = (
        int(summary.get("pass_count") or 0)
        + int(summary.get("fail_count") or 0)
        + int(summary.get("product_decision_required_count") or 0)
        + int(summary.get("deferred_count") or 0)
    )
    return counted or len(_list(founder_live_artifact.get("cases")))


def _decision_options() -> list[dict[str, Any]]:
    return [
        {
            "option_id": "stay_diagnostic",
            "description": "Keep Founder live as diagnostic-only evidence collection.",
            "auto_activation_allowed": True,
            "blocked_claims": ["product_ready", "user_facing_ready", "mutation_ready"],
        },
        {
            "option_id": "offline_shadow_replay",
            "description": "Compare live candidate outputs against deterministic truth offline before any shadow/canary stage.",
            "auto_activation_allowed": True,
            "blocked_claims": ["product_ready", "user_facing_ready", "mutation_ready"],
        },
        {
            "option_id": "narrow_live_contract_followup",
            "description": "Continue provider/model contract repair without changing product semantics.",
            "auto_activation_allowed": True,
            "blocked_claims": ["product_ready", "production_manager", "mutation_ready"],
        },
        {
            "option_id": "defer_until_product_decision",
            "description": "Stop because the next fix requires product semantic decision.",
            "auto_activation_allowed": False,
            "blocked_claims": ["runtime_semantic_change_without_approval"],
        },
        {
            "option_id": "prepare_shadow_candidate",
            "description": "Prepare a separate shadow-mode plan after all live cases strictly pass.",
            "auto_activation_allowed": False,
            "blocked_claims": ["automatic_shadow_rollout", "user_facing_ready", "mutation_ready"],
        },
    ]


def _readiness_claim() -> dict[str, Any]:
    return build_readiness_claim(
        claim_scope="live_diagnostic",
        activation_stage="live_diagnostic",
        semantic_authority_source="deterministic_validator",
        producer_honesty={
            "runner_inferred_semantics": False,
            "fake_provider_simulated_manager": False,
            "final_mapping_fabricated": False,
            "mutation_fabricated": False,
        },
        evidence_lineage={
            "artifacts": ["artifacts/wave1_founder_e2e_live_diagnostic.json"],
            "producers": ["scripts/build_wave1_founder_live_decision_pack.py"],
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=[
            "product_ready",
            "user_facing_ready",
            "mutation_ready",
            "production_ready",
            "runtime_web_activation_ready",
        ],
        readiness_claimed=False,
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if str(item)]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Wave 1 Founder live decision pack.")
    parser.add_argument("--founder-live-artifact", default=str(DEFAULT_FOUNDER_LIVE_ARTIFACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_founder_live_decision_pack(
        founder_live_artifact_path=Path(args.founder_live_artifact),
        output_dir=Path(args.output_dir),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
