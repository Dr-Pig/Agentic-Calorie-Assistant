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
    legacy_runner = "run_v2_" + "bundle" + "2_live_eval"
    target.write_text(f"token = '{legacy_runner}'\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["text_finding_count"] >= 1


def test_repo_legacy_surface_audit_detects_active_bundle_import_marker(tmp_path: Path) -> None:
    target = tmp_path / "app" / "composition" / "example.py"
    target.parent.mkdir(parents=True)
    marker = "app.composition." + "bundle" + "2_response"
    target.write_text(f"from {marker} import build_response\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is True
    assert report["legacy_naming_finding_count"] >= 1


def test_repo_legacy_surface_audit_allows_trace_fallback_path(tmp_path: Path) -> None:
    target = tmp_path / "app" / "budget" / "interface" / "today_trace_debug.py"
    target.parent.mkdir(parents=True)
    old_turn_trace = "v2_" + "bundle1"
    old_execution_trace = "v2_" + "bundle2"
    target.write_text(f"bundles = ('{old_turn_trace}', '{old_execution_trace}')\n", encoding="utf-8")

    report = build_report(root=tmp_path, tracked_paths=[])

    assert report["fails_build"] is False
    assert report["legacy_naming_finding_count"] == 0


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
