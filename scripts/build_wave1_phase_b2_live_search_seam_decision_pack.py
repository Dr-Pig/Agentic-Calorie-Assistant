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


DEFAULT_TAVILY_ARTIFACT = ROOT / "artifacts" / "wave1_phase_b2_exact_brand_tavily_live_trace_canary.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
DECISION_OPTION_IDS = (
    "no_live_search_seam",
    "trace_only_canary_continues",
    "narrow_exact_brand_web_seam",
    "defer_web_and_continue_B2_local",
)


def build_live_search_seam_decision_pack(tavily_artifact: dict[str, Any]) -> dict[str, Any]:
    cases = [case for case in tavily_artifact.get("cases") or [] if isinstance(case, dict)]
    input_integrity = _input_integrity(tavily_artifact, cases)
    failure_families = _failure_families(tavily_artifact, cases)
    evidence_summary = {
        "provider_mode": tavily_artifact.get("provider_mode"),
        "live_invoked": tavily_artifact.get("live_invoked") is True,
        "trace_only": tavily_artifact.get("trace_only") is True,
        "case_count": len(cases),
        "trace_blocker_count": sum(1 for case in cases if case.get("verdict_category") == "trace_canary_blocker"),
        "failure_families": failure_families,
    }
    selected_option, selection_reason = _select_safe_option(
        input_integrity=input_integrity,
        evidence_summary=evidence_summary,
    )
    return _json_safe(
        {
            "artifact_type": "wave1_phase_b2_live_search_seam_decision_pack",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_artifact_type": tavily_artifact.get("artifact_type"),
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "input_integrity": input_integrity,
            "evidence_summary": evidence_summary,
            "decision_options_ordered": list(DECISION_OPTION_IDS),
            "decision_options": _decision_options(),
            "recommended_safe_default": "no_live_search_seam",
            "selected_option": selected_option,
            "selection_reason": selection_reason,
            "requires_human_decision": selected_option == "narrow_exact_brand_web_seam",
            "runtime_web_activation_approved": False,
            "runtime_web_activation_recommended": False,
            "decision_boundary": {
                "trace_canary_is_runtime_activation_evidence": False,
                "accepted_extract_packet_is_exact_truth": False,
                "runtime_web_seam_requires_new_slice": True,
                "mutation_allowed": False,
                "product_readiness_claim_allowed": False,
            },
        }
    )


def _select_safe_option(
    *,
    input_integrity: dict[str, Any],
    evidence_summary: dict[str, Any],
) -> tuple[str, str]:
    if evidence_summary.get("live_invoked") is not True:
        return "no_live_search_seam", "tavily_live_not_invoked"
    if input_integrity.get("passed") is not True:
        return "no_live_search_seam", "input_integrity_blocked"
    if evidence_summary.get("trace_blocker_count", 0) or evidence_summary.get("failure_families"):
        return "no_live_search_seam", "trace_canary_has_blockers"
    return "trace_only_canary_continues", "trace_canary_clean_but_runtime_activation_not_approved"


def write_live_search_seam_decision_pack(
    *,
    tavily_artifact_path: Path = DEFAULT_TAVILY_ARTIFACT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    tavily_artifact = json.loads(tavily_artifact_path.read_text(encoding="utf-8"))
    pack = build_live_search_seam_decision_pack(tavily_artifact)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "wave1_phase_b2_live_search_seam_decision_pack.json"
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _input_integrity(tavily_artifact: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if tavily_artifact.get("artifact_type") != "b2_exact_brand_tavily_live_trace_canary":
        blockers.append("input_artifact_type_invalid")
    if tavily_artifact.get("readiness_claimed") is True:
        blockers.append("input_readiness_claimed")
    if tavily_artifact.get("trace_only") is not True:
        blockers.append("input_not_trace_only")
    if tavily_artifact.get("runtime_web_activation_recommended") is True:
        blockers.append("input_runtime_web_activation_recommended")
    for case in cases:
        if case.get("runtime_web_activation_recommended") is True:
            blockers.append("case_runtime_web_activation_recommended")
        trace = case.get("trace") if isinstance(case.get("trace"), dict) else {}
        boundary = trace.get("truth_boundary") if isinstance(trace.get("truth_boundary"), dict) else {}
        if boundary.get("accepted_extract_packet_truth_authority") is True:
            blockers.append("accepted_extract_packet_claimed_as_truth")
        if boundary.get("runtime_web_activation_recommended") is True:
            blockers.append("trace_runtime_web_activation_recommended")
    return {
        "passed": not blockers,
        "blockers": sorted(set(blockers)),
    }


def _failure_families(tavily_artifact: dict[str, Any], cases: list[dict[str, Any]]) -> list[str]:
    families: set[str] = set()
    top_level = tavily_artifact.get("failure_family")
    if isinstance(top_level, str) and top_level:
        families.add(top_level)
    for case in cases:
        family = case.get("failure_family")
        if isinstance(family, str) and family:
            families.add(family)
    return sorted(families)


def _decision_options() -> list[dict[str, Any]]:
    return [
        {
            "option_id": "no_live_search_seam",
            "description": "Keep B2 on local DB, packet, synthesis, and final-mapping closure without runtime web.",
            "auto_activation_allowed": True,
            "requires_new_slice": False,
            "blocked_claims": ["runtime_web_activation", "product_ready", "mutation_ready"],
        },
        {
            "option_id": "trace_only_canary_continues",
            "description": "Continue Tavily exact-brand observation as trace-only evidence collection.",
            "auto_activation_allowed": True,
            "requires_new_slice": False,
            "blocked_claims": ["runtime_web_activation", "product_ready", "mutation_ready"],
        },
        {
            "option_id": "narrow_exact_brand_web_seam",
            "description": "Plan a separate runtime seam for exact-brand/SKU lookup only, behind WebSearchPort/WebExtractPort.",
            "auto_activation_allowed": False,
            "requires_new_slice": True,
            "blocked_claims": ["runtime_web_activation", "product_ready", "mutation_ready"],
        },
        {
            "option_id": "defer_web_and_continue_B2_local",
            "description": "Defer web activation and continue local B2 DB, packet, synthesis, and final mapping hardening.",
            "auto_activation_allowed": True,
            "requires_new_slice": False,
            "blocked_claims": ["runtime_web_activation", "product_ready", "mutation_ready"],
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
            "artifacts": ["artifacts/wave1_phase_b2_exact_brand_tavily_live_trace_canary.json"],
            "producers": ["scripts/build_wave1_phase_b2_live_search_seam_decision_pack.py"],
            "trace_only": True,
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=[
            "runtime_web_activation",
            "product_ready",
            "user_facing_ready",
            "mutation_ready",
        ],
        readiness_claimed=False,
    )


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build B2 live search seam decision pack from Tavily trace-only canary.")
    parser.add_argument("--tavily-artifact", default=str(DEFAULT_TAVILY_ARTIFACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_live_search_seam_decision_pack(
        tavily_artifact_path=Path(args.tavily_artifact),
        output_dir=Path(args.output_dir),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
