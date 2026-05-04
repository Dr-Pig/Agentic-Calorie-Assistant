from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any


def build_local_zip_reference_summary(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    zip_files = _candidate_zip_files(root_path)
    previews = [_zip_preview(path) for path in zip_files]
    corpus = "\n".join(preview["text"].lower() for preview in previews)
    return {
        "read_only_review": True,
        "archive_extracted": False,
        "tool_or_provider_started": False,
        "zip_files_reviewed": len(zip_files),
        "zip_files": [str(path.relative_to(root_path)) for path in zip_files],
        "zip_entry_count": sum(len(preview["entries"]) for preview in previews),
        "evidence_entries": [
            entry for preview in previews for entry in preview["entries"]
        ],
        "adopted_zip_patterns": _adopted_zip_patterns(corpus),
        "deferred_zip_patterns": _deferred_zip_patterns(corpus),
    }


def _candidate_zip_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    zip_files: list[Path] = []
    for path in root.glob("*.zip"):
        lower = path.name.lower()
        if not any(token in lower for token in _zip_tokens()):
            continue
        zip_files.append(path)
        if len(zip_files) >= 20:
            break
    return zip_files


def _zip_tokens() -> tuple[str, ...]:
    return (
        "cc-haha",
        "claw",
        "openclaw",
        "hermes",
        "memory",
        "hindsight",
        "mem0",
        "langgraph",
        "openai-agents",
    )


def _zip_preview(path: Path) -> dict[str, Any]:
    entries: list[str] = []
    text_parts: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if len(entries) >= 30:
                    break
                if info.is_dir() or not _is_candidate_entry(info.filename):
                    continue
                entries.append(info.filename)
                with archive.open(info) as file:
                    text_parts.append(file.read(5000).decode("utf-8", errors="replace"))
    except (OSError, zipfile.BadZipFile):
        return {"zip_file": str(path), "entries": [], "text": ""}
    return {"zip_file": str(path), "entries": entries, "text": "\n".join(text_parts)}


def _is_candidate_entry(filename: str) -> bool:
    lower = filename.lower()
    if not lower.endswith((".md", ".mdx", ".json", ".ts", ".py", ".rs")):
        return False
    return any(token in lower for token in _entry_tokens())


def _entry_tokens() -> tuple[str, ...]:
    return (
        "memory",
        "recall",
        "retain",
        "rag",
        "context",
        "skill",
        "hindsight",
    )


def _adopted_zip_patterns(corpus: str) -> list[str]:
    patterns: list[str] = []
    if "future utility" in corpus:
        patterns.append("future_utility_gate")
    if "novelty" in corpus:
        patterns.append("novelty_gate")
    if "factual" in corpus:
        patterns.append("factuality_gate")
    if "safety" in corpus or "secret" in corpus:
        patterns.append("safety_or_secret_gate")
    if "tag" in corpus and "recall" in corpus:
        patterns.append("tag_or_scope_before_recall")
    if "timestamp" in corpus:
        patterns.append("timestamped_context_evidence")
    return patterns or ["read_only_zip_inventory"]


def _deferred_zip_patterns(corpus: str) -> list[str]:
    patterns = [
        "archive_code_execution",
        "provider_service_start",
        "live_recall_injection",
    ]
    if "memory_add" in corpus:
        patterns.append("automatic_memory_add")
    if "memory_update" in corpus:
        patterns.append("automatic_memory_update")
    return patterns


__all__ = ["build_local_zip_reference_summary"]
