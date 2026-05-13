from __future__ import annotations

from typing import Any, Mapping


def grade_context_engineering_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "capabilities_considered_visible": bool(trace.get("capabilities_considered")),
        "capabilities_invoked_visible": bool(trace.get("capabilities_invoked")),
        "capabilities_omitted_visible": "capabilities_omitted" in trace,
        "blocked_tools_visible": "blocked_tools" in trace,
        "response_claim_boundary_visible": bool(trace.get("response_claim_boundary")),
    }
    blockers = [
        check_name
        for check_name, passed in checks.items()
        if passed is not True
    ]
    return {
        "artifact_type": "advanced_product_lab_context_engineering_trace_grade",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "checks": checks,
        "blockers": blockers,
    }


__all__ = ["grade_context_engineering_trace"]
