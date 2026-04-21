from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app import database
from app.config import settings
from app.dependencies import template_context
from app.schemas import LoginForm, RegisterForm
from app.security import create_session_cookie, hash_password, verify_password

router = APIRouter(tags=["auth"])


def _templates(request: Request):
    return request.app.state.templates


def _redirect(url: str, status_code: int = 303) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=status_code)


@router.get("/login")
def login_page(request: Request):
    user = template_context(request)["current_user"]
    if user:
        return _redirect("/dashboard")
    return _templates(request).TemplateResponse(request, "login.html", template_context(request, page_title="Login"))


@router.post("/login")
def login_action(request: Request, email: str = Form(...), password: str = Form(...)):
    user = database.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return _templates(request).TemplateResponse(
            request,
            "login.html",
            template_context(request, page_title="Login", error="Invalid email or password."),
            status_code=400,
        )

    response = _redirect("/dashboard")
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_cookie(int(user["id"]), str(user["email"])),
        httponly=True,
        samesite="lax",
        secure=False,
    )
    database.log_activity(int(user["id"]), "auth.login", user["email"])
    return response


@router.get("/register")
def register_page(request: Request):
    user = template_context(request)["current_user"]
    if user:
        return _redirect("/dashboard")
    return _templates(request).TemplateResponse(request, "register.html", template_context(request, page_title="Register"))


@router.post("/register")
def register_action(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        payload = RegisterForm(full_name=full_name, email=email, password=password)
    except Exception as exc:
        return _templates(request).TemplateResponse(
            request,
            "register.html",
            template_context(request, page_title="Register", error=str(exc)),
            status_code=400,
        )

    existing = database.get_user_by_email(payload.email)
    if existing:
        return _templates(request).TemplateResponse(
            request,
            "register.html",
            template_context(request, page_title="Register", error="An account with that email already exists."),
            status_code=400,
        )

    user_id = database.create_user(payload.full_name, payload.email, hash_password(payload.password))
    database.log_activity(user_id, "auth.register", payload.email)

    response = _redirect("/dashboard")
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_cookie(user_id, payload.email),
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


@router.post("/logout")
def logout_action(request: Request):
    user = template_context(request)["current_user"]
    response = _redirect("/")
    response.delete_cookie(settings.session_cookie_name)
    if user:
        database.log_activity(int(user["id"]), "auth.logout", user["email"])
    return response
