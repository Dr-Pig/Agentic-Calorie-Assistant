from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ROOT = Path(os.getenv("RUNTIME_ROOT", REPO_ROOT / "runtime"))
WORKSPACE_DATA_ROOT = Path(os.getenv("WORKSPACE_DATA_ROOT", REPO_ROOT / "workspace_data"))

RUNTIME_DB_DIR = RUNTIME_ROOT / "db"
RUNTIME_LOG_DIR = RUNTIME_ROOT / "logs"
RUNTIME_ARTIFACT_DIR = RUNTIME_ROOT / "artifacts"
SESSION_RECORD_DIR = RUNTIME_ARTIFACT_DIR / "session_records"

LEGACY_DB_PATH = REPO_ROOT / "canary_persistence.db"
DEFAULT_DB_PATH = RUNTIME_DB_DIR / "canary_persistence.db"


def ensure_runtime_dirs() -> None:
    RUNTIME_DB_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_LOG_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_RECORD_DIR.mkdir(parents=True, exist_ok=True)

