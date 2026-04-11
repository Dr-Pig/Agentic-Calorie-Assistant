from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, desc, inspect
from sqlalchemy.orm import sessionmaker, Session

from .infrastructure.exact_item_search import ensure_exact_item_fts
from .models import Base, User, MealLog, MessageBuffer
from .paths import DEFAULT_DB_PATH, LEGACY_DB_PATH, REPO_ROOT, ensure_runtime_dirs

ensure_runtime_dirs()

default_sqlite_path = LEGACY_DB_PATH if LEGACY_DB_PATH.exists() else DEFAULT_DB_PATH
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_sqlite_path.as_posix()}")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

ALEMBIC_INI_PATH = REPO_ROOT / "alembic.ini"
MANAGED_TABLES = {
    "users",
    "meal_logs",
    "message_buffer",
    "meal_threads",
    "meal_versions",
    "meal_items",
    "legacy_meal_log_map",
    "day_budget_ledger",
    "ledger_entries",
    "body_observations",
    "body_plans",
    "proposal_containers",
    "proposal_options",
    "proactive_triggers",
}


def init_db():
    _run_database_migrations()
    ensure_exact_item_fts()


def _alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    return config


def _managed_tables_exist() -> bool:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    return bool(existing_tables.intersection(MANAGED_TABLES))


def _alembic_version_table_exists() -> bool:
    inspector = inspect(engine)
    return "alembic_version" in inspector.get_table_names()


def _run_database_migrations() -> None:
    config = _alembic_config()
    if _alembic_version_table_exists():
        command.upgrade(config, "head")
        return
    if _managed_tables_exist():
        raise RuntimeError(
            "Legacy schema detected without alembic_version. "
            "Run `alembic upgrade head` after resetting or migrating the database; "
            "automatic legacy stamping is disabled."
        )
    command.upgrade(config, "head")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── User ──────────────────────────────────────────────

def get_or_create_user(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ── MealLog (L1) ──────────────────────────────────────

def save_meal_log(
    db: Session,
    user: User,
    *,
    meal_title: str,
    raw_input: str,
    kcal: int,
    protein_g: int,
    carb_g: int,
    fat_g: int,
    components: list[dict[str, Any]],
    debug_steps: list[dict[str, Any]],
    status: str = "completed",
    pending_question: str | None = None,
    parent_log_id: int | None = None,
) -> MealLog:
    log = MealLog(
        user_id=user.id,
        meal_title=meal_title,
        raw_input=raw_input,
        kcal=kcal,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        components_json=components,
        debug_steps_json=debug_steps,
        status=status,
        pending_question=pending_question,
        parent_log_id=parent_log_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_latest_log(db: Session, user: User) -> MealLog | None:
    """Get the most recent non-superseded MealLog for this user."""
    print(f"[DEBUG] get_latest_log for internal user_id={user.id}")
    log = (
        db.query(MealLog)
        .filter(MealLog.user_id == user.id, MealLog.status != "superseded")
        .order_by(desc(MealLog.id))
        .first()
    )
    if log:
        print(f"[DEBUG] Checked DB: Found latest log ID={log.id}, title={log.meal_title}")
    else:
        print(f"[DEBUG] Checked DB: No suitable latest log found for user {user.id}")
    return log


def supersede_log(db: Session, log_id: int) -> None:
    """Mark a MealLog as superseded (replaced by a newer version)."""
    log = db.query(MealLog).filter(MealLog.id == log_id).first()
    if log:
        log.status = "superseded"
        db.commit()


def get_meal_log_history(db: Session, user: User, limit: int = 10, include_superseded: bool = False) -> list[MealLog]:
    query = db.query(MealLog).filter(MealLog.user_id == user.id)
    if not include_superseded:
        query = query.filter(MealLog.status != "superseded")
    print(f"[DEBUG] get_meal_log_history include_superseded={include_superseded}, count found: {query.count()}")
    return (
        query.order_by(desc(MealLog.id))
        .limit(limit)
        .all()
    )


# ── Message Buffer ────────────────────────────────────

def append_message(
    db: Session,
    user: User,
    role: str,
    content: str,
    *,
    linked_meal_log_id: int | None = None,
    trace_id: str | None = None,
) -> MessageBuffer:
    """Append a message to the conversation buffer."""
    msg = MessageBuffer(
        user_id=user.id,
        role=role,
        content=content,
        linked_meal_log_id=linked_meal_log_id,
        trace_id=trace_id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def update_message_linkage(
    db: Session,
    *,
    message_id: int,
    linked_meal_log_id: int | None,
    trace_id: str | None = None,
) -> MessageBuffer | None:
    msg = db.query(MessageBuffer).filter(MessageBuffer.id == message_id).first()
    if not msg:
        return None
    msg.linked_meal_log_id = linked_meal_log_id
    if trace_id is not None:
        msg.trace_id = trace_id
    db.commit()
    db.refresh(msg)
    return msg


def get_latest_message_for_role(db: Session, user: User, role: str) -> MessageBuffer | None:
    return (
        db.query(MessageBuffer)
        .filter(MessageBuffer.user_id == user.id, MessageBuffer.role == role)
        .order_by(desc(MessageBuffer.id))
        .first()
    )


def get_recent_messages(db: Session, user: User, limit: int = 10) -> list[MessageBuffer]:
    """Get the most recent messages for this user, ordered oldest-first."""
    msgs = (
        db.query(MessageBuffer)
        .filter(MessageBuffer.user_id == user.id)
        .order_by(desc(MessageBuffer.created_at))
        .limit(limit)
        .all()
    )
    return list(reversed(msgs))


def get_conversation_archive(db: Session, user: User, limit: int | None = None) -> list[MessageBuffer]:
    query = (
        db.query(MessageBuffer)
        .filter(MessageBuffer.user_id == user.id)
        .order_by(MessageBuffer.created_at.asc(), MessageBuffer.id.asc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()
