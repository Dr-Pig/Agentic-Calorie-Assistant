from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_QUALITY = ROOT / "docs" / "archive" / "quality"
QUALITY_DOCS = ROOT / "docs" / "quality"
OUTPUT_DIR = ROOT / "runtime" / "evals" / "benchmark_registry"
NORMALIZED_DIR = OUTPUT_DIR / "normalized"

V1_TEXT = QUALITY_DOCS / "benchmark_test_set_v1.txt"
V2_TEXT = QUALITY_DOCS / "benchmark_test_set_v2.txt"
REPLAY_JSON = QUALITY_DOCS / "turn2_hybrid_replay_pack_v1.json"

PROMOTION_FAMILIES = {
    "ask_followup_only_to_completion",
    "estimate_with_followup_to_refinement",
    "same_thread_correction",
}

EXACT_DOMAIN_REPRESENTATION_LIMIT = 1


def _normalize_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(value or "").lower())


def _repair_case_marker_boundaries(text: str) -> str:
    return re.sub(r"(?<!\n)(case_\d+\s*\n)", r"\n\1", text)


def _parse_key_value_block(lines: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") and current_list_key:
            data.setdefault(current_list_key, []).append(stripped[2:].strip())
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_list_key = None
        if value == "":
            current_list_key = key
            data.setdefault(key, [])
            continue
        lowered = value.lower()
        if lowered == "true":
            data[key] = True
        elif lowered == "false":
            data[key] = False
        else:
            data[key] = value.strip('"')
    return data


def _infer_case_family(*, action: str, exactness: str, input_text: str, lane_family: str | None = None) -> str:
    normalized = _normalize_text(input_text)
    if lane_family:
        return lane_family
    if "蒸餃" in normalized or "鍋貼" in normalized or "水餃" in normalized:
        return "dumpling_count_required"
    if "珍珠奶茶" in normalized:
        return "estimate_with_followup_to_refinement" if action == "estimate_with_followup" else "drink_exactness"
    if action == "exact_lookup":
        return "exactness_honesty"
    if action == "estimate_with_followup":
        return "estimate_with_followup"
    if action == "ask_followup_only":
        return "clarify_before_estimate"
    if exactness == "anchored":
        return "anchored_estimate"
    return "generic_shadow_case"


def _infer_workflow_effect(*, action: str, lane_family: str, exactness: str) -> str:
    if lane_family == "ask_followup_only_to_completion":
        return "followup_resolution_commit"
    if lane_family == "estimate_with_followup_to_refinement":
        return "followup_resolution_commit"
    if action == "exact_lookup":
        return "direct_commit"
    if action == "estimate_with_followup":
        return "commit_if_confirmed"
    if action == "ask_followup_only":
        return "ask_followup"
    if exactness == "anchored":
        return "commit_if_confirmed"
    return "shadow_only"


def _infer_source_domain(*, source_case_id: str, input_text: str) -> str:
    normalized = _normalize_text(input_text)
    case_id = _normalize_text(source_case_id)
    if "星巴克" in normalized:
        return "starbucks"
    if "摩斯" in normalized or "mos" in case_id:
        return "mos"
    if "麥當勞" in normalized or "大麥克" in normalized or "麥香雞" in normalized or "麥脆雞" in normalized:
        return "mcdonalds"
    if "711" in normalized or "7-11" in normalized or "_711_" in case_id:
        return "7eleven"
    if "全家" in normalized or "familymart" in case_id:
        return "familymart"
    if "吉野家" in normalized:
        return "yoshinoya"
    if "松屋" in normalized:
        return "matsuya"
    if "subway" in normalized:
        return "subway"
    return "generic"


def _infer_evidence_topology(*, source_suite: str, action: str, exactness: str, input_text: str, case_family: str) -> str:
    normalized = _normalize_text(input_text)
    if source_suite == "turn2_hybrid_replay_pack_v1":
        if case_family == "ask_followup_only_to_completion":
            return "replay_ask_completion"
        return "replay_estimate_refinement"
    if action == "exact_lookup":
        if any(token in normalized for token in ("跟", "和", "、")):
            return "multi_item_exact_combo"
        return "single_item_exact"
    if action == "estimate_with_followup":
        return "estimate_with_followup"
    if action == "ask_followup_only":
        return "ask_followup_only"
    if exactness == "anchored":
        return "anchored_direct_estimate"
    return "generic"


def _dedupe_category(*, case_family: str, workflow_effect: str, source_suite: str) -> str:
    if case_family in {"estimate_with_followup", "clarify_before_estimate"} and source_suite != "turn2_hybrid_replay_pack_v1":
        return "duplicate_of_official"
    if case_family in {"dumpling_count_required", "same_turn_budget_sync", "provenance_honesty"}:
        return "duplicate_of_founder_realism"
    if case_family in PROMOTION_FAMILIES or workflow_effect in {"followup_resolution_commit", "correction_applied"}:
        return "benchmark_unique_blocking_candidate"
    return "benchmark_unique_shadow_candidate"


def _promotion_group_key(case: dict[str, Any]) -> str:
    topology = str(case.get("evidence_topology") or "generic")
    if topology.startswith("replay_"):
        return f"replay:{case.get('case_family')}"
    if str(case.get("case_family")) == "exactness_honesty":
        return f"exact_domain:{case.get('source_domain')}:{topology}"
    return f"family:{case.get('case_family')}:{topology}"


def select_blocking_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    exact_domain_counts: dict[str, int] = {}
    for case in cases:
        if str(case.get("dedupe_status", "")).startswith("duplicate_of_"):
            case["blocking_candidate"] = False
            case["promotion_candidate_status"] = "duplicate"
            continue
        topology = str(case.get("evidence_topology") or "")
        family = str(case.get("case_family") or "")
        if topology.startswith("replay_"):
            case["blocking_candidate"] = True
            case["promotion_candidate_status"] = "promoted"
            case["promotion_reason"] = "unique multi-turn workflow family"
            selected.append(case)
            continue
        if family == "exactness_honesty":
            domain = str(case.get("source_domain") or "generic")
            topology = str(case.get("evidence_topology") or "single_item_exact")
            representation_key = f"{domain}:{topology}"
            current = exact_domain_counts.get(representation_key, 0)
            if current < EXACT_DOMAIN_REPRESENTATION_LIMIT:
                exact_domain_counts[representation_key] = current + 1
                case["blocking_candidate"] = True
                case["promotion_candidate_status"] = "promoted"
                case["promotion_reason"] = "representative exactness-honesty domain/topology case"
                selected.append(case)
            else:
                case["blocking_candidate"] = False
                case["promotion_candidate_status"] = "shadow_only"
                case["promotion_reason"] = "duplicate exactness domain/topology representation"
            continue
        case["blocking_candidate"] = False
        case["promotion_candidate_status"] = "shadow_only"
    return selected


def _parse_v1_cases() -> list[dict[str, Any]]:
    text = _repair_case_marker_boundaries(V1_TEXT.read_text(encoding="utf-8-sig"))
    parts = re.split(r"(?m)^(case_\d+)\s*$", text)
    cases: list[dict[str, Any]] = []
    for index in range(1, len(parts), 2):
        case_id = parts[index].strip()
        body = parts[index + 1]
        input_match = re.search(r"(?ms)^input\s*(.*?)^\s*expected_behavior\s*$", body)
        behavior_match = re.search(r"(?ms)^expected_behavior\s*(.*?)^\s*expected_evidence_outcome\s*$", body)
        evidence_match = re.search(r"(?ms)^expected_evidence_outcome\s*(.*?)^\s*source_of_truth\s*$", body)
        if not input_match or not behavior_match or not evidence_match:
            continue
        input_text = input_match.group(1).strip()
        behavior = _parse_key_value_block(behavior_match.group(1).splitlines())
        evidence = _parse_key_value_block(evidence_match.group(1).splitlines())
        action = str(behavior.get("action") or "unknown")
        exactness = str(behavior.get("exactness") or "unknown")
        case_family = _infer_case_family(action=action, exactness=exactness, input_text=input_text)
        workflow_effect = _infer_workflow_effect(action=action, lane_family=case_family, exactness=exactness)
        dedupe_status = _dedupe_category(case_family=case_family, workflow_effect=workflow_effect, source_suite="benchmark_test_set_v1")
        source_domain = _infer_source_domain(source_case_id=case_id, input_text=input_text)
        evidence_topology = _infer_evidence_topology(
            source_suite="benchmark_test_set_v1",
            action=action,
            exactness=exactness,
            input_text=input_text,
            case_family=case_family,
        )
        cases.append(
            {
                "source_suite": "benchmark_test_set_v1",
                "source_case_id": case_id,
                "title": case_id,
                "input_text": input_text,
                "input_shape": "single_turn_text",
                "case_family": case_family,
                "lane_family": action,
                "workflow_effect": workflow_effect,
                "expected_action": action,
                "expected_exactness": exactness,
                "expected_followup_policy": "ask_if_needed" if action == "estimate_with_followup" else "none",
                "expected_persistence": {"canonical_commit_required": action == "exact_lookup"},
                "source_truth_strength": "hand_authored_archive",
                "quality_oracle_type": "behavioral_oracle",
                "dedupe_status": dedupe_status,
                "blocking_candidate": False,
                "evidence_class": "exact" if action == "exact_lookup" else exactness,
                "source_domain": source_domain,
                "evidence_topology": evidence_topology,
                "evidence_requirements": evidence,
            }
        )
    return cases


def _parse_v2_cases() -> list[dict[str, Any]]:
    lines = V2_TEXT.read_text(encoding="utf-8-sig").splitlines()
    cases: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    section: str | None = None
    sub_section: str | None = None
    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- id:"):
            if current:
                cases.append(current)
            current = {
                "source_suite": "benchmark_test_set_v2",
                "source_case_id": stripped.split(":", 1)[1].strip(),
                "expected_behavior": {},
                "expected_evidence_outcome": {},
            }
            section = None
            sub_section = None
            continue
        if current is None:
            continue
        if stripped == "expected_behavior:":
            section = "expected_behavior"
            sub_section = None
            continue
        if stripped == "expected_evidence_outcome:":
            section = "expected_evidence_outcome"
            sub_section = None
            continue
        if stripped == "source_of_truth:":
            section = "source_of_truth"
            sub_section = None
            continue
        if stripped.endswith(":") and section == "source_of_truth":
            sub_section = stripped[:-1]
            current.setdefault("source_of_truth", {}).setdefault(sub_section, {})
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"')
            if section == "expected_behavior":
                current["expected_behavior"][key] = value
            elif section == "expected_evidence_outcome":
                current["expected_evidence_outcome"][key] = value
            elif section == "source_of_truth" and sub_section:
                current.setdefault("source_of_truth", {}).setdefault(sub_section, {})[key] = value
            elif key == "input":
                current["input_text"] = value
            elif key == "title":
                current["title"] = value
    if current:
        cases.append(current)

    normalized: list[dict[str, Any]] = []
    for current in cases:
        behavior = current.get("expected_behavior") or {}
        evidence = current.get("expected_evidence_outcome") or {}
        action = str(behavior.get("action") or "unknown")
        exactness = str(behavior.get("exactness") or "unknown")
        input_text = str(current.get("input_text") or "")
        case_family = _infer_case_family(action=action, exactness=exactness, input_text=input_text)
        workflow_effect = _infer_workflow_effect(action=action, lane_family=case_family, exactness=exactness)
        dedupe_status = _dedupe_category(case_family=case_family, workflow_effect=workflow_effect, source_suite="benchmark_test_set_v2")
        source_domain = _infer_source_domain(source_case_id=str(current["source_case_id"]), input_text=input_text)
        evidence_topology = _infer_evidence_topology(
            source_suite="benchmark_test_set_v2",
            action=action,
            exactness=exactness,
            input_text=input_text,
            case_family=case_family,
        )
        normalized.append(
            {
                "source_suite": "benchmark_test_set_v2",
                "source_case_id": current["source_case_id"],
                "title": current.get("title") or current["source_case_id"],
                "input_text": input_text,
                "input_shape": "single_turn_text",
                "case_family": case_family,
                "lane_family": action,
                "workflow_effect": workflow_effect,
                "expected_action": action,
                "expected_exactness": exactness,
                "expected_followup_policy": "ask_if_needed" if action == "estimate_with_followup" else "none",
                "expected_persistence": {"canonical_commit_required": action == "exact_lookup"},
                "source_truth_strength": "hand_authored_archive",
                "quality_oracle_type": "behavioral_oracle",
                "dedupe_status": dedupe_status,
                "blocking_candidate": False,
                "evidence_class": behavior.get("exactness") or "unknown",
                "source_domain": source_domain,
                "evidence_topology": evidence_topology,
                "evidence_requirements": evidence,
            }
        )
    return normalized


def _parse_replay_cases() -> list[dict[str, Any]]:
    data = json.loads(REPLAY_JSON.read_text(encoding="utf-8-sig"))
    normalized: list[dict[str, Any]] = []
    for item in data.get("cases", []):
        lane_family = str(item.get("lane_family") or item.get("lane") or "unknown")
        workflow_effect = _infer_workflow_effect(action=lane_family, lane_family=lane_family, exactness="unknown")
        dedupe_status = _dedupe_category(case_family=lane_family, workflow_effect=workflow_effect, source_suite="turn2_hybrid_replay_pack_v1")
        evidence_topology = _infer_evidence_topology(
            source_suite="turn2_hybrid_replay_pack_v1",
            action=lane_family,
            exactness="followup_refinement",
            input_text=f"{item.get('turn1_input', '')} || {item.get('turn2_input', '')}",
            case_family=lane_family,
        )
        normalized.append(
            {
                "source_suite": "turn2_hybrid_replay_pack_v1",
                "source_case_id": item.get("case_id"),
                "title": item.get("title"),
                "input_text": f"{item.get('turn1_input', '')} || {item.get('turn2_input', '')}",
                "input_shape": "multi_turn_text_pair",
                "case_family": lane_family,
                "lane_family": lane_family,
                "workflow_effect": workflow_effect,
                "expected_action": item.get("expected_turn1_lane"),
                "expected_exactness": "followup_refinement",
                "expected_followup_policy": item.get("expected_turn2_outcome"),
                "expected_persistence": item.get("expected_persistence"),
                "source_truth_strength": "hand_authored_archive",
                "quality_oracle_type": "behavioral_oracle",
                "dedupe_status": dedupe_status,
                "blocking_candidate": False,
                "evidence_class": "multi_turn_replay",
                "source_domain": "generic",
                "evidence_topology": evidence_topology,
                "target_attachment": item.get("expected_attachment"),
                "forbidden_outcomes": item.get("forbidden_outcomes", []),
            }
        )
    return normalized


def build_normalized_registry() -> list[dict[str, Any]]:
    cases = _parse_v1_cases() + _parse_v2_cases() + _parse_replay_cases()
    seen: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    for case in cases:
        dedupe_key = "|".join(
            [
                str(case.get("lane_family") or ""),
                str(case.get("workflow_effect") or ""),
                str(case.get("expected_exactness") or ""),
                _normalize_text(case.get("input_text")),
            ]
        )
        case["dedupe_key"] = dedupe_key
        if dedupe_key in seen:
            case["dedupe_status"] = f"duplicate_of_archive_case:{seen[dedupe_key]}"
            case["blocking_candidate"] = False
        else:
            seen[dedupe_key] = str(case.get("source_case_id"))
        normalized.append(case)
    return normalized


def build_shadow_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(case["dedupe_status"] for case in cases)
    blocking_registry = select_blocking_cases(cases)
    promotion_candidates = [case["source_case_id"] for case in blocking_registry]
    blocking_family_counts = Counter(
        f"{case.get('case_family')}::{case.get('evidence_topology')}" for case in blocking_registry
    )
    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_cases": len(cases),
            "shadow_case_status": "normalized",
            "dedupe_status": "complete",
            "promotion_candidate_status": "identified" if promotion_candidates else "none",
            "quality_gap_status": "not_run",
            "dedupe_counts": dict(counts),
            "blocking_case_count": len(blocking_registry),
            "blocking_family_counts": dict(blocking_family_counts),
            "promotion_candidates": promotion_candidates,
        },
        "blocking_registry": blocking_registry,
        "cases": cases,
    }


def write_outputs(report: dict[str, Any]) -> tuple[Path, Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    registry_path = NORMALIZED_DIR / f"benchmark_registry_{ts}.json"
    blocking_path = NORMALIZED_DIR / f"benchmark_blocking_registry_{ts}.json"
    report_path = OUTPUT_DIR / f"benchmark_shadow_{ts}.json"
    registry_path.write_text(json.dumps(report["cases"], ensure_ascii=False, indent=2), encoding="utf-8")
    blocking_path.write_text(json.dumps(report["blocking_registry"], ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry_path, blocking_path, report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize, dedupe, and classify archive benchmark suites into shadow governance.")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    cases = build_normalized_registry()
    report = build_shadow_report(cases)
    registry_path, blocking_path, report_path = write_outputs(report)
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "total_cases": report["summary"]["total_cases"],
                "dedupe_status": report["summary"]["dedupe_status"],
                "promotion_candidate_status": report["summary"]["promotion_candidate_status"],
                "registry": str(registry_path),
                "blocking_registry": str(blocking_path),
                "report": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
