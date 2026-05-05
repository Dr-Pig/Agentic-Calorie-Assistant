from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .web_extract_port import WebExtractPort


_GATE_FORBIDDEN_TRUE_FLAGS = {
    "live_provider_used": "gate_used_live_provider",
    "live_websearch_used": "gate_used_live_websearch",
    "source_live_websearch_used": "gate_used_source_live_websearch",
    "live_extract_used": "gate_used_live_extract",
    "runtime_truth_changed": "gate_changed_runtime_truth",
    "mutation_changed": "gate_changed_mutation",
    "runtime_mutation_allowed": "gate_allowed_runtime_mutation",
    "websearch_runtime_truth_allowed": "gate_allowed_websearch_runtime_truth",
    "runtime_web_activation_approved": "gate_approved_runtime_web_activation",
    "runtime_web_activation_recommended": "gate_recommended_runtime_web_activation",
    "ready_for_runtime_truth": "gate_claimed_ready_for_runtime_truth",
    "ready_for_runtime_mutation": "gate_claimed_ready_for_runtime_mutation",
    "readiness_claimed": "gate_claimed_readiness",
    "manager_context_changed": "gate_changed_manager_context",
    "manager_context_packet_changed": "gate_changed_manager_context_packet",
    "manager_context_packet_schema_changed": "gate_changed_manager_context_packet_schema",
    "packetizer_format_changed": "gate_changed_packetizer_format",
    "packetizer_changed": "gate_changed_packetizer",
    "shared_contract_changed": "gate_changed_shared_contract",
    "nutrition_evidence_store_port_changed": "gate_changed_nutrition_evidence_store_port",
    "basket_semantics_changed": "gate_changed_basket_semantics",
    "product_loop_activated": "gate_activated_product_loop",
    "product_loop_integration_claimed": "gate_claimed_product_loop_integration",
    "ce_activated": "gate_activated_context_engineering",
    "context_engineering_changed": "gate_changed_context_engineering",
    "webshell_activated": "gate_activated_webshell",
    "webshell_changed": "gate_changed_webshell",
    "exact_card_created": "gate_created_exact_card",
}
_TOP_LEVEL_MALFORMED_ROWS_TYPE = "__top_level_malformed_extract_rows_type__"


def _fixture_provider_names() -> set[str]:
    return {"fixture", "fake", "stub", "cached_fixture"}


async def build_websearch_live_extract_diagnostic_canary(
    *,
    diagnostic_gate_artifact: dict[str, Any] | None,
    live_permission_granted: bool,
    extract_port: WebExtractPort | None,
) -> dict[str, Any]:
    gate = _compact_gate(diagnostic_gate_artifact)
    port_gate = _compact_port_presence(extract_port)
    blockers = []
    if gate["blocked"]:
        blockers.append(f"diagnostic_gate_not_clear:{gate['next_required_slice']}")
        blockers.extend(f"diagnostic_gate:{blocker}" for blocker in gate["blockers"])
    if not live_permission_granted:
        blockers.append("live_extract_permission_required")
    if port_gate["blocked"]:
        blockers.extend(port_gate["blockers"])
    review_refs = gate["review_packet_refs"] if not blockers else []
    cases: list[dict[str, Any]] = []
    extract_port_call_count = 0
    extract_port_profile = {"provider": None, "configured": False}
    if not blockers:
        metered_port = _MeteredExtractPort(extract_port)
        extract_port_profile = metered_port.readiness()
        if extract_port_profile.get("configured") is not True:
            blockers.append("extract_port_not_configured")
        else:
            for ref in review_refs[:1]:
                rows = await metered_port.extract_rows(
                    urls=[str(ref["source_url"])],
                    query=str(ref["canonical_name"] or ref["packet_id"]),
                )
                cases.append(
                    _case_result(review_ref=ref, rows=_normalize_extract_rows(rows))
                )
            extract_port_call_count = metered_port.call_count
            blockers.extend(
                f"canary_case_failed:{case['case_id']}"
                for case in cases
                if case["status"] != "pass"
            )
    clear = not blockers
    live_extract_used = _external_extract_port_used(
        extract_port_profile=extract_port_profile,
        extract_port_call_count=extract_port_call_count,
    )
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_diagnostic_canary_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_canary_harness_only",
        "claim_scope": "websearch_live_extract_diagnostic_canary_without_runtime_truth",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "live_permission_granted": live_permission_granted,
        "extract_port_used": extract_port_call_count > 0,
        "live_extract_used": live_extract_used,
        "live_websearch_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "exact_card_created": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "shared_contract_changed": False,
        "readiness_claimed": False,
        "ready_for_runtime_truth": False,
        "ready_for_runtime_mutation": False,
        "diagnostic_gate": gate,
        "port_gate": {
            **port_gate,
            "extract_port_profile": extract_port_profile,
        },
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "pass_count": sum(1 for case in cases if case["status"] == "pass"),
            "fail_count": sum(1 for case in cases if case["status"] != "pass"),
            "extract_port_call_count": extract_port_call_count,
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
        },
        "next_required_slice": (
            "websearch_live_extract_diagnostic_report"
            if clear
            else "inspect_websearch_live_extract_diagnostic_canary_blockers"
        ),
        "non_claims": [
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_runtime_web_activation",
            "no_readiness_claim",
        ],
    }


def _compact_gate(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {
            "status": "not_provided",
            "next_required_slice": "inspect_websearch_live_extract_diagnostic_gate",
            "blocked": True,
            "review_packet_refs": [],
            "blockers": ["artifact_missing"],
        }
    if artifact.get("artifact_type") != "accurate_intake_websearch_live_extract_diagnostic_gate_v1":
        raise ValueError("unsupported_websearch_live_extract_diagnostic_gate")
    unsafe = any(artifact.get(key) is True for key in _GATE_FORBIDDEN_TRUE_FLAGS)
    review_refs = _review_packet_refs(artifact)
    clear = (
        artifact.get("status") == "pass"
        and artifact.get("ready_for_trace_only_live_extract_diagnostic") is True
        and artifact.get("ready_for_runtime_truth") is False
        and artifact.get("ready_for_runtime_mutation") is False
        and artifact.get("blockers") == []
        and artifact.get("next_required_slice") == "websearch_live_extract_diagnostic_canary_harness"
        and review_refs
        and not unsafe
    )
    blockers = [
        blocker
        for key, blocker in _GATE_FORBIDDEN_TRUE_FLAGS.items()
        if artifact.get(key) is True
    ]
    return {
        "status": "clear" if clear else "blocked",
        "next_required_slice": (
            "websearch_live_extract_diagnostic_canary_harness"
            if clear
            else "inspect_websearch_live_extract_diagnostic_gate"
        ),
        "blocked": not clear,
        "review_packet_refs": review_refs if clear else [],
        "blockers": blockers,
    }


def _review_packet_refs(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for ref in artifact.get("review_packet_refs") or []:
        if not isinstance(ref, dict):
            continue
        packet_id = str(ref.get("packet_id") or "").strip()
        source_url = str(ref.get("source_url") or "").strip()
        packet_digest = str(ref.get("packet_digest") or "").strip()
        if packet_id and source_url and packet_digest:
            refs.append(
                {
                    "packet_id": packet_id,
                    "source_url": source_url,
                    "canonical_name": str(ref.get("canonical_name") or "").strip(),
                    "packet_digest": packet_digest,
                }
            )
    return refs


def _compact_port_presence(extract_port: WebExtractPort | None) -> dict[str, Any]:
    blockers = []
    if extract_port is None:
        blockers.append("extract_port_unavailable")
    return {
        "status": "clear" if not blockers else "blocked",
        "blockers": sorted(blockers),
        "blocked": bool(blockers),
    }


def _case_result(*, review_ref: dict[str, Any], rows: list[Any]) -> dict[str, Any]:
    candidate_rows = [
        _row_summary(row=row, review_ref=review_ref)
        if isinstance(row, dict) and _TOP_LEVEL_MALFORMED_ROWS_TYPE not in row
        else _malformed_row_summary(row)
        for row in rows
    ]
    usable_rows = [
        row
        for row in candidate_rows
        if row["source_url_match"] is True
        and row["kcal_value_candidate_present"] is True
        and row["serving_basis_candidate_present"] is True
        and row["identity_text_present"] is True
        and row["raw_content_included"] is False
    ]
    status = "pass" if usable_rows else "fail"
    return {
        "case_id": f"live_extract_review_candidate:{review_ref['packet_id']}",
        "status": status,
        "review_packet_ref": {
            "packet_id": review_ref["packet_id"],
            "source_url": review_ref["source_url"],
            "packet_digest": review_ref["packet_digest"],
        },
        "extract_result_role": "review_candidate_only",
        "runtime_truth_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "raw_content_in_manager_context": False,
        "candidate_row_count": len(candidate_rows),
        "usable_review_candidate_count": len(usable_rows),
        "candidate_rows": candidate_rows,
    }


def _normalize_extract_rows(rows: object) -> list[Any]:
    if isinstance(rows, list):
        return rows
    return [{_TOP_LEVEL_MALFORMED_ROWS_TYPE: type(rows).__name__}]


def _row_summary(*, row: dict[str, Any], review_ref: dict[str, Any]) -> dict[str, Any]:
    source_url = str(row.get("source_url") or row.get("url") or "").strip()
    return {
        "source_url": source_url,
        "source_url_match": source_url == review_ref["source_url"],
        "kcal_value_candidate_present": _kcal_value(row.get("kcal_value_candidate")) is not None,
        "serving_basis_candidate_present": bool(
            str(row.get("serving_basis_candidate") or row.get("serving_basis") or "").strip()
        ),
        "identity_text_present": row.get("identity_text_present") is True
        or bool(str(row.get("matched_name") or row.get("canonical_name") or "").strip()),
        "raw_content_included": "raw_content" in row,
        "runtime_truth_allowed": False,
        "exact_card_created": False,
    }


def _malformed_row_summary(row: object) -> dict[str, Any]:
    malformed_row_type = (
        str(row[_TOP_LEVEL_MALFORMED_ROWS_TYPE])
        if isinstance(row, dict) and _TOP_LEVEL_MALFORMED_ROWS_TYPE in row
        else type(row).__name__
    )
    return {
        "source_url": None,
        "source_url_match": False,
        "kcal_value_candidate_present": False,
        "serving_basis_candidate_present": False,
        "identity_text_present": False,
        "raw_content_included": False,
        "runtime_truth_allowed": False,
        "exact_card_created": False,
        "malformed_row_type": malformed_row_type,
    }


def _kcal_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _safe_readiness(port: object | None) -> dict[str, Any]:
    if port is None:
        return {"provider": None, "configured": False}
    readiness = getattr(port, "readiness", None)
    profile = readiness() if callable(readiness) else {}
    return {
        "port_type": type(port).__name__,
        **(profile if isinstance(profile, dict) else {}),
    }


class _MeteredExtractPort:
    def __init__(self, inner: WebExtractPort) -> None:
        self._inner = inner
        self.call_count = 0

    def readiness(self) -> dict[str, Any]:
        return _safe_readiness(self._inner)

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        self.call_count += 1
        return await self._inner.extract_rows(urls=urls, query=query)


def _external_extract_port_used(
    *,
    extract_port_profile: dict[str, Any],
    extract_port_call_count: int,
) -> bool:
    if extract_port_call_count <= 0:
        return False
    provider = str(extract_port_profile.get("provider") or "").strip().lower()
    return provider not in _fixture_provider_names()


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_live_extract_diagnostic_canary"]
