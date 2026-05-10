from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import yaml

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.edge_case_coverage"
)
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = ROOT / "docs" / "quality" / "advanced_capability_activation_ladder.yaml"
ARTIFACT_TYPE = "advanced_shadow_edge_case_coverage_contract"
REQUIRED_DOMAINS = [
    "long_term_memory",
    "recommendation",
    "rescue",
    "proactive",
    "chat_ux_packet",
]
NON_AUTHORITY_ROLE = "evidence_index_not_product_semantic_authority"
REQUIRED_LIST_FIELDS = (
    "product_contract_refs",
    "trace_fields",
    "guard_or_rubric_refs",
)


def load_edge_case_coverage_contract(
    path: Path | str = DEFAULT_CONTRACT_PATH,
) -> dict[str, Any]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return validate_edge_case_coverage_contract(
        _mapping(raw.get("edge_case_coverage_contract"))
    )


def validate_edge_case_coverage_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    source_contract = dict(contract)
    entries = [_entry(item) for item in contract.get("coverage_entries") or []]
    blockers = [
        *_top_level_blockers(contract),
        *_domain_blockers(contract, entries),
        *_entry_blockers(entries),
    ]
    domains = Counter(str(entry.get("capability_domain") or "") for entry in entries)
    missing = _missing_domains(entries)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "status": "pass" if not blockers else "blocked",
        "owner": str(contract.get("owner") or ""),
        "consumer": str(contract.get("consumer") or ""),
        "retirement_trigger": str(contract.get("retirement_trigger") or ""),
        "artifact_classification": str(contract.get("artifact_classification") or ""),
        "coverage_role": str(contract.get("coverage_role") or ""),
        "required_domains": list(contract.get("required_domains") or []),
        "missing_domains": missing,
        "coverage_entry_count": len(entries),
        "covered_domain_count": len([domain for domain in REQUIRED_DOMAINS if domains[domain] > 0]),
        "domain_summary": {
            domain: {"covered_count": domains[domain]}
            for domain in sorted(domain for domain in REQUIRED_DOMAINS if domains[domain] > 0)
        },
        "coverage_entries": entries,
        "source_contract": source_contract,
        "blockers": blockers,
        "new_report_family_created": contract.get("new_report_family_created") is True,
        "live_diagnostics_required": contract.get("live_diagnostics_required") is True,
        "raw_keyword_semantic_oracle_allowed": (
            contract.get("raw_keyword_semantic_oracle_allowed") is True
        ),
    }


def edge_case_coverage_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": str(artifact.get("status") or "blocked"),
        "covered_domain_count": _int(artifact.get("covered_domain_count")),
        "coverage_entry_count": _int(artifact.get("coverage_entry_count")),
        "missing_domains": list(artifact.get("missing_domains") or []),
        "new_report_family_created": artifact.get("new_report_family_created") is True,
        "coverage_role": str(artifact.get("coverage_role") or ""),
    }


def edge_case_coverage_row(artifact: Mapping[str, Any]) -> dict[str, str]:
    status = str(artifact.get("status") or "blocked")
    return {
        "surface": "cross_domain_edge_case_coverage",
        "fixture_status": status,
        "dogfood_status": "not_applicable",
        "live_status": "not_required",
        "finding": "edge_case_contract_linkage_passed"
        if status == "pass"
        else "edge_case_contract_linkage_blocked",
    }


def edge_case_coverage_blockers(artifact: Mapping[str, Any]) -> list[str]:
    if artifact.get("status") == "pass":
        return []
    return [f"edge_case_coverage.{blocker}" for blocker in artifact.get("blockers") or []]


def _top_level_blockers(contract: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if contract.get("artifact_classification") != "merge_safe":
        blockers.append("artifact_classification_not_merge_safe")
    if contract.get("coverage_role") != NON_AUTHORITY_ROLE:
        blockers.append("coverage_role_not_evidence_index")
    for field in (
        "new_report_family_created",
        "live_diagnostics_required",
        "raw_keyword_semantic_oracle_allowed",
    ):
        if contract.get(field) is not False:
            blockers.append(f"{field}_not_false")
    return blockers


def _domain_blockers(contract: Mapping[str, Any], entries: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if list(contract.get("required_domains") or []) != REQUIRED_DOMAINS:
        blockers.append("required_domains_mismatch")
    missing = _missing_domains(entries)
    if missing:
        blockers.append(f"missing_domains:{','.join(missing)}")
    return blockers


def _entry_blockers(entries: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for entry in entries:
        edge_id = str(entry.get("edge_case_id") or "unknown_edge_case")
        if entry.get("capability_domain") not in REQUIRED_DOMAINS:
            blockers.append(f"{edge_id}.unsupported_capability_domain")
        for field in REQUIRED_LIST_FIELDS:
            if not entry.get(field):
                blockers.append(f"{edge_id}.{field}_missing")
        if entry.get("claim_boundary") != "non_claim":
            blockers.append(f"{edge_id}.claim_boundary_not_non_claim")
        if entry.get("raw_keyword_semantic_oracle_allowed") is not False:
            blockers.append(f"{edge_id}.raw_keyword_semantic_oracle_allowed")
    return blockers


def _missing_domains(entries: list[Mapping[str, Any]]) -> list[str]:
    domains = {str(entry.get("capability_domain") or "") for entry in entries}
    return [domain for domain in REQUIRED_DOMAINS if domain not in domains]


def _entry(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "edge_case_coverage_blockers",
    "edge_case_coverage_row",
    "edge_case_coverage_summary",
    "load_edge_case_coverage_contract",
    "validate_edge_case_coverage_contract",
]
