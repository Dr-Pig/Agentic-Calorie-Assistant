from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path


HOME = Path.home()
CODEX_HOME = HOME / ".codex"
AUTOMATIONS_DIR = CODEX_HOME / "automations"
DB_PATH = CODEX_HOME / "sqlite" / "codex-dev.db"
REPO_ROOT = Path(__file__).resolve().parents[1]

AUTOMATION_NAME = "Bundle Eval Heartbeat"
AUTOMATION_PROMPT = (
    "Run the strict eval heartbeat pipeline for the line-liff calorie app. "
    "Load owner truth, run parity audits, Bundle 1 and Bundle 2 official eval, "
    "trace/text integrity checks, founder realism, and benchmark shadow suite. "
    "Report only verdicts, blockers, deltas, and latest report paths. "
    "Do not claim pass unless official, founder, and promoted blocking benchmark gates are green."
)
AUTOMATION_RRULE = "FREQ=HOURLY;INTERVAL=1;BYMINUTE=0"


def _toml_text(automation_id: str) -> str:
    cwd = str(REPO_ROOT).replace("\\", "\\\\")
    prompt = AUTOMATION_PROMPT.replace('"', '\\"')
    return (
        f'id = "{automation_id}"\n'
        f'name = "{AUTOMATION_NAME}"\n'
        f'prompt = "{prompt}"\n'
        'kind = "heartbeat"\n'
        'destination = "thread"\n'
        'status = "ACTIVE"\n'
        f'rrule = "{AUTOMATION_RRULE}"\n'
        'model = "gpt-5.4"\n'
        'reasoningEffort = "high"\n'
        f'cwds = ["{cwd}"]\n'
    )


def main() -> int:
    AUTOMATIONS_DIR.mkdir(parents=True, exist_ok=True)
    automation_id = f"bundle-eval-heartbeat-{uuid.uuid4().hex[:8]}"
    automation_dir = AUTOMATIONS_DIR / automation_id
    automation_dir.mkdir(parents=True, exist_ok=True)
    (automation_dir / "automation.toml").write_text(_toml_text(automation_id), encoding="utf-8")

    now = int(time.time())
    next_run = now + 3600
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO automations
            (id, name, prompt, status, next_run_at, last_run_at, cwds, rrule, model, reasoning_effort, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                automation_id,
                AUTOMATION_NAME,
                AUTOMATION_PROMPT,
                "ACTIVE",
                next_run,
                None,
                json.dumps([str(REPO_ROOT)]),
                AUTOMATION_RRULE,
                "gpt-5.4",
                "high",
                now,
                now,
            ),
        )
        con.commit()
    finally:
        con.close()

    print(
        json.dumps(
            {
                "automation_id": automation_id,
                "toml_path": str(automation_dir / "automation.toml"),
                "db_path": str(DB_PATH),
                "next_run_at": next_run,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
