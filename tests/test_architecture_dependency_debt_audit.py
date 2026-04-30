from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import audit_architecture_dependency_debt as audit


def test_b2_exact_item_search_no_longer_depends_on_central_database() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    database_source = (repo_root / "app" / "database.py").read_text(encoding="utf-8")
    exact_search_source = (
        repo_root / "app" / "nutrition" / "infrastructure" / "exact_item_search.py"
    ).read_text(encoding="utf-8")

    assert "exact_item_search" not in database_source
    assert "ensure_exact_item_fts" not in database_source
    assert "app.database" not in exact_search_source


def test_architecture_debt_audit_flags_new_forbidden_import(tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    runtime_dir = app_root / "runtime" / "application"
    runtime_dir.mkdir(parents=True)
    (app_root / "__init__.py").write_text("", encoding="utf-8")
    (app_root / "runtime" / "__init__.py").write_text("", encoding="utf-8")
    (runtime_dir / "__init__.py").write_text("", encoding="utf-8")
    offender = runtime_dir / "new_runtime_coupling.py"
    offender.write_text("from app.budget.application import current_budget_answer\n", encoding="utf-8")

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({"allowed_findings": []}, indent=2), encoding="utf-8")

    report = audit.audit_architecture_dependency_debt(
        repo_root=tmp_path,
        baseline_path=baseline_path,
    )

    assert report["passed"] is False
    assert report["new_finding_count"] == 1
    assert report["new_findings"][0]["category"] == "runtime_shared_to_business_domain"


def test_architecture_debt_audit_allows_recorded_baseline(tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    runtime_dir = app_root / "runtime" / "application"
    runtime_dir.mkdir(parents=True)
    (app_root / "__init__.py").write_text("", encoding="utf-8")
    (app_root / "runtime" / "__init__.py").write_text("", encoding="utf-8")
    (runtime_dir / "__init__.py").write_text("", encoding="utf-8")
    offender = runtime_dir / "existing_runtime_coupling.py"
    offender.write_text("from app.budget.application import current_budget_answer\n", encoding="utf-8")

    expected = audit.Finding(
        category="runtime_shared_to_business_domain",
        path="app/runtime/application/existing_runtime_coupling.py",
        line=1,
        import_name="app.budget.application",
    )
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps({"allowed_findings": [expected.to_dict()]}, indent=2),
        encoding="utf-8",
    )

    report = audit.audit_architecture_dependency_debt(
        repo_root=tmp_path,
        baseline_path=baseline_path,
    )

    assert report["passed"] is True
    assert report["known_finding_count"] == 1
    assert report["new_findings"] == []

