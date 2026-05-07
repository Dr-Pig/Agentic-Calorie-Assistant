from __future__ import annotations

from hmac import compare_digest
import os

from fastapi import Header, HTTPException, Request

LOCAL_DEBUG_API_TOKEN_ENV = "LOCAL_DEBUG_API_TOKEN"
LOCAL_DEBUG_API_TOKEN_HEADER = "X-Local-Debug-Token"

_PLACEHOLDER_TOKENS = {
    "change-me",
    "changeme",
    "placeholder",
    "replace-me",
}
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost", "testclient"}


def _configured_local_debug_token() -> str:
    token = os.getenv(LOCAL_DEBUG_API_TOKEN_ENV, "").strip()
    if token.lower() in _PLACEHOLDER_TOKENS:
        return ""
    return token


def _request_is_local(request: Request) -> bool:
    client = getattr(request, "client", None)
    host = getattr(client, "host", "") if client is not None else ""
    return host.strip().lower() in _LOOPBACK_HOSTS


def require_local_debug_access(
    request: Request,
    x_local_debug_token: str | None = Header(default=None, alias=LOCAL_DEBUG_API_TOKEN_HEADER),
) -> None:
    expected_token = _configured_local_debug_token()
    if not expected_token:
        raise HTTPException(status_code=404, detail="Not found")
    if not _request_is_local(request):
        raise HTTPException(status_code=404, detail="Not found")

    supplied_token = (x_local_debug_token or "").strip()
    if not supplied_token or not compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=403, detail="Forbidden")
