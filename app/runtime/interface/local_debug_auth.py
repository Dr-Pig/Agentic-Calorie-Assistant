from __future__ import annotations

from hmac import compare_digest
import os

from fastapi import Cookie, Header, HTTPException, Request, Response

LOCAL_DEBUG_API_TOKEN_ENV = "LOCAL_DEBUG_API_TOKEN"
LOCAL_DEBUG_API_TOKEN_HEADER = "X-Local-Debug-Token"
LOCAL_DEBUG_SESSION_COOKIE = "local_debug_session"
LOCAL_DEBUG_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60

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
    local_debug_session: str | None = Cookie(default=None, alias=LOCAL_DEBUG_SESSION_COOKIE),
) -> None:
    expected_token = _configured_local_debug_token()
    if not expected_token:
        raise HTTPException(status_code=404, detail="Not found")
    if not _request_is_local(request):
        raise HTTPException(status_code=404, detail="Not found")

    supplied_token = (x_local_debug_token or "").strip()
    supplied_session = (local_debug_session or "").strip()
    if compare_digest(supplied_token, expected_token):
        return
    if compare_digest(supplied_session, expected_token):
        return
    if not supplied_token and not supplied_session:
        raise HTTPException(status_code=403, detail="Forbidden")
    raise HTTPException(status_code=403, detail="Forbidden")


def configured_local_debug_token_for_request(request: Request) -> str | None:
    expected_token = _configured_local_debug_token()
    if not expected_token or not _request_is_local(request):
        return None
    return expected_token


def set_local_debug_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=LOCAL_DEBUG_SESSION_COOKIE,
        value=token,
        max_age=LOCAL_DEBUG_SESSION_MAX_AGE_SECONDS,
        path="/",
        httponly=True,
        samesite="strict",
    )


def validate_local_debug_token(request: Request, supplied_token: str) -> str:
    expected_token = _configured_local_debug_token()
    if not expected_token:
        raise HTTPException(status_code=404, detail="Not found")
    if not _request_is_local(request):
        raise HTTPException(status_code=404, detail="Not found")
    token = supplied_token.strip()
    if not token or not compare_digest(token, expected_token):
        raise HTTPException(status_code=403, detail="Forbidden")
    return expected_token
