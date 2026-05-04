from __future__ import annotations

import zipfile
from pathlib import Path


def test_local_framework_deep_review_reads_memory_reference_zip_without_extracting(
    tmp_path: Path,
) -> None:
    zip_path = tmp_path / "cc-haha-main.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "cc-haha-main/docs/memory.md",
            "future utility novelty factuality safety recall tags timestamp memory_add",
        )

    from app.memory.application.local_memory_framework_review import (
        build_local_framework_deep_review,
    )

    artifact = build_local_framework_deep_review(tmp_path)

    assert artifact["read_only_review"] is True
    assert artifact["service_started"] is False
    assert artifact["live_provider_called"] is False
    assert artifact["zip_reference_summary"]["zip_files_reviewed"] == 1
    assert artifact["zip_reference_summary"]["archive_extracted"] is False
    assert artifact["zip_reference_summary"]["tool_or_provider_started"] is False
    assert "cc-haha-main.zip" in artifact["zip_reference_summary"]["zip_files"][0]
    assert (
        "future_utility_gate"
        in artifact["zip_reference_summary"]["adopted_zip_patterns"]
    )
    assert (
        "automatic_memory_add"
        in artifact["zip_reference_summary"]["deferred_zip_patterns"]
    )
