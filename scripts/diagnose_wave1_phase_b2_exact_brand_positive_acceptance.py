from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.evidence_candidate_packetizer import add_hard_recheck_metadata_many
from app.nutrition.application.evidence_packet_consumption import consume_rechecked_packets
from app.nutrition.application.retrieval_intent import build_retrieval_intent
from app.nutrition.application.web_extract_packetizer import _extract_requested_size_kcal, build_web_extract_packets, _KCAL_FIELD_KEYS, _parse_single_kcal_value
from app.providers.tavily_extract_port import TavilyExtractPort

DEFAULT_ARTIFACT_DIR = ROOT / "artifacts"
DEFAULT_OUTPUT = DEFAULT_ARTIFACT_DIR / "wave1_phase_b2_exact_brand_positive_acceptance_diagnostic.json"

_CACHED_LATEST_CANARY: dict[str, Any] | None = None


def find_latest_canary_artifact(artifact_dir: Path) -> Path | None:
    candidates = list(artifact_dir.glob("wave1_phase_b2_exact_brand_tavily_live_trace_canary*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def classify_primary_root_cause(
    *,
    reason_if_missing: str | None,
    hard_recheck_rejected: bool,
    hard_recheck_too_strict: bool,
    packet_consumption_rejected: bool,
    raw_content_present: bool,
    requested_item_present: bool = False,
    requested_size_present: bool,
    kcal_candidates_found: bool,
) -> str:
    if not raw_content_present:
        return "official_source_missing_nutrition"
    if not requested_size_present:
        return "extract_missing_requested_size"
    if requested_item_present and requested_size_present and not kcal_candidates_found:
        return "extract_missing_parseable_kcal"
    if not kcal_candidates_found:
        return "extract_missing_requested_size"
    if reason_if_missing:
        return "extract_packetization_gap"
    if hard_recheck_too_strict:
        return "hard_recheck_too_strict"
    if hard_recheck_rejected:
        return "hard_recheck_correct_reject"
    if packet_consumption_rejected:
        return "packet_consumption_gap"
    return "unknown"


def check_requested_size_present(content: str) -> bool:
    content_lower = content.lower()
    if bool(re.search(r"(?<!特)大杯", content_lower)):
        return True
    return any(
        term in content_lower
        for term in ("grande", "large", "16 oz", "473ml", "473 ml", "473")
    )


def check_requested_item_present(content: str) -> bool:
    content_lower = content.lower()
    return any(term in content_lower for term in ("那堤", "latte", "星巴克那堤"))


async def diagnose_positive_case(
    *,
    canary_json: dict[str, Any],
    case_id: str,
    extract_port: Any,
) -> dict[str, Any]:
    case_data = next((c for c in canary_json.get("cases", []) if c.get("case_id") == case_id), None)
    if not case_data:
        raise ValueError(f"Case {case_id} not found in canary artifact")
    
    trace = case_data.get("trace", {})
    selected_search_packet_id = trace.get("selected_search_packet_id")
    candidate_traces = trace.get("candidate_traces", [])
    selected_candidate = next((c for c in candidate_traces if c.get("packet_id") == selected_search_packet_id), None)
    
    if not selected_candidate:
        return {"error": "selected_candidate_missing"}
    
    source_url = selected_candidate.get("source_url")
    if not source_url:
        return {"error": "selected_candidate_missing_url"}

    # Re-run extraction
    extract_rows = []
    try:
        extract_rows = await extract_port.extract_rows(urls=[source_url], query=trace.get("web_query") or case_data.get("web_query"))
    except Exception as e:
        print(f"Extraction failed: {e}")
    
    row = extract_rows[0] if extract_rows else {"url": source_url, "raw_content": ""}
    raw_content = str(row.get("raw_content") or "")
    
    intent = build_retrieval_intent(case_data.get("raw_user_input", ""))
    
    raw_content_present = bool(raw_content.strip())
    requested_item_present = check_requested_item_present(raw_content) if raw_content_present else False
    requested_size_present = check_requested_size_present(raw_content) if raw_content_present else False
    
    # Kcal isolation test
    requested_size_kcal_isolated = False
    kcal_candidates_found = False
    if raw_content_present:
        isolated_kcal = _extract_requested_size_kcal(row, intent=intent)
        if isolated_kcal is not None:
            requested_size_kcal_isolated = True
            kcal_candidates_found = True
        else:
            # Check if any kcal values are extractable at all
            field_values = [_parse_single_kcal_value(row.get(key)) for key in _KCAL_FIELD_KEYS]
            parsed_field_values = [value for value in field_values if value is not None]
            if parsed_field_values:
                kcal_candidates_found = True
            else:
                for pattern in _KCAL_FIELD_KEYS: pass # not doing full regex manually if not needed, just rely on the packetizer internals
    
    # Check packetization
    selected_search_packet = {
        "packet_id": selected_search_packet_id,
        "url": source_url,
        "title": selected_candidate.get("source_title"),
        "canonical_name": selected_candidate.get("candidate_identity"),
        "matched_name": selected_candidate.get("candidate_identity"),
    }
    extracted_packets_raw = build_web_extract_packets(
        intent,
        selected_search_packet=selected_search_packet,
        extract_rows=[row]
    )
    
    packet_created = bool(extracted_packets_raw)
    packet_id = extracted_packets_raw[0].get("packet_id") if packet_created else None
    reason_if_missing = "packetizer_discarded_due_to_missing_kcal" if not packet_created else None
    
    hard_recheck_accepted = False
    failed_field = None
    rejected_risks = []
    if packet_created:
        rechecked = tuple(add_hard_recheck_metadata_many(extracted_packets_raw))
        rechecked_packet = rechecked[0]
        rejected_risks = rechecked_packet.get("hard_recheck_risks", [])
        hard_recheck_accepted = not bool(rejected_risks)
        if rejected_risks:
            failed_field = "hard_recheck_risks"
    
    accepted_packets_count = 0
    accepted_usage = None
    rejected_candidates_count = 0
    packet_consumption_rejected = False
    
    if packet_created:
        consumption = consume_rechecked_packets(tuple(add_hard_recheck_metadata_many(extracted_packets_raw)))
        accepted_packets_count = len(consumption.accepted_packets)
        rejected_candidates_count = len(consumption.rejected_candidates)
        if accepted_packets_count > 0:
            accepted_usage = consumption.accepted_packets[0].get("accepted_usage")
        else:
            packet_consumption_rejected = True
    
    primary_root_cause = classify_primary_root_cause(
        reason_if_missing=reason_if_missing,
        hard_recheck_rejected=bool(rejected_risks),
        hard_recheck_too_strict=False, # We don't have a heuristic for this yet
        packet_consumption_rejected=packet_consumption_rejected,
        raw_content_present=raw_content_present,
        requested_item_present=requested_item_present,
        requested_size_present=requested_size_present,
        kcal_candidates_found=kcal_candidates_found,
    )
    
    contributing_factors = []
    if not requested_size_kcal_isolated and kcal_candidates_found:
        contributing_factors.append("size_alias_normalization_gap")
    if reason_if_missing:
        contributing_factors.append(reason_if_missing)
    if primary_root_cause == "extract_missing_parseable_kcal":
        contributing_factors.append("official_source_dynamic_nutrition_not_extractable")
        
    recommended_next_step = (
        "defer_to_manual_product_decision" if primary_root_cause == "official_source_missing_nutrition"
        else "defer_exact_brand_positive_acceptance" if primary_root_cause == "extract_missing_parseable_kcal"
        else "improve_size_alias_normalization_in_extractor" if primary_root_cause == "extract_missing_requested_size"
        else "investigate_hard_recheck_rules" if "hard_recheck" in primary_root_cause
        else "review_packetization_logic"
    )

    return {
        "case_id": case_id,
        "raw_user_input": case_data.get("raw_user_input"),
        "web_query": case_data.get("web_query"),
        "selected_candidate": {
            "source_url": source_url,
            "source_title": selected_candidate.get("source_title"),
            "source_domain": selected_candidate.get("source_domain"),
            "candidate_identity": selected_candidate.get("candidate_identity"),
            "hard_recheck_verdict": selected_candidate.get("hard_recheck_verdict"),
            "rejected_risk": selected_candidate.get("rejected_risk"),
        },
        "extract": {
            "attempted": True,
            "raw_content_present": raw_content_present,
            "requested_item_present": requested_item_present,
            "requested_size_present": requested_size_present,
            "kcal_candidates_found": kcal_candidates_found,
            "requested_size_kcal_isolated": requested_size_kcal_isolated,
        },
        "extract_packet": {
            "created": packet_created,
            "packet_id": packet_id,
            "reason_if_missing": reason_if_missing,
        },
        "hard_recheck": {
            "accepted_for_exact": hard_recheck_accepted,
            "rejected_risks": rejected_risks,
            "failed_field": failed_field,
        },
        "packet_consumption": {
            "accepted_packets_count": accepted_packets_count,
            "accepted_usage": accepted_usage,
            "rejected_candidates_count": rejected_candidates_count,
        },
        "primary_root_cause": primary_root_cause,
        "contributing_factors": contributing_factors,
        "recommended_next_step": recommended_next_step,
    }


async def _main_async(args: argparse.Namespace) -> int:
    canary_path = args.canary_path
    if not canary_path:
        canary_path = find_latest_canary_artifact(Path(args.artifact_dir))
    if not canary_path:
        print("No canary artifact found.")
        return 1
    
    canary_json = json.loads(Path(canary_path).read_text(encoding="utf-8"))
    
    extract_port = TavilyExtractPort()
    report = await diagnose_positive_case(
        canary_json=canary_json,
        case_id="starbucks_latte_positive",
        extract_port=extract_port,
    )
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Diagnostic artifact saved to {output_path}")
    print(json.dumps({"primary_root_cause": report.get("primary_root_cause")}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose B2 exact-brand positive web acceptance")
    parser.add_argument("--canary-path", default=None, help="Path to the canary json artifact.")
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR), help="Dir to search for canary.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output path.")
    args = parser.parse_args(argv)
    
    if not os.getenv("TAVILY_API_KEY"):
         print("WARNING: TAVILY_API_KEY missing, extraction will fail if it fetches the real web")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
