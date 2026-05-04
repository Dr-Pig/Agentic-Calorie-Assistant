from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class LocalSQLiteRouteHarness:
    """Context-managed FastAPI route harness for isolated local SQLite tests."""

    def __init__(
        self,
        *,
        app: FastAPI,
        db_dependency: Callable[..., Any],
        db_path: Path,
        base_metadata: Any | None = None,
    ) -> None:
        self.app = app
        self.db_dependency = db_dependency
        self.db_path = db_path
        self.base_metadata = base_metadata
        self.engine: Engine | None = None
        self.SessionLocal: sessionmaker[Session] | None = None
        self.client: TestClient | None = None
        self._had_previous_override = False
        self._previous_override: Any = None

    def __enter__(self) -> "LocalSQLiteRouteHarness":
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        if self.base_metadata is not None:
            self.base_metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._had_previous_override = self.db_dependency in self.app.dependency_overrides
        self._previous_override = self.app.dependency_overrides.get(self.db_dependency)

        def override_get_db():
            if self.SessionLocal is None:
                raise RuntimeError("LocalSQLiteRouteHarness is not active.")
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[self.db_dependency] = override_get_db
        self.client = TestClient(self.app)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
        if self._had_previous_override:
            self.app.dependency_overrides[self.db_dependency] = self._previous_override
        else:
            self.app.dependency_overrides.pop(self.db_dependency, None)
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None
        self.SessionLocal = None


__all__ = ["LocalSQLiteRouteHarness"]
