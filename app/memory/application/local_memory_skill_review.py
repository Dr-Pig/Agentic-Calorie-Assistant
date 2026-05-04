from __future__ import annotations

from pathlib import Path
from typing import Any


def build_local_skill_reference_summary(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    files = _candidate_skill_files(root_path)
    corpus = "\n".join(_read_preview(path).lower() for path in files)
    return {
        "read_only_review": True,
        "tool_or_provider_started": False,
        "skill_files_reviewed": len(files),
        "evidence_files": [str(path.relative_to(root_path)) for path in files],
        "adopted_skill_patterns": _adopted_skill_patterns(corpus),
        "deferred_skill_patterns": _deferred_skill_patterns(corpus),
        "product_translation": {
            "raw_input": "retain as evidence with context, timestamp, and source refs",
            "canonical_meal_record": (
                "keep MealThread/FoodDB as truth; memory stores refs and patterns"
            ),
            "reviewed_memory": (
                "promote only after future utility, novelty, factuality, and safety"
            ),
            "rag": "scope and metadata filters before semantic or hybrid retrieval",
        },
    }


def _candidate_skill_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    matched: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name != "SKILL.md" and path.suffix.lower() not in {".md", ".mdx"}:
            continue
        lower = str(path).lower()
        if not any(token in lower for token in _skill_tokens()):
            continue
        matched.append(path)
        if len(matched) >= 40:
            break
    return matched


def _skill_tokens() -> tuple[str, ...]:
    return (
        "skill",
        "memory",
        "recall",
        "retain",
        "rag",
        "hindsight",
        "mem0",
        "openclaw",
        "hermes",
    )


def _read_preview(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")[:4000]
    except OSError:
        return ""


def _adopted_skill_patterns(corpus: str) -> list[str]:
    patterns: list[str] = []
    if "future utility" in corpus:
        patterns.append("future_utility_gate")
    if "novelty" in corpus:
        patterns.append("novelty_gate")
    if "factual" in corpus:
        patterns.append("factuality_gate")
    if "safe" in corpus or "credential" in corpus or "secret" in corpus:
        patterns.append("safety_secret_gate")
    if "document_id" in corpus:
        patterns.append("stable_document_id")
    if "tag" in corpus and "recall" in corpus:
        patterns.append("tag_scope_before_recall")
    if "context" in corpus and "timestamp" in corpus:
        patterns.append("context_timestamp_required")
    return patterns or ["read_only_skill_inventory"]


def _deferred_skill_patterns(corpus: str) -> list[str]:
    patterns = [
        "automatic_memory_add",
        "automatic_memory_update",
        "live_recall_injection",
        "provider_service_start",
    ]
    if "memory_delete" in corpus:
        patterns.append("automatic_memory_delete")
    if "post_llm_call" in corpus or "after every response" in corpus:
        patterns.append("post_response_auto_capture")
    return patterns


__all__ = ["build_local_skill_reference_summary"]
