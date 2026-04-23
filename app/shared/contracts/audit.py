from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    request_id: str
    timestamp: str
    text: str
    raw_user_input: str | None = None
    normalized_user_input: str | None = None
    user_input_unicode_escape: str | None = None
    source_page_version: str | None = None
    allow_search: bool
    status: Literal["ok", "error"]
    route_target: str | None = None
    action_taken: str | None = None
    debug_steps: list[dict[str, Any]] = Field(default_factory=list)
    llm_traces: list[dict[str, Any]] = Field(default_factory=list)
    payload: dict[str, Any] | None = None
    error: str | None = None
    trace_artifact_path: str | None = None
