from __future__ import annotations

from pathlib import Path

from scripts.repo_policy import (
    category_for_repo_path,
    effective_cap_for_repo_path,
    iter_active_python_files,
    load_active_code_policy,
    normalize_repo_path,
)

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CODE_POLICY = load_active_code_policy()
ALLOWED_SUPPORT_HELPER_SEAMS = {
    "app/composition/canonical_body_support.py",
    "app/composition/canonical_commit_support.py",
    "app/composition/canonical_proposal_support.py",
    "app/intake/application/intake_turn_support.py",
    "app/runtime/agent/manager_support_prompts.py",
    "app/runtime/infrastructure/session_archive_query_support.py",
    "app/nutrition/application/answer_support.py",
    "app/nutrition/agent/nutrition_estimation_support.py",
    "app/nutrition/agent/exact_item_candidate_support.py",
}


def _legacy_path_token(*parts: str) -> str:
    return "".join(parts)

ACTIVE_FILE_LINE_LIMITS = {
    ROOT / Path(path): int(limit)
    for path, limit in ACTIVE_CODE_POLICY["transition_overrides"].items()
}

ACTIVE_IMPORT_GUARDS = {
    ROOT / "app" / "composition" / "intake_turn_orchestrator.py": (
        _legacy_path_token("app.", "use", "cases"),
        _legacy_path_token("..", "use", "cases"),
    ),
    ROOT / "app" / "composition" / "intake_execution_orchestrator.py": (
        _legacy_path_token("app.", "use", "cases"),
        _legacy_path_token("..", "use", "cases"),
    ),
    ROOT / "app" / "composition" / "state_resolver.py": (
        "app.runtime.application",
        "..application",
    ),
    ROOT / "app" / "composition" / "onboarding_service.py": (
        "app.runtime.application",
        "..application",
    ),
    ROOT / "app" / "composition" / "current_budget_answer.py": (
        "app.runtime.application",
        "..application",
    ),
    ROOT / "app" / "composition" / "calibration_commit_bridge.py": (
        "app.runtime.application",
        "..application",
    ),
    ROOT / "app" / "composition" / "intake_routes.py": (
        _legacy_path_token("app.", "use", "cases"),
        _legacy_path_token("..", "use", "cases"),
    ),
}

IGNORED_REPO_PARTS = {
    ".git",
    "__pycache__",
    "runtime",
    ".logs",
    ".pytest_tmp_local",
    ".pytest_tmp2",
    "artifacts",
    "docs-snapshots",
}


def _legacy_token(prefix: str, suffix: str) -> str:
    return prefix + suffix


LEGACY_BANNED_TOKENS = (
    _legacy_token("planner", "_provider"),
    _legacy_token("primary", "_provider"),
    "planner" + "_pass",
    "planner" + "_pass_initial",
    "decision" + "_pass",
    "nutrition" + "_resolution_pass",
    "final" + "_response_pass",
    "first" + "_bad_pass",
    "Decision" + "PassResult",
    "Nutrition" + "ResolutionResult",
    "Pass" + "ExecutionEnvelope",
)


def test_active_domain_files_stay_under_line_limits() -> None:
    violations: list[str] = []
    for path, limit in ACTIVE_FILE_LINE_LIMITS.items():
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > limit:
            violations.append(f"{path.name}: {line_count}>{limit}")
    assert not violations, f"fat-file guard failed: {', '.join(violations)}"


def test_active_app_python_files_are_mapped_to_categories() -> None:
    unmapped: list[str] = []
    for path in iter_active_python_files(ACTIVE_CODE_POLICY):
        repo_path = normalize_repo_path(path)
        if category_for_repo_path(repo_path, ACTIVE_CODE_POLICY) is None:
            unmapped.append(repo_path)
    assert not unmapped, f"active app python files are unmapped in the active code policy: {unmapped[:20]}"


def test_top_level_app_packages_have_domain_status() -> None:
    excluded_packages = {"__pycache__"}
    known_domains = set(ACTIVE_CODE_POLICY["domain_status"])
    top_level_packages = {
        path.name
        for path in (ROOT / "app").iterdir()
        if path.is_dir() and path.name not in excluded_packages
    }
    missing = sorted(top_level_packages - known_domains)

    assert not missing, f"top-level app packages need domain_status ownership entries: {missing}"


def test_no_empty_symmetry_files_under_active_app_packages() -> None:
    owned_layer_dirs = {"agent", "application", "contracts", "domain", "infrastructure", "interface"}
    offenders: list[str] = []

    for path in iter_active_python_files(ACTIVE_CODE_POLICY):
        repo_path = normalize_repo_path(path)
        if path.name == "__init__.py":
            continue
        if not any(part in owned_layer_dirs for part in path.parts):
            continue

        meaningful_lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip()
            and not line.strip().startswith("#")
            and line.strip() != "from __future__ import annotations"
        ]
        if not meaningful_lines or meaningful_lines == ["pass"]:
            offenders.append(repo_path)

    assert not offenders, f"empty symmetry files are not allowed in active app packages: {offenders}"


def test_transition_override_paths_have_effective_caps() -> None:
    missing: list[str] = []
    for path_str in ACTIVE_CODE_POLICY["transition_overrides"]:
        if effective_cap_for_repo_path(path_str, ACTIVE_CODE_POLICY) is None:
            missing.append(path_str)
    assert not missing, f"transition override paths must resolve to effective caps: {missing}"


def test_active_domain_files_do_not_reimport_legacy_usecases() -> None:
    violations: list[str] = []
    for path, banned_imports in ACTIVE_IMPORT_GUARDS.items():
        source = path.read_text(encoding="utf-8")
        for banned in banned_imports:
            if banned in source:
                violations.append(f"{path.name}: {banned}")
    assert not violations, f"layer dependency guard failed: {', '.join(violations)}"


def test_intake_execution_orchestrator_stays_thin_and_does_not_own_domain_semantics() -> None:
    source = (ROOT / "app" / "composition" / "intake_execution_orchestrator.py").read_text(encoding="utf-8")
    banned_tokens = (
        "_CORRECTION_STOP_TOKENS",
        "_REMOVAL_CUE_TOKENS",
        "_apply_component_replacement_correction_fallback",
        "_apply_item_removal_correction_fallback",
        "_nutrition_tool_outputs",
        "_promotion_signals",
        "_macro_summary",
        "_evidence_summary",
    )
    offenders = [token for token in banned_tokens if token in source]
    assert not offenders, f"intake_execution_orchestrator owns extracted semantics: {offenders}"


def test_active_path_uses_single_manager_loop_not_fixed_step_pipeline() -> None:
    active_paths = (
        ROOT / "app" / "composition" / "intake_turn_orchestrator.py",
        ROOT / "app" / "composition" / "intake_execution_orchestrator.py",
        ROOT / "app" / "runtime" / "application" / "manager_service.py",
        ROOT / "app" / "runtime" / "agent" / "manager.py",
    )
    banned_tokens = (
        "decide_" + "intake_turn_turn",
        "decide_" + "intake_execution_step1",
        "decide_" + "intake_execution_step2",
        "execute_" + "intake_manager_tool_batch",
        "def _normalized(",
        "promotion_" + "signals",
    )
    offenders: list[str] = []
    for path in active_paths:
        source = path.read_text(encoding="utf-8", errors="ignore")
        for token in banned_tokens:
            if token in source:
                offenders.append(f"{path.relative_to(ROOT)}:{token}")
    assert not offenders, f"single-manager hardening guard failed: {offenders}"


def test_active_manager_contract_does_not_expose_reasoning_fields() -> None:
    active_paths = (
        ROOT / "app" / "runtime" / "agent" / "manager.py",
        ROOT / "app" / "providers" / "deepseek_adapter.py",
        ROOT / "app" / "providers" / "builderspace_adapter.py",
    )
    banned_tokens = (
        '"thoughts"',
        "'thoughts'",
        '"reasoning"',
        "'reasoning'",
        "chain-of-thought",
    )
    offenders: list[str] = []
    for path in active_paths:
        source = path.read_text(encoding="utf-8", errors="ignore")
        for token in banned_tokens:
            if token in source:
                offenders.append(f"{path.relative_to(ROOT)}:{token}")
    assert not offenders, f"manager contract leaked reasoning fields: {offenders}"


def test_active_manager_tool_surface_does_not_devolve_into_micro_tools() -> None:
    source = (ROOT / "app" / "composition" / "intake_execution_orchestrator.py").read_text(encoding="utf-8", errors="ignore")
    banned_tokens = (
        "lookup_nutrition_db",
        "search_official_nutrition",
        "persist_meal_log",
        "update_meal_item",
        "mark_item_removed",
        "remove_meal_thread",
    )
    offenders = [token for token in banned_tokens if token in source]
    assert not offenders, f"intake_execution manager surface devolved into micro-tools: {offenders}"


def test_active_code_does_not_encode_benchmark_fixture_shape() -> None:
    offenders: list[str] = []
    banned_tokens = (
        "expected_behavior",
        "ideal_output",
        "should_overclaim_exactness",
        "preferred_evidence_tier",
        "case_001_",
        "case_002_",
        "same_intake_thread",
    )
    active_roots = (
        ROOT / "app" / "composition",
        ROOT / "app" / "intake",
        ROOT / "app" / "runtime",
        ROOT / "app" / "providers",
    )
    ignored_suffixes = {
        "app/runtime/infrastructure/trace/trace_triage.py",
    }
    for root in active_roots:
        for path in root.rglob("*.py"):
            normalized = path.relative_to(ROOT).as_posix()
            if normalized in ignored_suffixes:
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            for token in banned_tokens:
                if token in source:
                    offenders.append(f"{path.relative_to(ROOT)}:{token}")
    assert not offenders, f"active code is encoding fixture shape instead of product truth: {offenders}"


def test_repo_has_no_provider_split_or_trace_compat_tokens() -> None:
    banned_tokens = LEGACY_BANNED_TOKENS + (
        _legacy_token("manager", "_decision_1"),
        _legacy_token("manager", "_decision_2"),
    )
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".md", ".json"}:
            continue
        normalized = str(path.relative_to(ROOT)).replace("\\", "/")
        if any(part in IGNORED_REPO_PARTS for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for token in banned_tokens:
            if token in content:
                offenders.append(f"{path.relative_to(ROOT)}:{token}")
    assert not offenders, f"hard-cut token guard failed: {offenders[:20]}"


def test_active_repo_paths_do_not_reintroduce_stage_pass_vocabulary() -> None:
    offenders: list[str] = []
    banned_path_tokens = ("pass", "planner")
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        normalized = path.relative_to(ROOT).as_posix()
        if any(part in IGNORED_REPO_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".md", ".json", ".ps1"}:
            continue
        name_lower = path.name.lower()
        if any(token in name_lower for token in banned_path_tokens):
            offenders.append(normalized)
    assert not offenders, f"legacy path vocabulary guard failed: {offenders[:20]}"


def test_active_support_or_helper_paths_must_be_allowlisted() -> None:
    offenders: list[str] = []
    for path in iter_active_python_files(ACTIVE_CODE_POLICY):
        repo_path = normalize_repo_path(path)
        file_name = path.name.lower()
        if "support" not in file_name and "helper" not in file_name and "helpers" not in file_name:
            continue
        if repo_path not in ALLOWED_SUPPORT_HELPER_SEAMS:
            offenders.append(repo_path)
    assert not offenders, f"unexpected support/helper seam paths require explicit review: {offenders}"


def test_active_mainline_paths_do_not_import_archive_app_family() -> None:
    offenders: list[str] = []
    active_roots = (
        ROOT / "app" / "intake",
        ROOT / "app" / "nutrition",
        ROOT / "app" / "budget",
        ROOT / "app" / "body",
        ROOT / "app" / "runtime",
        ROOT / "app" / "shared",
        ROOT / "app" / "providers",
    )
    for root in active_roots:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8", errors="ignore")
            if ("app." + "archive") in source:
                offenders.append(path.relative_to(ROOT).as_posix())
    assert not offenders, f"active mainline code must not import archive app families: {offenders}"


def test_canonical_specs_do_not_describe_v2_as_four_pass_runtime() -> None:
    spec_paths = (
        ROOT / "docs" / "specs" / "APP_V2_IMPLEMENTATION_PLAN.md",
        ROOT / "docs" / "specs" / "app_v2_ideal_architecture_final.md",
        ROOT / "docs" / "specs" / "L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md",
        ROOT / "docs" / "specs" / "L1_RUNTIME_OWNERSHIP_SPEC.md",
        ROOT / "docs" / "specs" / "L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md",
    )
    banned_tokens = LEGACY_BANNED_TOKENS
    offenders: list[str] = []
    for path in spec_paths:
        source = path.read_text(encoding="utf-8", errors="ignore")
        for token in banned_tokens:
            if token in source:
                offenders.append(f"{path.name}:{token}")
    assert not offenders, f"canonical spec legacy vocabulary guard failed: {offenders}"


def test_product_truth_first_guardrails_are_written_into_canonical_docs() -> None:
    required_markers = {
        ROOT / "AGENTS.md": "Product Truth Priority",
        ROOT / "docs" / "specs" / "L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md": "Product-Truth-First Build Frame",
        ROOT / "docs" / "specs" / "APP_V2_IMPLEMENTATION_PLAN.md": "Single-Manager Guardrail Frame",
    }
    missing: list[str] = []
    for path, marker in required_markers.items():
        source = path.read_text(encoding="utf-8", errors="ignore")
        if marker not in source:
            missing.append(f"{path.name}:{marker}")
    assert not missing, f"product-truth-first canonical docs are incomplete: {missing}"
