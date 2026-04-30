from __future__ import annotations

from pathlib import Path

from scripts.audit_repo_legacy_surfaces import build_report


def test_repo_legacy_surface_audit_detects_tracked_archive_path(tmp_path: Path) -> None:
    report = build_report(
        root=tmp_path,
        tracked_paths=[("docs/" + "archive/old.md")],
    )

    assert report["fails_build"] is True
    assert report["tracked_path_finding_count"] == 1


def test_repo_legacy_surface_audit_detects_stale_text_marker(tmp_path: Path) -> None:
    target = tmp_path / "app" / "runtime" / "example.py"
    target.parent.mkdir(parents=True)
    legacy_action = "run_" + "nutrition" + "_resolution"
    target.write_text(f"token = '{legacy_action}'\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["text_finding_count"] >= 1


def test_repo_legacy_surface_audit_detects_legacy_bundle_runner_marker(tmp_path: Path) -> None:
    target = tmp_path / "scripts" / "example.py"
    target.parent.mkdir(parents=True)
    legacy_runner = "run_v2_" + "bundle2" + "_live_eval"
    target.write_text(f"token = '{legacy_runner}'\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["text_finding_count"] >= 1


def test_repo_legacy_surface_audit_detects_legacy_bundle_readiness_language(tmp_path: Path) -> None:
    target = tmp_path / "docs" / "quality" / "example.md"
    target.parent.mkdir(parents=True)
    marker = "Bundle " + "readiness"
    target.write_text(f"## {marker}\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["text_finding_count"] >= 1


def test_repo_legacy_surface_audit_passes_clean_temp_repo(tmp_path: Path) -> None:
    target = tmp_path / "app" / "runtime" / "example.py"
    target.parent.mkdir(parents=True)
    target.write_text("token = 'manager_runtime'\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=["app/runtime/example.py"])

    assert report["fails_build"] is False
    assert report["finding_count"] == 0
