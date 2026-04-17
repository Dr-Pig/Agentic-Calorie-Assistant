from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
RUNNER_REGISTRY_PATH = ROOT / "docs" / "quality" / "AUDIT_RUNNER_REGISTRY.json"
FIXTURE_REGISTRY_PATH = ROOT / "docs" / "quality" / "AUDIT_FIXTURE_REGISTRY.json"


@dataclass(frozen=True)
class SuiteFilters:
    authority_tiers: tuple[str, ...] = ()
    workflow_families: tuple[str, ...] = ()
    validation_layers: tuple[str, ...] = ()
    suite_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlannedCommand:
    suite_id: str
    command: tuple[str, ...]
    runner_path: str
    fixture_path: str | None
    note: str


@dataclass(frozen=True)
class SuitePlan:
    suite_id: str
    authority_tier: str
    workflow_family: str
    validation_layer: str
    runners: tuple[dict[str, str], ...]
    fixtures: tuple[dict[str, str], ...]
    commands: tuple[PlannedCommand, ...]
    issues: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionResult:
    suite_id: str
    returncode: int
    command: tuple[str, ...]
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _load_registry(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list")
    normalized: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"{path} entries must be objects")
        normalized.append({str(key): str(value) for key, value in item.items()})
    return normalized


def _matches_filters(entry: dict[str, str], filters: SuiteFilters) -> bool:
    if filters.authority_tiers and entry.get("authority_tier") not in filters.authority_tiers:
        return False
    if filters.workflow_families and entry.get("workflow_family") not in filters.workflow_families:
        return False
    if filters.validation_layers and entry.get("validation_layer") not in filters.validation_layers:
        return False
    if filters.suite_ids and entry.get("suite_id") not in filters.suite_ids:
        return False
    return True


def _selected_entries(entries: Sequence[dict[str, str]], filters: SuiteFilters) -> list[dict[str, str]]:
    return [entry for entry in entries if _matches_filters(entry, filters)]


def _read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_known_commands(
    runner: dict[str, str],
    fixtures: Sequence[dict[str, str]],
    *,
    semantic_routing_mock: bool,
) -> tuple[list[PlannedCommand], list[str]]:
    script_path = ROOT / runner["path"]
    script_name = script_path.name
    suite_id = runner["suite_id"]
    commands: list[PlannedCommand] = []
    issues: list[str] = []

    if script_name == "run_founder_golden_audit.py":
        if not fixtures:
            issues.append("missing_fixture_for_runner")
            return commands, issues
        for fixture in fixtures:
            commands.append(
                PlannedCommand(
                    suite_id=suite_id,
                    command=(
                        sys.executable,
                        str(script_path),
                        "--fixture",
                        str(ROOT / fixture["path"]),
                    ),
                    runner_path=runner["path"],
                    fixture_path=fixture["path"],
                    note="single_fixture_run",
                )
            )
        return commands, issues

    if script_name == "run_turn2_hybrid_replay.py":
        if not fixtures:
            issues.append("missing_fixture_for_runner")
            return commands, issues
        for fixture in fixtures:
            payload = _read_json_file(ROOT / fixture["path"])
            cases = payload.get("cases", [])
            if not isinstance(cases, list) or not cases:
                issues.append(f"fixture_has_no_cases:{fixture['path']}")
                continue
            for case in cases:
                case_id = case.get("case_id")
                if not isinstance(case_id, str) or not case_id:
                    issues.append(f"fixture_case_missing_case_id:{fixture['path']}")
                    continue
                commands.append(
                    PlannedCommand(
                        suite_id=suite_id,
                        command=(
                            sys.executable,
                            str(script_path),
                            "--case-id",
                            case_id,
                            "--mode",
                            "full",
                        ),
                        runner_path=runner["path"],
                        fixture_path=fixture["path"],
                        note="expanded_from_fixture_cases",
                    )
                )
        return commands, issues

    if script_name == "run_semantic_routing_eval.py":
        if suite_id == "semantic_routing_provisional_smoke_v1":
            command = [sys.executable, str(script_path), "--mode", "provisional_smoke"]
        elif suite_id == "semantic_routing_official_canonical_v1":
            command = [sys.executable, str(script_path), "--mode", "official_canonical"]
        else:
            issues.append(f"unsupported_semantic_routing_suite:{suite_id}")
            return commands, issues

        if semantic_routing_mock:
            command.append("--mock")

        matched_fixture_path = fixtures[0]["path"] if fixtures else None
        commands.append(
            PlannedCommand(
                suite_id=suite_id,
                command=tuple(command),
                runner_path=runner["path"],
                fixture_path=matched_fixture_path,
                note="runner_owned_fixture_selection",
            )
        )
        if not fixtures:
            issues.append("runner_has_no_fixture_match")
        return commands, issues

    if script_name == "run_rescue_executable_pack.py":
        matched_fixture_path = fixtures[0]["path"] if fixtures else None
        commands.append(
            PlannedCommand(
                suite_id=suite_id,
                command=(sys.executable, str(script_path)),
                runner_path=runner["path"],
                fixture_path=matched_fixture_path,
                note="derived_executable_runner",
            )
        )
        if not fixtures:
            issues.append("runner_has_no_fixture_match")
        return commands, issues

    if script_name == "run_intake_executable_pack.py":
        matched_fixture_path = fixtures[0]["path"] if fixtures else None
        commands.append(
            PlannedCommand(
                suite_id=suite_id,
                command=(sys.executable, str(script_path)),
                runner_path=runner["path"],
                fixture_path=matched_fixture_path,
                note="derived_executable_runner",
            )
        )
        if not fixtures:
            issues.append("runner_has_no_fixture_match")
        return commands, issues

    issues.append(f"unsupported_runner:{runner['path']}")
    return commands, issues


def build_suite_plan(*, filters: SuiteFilters, semantic_routing_mock: bool = False) -> dict[str, tuple[SuitePlan, ...]]:
    runners = _selected_entries(_load_registry(RUNNER_REGISTRY_PATH), filters)
    fixtures = _selected_entries(_load_registry(FIXTURE_REGISTRY_PATH), filters)

    runner_map: dict[str, list[dict[str, str]]] = {}
    fixture_map: dict[str, list[dict[str, str]]] = {}
    for runner in runners:
        runner_map.setdefault(runner["suite_id"], []).append(runner)
    for fixture in fixtures:
        fixture_map.setdefault(fixture["suite_id"], []).append(fixture)

    selected_suite_ids = sorted(set(runner_map) | set(fixture_map))
    runnable: list[SuitePlan] = []
    fixture_only: list[SuitePlan] = []
    runner_only: list[SuitePlan] = []
    unsupported: list[SuitePlan] = []

    for suite_id in selected_suite_ids:
        suite_runners = tuple(runner_map.get(suite_id, ()))
        suite_fixtures = tuple(fixture_map.get(suite_id, ()))
        metadata_source = suite_runners[0] if suite_runners else suite_fixtures[0]
        all_commands: list[PlannedCommand] = []
        issues: list[str] = []
        for runner in suite_runners:
            runner_commands, runner_issues = _build_known_commands(
                runner,
                suite_fixtures,
                semantic_routing_mock=semantic_routing_mock,
            )
            all_commands.extend(runner_commands)
            issues.extend(runner_issues)

        suite_plan = SuitePlan(
            suite_id=suite_id,
            authority_tier=metadata_source["authority_tier"],
            workflow_family=metadata_source["workflow_family"],
            validation_layer=metadata_source["validation_layer"],
            runners=suite_runners,
            fixtures=suite_fixtures,
            commands=tuple(all_commands),
            issues=tuple(issues),
        )

        if suite_runners and suite_fixtures and suite_plan.commands:
            runnable.append(suite_plan)
        elif suite_runners and not suite_fixtures:
            runner_only.append(suite_plan)
        elif suite_fixtures and not suite_runners:
            fixture_only.append(suite_plan)
        else:
            unsupported.append(suite_plan)

    return {
        "runnable": tuple(runnable),
        "fixture_only": tuple(fixture_only),
        "runner_only": tuple(runner_only),
        "unsupported": tuple(unsupported),
    }


def execute_suite_plan(plan: dict[str, tuple[SuitePlan, ...]]) -> dict[str, tuple[ExecutionResult, ...]]:
    passed: list[ExecutionResult] = []
    failed: list[ExecutionResult] = []

    for suite_plan in plan["runnable"]:
        for command in suite_plan.commands:
            completed = subprocess.run(
                list(command.command),
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            result = ExecutionResult(
                suite_id=command.suite_id,
                returncode=completed.returncode,
                command=command.command,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
            if result.ok:
                passed.append(result)
            else:
                failed.append(result)

    return {
        "passed": tuple(passed),
        "failed": tuple(failed),
    }


def _print_filters(filters: SuiteFilters) -> None:
    print("Selected filters:")
    print(f"  authority_tier={list(filters.authority_tiers) or ['*']}")
    print(f"  workflow_family={list(filters.workflow_families) or ['*']}")
    print(f"  validation_layer={list(filters.validation_layers) or ['*']}")
    print(f"  suite_id={list(filters.suite_ids) or ['*']}")


def _print_plan_group(label: str, plans: Sequence[SuitePlan]) -> None:
    print(f"{label}: {len(plans)}")
    for plan in plans:
        print(
            f"  - {plan.suite_id} | authority={plan.authority_tier} | "
            f"workflow={plan.workflow_family} | validation={plan.validation_layer}"
        )
        if plan.runners:
            print(f"    runners={', '.join(item['path'] for item in plan.runners)}")
        if plan.fixtures:
            print(f"    fixtures={', '.join(item['path'] for item in plan.fixtures)}")
        for issue in plan.issues:
            print(f"    issue={issue}")
        for command in plan.commands:
            print(f"    command={' '.join(command.command)}")


def print_suite_plan(plan: dict[str, tuple[SuitePlan, ...]], filters: SuiteFilters) -> None:
    _print_filters(filters)
    print("Plan summary:")
    _print_plan_group("  runnable", plan["runnable"])
    _print_plan_group("  fixture_only", plan["fixture_only"])
    _print_plan_group("  runner_only", plan["runner_only"])
    _print_plan_group("  unsupported", plan["unsupported"])


def print_execution_results(results: dict[str, tuple[ExecutionResult, ...]]) -> None:
    print("Execution results:")
    print(f"  passed={len(results['passed'])}")
    print(f"  failed={len(results['failed'])}")
    for result in results["passed"]:
        print(f"  [PASS] {result.suite_id} :: {' '.join(result.command)}")
    for result in results["failed"]:
        print(f"  [FAIL] {result.suite_id} :: {' '.join(result.command)}")
        if result.stderr.strip():
            print(f"    stderr={result.stderr.strip()}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Filter and orchestrate registered suite runners.")
    parser.add_argument("--authority-tier", action="append", default=[], help="Filter by authority_tier.")
    parser.add_argument("--workflow-family", action="append", default=[], help="Filter by workflow_family.")
    parser.add_argument("--validation-layer", action="append", default=[], help="Filter by validation_layer.")
    parser.add_argument("--suite-id", action="append", default=[], help="Filter by suite_id.")
    parser.add_argument("--execute", action="store_true", help="Run the planned commands after printing the plan.")
    parser.add_argument(
        "--semantic-routing-mock",
        action="store_true",
        help="Append --mock when orchestrating the semantic routing runner.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    filters = SuiteFilters(
        authority_tiers=tuple(args.authority_tier),
        workflow_families=tuple(args.workflow_family),
        validation_layers=tuple(args.validation_layer),
        suite_ids=tuple(args.suite_id),
    )
    plan = build_suite_plan(filters=filters, semantic_routing_mock=bool(args.semantic_routing_mock))
    print_suite_plan(plan, filters)
    if not args.execute:
        return 0

    results = execute_suite_plan(plan)
    print_execution_results(results)
    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
