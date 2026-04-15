from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status

from app import database
from app.config import settings
from app.security import SessionData, read_session_cookie


def get_current_session(request: Request) -> SessionData | None:
    token = request.cookies.get(settings.session_cookie_name)
    return read_session_cookie(token)


def get_current_user_optional(request: Request):
    session = get_current_session(request)
    if not session:
        return None
    return database.get_user_by_id(session.user_id)


def get_current_user(request: Request):
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def template_context(request: Request, **extra: Any) -> dict[str, Any]:
    return {
        "request": request,
        "current_user": get_current_user_optional(request),
        **extra,
    }
