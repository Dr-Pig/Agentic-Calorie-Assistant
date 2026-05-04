from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.memory.application.long_term_context_shadow_lab import (
    SHADOW_NON_CLAIM_FLAGS,
    artifact_review_contract,
)
from app.memory.application.local_memory_skill_review import (
    build_local_skill_reference_summary,
)
from app.memory.application.local_memory_zip_review import (
    build_local_zip_reference_summary,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.local_memory_framework_review"
)


def build_local_framework_review(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    reviews = [
        _review_framework(
            framework_id, root_path, _candidate_files(root_path, framework_id)
        )
        for framework_id in (
            "hermes",
            "openclaw",
            "mem0",
            "hindsight",
            "graphiti",
            "letta",
            "memu",
        )
    ]
    reviews = [review for review in reviews if review["evidence_files"]]
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "local_memory_framework_review",
        "status": "generated",
        "claim_scope": "local_framework_review_only",
        "local_framework_root": str(root_path),
        "new_dependency_introduced": False,
        "service_started": False,
        "live_provider_called": False,
        **SHADOW_NON_CLAIM_FLAGS,
        **artifact_review_contract("local_memory_framework_review"),
        "framework_reviews": reviews,
    }


def build_local_framework_deep_review(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    base_review = build_local_framework_review(root_path)
    scorecards = [
        _framework_scorecard(review)
        for review in base_review.get("framework_reviews", [])
        if isinstance(review, dict)
    ]
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "local_memory_framework_deep_review",
        "status": "generated",
        "claim_scope": "local_framework_deep_review_only",
        "local_framework_root": str(root_path),
        "read_only_review": True,
        "new_dependency_introduced": False,
        "service_started": False,
        "live_provider_called": False,
        "runtime_integration_recommended": False,
        **SHADOW_NON_CLAIM_FLAGS,
        **artifact_review_contract("local_memory_framework_deep_review"),
        "review_questions": [
            "raw_history_vs_derived_vs_confirmed_memory",
            "promotion_and_demotion_policy",
            "provenance_and_source_refs",
            "freshness_and_staleness",
            "prompt_pollution_prevention",
            "retrieval_ranking_and_scope",
            "user_correction_deletion_suppression",
            "no_send_proactive_simulation",
        ],
        "framework_scorecards": scorecards,
        "local_skill_reference_summary": build_local_skill_reference_summary(root_path),
        "zip_reference_summary": build_local_zip_reference_summary(root_path),
        "global_adoptable_patterns": _global_deep_adoptable_patterns(scorecards),
        "global_deferred_patterns": _global_deep_deferred_patterns(scorecards),
    }


def _framework_scorecard(review: dict[str, Any]) -> dict[str, Any]:
    capabilities = list(review.get("observed_capabilities") or [])
    adoptable = list(review.get("adoptable_patterns") or [])
    deferred = list(review.get("rejected_or_deferred_patterns") or [])
    fit_score = min(
        1.0,
        round(
            0.2
            + 0.1 * len(capabilities)
            + 0.08 * len(adoptable)
            - 0.04 * len(deferred),
            2,
        ),
    )
    return {
        "framework_id": str(review.get("framework_id") or "unknown"),
        "evidence_files": list(review.get("evidence_files") or []),
        "observed_capabilities": capabilities,
        "product_fit_score": max(0.0, fit_score),
        "adoptable_pattern_count": len(adoptable),
        "deferred_pattern_count": len(deferred),
        "runtime_violation_risks": [
            pattern
            for pattern in deferred
            if "auto" in pattern.lower()
            or "provider" in pattern.lower()
            or "runtime" in pattern.lower()
        ],
        "recommended_translation": str(review.get("shadow_lab_translation") or ""),
        "runtime_effect_allowed": False,
    }


def _global_deep_adoptable_patterns(
    scorecards: list[dict[str, Any]],
) -> list[str]:
    patterns = [
        "scope_key_first_retrieval",
        "source_ref_required_memory_candidates",
        "review_lane_before_promotion",
    ]
    if any(
        "entity_or_graph_memory" in scorecard["observed_capabilities"]
        for scorecard in scorecards
    ):
        patterns.append("entity_links_as_shadow_normalization_pressure")
    return patterns


def _global_deep_deferred_patterns(
    scorecards: list[dict[str, Any]],
) -> list[str]:
    patterns = [
        "provider_context_auto_injection",
        "auto_capture_after_response",
        "runtime_memory_tool_registration",
        "live_vector_or_hybrid_search",
    ]
    if any(scorecard["runtime_violation_risks"] for scorecard in scorecards):
        patterns.append("framework_runtime_hooks")
    return patterns


def _candidate_files(root: Path, framework_id: str) -> list[Path]:
    if not root.exists():
        return []
    aliases = _framework_aliases(framework_id)
    results: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".mdx", ".json", ".ts", ".py", ".rs"}:
            continue
        lower = str(path).lower()
        if any(token in lower for token in aliases):
            results.append(path)
        if len(results) >= 80:
            break
    return results


def _framework_aliases(framework_id: str) -> tuple[str, ...]:
    if framework_id == "mem0":
        return ("mem0", "openmemory")
    if framework_id == "openclaw":
        return ("openclaw", "claw")
    if framework_id == "memu":
        return ("memu", "memu-main")
    return (framework_id,)


def _review_framework(
    framework_id: str, root: Path, files: list[Path]
) -> dict[str, Any]:
    matching = [
        path
        for path in files
        if framework_id in path.name.lower()
        or framework_id in str(path.relative_to(root)).lower()
    ]
    if framework_id == "mem0":
        matching.extend(
            path
            for path in files
            if "openmemory" in str(path.relative_to(root)).lower()
        )
    if framework_id == "openclaw":
        matching.extend(
            path for path in files if "claw" in str(path.relative_to(root)).lower()
        )
    matching = _dedupe_paths(matching)[:12]
    snippets = [_read_preview(path) for path in matching]
    corpus = "\n".join(snippets).lower()
    return {
        "framework_id": framework_id,
        "evidence_files": [str(path.relative_to(root)) for path in matching],
        "observed_capabilities": _observed_capabilities(corpus),
        "adoptable_patterns": _adoptable_patterns(corpus),
        "rejected_or_deferred_patterns": _rejected_or_deferred_patterns(corpus),
        "shadow_lab_translation": _shadow_translation(framework_id, corpus),
    }


def _observed_capabilities(corpus: str) -> list[str]:
    capabilities: list[str] = []
    if "auto-recall" in corpus or "autorecall" in corpus or "pre_llm_call" in corpus:
        capabilities.append("auto_recall")
    if "auto-capture" in corpus or "auto-retain" in corpus or "post_llm_call" in corpus:
        capabilities.append("auto_capture")
    if "userid" in corpus or "user_id" in corpus or "scope" in corpus:
        capabilities.append("scope_isolation")
    if "secretref" in corpus or "api key" in corpus:
        capabilities.append("secret_handling")
    if "graph" in corpus or "entity" in corpus:
        capabilities.append("entity_or_graph_memory")
    if "dream" in corpus or "review" in corpus or "backfill" in corpus:
        capabilities.append("review_or_promotion_surface")
    return capabilities or ["documentation_or_code_present"]


def _adoptable_patterns(corpus: str) -> list[str]:
    patterns = [
        "Keep memory candidates scoped by stable user/source identifiers.",
        "Preserve provenance and source references before any promotion.",
        "Use review artifacts before durable memory writes.",
    ]
    if "secretref" in corpus:
        patterns.append(
            "Represent secret handling as policy evidence; never store secrets in artifacts."
        )
    if "recallinjectionposition" in corpus:
        patterns.append(
            "Track future injection position as an explicit reviewed context-packing decision."
        )
    if "dream" in corpus or "backfill" in corpus:
        patterns.append(
            "Keep promotion/backfill reviewable before live memory mutation."
        )
    return patterns


def _rejected_or_deferred_patterns(corpus: str) -> list[str]:
    patterns = [
        "Defer auto-recall and auto-capture because V1 shadow lab cannot inject context or persist memory.",
        "Reject provider SDK/service startup in this PR; local review is read-only.",
    ]
    if "api key" in corpus or "secretref" in corpus:
        patterns.append(
            "Reject storing raw provider credentials or secrets in fixtures/artifacts."
        )
    if "post_llm_call" in corpus:
        patterns.append(
            "Defer post-response retain hooks until durable memory promotion is explicitly approved."
        )
    return patterns


def _shadow_translation(framework_id: str, corpus: str) -> str:
    if framework_id == "openclaw" and "recallinjectionposition" in corpus:
        return "Model recall injection as a reviewed future context-packing variable, not as runtime wiring."
    if framework_id == "hermes" and "memory_mode" in corpus:
        return "Model context/tools/hybrid as future activation modes, all disabled in shadow artifacts."
    if framework_id == "mem0":
        return "Use user-scoped memory evidence and explicit CRUD vocabulary as review metadata only."
    if framework_id == "hindsight":
        return "Use retain/recall/reflect as conceptual review lanes without starting a memory daemon."
    if framework_id == "graphiti":
        return "Use temporal provenance and entity links as future schema pressure, not V1 dependency."
    return "Record observed patterns as local research evidence without changing canonical L4A/L4C specs."


def _read_preview(path: Path) -> str:
    try:
        if path.suffix.lower() == ".json":
            return json.dumps(
                json.loads(path.read_text(encoding="utf-8-sig")), ensure_ascii=False
            )[:5000]
        return path.read_text(encoding="utf-8-sig", errors="replace")[:5000]
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return ""


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_local_framework_deep_review",
    "build_local_framework_review",
]
