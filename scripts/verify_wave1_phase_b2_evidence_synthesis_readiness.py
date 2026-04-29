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

from app.nutrition.application.packet_mismatch_oracles import (
    exact_claim_mismatch_risks,
    packet_supports_exact_claim as _oracle_packet_supports_exact_claim,
    sibling_variant_risk_present as _oracle_sibling_variant_risk_present,
)

DEFAULT_PHASE_B2_REPORT = ROOT / "artifacts" / "wave1_phase_b2_evidence_synthesis_smoke.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "wave1_phase_b2_evidence_synthesis_readiness.json"
EXPECTED_B1_HANDOFF_KEYS = (
    "b1_gate_scope",
    "smoke_artifact",
    "readiness_artifact",
    "ready_for_phase_b1_implementation",
    "blockers",
    "not_claiming",
)

REQUIRED_SMOKE_CASES = (
    "我吃了一顆茶葉蛋",
    "我喝了一杯珍珠奶茶",
    "我吃了一個便當",
    "我吃了滷味",
    "我吃了豆干、海帶、貢丸的滷味",
    "迷客夏珍珠紅茶拿鐵",
    "松屋特盛牛丼",
    "珍珠奶茶多少熱量？",
    "sibling_negative_milkshop_black_tea_latte_matched_fresh_milk_tea",
    "official_wrong_item_negative",
)
REQUIRED_PACKET_FIELDS = ("packet_id", "truth_level", "source_type", "source_quality_label", "raw_ref")
SAME_ITEM_DIMENSION_FIELDS = (
    "matched_name",
    "canonical_name",
    "brand_match",
    "size_or_serving_match",
    "modifier_match",
    "serving_basis",
    "sibling_variant_risk",
)
SOURCE_QUALITY_LABELS = {
    "internal_exact",
    "internal_generic",
    "official",
    "brand_menu",
    "trusted_database",
    "third_party",
    "semantic_hint",
    "llm_prior",
    "unknown",
}
TRUTH_LEVELS = {"candidate", "hint", "rule_hint"}
SOURCE_TYPES = {"exact_db", "generic_db", "web_search", "web_extract", "taiwan_skill", "llm_prior"}
MATCH_TYPES = {"exact", "alias_exact", "generic", "related", "no_match"}
EVIDENCE_USAGE = {"exact", "anchor", "fallback", "semantic_hint", "rejected"}
EVIDENCE_CONFIDENCE = {"exact", "strong", "moderate", "weak", "insufficient"}
EXACTNESS_POSTURES = {"exact", "estimated", "provisional", "unresolved"}
SAME_ITEM_MATCH_TYPES = {"exact", "alias_exact"}
EXACT_SOURCE_QUALITY = {"internal_exact", "official", "brand_menu"}
EXACT_SOURCE_TYPES = {"exact_db", "web_search", "web_extract"}
FORBIDDEN_PACKET_FINAL_TRUTH_FIELDS = {
    "final_kcal",
    "final_truth",
    "primary_source",
    "ledger_mutation_result",
}
FORBIDDEN_TAIWAN_SKILL_FIELDS = {
    "kcal",
    "kcal_range",
    "likely_kcal",
    "macro",
    "macros",
    "macro_candidate",
    "portion",
    "portion_grams",
}
REQUIRED_CACHE_FIELDS = ("cache_key", "cache_hit", "cache_policy", "unavailable_reason")
REQUIRED_GENERIC_SEED_FOODS = {"茶葉蛋", "珍珠奶茶", "便當", "豆干", "海帶", "貢丸"}
REQUIRED_SEED_FIELDS = ("food_name", "seed_type", "used_by_smoke_case", "fixture_only", "allowed_fields")
GENERIC_SEED_ALLOWED_FIELDS = {"kcal_range", "likely_kcal", "macro_candidate"}
LLM_PRIOR_ALLOWED_CONFIDENCE = {"weak", "insufficient"}
PRODUCER_BACKING_CLASSES = {"runtime_backed", "synthetic_compatibility"}
PRODUCER_SUPPORT_BASES = {
    "generic_anchor",
    "clarify_support",
    "exact_item_card",
    "web_search_rejection",
    "listed_item_runtime_fanout",
    "selected_extract_exact_positive",
    "listed_item_synthetic",
    "web_exact_positive_synthetic",
}
LISTED_ITEM_FANOUT_RESOLUTION_STATUSES = {"resolved", "unresolved"}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_path(path_text: str | None, *, default: Path) -> Path:
    if not path_text:
        return default
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def _project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _add(blockers: list[dict[str, str]], code: str, detail: str) -> None:
    blockers.append({"code": code, "detail": detail})


def _warn(warnings: list[dict[str, str]], code: str, detail: str) -> None:
    warnings.append({"code": code, "detail": detail})


def _contains_key(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        return key_name in value or any(_contains_key(item, key_name) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key_name) for item in value)
    return False


def _contains_any_key(value: Any, keys: set[str]) -> str | None:
    for key in keys:
        if _contains_key(value, key):
            return key
    return None


def _sibling_risk_present(packet: dict[str, Any]) -> bool:
    return _oracle_sibling_variant_risk_present(packet)


def _packet_supports_exact_claim(packet: dict[str, Any]) -> bool:
    return _oracle_packet_supports_exact_claim(packet)


def _packets_by_id(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packets: dict[str, dict[str, Any]] = {}
    for packet in case.get("packets") or []:
        if isinstance(packet, dict) and isinstance(packet.get("packet_id"), str):
            packets[packet["packet_id"]] = packet
    return packets


def _check_smoke_cases(report: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    cases_run = set(str(item) for item in report.get("smoke_cases_run") or [])
    missing = [case for case in REQUIRED_SMOKE_CASES if case not in cases_run]
    if missing:
        _add(blockers, "phase_b2_smoke_case_missing", f"Missing Phase B-2 smoke cases: {', '.join(missing)}.")
    return {"required": list(REQUIRED_SMOKE_CASES), "missing": missing, "passed": not missing}


def _check_non_scope(report: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    non_scope = report.get("non_scope") or {}
    disallowed = [
        key
        for key in (
            "autonomous_nutrition_subagent",
            "independent_llm_evidence_normalizer",
            "full_macro_engine",
            "nutrition_accuracy_production_ready_claim",
        )
        if bool(non_scope.get(key))
    ]
    if disallowed:
        _add(blockers, "phase_b2_non_scope_enabled", f"Phase B-2 gate must not enable: {', '.join(disallowed)}.")
    return {"disallowed": disallowed, "passed": not disallowed}


def _trusted_source_ids(report: dict[str, Any]) -> set[str]:
    manifest = report.get("trusted_source_manifest") or {}
    entries = manifest.get("entries") if isinstance(manifest, dict) else []
    return {
        str(entry.get("source_id"))
        for entry in entries or []
        if isinstance(entry, dict)
        and entry.get("source_quality_label") == "trusted_database"
        and bool(entry.get("approved"))
        and entry.get("source_id")
    }


def _check_trusted_database_policy(report: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    policy = report.get("trusted_database_policy") or {}
    allowlist = set(str(item) for item in policy.get("allowlist") or []) if isinstance(policy, dict) else set()
    manifest_ids = _trusted_source_ids(report)
    unresolved: list[dict[str, Any]] = []
    for case in report.get("cases") or []:
        if not isinstance(case, dict):
            continue
        for packet in case.get("packets") or []:
            if not isinstance(packet, dict) or packet.get("source_quality_label") != "trusted_database":
                continue
            source_id = packet.get("source_id")
            explicit_justification = packet.get("trusted_database_justification") or packet.get("justification")
            source_resolved = isinstance(source_id, str) and source_id in manifest_ids and source_id in allowlist
            if not source_resolved and not explicit_justification:
                unresolved.append({"case_id": case.get("case_id"), "packet_id": packet.get("packet_id"), "source_id": source_id})
    if unresolved:
        _add(
            blockers,
            "trusted_database_source_unresolved",
            "trusted_database packets must resolve source_id to an approved manifest entry/allowlist or include explicit artifact-level justification.",
        )
    return {"unresolved": unresolved, "approved_manifest_ids": sorted(manifest_ids), "passed": not unresolved}


def _llm_prior_packets_or_evidence_present(report: dict[str, Any]) -> bool:
    for case in report.get("cases") or []:
        if not isinstance(case, dict):
            continue
        for packet in case.get("packets") or []:
            if isinstance(packet, dict) and (
                packet.get("source_type") == "llm_prior" or packet.get("source_quality_label") == "llm_prior"
            ):
                return True
        for item in ((case.get("manager_pass_2") or {}).get("item_results") or []):
            if not isinstance(item, dict):
                continue
            for evidence in item.get("evidence_used") or []:
                if isinstance(evidence, dict) and (
                    evidence.get("source_type") == "llm_prior" or evidence.get("source_quality_label") == "llm_prior"
                ):
                    return True
    return False


def _check_llm_prior_trace(report: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    used = _llm_prior_packets_or_evidence_present(report)
    trace = report.get("llm_prior_trace") or {}
    missing_or_invalid = False
    exact_claim_allowed = False
    if used:
        rationale = trace.get("why_no_better_evidence_available") if isinstance(trace, dict) else None
        confidence = trace.get("evidence_confidence") if isinstance(trace, dict) else None
        missing_or_invalid = (
            not isinstance(trace, dict)
            or trace.get("llm_prior_used") is not True
            or not rationale
            or trace.get("exact_claim_allowed") is not False
            or confidence not in LLM_PRIOR_ALLOWED_CONFIDENCE
        )
        exact_claim_allowed = (
            isinstance(trace, dict)
            and (
                trace.get("exact_claim_allowed") is not False
                or trace.get("evidence_confidence") in {"exact", "strong", "moderate"}
            )
        )
    if used and missing_or_invalid:
        _add(
            blockers,
            "llm_prior_trace_missing",
            "LLM prior requires last-resort trace with rationale, exact_claim_allowed=false, and weak/insufficient confidence.",
        )
    if used and exact_claim_allowed:
        _add(blockers, "llm_prior_exact_claim_allowed", "LLM prior must never support exact claims or strong evidence confidence.")
    return {"llm_prior_used": used, "trace_present": bool(trace), "passed": not (used and (missing_or_invalid or exact_claim_allowed))}


def _check_minimal_db_seed_manifest(report: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    manifest = report.get("minimal_db_seed_manifest")
    if not isinstance(manifest, dict):
        _add(blockers, "minimal_db_seed_manifest_missing", "Phase B-2 readiness requires minimal_db_seed_manifest.")
        return {"missing": True, "passed": False}
    seeds = manifest.get("seeds")
    if not isinstance(seeds, list):
        _add(blockers, "minimal_db_seed_manifest_missing", "minimal_db_seed_manifest must include a seeds list.")
        return {"missing": True, "passed": False}

    smoke_cases = set(str(item) for item in report.get("smoke_cases_run") or [])
    found_generic = {
        str(seed.get("food_name"))
        for seed in seeds
        if isinstance(seed, dict) and seed.get("seed_type") == "generic" and seed.get("food_name")
    }
    missing_default = sorted(REQUIRED_GENERIC_SEED_FOODS - found_generic)
    malformed: list[dict[str, Any]] = []
    exact_truth: list[dict[str, Any]] = []
    outside_scope: list[dict[str, Any]] = []
    exact_runtime_seeds: list[dict[str, Any]] = []
    for index, seed in enumerate(seeds):
        if not isinstance(seed, dict):
            malformed.append({"index": index, "reason": "seed_not_object"})
            continue
        missing_fields = [field for field in REQUIRED_SEED_FIELDS if field not in seed]
        if missing_fields:
            malformed.append({"index": index, "missing": missing_fields})
        seed_type = seed.get("seed_type")
        fixture_only = bool(seed.get("fixture_only"))
        used_by = str(seed.get("used_by_smoke_case") or "")
        if seed_type == "generic":
            allowed_fields = set(str(item) for item in seed.get("allowed_fields") or [])
            forbidden_allowed_fields = sorted(allowed_fields - GENERIC_SEED_ALLOWED_FIELDS)
            if forbidden_allowed_fields or seed.get("source_quality_label") == "internal_exact" or seed.get("match_type") in SAME_ITEM_MATCH_TYPES:
                exact_truth.append({"index": index, "food_name": seed.get("food_name"), "forbidden": forbidden_allowed_fields})
        elif seed_type == "exact" and not fixture_only:
            exact_runtime_seeds.append({"index": index, "food_name": seed.get("food_name")})
        elif seed_type not in {"generic", "exact"}:
            malformed.append({"index": index, "seed_type": seed_type})
        if used_by not in smoke_cases and not fixture_only and not bool(seed.get("out_of_scope")):
            outside_scope.append({"index": index, "food_name": seed.get("food_name"), "used_by_smoke_case": used_by})
    if missing_default or malformed:
        _add(blockers, "minimal_db_seed_manifest_missing", "minimal_db_seed_manifest must include all required smoke generic seeds with required fields.")
    if exact_truth or exact_runtime_seeds:
        _add(blockers, "minimal_db_seed_contains_exact_truth", "Generic seeds must not contain brand exact truth; real exact seeds must stay empty in this slice.")
    if outside_scope:
        _add(blockers, "minimal_db_seed_outside_smoke_scope", "Extra non-smoke seeds must be fixture_only or explicitly out_of_scope.")
    return {
        "missing_default_generic_seeds": missing_default,
        "malformed": malformed,
        "exact_truth": exact_truth,
        "outside_scope": outside_scope,
        "exact_runtime_seeds": exact_runtime_seeds,
        "passed": not missing_default and not malformed and not exact_truth and not outside_scope and not exact_runtime_seeds,
    }


def _check_runtime_trace_parity(report: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    parity = report.get("runtime_trace_parity")
    if not isinstance(parity, dict):
        _add(blockers, "runtime_trace_parity_failed", "runtime_trace_parity must be present; synthetic-only artifacts may use status=not_applicable.")
        return {"missing": True, "passed": False}
    passed = (
        parity.get("required_core_fields_match") is True
        and parity.get("extra_fields_allowed") is True
        and parity.get("renamed_core_fields_allowed") is False
        and parity.get("missing_core_fields_allowed") is False
    )
    if not passed:
        _add(
            blockers,
            "runtime_trace_parity_failed",
            "Runtime trace may add metadata but must not rename or omit canonical packet, Pass 2, mutation, or renderer fields.",
        )
    return {"status": parity.get("status"), "passed": passed}


def _check_b1_green_handoff_snapshot(report: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    snapshot = report.get("b1_green_handoff_snapshot")
    if not isinstance(snapshot, dict):
        _add(blockers, "b1_green_handoff_snapshot_missing", "Phase B-2 gate requires a B-1 green handoff snapshot.")
        return {"missing": True, "passed": False}

    missing = [field for field in EXPECTED_B1_HANDOFF_KEYS if field not in snapshot]
    if missing:
        _add(blockers, "b1_green_handoff_snapshot_incomplete", "B-1 green handoff snapshot must keep the canonical handoff fields.")

    gate_scope_ok = snapshot.get("b1_gate_scope") == "Phase B-1 minimal tool-loop full natural-probe"
    ready_ok = snapshot.get("ready_for_phase_b1_implementation") is True
    blockers_empty = list(snapshot.get("blockers") or []) == []
    not_claiming_ok = snapshot.get("not_claiming") == "whole Wave 1 completion"
    smoke_artifact_ok = isinstance(snapshot.get("smoke_artifact"), str) and bool(str(snapshot.get("smoke_artifact")).strip())
    readiness_artifact_ok = isinstance(snapshot.get("readiness_artifact"), str) and bool(str(snapshot.get("readiness_artifact")).strip())

    if not gate_scope_ok or not ready_ok or not blockers_empty or not not_claiming_ok or not smoke_artifact_ok or not readiness_artifact_ok:
        _add(
            blockers,
            "b1_green_handoff_snapshot_invalid",
            "B-1 handoff snapshot must record a green Phase B-1 natural-probe handoff without claiming whole Wave 1 completion.",
        )
    return {
        "missing": missing,
        "gate_scope_ok": gate_scope_ok,
        "ready_ok": ready_ok,
        "blockers_empty": blockers_empty,
        "not_claiming_ok": not_claiming_ok,
        "smoke_artifact_ok": smoke_artifact_ok,
        "readiness_artifact_ok": readiness_artifact_ok,
        "passed": not missing and gate_scope_ok and ready_ok and blockers_empty and not_claiming_ok and smoke_artifact_ok and readiness_artifact_ok,
    }


def _check_packet_contract(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    invalid_packets: list[dict[str, Any]] = []
    packets = case.get("packets") or []
    for index, packet in enumerate(packets):
        if not isinstance(packet, dict):
            invalid_packets.append({"index": index, "reason": "packet_not_object"})
            continue
        missing = [field for field in REQUIRED_PACKET_FIELDS if field not in packet]
        if missing:
            _add(blockers, "packet_contract_missing_required_field", "Every B-2 packet must include packet_id, truth_level, source_type, source_quality_label, and raw_ref.")
            invalid_packets.append({"index": index, "missing": missing})
        if packet.get("truth_level") not in TRUTH_LEVELS:
            _add(blockers, "packet_truth_level_invalid", "B-2 read/packetizer packets must use candidate, hint, or rule_hint.")
            invalid_packets.append({"index": index, "truth_level": packet.get("truth_level")})
        if packet.get("source_type") not in SOURCE_TYPES:
            _add(blockers, "packet_source_type_invalid", "B-2 packet source_type must use the evidence source enum.")
            invalid_packets.append({"index": index, "source_type": packet.get("source_type")})
        if packet.get("source_quality_label") not in SOURCE_QUALITY_LABELS:
            _add(blockers, "packet_source_quality_label_invalid", "B-2 packet source_quality_label must use the Phase B-2 enum.")
            invalid_packets.append({"index": index, "source_quality_label": packet.get("source_quality_label")})
        final_truth_key = _contains_any_key(packet, FORBIDDEN_PACKET_FINAL_TRUTH_FIELDS)
        if final_truth_key:
            _add(blockers, "packet_final_truth_present", "Candidate packets must not contain final truth fields such as final_kcal or primary_source.")
            invalid_packets.append({"index": index, "final_truth_key": final_truth_key})
        if packet.get("source_type") == "generic_db" and packet.get("match_type") in SAME_ITEM_MATCH_TYPES:
            _add(blockers, "generic_db_marked_exact", "Generic DB packets must not claim exact or alias_exact match_type.")
            invalid_packets.append({"index": index, "reason": "generic_db_marked_exact"})
        if packet.get("source_type") == "generic_db" and packet.get("source_quality_label") == "internal_exact":
            _add(blockers, "generic_db_marked_exact", "Generic DB packets must not use internal_exact source quality.")
            invalid_packets.append({"index": index, "reason": "generic_db_internal_exact"})
        if packet.get("source_type") == "taiwan_skill":
            forbidden_key = _contains_any_key(packet, FORBIDDEN_TAIWAN_SKILL_FIELDS)
            if forbidden_key:
                _add(blockers, "taiwan_skill_contains_nutrition_truth", "Taiwan Skill packets may contain semantic hints only, not kcal, macro, or portion truth.")
                invalid_packets.append({"index": index, "forbidden_skill_key": forbidden_key})
        elif packet.get("source_type") in {"exact_db", "generic_db", "web_search", "web_extract"}:
            missing_dimensions = [field for field in SAME_ITEM_DIMENSION_FIELDS if field not in packet]
            if missing_dimensions:
                _add(blockers, "candidate_same_item_dimensions_missing", "Candidate packets must include same-item dimensions.")
                invalid_packets.append({"index": index, "missing_same_item_dimensions": missing_dimensions})
        match_type = packet.get("match_type")
        if match_type is not None and match_type not in MATCH_TYPES:
            _add(blockers, "packet_match_type_invalid", "match_type must distinguish exact, alias_exact, generic, related, or no_match.")
            invalid_packets.append({"index": index, "match_type": match_type})
    return {"invalid_packets": invalid_packets, "passed": not invalid_packets}


def _check_producer_trace(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    trace = case.get("producer_trace")
    if not isinstance(trace, dict):
        _add(blockers, "producer_trace_missing", "Official B-2 producer cases must declare report-only producer_trace provenance.")
        return {"missing": True, "passed": False}

    missing = [field for field in ("backing_class", "support_basis", "compatibility_reason") if field not in trace]
    if missing:
        _add(
            blockers,
            "producer_trace_incomplete",
            "producer_trace must include backing_class, support_basis, and compatibility_reason for report/readiness diagnostics.",
        )

    backing_class = trace.get("backing_class")
    support_basis = trace.get("support_basis")
    compatibility_reason = trace.get("compatibility_reason")

    if backing_class not in PRODUCER_BACKING_CLASSES:
        _add(blockers, "producer_trace_invalid_backing_class", "producer_trace.backing_class must use the B-2 honesty diagnostic enum.")
    if support_basis not in PRODUCER_SUPPORT_BASES:
        _add(blockers, "producer_trace_invalid_support_basis", "producer_trace.support_basis must use the B-2 honesty diagnostic enum.")

    if backing_class == "synthetic_compatibility" and not str(compatibility_reason or "").strip():
        _add(
            blockers,
            "producer_trace_synthetic_missing_reason",
            "Synthetic compatibility cases must state why the official producer is not yet runtime-backed.",
        )
    if backing_class == "runtime_backed" and compatibility_reason is not None:
        _add(
            blockers,
            "producer_trace_runtime_backed_has_reason",
            "Runtime-backed producer cases must keep compatibility_reason=null because provenance diagnostics are not product semantics.",
        )

    return {
        "backing_class": backing_class,
        "support_basis": support_basis,
        "compatibility_reason": compatibility_reason,
        "missing": missing,
        "passed": not missing
        and backing_class in PRODUCER_BACKING_CLASSES
        and support_basis in PRODUCER_SUPPORT_BASES
        and not (
            (backing_class == "synthetic_compatibility" and not str(compatibility_reason or "").strip())
            or (backing_class == "runtime_backed" and compatibility_reason is not None)
        ),
    }


SOURCE_SELECTION_PATHS = {"exact_db", "generic_anchor", "listed_item_fanout", "ask_user"}
SOURCE_SELECTION_EVIDENCE = {
    "exact_item_card",
    "generic_anchor_packet",
    "generic_anchor_packet_per_listed_item",
    "clarify_support",
}
SOURCE_SELECTION_POLICY_STATUS = {"source_selection_only", "pending_or_provisional"}


def _check_source_selection(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    selection = case.get("source_selection")
    if not isinstance(selection, dict):
        _add(blockers, "source_selection_missing", "Official B-2 producer cases must include source_selection from the B2 source-selection owner.")
        return {"missing": True, "passed": False}

    missing = [
        field
        for field in (
            "source_path",
            "evidence_required",
            "reason",
            "web_allowed",
            "read_only",
            "mutation_allowed",
            "decides_logged_or_draft",
            "product_policy_status",
        )
        if field not in selection
    ]
    if missing:
        _add(blockers, "source_selection_incomplete", "source_selection must expose path, evidence, web, read-only, mutation, and ownership fields.")

    if selection.get("source_path") not in SOURCE_SELECTION_PATHS:
        _add(blockers, "source_selection_path_invalid", "source_selection.source_path must use the B2 source-selection enum.")
    if selection.get("evidence_required") not in SOURCE_SELECTION_EVIDENCE:
        _add(blockers, "source_selection_evidence_invalid", "source_selection.evidence_required must use the B2 evidence enum.")
    if selection.get("product_policy_status") not in SOURCE_SELECTION_POLICY_STATUS:
        _add(blockers, "source_selection_policy_status_invalid", "source_selection must declare source-only or pending/provisional policy status.")
    if selection.get("web_allowed") is not False:
        _add(blockers, "source_selection_web_activation_forbidden", "B2 deterministic closure must not activate web from source selection.")
    if selection.get("decides_logged_or_draft") is not False:
        _add(blockers, "source_selection_semantic_owner_forbidden", "Source selection must not decide logged/draft semantics.")
    if selection.get("read_only") is True and selection.get("mutation_allowed") is not False:
        _add(blockers, "source_selection_query_mutation_allowed", "Read-only source selection must not allow mutation.")

    passed = (
        not missing
        and selection.get("source_path") in SOURCE_SELECTION_PATHS
        and selection.get("evidence_required") in SOURCE_SELECTION_EVIDENCE
        and selection.get("product_policy_status") in SOURCE_SELECTION_POLICY_STATUS
        and selection.get("web_allowed") is False
        and selection.get("decides_logged_or_draft") is False
        and not (selection.get("read_only") is True and selection.get("mutation_allowed") is not False)
    )
    return {"missing": False, "missing_fields": missing, "passed": passed}


def _check_listed_item_fanout(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    trace = case.get("listed_item_fanout")
    producer_trace = case.get("producer_trace")
    support_basis = producer_trace.get("support_basis") if isinstance(producer_trace, dict) else None
    if support_basis != "listed_item_runtime_fanout":
        return {"required": False, "passed": True}

    if not isinstance(trace, dict):
        _add(
            blockers,
            "listed_item_fanout_trace_missing",
            "listed_item_runtime_fanout cases must expose per-item fanout trace for report/readiness diagnostics only.",
        )
        return {"required": True, "missing": True, "passed": False}

    resolutions = trace.get("resolutions")
    if not isinstance(resolutions, list) or not resolutions:
        _add(
            blockers,
            "listed_item_fanout_trace_incomplete",
            "listed_item_runtime_fanout cases must include non-empty per-item resolutions.",
        )
        return {"required": True, "missing": False, "passed": False, "invalid_resolutions": []}

    invalid_resolutions: list[dict[str, Any]] = []
    for index, resolution in enumerate(resolutions):
        if not isinstance(resolution, dict):
            _add(
                blockers,
                "listed_item_fanout_trace_incomplete",
                "listed_item fanout resolutions must be objects with per-item runtime diagnostics.",
            )
            invalid_resolutions.append({"index": index, "reason": "not_object"})
            continue

        missing = [
            field
            for field in (
                "listed_item",
                "resolution_status",
                "defer_reason",
                "clarify_support_present",
                "packet_ids",
            )
            if field not in resolution
        ]
        if missing:
            _add(
                blockers,
                "listed_item_fanout_trace_incomplete",
                "listed_item fanout resolutions must keep listed_item, resolution_status, defer_reason, clarify_support_present, and packet_ids.",
            )
            invalid_resolutions.append({"index": index, "missing": missing})
            continue

        resolution_status = resolution.get("resolution_status")
        packet_ids = resolution.get("packet_ids")
        defer_reason = resolution.get("defer_reason")
        clarify_support_present = resolution.get("clarify_support_present")
        if resolution_status not in LISTED_ITEM_FANOUT_RESOLUTION_STATUSES:
            _add(
                blockers,
                "listed_item_fanout_trace_invalid_status",
                "listed_item fanout resolution_status must be resolved or unresolved.",
            )
            invalid_resolutions.append({"index": index, "resolution_status": resolution_status})
        if not isinstance(packet_ids, list) or any(not isinstance(packet_id, str) or not packet_id.strip() for packet_id in packet_ids):
            _add(
                blockers,
                "listed_item_fanout_trace_incomplete",
                "listed_item fanout packet_ids must be a list of packet ids for per-item runtime diagnostics.",
            )
            invalid_resolutions.append({"index": index, "packet_ids": packet_ids})
        if not isinstance(clarify_support_present, bool):
            _add(
                blockers,
                "listed_item_fanout_trace_incomplete",
                "listed_item fanout clarify_support_present must be boolean for report/readiness diagnostics.",
            )
            invalid_resolutions.append({"index": index, "clarify_support_present": clarify_support_present})

        if resolution_status == "resolved":
            if not packet_ids:
                _add(
                    blockers,
                    "listed_item_fanout_trace_incomplete",
                    "Resolved listed_item fanout entries must cite runtime packet_ids.",
                )
                invalid_resolutions.append({"index": index, "reason": "resolved_without_packets"})
            if defer_reason is not None:
                _add(
                    blockers,
                    "listed_item_fanout_trace_incomplete",
                    "Resolved listed_item fanout entries must keep defer_reason=null.",
                )
                invalid_resolutions.append({"index": index, "reason": "resolved_with_defer_reason"})
        elif resolution_status == "unresolved":
            if packet_ids:
                _add(
                    blockers,
                    "listed_item_fanout_trace_incomplete",
                    "Unresolved listed_item fanout entries must not claim runtime packet_ids.",
                )
                invalid_resolutions.append({"index": index, "reason": "unresolved_with_packets"})
            if not str(defer_reason or "").strip():
                _add(
                    blockers,
                    "listed_item_fanout_trace_incomplete",
                    "Unresolved listed_item fanout entries must expose a per-item defer_reason.",
                )
                invalid_resolutions.append({"index": index, "reason": "unresolved_without_defer_reason"})

    return {
        "required": True,
        "missing": False,
        "resolutions": _json_safe(resolutions),
        "invalid_resolutions": invalid_resolutions,
        "passed": not invalid_resolutions,
    }


def _check_selected_extract_exact_positive(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    producer_trace = case.get("producer_trace")
    support_basis = producer_trace.get("support_basis") if isinstance(producer_trace, dict) else None
    if support_basis != "selected_extract_exact_positive":
        return {"required": False, "passed": True}

    packets = _packets_by_id(case)
    extract_policy = case.get("extract_policy") or {}
    selected_packet_id = extract_policy.get("selected_search_packet_id")
    selected_packet = packets.get(selected_packet_id) if isinstance(selected_packet_id, str) else None
    extract_packets = [
        packet
        for packet in case.get("packets") or []
        if isinstance(packet, dict) and packet.get("source_type") == "web_extract"
    ]

    if not isinstance(selected_packet, dict) or selected_packet.get("source_type") != "web_search":
        _add(
            blockers,
            "selected_extract_policy_selected_packet_not_web_search",
            "Runtime-backed selected extract cases must point extract_policy.selected_search_packet_id at an in-case web_search packet.",
        )

    linked_extract_packets = [
        packet
        for packet in extract_packets
        if packet.get("selected_search_packet_id") == selected_packet_id
    ]
    if not linked_extract_packets:
        _add(
            blockers,
            "selected_extract_exact_positive_missing_web_extract_packet",
            "Runtime-backed selected extract cases must include at least one linked web_extract packet.",
        )

    exact_web_extract_packet_ids = {
        str(packet.get("packet_id") or "")
        for packet in linked_extract_packets
        if packet.get("supports_exact_claim") is True
        and not tuple(str(risk).strip() for risk in packet.get("hard_recheck_risks", []) if str(risk).strip())
    }

    item_results = ((case.get("manager_pass_2") or {}).get("item_results") or [])
    exact_evidence_packet_ids: list[str] = []
    web_search_exact_evidence_ids: list[str] = []
    for item in item_results:
        if not isinstance(item, dict):
            continue
        for evidence in item.get("evidence_used") or []:
            if not isinstance(evidence, dict) or evidence.get("usage") != "exact":
                continue
            packet_id = str(evidence.get("packet_id") or "")
            exact_evidence_packet_ids.append(packet_id)
            packet = packets.get(packet_id)
            if isinstance(packet, dict) and packet.get("source_type") == "web_search":
                web_search_exact_evidence_ids.append(packet_id)

    if web_search_exact_evidence_ids:
        _add(
            blockers,
            "selected_extract_exact_result_not_backed_by_web_extract",
            "Runtime-backed exact-positive web cases must cite accepted web_extract packets, not web_search packets, as exact evidence.",
        )
    if not exact_web_extract_packet_ids or not any(packet_id in exact_web_extract_packet_ids for packet_id in exact_evidence_packet_ids):
        _add(
            blockers,
            "selected_extract_exact_positive_missing_accepted_web_extract",
            "Runtime-backed selected extract cases must contain an accepted exact-support web_extract packet used by Manager Pass 2.",
        )

    return {
        "required": True,
        "selected_search_packet_id": selected_packet_id,
        "linked_extract_packet_ids": [packet.get("packet_id") for packet in linked_extract_packets],
        "exact_evidence_packet_ids": exact_evidence_packet_ids,
        "passed": not web_search_exact_evidence_ids
        and bool(exact_web_extract_packet_ids)
        and any(packet_id in exact_web_extract_packet_ids for packet_id in exact_evidence_packet_ids)
        and isinstance(selected_packet, dict)
        and selected_packet.get("source_type") == "web_search",
    }


def _evidence_packet(entry: dict[str, Any], packets: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    packet_id = entry.get("packet_id")
    return packets.get(packet_id) if isinstance(packet_id, str) else None


def _check_manager_pass_2(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    packets = _packets_by_id(case)
    invalid_evidence: list[dict[str, Any]] = []
    unresolved_ledger_violations: list[dict[str, Any]] = []
    exactness_violations: list[dict[str, Any]] = []
    rejected_candidate_violations: list[dict[str, Any]] = []
    final_mapping_violations: list[dict[str, Any]] = []
    item_results = ((case.get("manager_pass_2") or {}).get("item_results") or [])
    for item_index, item in enumerate(item_results):
        if not isinstance(item, dict):
            continue
        final_mapping = item.get("final_mapping")
        if not isinstance(final_mapping, dict):
            _add(blockers, "b2_final_mapping_missing", "Manager Pass 2 item_results must carry B2 final_mapping from the B2 final mapping owner.")
            final_mapping_violations.append({"item_index": item_index, "reason": "missing"})
        elif final_mapping.get("final_mapping_owner") != "b2_final_mapping":
            _add(blockers, "b2_final_mapping_owner_invalid", "final_mapping must be owned by b2_final_mapping.")
            final_mapping_violations.append({"item_index": item_index, "owner": final_mapping.get("final_mapping_owner")})
        elif item.get("ledger_status") != final_mapping.get("ledger_status"):
            _add(blockers, "b2_final_mapping_ledger_status_mismatch", "ledger_status must be derived from B2 final_mapping, not compatibility helper logic.")
            final_mapping_violations.append(
                {
                    "item_index": item_index,
                    "ledger_status": item.get("ledger_status"),
                    "final_mapping_ledger_status": final_mapping.get("ledger_status"),
                }
            )
        evidence_confidence = item.get("evidence_confidence")
        exactness_posture = item.get("exactness_posture")
        if evidence_confidence not in EVIDENCE_CONFIDENCE:
            _add(blockers, "evidence_confidence_invalid", "Manager Pass 2 must output evidence_confidence from the B-2 enum.")
            exactness_violations.append({"item_index": item_index, "evidence_confidence": evidence_confidence})
        if exactness_posture not in EXACTNESS_POSTURES:
            _add(blockers, "exactness_posture_invalid", "Manager Pass 2 must output exactness_posture from the B-2 enum.")
            exactness_violations.append({"item_index": item_index, "exactness_posture": exactness_posture})

        exact_supporting_packets: list[str] = []
        for evidence_index, evidence in enumerate(item.get("evidence_used") or []):
            if not isinstance(evidence, dict):
                _add(blockers, "evidence_used_missing_packet_ref", "evidence_used entries must be packet-ref objects, not free text.")
                invalid_evidence.append({"item_index": item_index, "evidence_index": evidence_index, "reason": "not_object"})
                continue
            missing = [
                field
                for field in ("packet_id", "source_type", "source_quality_label", "usage", "reason")
                if field not in evidence
            ]
            if missing:
                _add(blockers, "evidence_used_missing_packet_ref", "Manager Pass 2 evidence_used must cite packet_id, source_type, source_quality_label, usage, and reason.")
                invalid_evidence.append({"item_index": item_index, "evidence_index": evidence_index, "missing": missing})
                continue
            if evidence.get("usage") not in EVIDENCE_USAGE:
                _add(blockers, "evidence_used_usage_invalid", "evidence_used.usage must use exact, anchor, fallback, semantic_hint, or rejected.")
                invalid_evidence.append({"item_index": item_index, "evidence_index": evidence_index, "usage": evidence.get("usage")})
            packet = _evidence_packet(evidence, packets)
            if packet is None:
                _add(blockers, "evidence_used_unknown_packet_id", "Manager Pass 2 evidence_used must cite a packet_id present in the case packets.")
                invalid_evidence.append({"item_index": item_index, "evidence_index": evidence_index, "packet_id": evidence.get("packet_id")})
                continue
            if evidence.get("usage") == "exact":
                mismatch_risks = set(exact_claim_mismatch_risks(packet))
                if "wrong_item" in mismatch_risks:
                    _add(blockers, "wrong_item_used_as_exact", "Different-item candidates must not support exact claims.")
                    invalid_evidence.append({"item_index": item_index, "packet_id": packet.get("packet_id"), "reason": "wrong_item"})
                if "sibling_variant" in mismatch_risks:
                    _add(blockers, "sibling_variant_used_as_exact", "Sibling or related variants must not support exact claims.")
                    invalid_evidence.append({"item_index": item_index, "packet_id": packet.get("packet_id"), "reason": "sibling_exact"})
                if "wrong_size" in mismatch_risks:
                    _add(blockers, "wrong_size_used_as_exact", "Different size or serving candidates must not support exact claims.")
                    invalid_evidence.append({"item_index": item_index, "packet_id": packet.get("packet_id"), "reason": "wrong_size"})
                if "wrong_modifier" in mismatch_risks:
                    _add(blockers, "wrong_modifier_used_as_exact", "Different modifier candidates must not support exact claims.")
                    invalid_evidence.append({"item_index": item_index, "packet_id": packet.get("packet_id"), "reason": "wrong_modifier"})
                if "insufficient_evidence" in mismatch_risks:
                    _add(blockers, "insufficient_evidence_used_as_exact", "Exact claims require explicit serving or portion evidence.")
                    invalid_evidence.append({"item_index": item_index, "packet_id": packet.get("packet_id"), "reason": "insufficient_evidence"})
                if packet.get("source_type") == "llm_prior":
                    _add(blockers, "llm_prior_used_for_exact_claim", "LLM prior is last resort and must not support exact claims.")
                    invalid_evidence.append({"item_index": item_index, "packet_id": packet.get("packet_id"), "reason": "llm_prior_exact"})
                if not _packet_supports_exact_claim(packet):
                    _add(blockers, "exact_claim_without_same_item_evidence", "Exact claims require same-item match and exact internal or official/brand evidence.")
                    invalid_evidence.append({"item_index": item_index, "packet_id": packet.get("packet_id"), "reason": "not_exact_evidence"})
                else:
                    exact_supporting_packets.append(str(packet.get("packet_id")))

        if exactness_posture == "exact" and not exact_supporting_packets:
            _add(blockers, "exactness_guard_failed", "exact exactness_posture requires exact internal DB or official/brand same-item evidence.")
            exactness_violations.append({"item_index": item_index, "reason": "no_exact_support"})
        if exactness_posture == "unresolved" and item.get("ledger_status") == "included":
            _add(blockers, "unresolved_entered_ledger", "unresolved exactness_posture must forbid ledger inclusion.")
            unresolved_ledger_violations.append({"item_index": item_index})

        rejected = item.get("rejected_candidates") or []
        rejected_ids = {
            entry.get("packet_id")
            for entry in rejected
            if isinstance(entry, dict) and isinstance(entry.get("packet_id"), str)
        }
        for rejected_entry in rejected:
            if not isinstance(rejected_entry, dict):
                _add(blockers, "rejected_candidate_missing_packet_ref", "rejected_candidates entries must cite packet_id, risk_type, and reason.")
                rejected_candidate_violations.append({"item_index": item_index, "reason": "not_object"})
                continue
            missing_rejected = [field for field in ("packet_id", "risk_type", "reason") if field not in rejected_entry]
            if missing_rejected:
                _add(blockers, "rejected_candidate_missing_packet_ref", "rejected_candidates entries must cite packet_id, risk_type, and reason.")
                rejected_candidate_violations.append({"item_index": item_index, "missing": missing_rejected})
        anchor_ids = {
            evidence.get("packet_id")
            for evidence in item.get("evidence_used") or []
            if isinstance(evidence, dict) and evidence.get("usage") == "anchor"
        }
        for packet_id, packet in packets.items():
            should_reject_or_anchor = _sibling_risk_present(packet) or packet.get("match_type") in {"related", "no_match"}
            if (
                packet.get("source_type") == "web_search"
                and should_reject_or_anchor
                and packet_id in anchor_ids
            ):
                _add(
                    blockers,
                    "web_search_mismatch_used_as_anchor",
                    "Current runtime-slice official B-2 artifacts must reject mismatched web_search candidates instead of downgrading them to anchor evidence.",
                )
                rejected_candidate_violations.append({"item_index": item_index, "packet_id": packet_id, "reason": "web_search_anchor"})
            if should_reject_or_anchor and packet_id not in rejected_ids and packet_id not in anchor_ids:
                _add(
                    blockers,
                    "sibling_candidate_not_rejected_or_downgraded",
                    "Sibling or wrong-item candidates must be rejected or explicitly downgraded using existing evidence usage enums.",
                )
                rejected_candidate_violations.append({"item_index": item_index, "packet_id": packet_id})
    return {
        "invalid_evidence": invalid_evidence,
        "exactness_violations": exactness_violations,
        "unresolved_ledger_violations": unresolved_ledger_violations,
        "rejected_candidate_violations": rejected_candidate_violations,
        "final_mapping_violations": final_mapping_violations,
        "passed": not invalid_evidence
        and not exactness_violations
        and not unresolved_ledger_violations
        and not rejected_candidate_violations
        and not final_mapping_violations,
    }


def _check_extract_policy(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    policy = case.get("extract_policy") or {}
    packets = _packets_by_id(case)
    required = (
        "selected_search_packet_id",
        "extract_reason",
        "extract_allowed_by_policy",
        "max_extract_urls",
        "extract_count",
    )
    missing = [field for field in required if field not in policy]
    if missing:
        _add(blockers, "extract_policy_trace_incomplete", "Selected extract policy must trace selected packet, reason, policy decision, max URLs, and count.")
    selected = policy.get("selected_search_packet_id")
    extract_count = int(policy.get("extract_count") or 0)
    max_extract_urls = int(policy.get("max_extract_urls") or 0)
    all_web = selected == "*" or (extract_count > 0 and not selected)
    too_many = max_extract_urls >= 0 and extract_count > max_extract_urls
    selected_missing = isinstance(selected, str) and selected not in {"*"} and selected not in packets
    if all_web or too_many:
        _add(blockers, "extract_policy_all_web_extract", "B-2 selected extract forbids all-web extract and must respect max_extract_urls.")
    if selected_missing:
        _add(blockers, "extract_policy_selected_packet_missing", "selected_search_packet_id must refer to a packet in the case.")
    return {
        "missing": missing,
        "all_web": all_web,
        "too_many": too_many,
        "selected_missing": selected_missing,
        "passed": not missing and not all_web and not too_many and not selected_missing,
    }


def _check_mutation(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    mutation = case.get("mutation") or {}
    missing = [field for field in ("mutation_attempted", "reason", "mutation_result") if field not in mutation]
    if missing:
        _add(blockers, "mutation_trace_incomplete", "B-2 cases must keep explicit mutation trace.")
    no_mutation_query = case.get("input_message") == "珍珠奶茶多少熱量？"
    no_mutation_violation = no_mutation_query and bool(mutation.get("mutation_attempted"))
    if no_mutation_violation:
        _add(blockers, "no_mutation_query_mutated_ledger", "Nutrition info query may use read tools but must not mutate.")
    return {"missing": missing, "no_mutation_violation": no_mutation_violation, "passed": not missing and not no_mutation_violation}


def _check_renderer(case: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    renderer = case.get("renderer") or {}
    renderer_input = renderer.get("input")
    missing_input: list[str] = []
    if not isinstance(renderer_input, dict):
        missing_input = ["input"]
    else:
        missing_input = [field for field in ("allowed_facts", "forbidden_claims", "item_results", "ledger_mutation_result") if field not in renderer_input]
    if missing_input:
        _add(blockers, "renderer_input_incomplete", "Renderer input must carry allowed_facts, forbidden_claims, item_results, and ledger_mutation_result.")
    response = str(renderer.get("final_response") or "")
    allowed_text = json.dumps(renderer_input or {}, ensure_ascii=False)
    has_exact_wording = "資料顯示" in response
    exact_allowed_by_input = "資料顯示" in allowed_text
    item_results = ((case.get("manager_pass_2") or {}).get("item_results") or [])
    response_exactness_allowed = any(isinstance(item, dict) and item.get("exactness_posture") == "exact" for item in item_results)
    unsupported_kcal_claim = "999" in response and "999" not in allowed_text
    if (has_exact_wording and (not exact_allowed_by_input or not response_exactness_allowed)) or unsupported_kcal_claim:
        _add(blockers, "renderer_exactness_wording_exceeds_input", "Renderer exactness wording must not exceed RendererInput or item exactness posture.")
    return {
        "missing_input": missing_input,
        "has_exact_wording": has_exact_wording,
        "response_exactness_allowed": response_exactness_allowed,
        "unsupported_kcal_claim": unsupported_kcal_claim,
        "passed": not missing_input and not ((has_exact_wording and (not exact_allowed_by_input or not response_exactness_allowed)) or unsupported_kcal_claim),
    }


def _check_cache(case: dict[str, Any], blockers: list[dict[str, str]], warnings: list[dict[str, str]]) -> dict[str, Any]:
    cache = case.get("cache")
    if not isinstance(cache, dict):
        _warn(warnings, "cache_metadata_missing", "Cache metadata should keep stable nullable fields even before cache implementation.")
        return {"missing": list(REQUIRED_CACHE_FIELDS), "passed": False}
    missing = [field for field in REQUIRED_CACHE_FIELDS if field not in cache]
    if missing:
        _warn(warnings, "cache_metadata_incomplete", "Cache metadata should keep stable nullable fields even before cache implementation.")
    return {"missing": missing, "passed": not missing}


def _honesty_gate_status() -> dict[str, bool]:
    return {
        "snippet_final_truth_blocked": True,
        "wrong_item_blocked": True,
        "sibling_variant_blocked": True,
        "wrong_size_blocked": True,
        "wrong_modifier_blocked": True,
        "insufficient_evidence_blocked": True,
    }


REQUIRED_ARTIFACT_CHAIN_NODES = [
    "source_selection",
    "candidate_packets",
    "exact_hard_recheck",
    "packet_consumption",
    "synthesis_item_results",
    "final_mapping",
    "readiness_summary",
]
PENDING_PRODUCT_POLICY_IDS = {
    "homemade_dish_minimum_estimability",
    "tavily_exact_brand_scope",
    "llm_synthesis_trust_boundary",
    "founder_human_e2e_required_journeys",
}


def _artifact_completeness_audit(
    report_data: dict[str, Any],
    *,
    case_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    missing_chain_nodes: list[dict[str, Any]] = []
    rejected_packet_evidence_ref_violations: list[dict[str, Any]] = []
    source_selection_semantic_owner_violations: list[dict[str, Any]] = []
    producer_final_mapping_owner_violations: list[dict[str, Any]] = []
    strict_exact_estimability_violations: list[dict[str, Any]] = []

    for case in report_data.get("cases") or []:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        packets = _packets_by_id(case)
        item_results = ((case.get("manager_pass_2") or {}).get("item_results") or [])
        source_selection = case.get("source_selection")

        if not isinstance(source_selection, dict):
            missing_chain_nodes.append({"case_id": case_id, "node": "source_selection"})
        elif source_selection.get("decides_logged_or_draft") is not False:
            source_selection_semantic_owner_violations.append({"case_id": case_id})

        if not packets:
            missing_chain_nodes.append({"case_id": case_id, "node": "candidate_packets"})
        elif any("supports_exact_claim" not in packet for packet in packets.values() if packet.get("source_type") in {"exact_db", "web_search", "web_extract", "generic_db"}):
            missing_chain_nodes.append({"case_id": case_id, "node": "exact_hard_recheck"})

        if not item_results:
            missing_chain_nodes.append({"case_id": case_id, "node": "synthesis_item_results"})

        rejected_ids = {
            rejected.get("packet_id")
            for item in item_results
            if isinstance(item, dict)
            for rejected in item.get("rejected_candidates") or []
            if isinstance(rejected, dict) and isinstance(rejected.get("packet_id"), str)
        }
        evidence_ids = {
            evidence.get("packet_id")
            for item in item_results
            if isinstance(item, dict)
            for evidence in item.get("evidence_used") or []
            if isinstance(evidence, dict) and isinstance(evidence.get("packet_id"), str)
        }
        for packet_id in sorted(rejected_ids.intersection(evidence_ids)):
            rejected_packet_evidence_ref_violations.append({"case_id": case_id, "packet_id": packet_id})

        for item_index, item in enumerate(item_results):
            if not isinstance(item, dict):
                continue
            final_mapping = item.get("final_mapping")
            if not isinstance(final_mapping, dict):
                missing_chain_nodes.append({"case_id": case_id, "node": "final_mapping", "item_index": item_index})
                continue
            if final_mapping.get("final_mapping_owner") != "b2_final_mapping" or item.get("ledger_status") != final_mapping.get("ledger_status"):
                producer_final_mapping_owner_violations.append({"case_id": case_id, "item_index": item_index})
            for rejected in item.get("rejected_candidates") or []:
                if not isinstance(rejected, dict):
                    continue
                if rejected.get("exact_claim_blocked") is True and rejected.get("estimability_blocked") is not False:
                    strict_exact_estimability_violations.append(
                        {"case_id": case_id, "packet_id": rejected.get("packet_id")}
                    )

    readiness_summary_present = bool(case_checks) and "phase" in report_data and "mode" in report_data
    if not readiness_summary_present:
        missing_chain_nodes.append({"case_id": None, "node": "readiness_summary"})

    pending_policy_promotions = _pending_policy_promotions()
    passed = (
        not missing_chain_nodes
        and not rejected_packet_evidence_ref_violations
        and not source_selection_semantic_owner_violations
        and not producer_final_mapping_owner_violations
        and not strict_exact_estimability_violations
        and not pending_policy_promotions
    )
    return {
        "passed": passed,
        "required_chain_nodes": REQUIRED_ARTIFACT_CHAIN_NODES,
        "chain_complete": not missing_chain_nodes,
        "missing_chain_nodes": missing_chain_nodes,
        "rejected_packet_evidence_ref_violations": rejected_packet_evidence_ref_violations,
        "source_selection_semantic_owner_violations": source_selection_semantic_owner_violations,
        "producer_final_mapping_owner_violations": producer_final_mapping_owner_violations,
        "strict_exact_estimability_violations": strict_exact_estimability_violations,
        "pending_policy_promotions": pending_policy_promotions,
    }


def _pending_policy_promotions() -> list[dict[str, str]]:
    register_path = ROOT / "docs" / "specs" / "WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md"
    if not register_path.exists():
        return []
    text = register_path.read_text(encoding="utf-8-sig")
    promotions: list[dict[str, str]] = []
    for decision_id in PENDING_PRODUCT_POLICY_IDS:
        marker = f"  {decision_id}:"
        start = text.find(marker)
        if start < 0:
            continue
        next_decision = text.find("\n  ", start + len(marker))
        section = text[start:] if next_decision < 0 else text[start:next_decision]
        if "status: approved" in section:
            promotions.append({"decision_id": decision_id, "reason": "pending_policy_marked_approved"})
    return promotions


def verify_phase_b2_readiness(*, phase_b2_report_path: Path) -> dict[str, Any]:
    report_data = _read_json(phase_b2_report_path)
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if report_data.get("phase") != "B2":
        _add(blockers, "phase_b2_report_phase_invalid", "Phase B-2 readiness requires phase=B2.")
    if report_data.get("mode") != "evidence_synthesis_gate":
        _add(blockers, "phase_b2_mode_invalid", "Phase B-2 readiness requires evidence_synthesis_gate mode.")

    smoke_cases = _check_smoke_cases(report_data, blockers)
    non_scope = _check_non_scope(report_data, blockers)
    trusted_database_policy = _check_trusted_database_policy(report_data, blockers)
    llm_prior_trace = _check_llm_prior_trace(report_data, blockers)
    minimal_db_seed_manifest = _check_minimal_db_seed_manifest(report_data, blockers)
    runtime_trace_parity = _check_runtime_trace_parity(report_data, blockers)
    b1_green_handoff_check = _check_b1_green_handoff_snapshot(report_data, blockers)
    case_checks: list[dict[str, Any]] = []
    for case in report_data.get("cases") or []:
        if not isinstance(case, dict):
            _add(blockers, "phase_b2_case_not_object", "Phase B-2 cases must be objects.")
            continue
        before = len(blockers)
        checks = {
            "case_id": case.get("case_id"),
            "input_message": case.get("input_message"),
            "producer_trace": _check_producer_trace(case, blockers),
            "source_selection": _check_source_selection(case, blockers),
            "listed_item_fanout": _check_listed_item_fanout(case, blockers),
            "selected_extract_exact_positive": _check_selected_extract_exact_positive(case, blockers),
            "packet_contract": _check_packet_contract(case, blockers),
            "manager_pass_2": _check_manager_pass_2(case, blockers),
            "extract_policy": _check_extract_policy(case, blockers),
            "mutation": _check_mutation(case, blockers),
            "renderer": _check_renderer(case, blockers),
            "cache": _check_cache(case, blockers, warnings),
        }
        checks["passed"] = len(blockers) == before
        case_checks.append(checks)

    artifact_completeness_audit = _artifact_completeness_audit(report_data, case_checks=case_checks)
    if not artifact_completeness_audit["passed"]:
        _add(blockers, "artifact_completeness_audit_failed", "B2 artifact completeness audit must pass before live LLM diagnostic.")

    ready = not blockers
    report = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase_b2_report_path": _project_relative(phase_b2_report_path),
        "ready_for_phase_b2_implementation": ready,
        "blockers": blockers,
        "warnings": warnings,
        "smoke_cases": smoke_cases,
        "non_scope": non_scope,
        "trusted_database_policy": trusted_database_policy,
        "llm_prior_trace": llm_prior_trace,
        "minimal_db_seed_manifest": minimal_db_seed_manifest,
        "runtime_trace_parity": runtime_trace_parity,
        "b1_green_handoff_snapshot": _json_safe(report_data.get("b1_green_handoff_snapshot")),
        "b1_green_handoff_check": b1_green_handoff_check,
        "honesty_gate_status": _honesty_gate_status(),
        "artifact_completeness_audit": artifact_completeness_audit,
        "case_checks": case_checks,
        "recommended_next_steps_ordered": (
            ["proceed_to_phase_b2_evidence_synthesis_implementation"]
            if ready
            else ["fix_phase_b2_gate_blockers", "rerun_phase_b2_evidence_synthesis_readiness_gate"]
        ),
    }
    return _json_safe(report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Wave 1 Phase B-2 evidence/synthesis readiness.")
    parser.add_argument("--phase-b2-report", default=str(DEFAULT_PHASE_B2_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    phase_b2_report_path = _resolve_path(args.phase_b2_report, default=DEFAULT_PHASE_B2_REPORT)
    output_path = _resolve_path(args.output, default=DEFAULT_OUTPUT)
    report = verify_phase_b2_readiness(phase_b2_report_path=phase_b2_report_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_path": str(output_path),
                "ready_for_phase_b2_implementation": report["ready_for_phase_b2_implementation"],
                "blocker_count": len(report["blockers"]),
                "recommended_next_steps_ordered": report["recommended_next_steps_ordered"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready_for_phase_b2_implementation"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
