from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_replay_pack import (  # noqa: E402
    build_context_replay_pack_artifact,
)
from app.composition.accurate_intake_fake_provider_context_smoke import (  # noqa: E402
    build_fake_provider_context_smoke_artifact,
)
from app.composition.current_shell_fixture_e2e import (  # noqa: E402
    build_current_shell_fixture_e2e_artifact,
)
from scripts.run_accurate_intake_browser_realistic_web_dogfood_v2 import (  # noqa: E402
    build_browser_realistic_web_dogfood_v2_report,
)
from scripts.run_accurate_intake_mvp_self_use_smoke import (  # noqa: E402
    build_one_day_self_use_reopen_report,
    build_one_day_self_use_scenario_wall_report,
)

DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_current_shell_fixture_e2e.sqlite3"
DEFAULT_BROWSER_DB_PATH = (
    ROOT / ".pytest_tmp_local" / "accurate_intake_current_shell_fixture_e2e_browser.sqlite3"
)
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_current_shell_fixture_e2e.json"


def build_current_shell_fixture_e2e_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    browser_db_path: Path = DEFAULT_BROWSER_DB_PATH,
    require_browser_execution: bool = False,
    timeout_ms: int = 15000,
    headless: bool = True,
) -> dict[str, object]:
    one_day_wall = build_one_day_self_use_scenario_wall_report(
        db_path=db_path,
        reset_db=True,
    )
    reopen_continuity = build_one_day_self_use_reopen_report(db_path=db_path)
    browser_realistic = build_browser_realistic_web_dogfood_v2_report(
        db_path=browser_db_path,
        reset_db=True,
        require_browser_execution=require_browser_execution,
        timeout_ms=timeout_ms,
        headless=headless,
    )
    return build_current_shell_fixture_e2e_artifact(
        one_day_wall=one_day_wall,
        reopen_continuity=reopen_continuity,
        browser_realistic=browser_realistic,
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the fixture-only CurrentShell E2E diagnostic."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--browser-db-path", default=str(DEFAULT_BROWSER_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args(argv)

    report = build_current_shell_fixture_e2e_report(
        db_path=Path(args.db_path),
        browser_db_path=Path(args.browser_db_path),
        require_browser_execution=args.require_browser_execution,
        timeout_ms=args.timeout_ms,
        headless=not args.headed,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] == "current_shell_fixture_e2e_diagnostic_pass":
        return 0
    if report["status"] == "blocked_browser_execution_unavailable" and not args.require_browser_execution:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
