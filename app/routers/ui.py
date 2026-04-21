from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from app import database
from app.config import settings
from app.dependencies import get_current_user_optional, template_context
from app.schemas import NoteCreate, TaskCreate
from app.services.assistant_service import AssistantService
from app.services.file_storage import save_upload

router = APIRouter(tags=["ui"])
assistant_service = AssistantService()


def _templates(request: Request):
    return request.app.state.templates


def _redirect(url: str, status_code: int = 303) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=status_code)


def _require_user(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return None, _redirect("/login", 302)
    return user, None


@router.get("/")
def home(request: Request):
    current_user = get_current_user_optional(request)
    if current_user:
        return _redirect("/dashboard")
    return _templates(request).TemplateResponse(request, "index.html", template_context(request, page_title="Home"))


@router.get("/dashboard")
def dashboard(request: Request, q: str = ""):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    results = database.search_workspace(int(user["id"]), q) if q.strip() else {"notes": [], "tasks": [], "files": []}
    notes = database.list_notes(int(user["id"]))[:5]
    tasks = database.list_tasks(int(user["id"]))[:8]
    files = database.list_files(int(user["id"]))[:5]
    activity = database.list_recent_activity(int(user["id"]), limit=8)
    return _templates(request).TemplateResponse(
        request,
        "dashboard.html",
        template_context(
            request,
            page_title="Dashboard",
            q=q,
            search_results=results,
            notes=notes,
            tasks=tasks,
            files=files,
            activity=activity,
        ),
    )


@router.get("/notes")
def notes_page(request: Request, q: str = ""):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    notes = database.list_notes(int(user["id"]), query=q)
    return _templates(request).TemplateResponse(
        request,
        "notes.html",
        template_context(request, page_title="Notes", notes=notes, q=q, editing_note=None),
    )


@router.post("/notes")
def create_note(request: Request, title: str = Form(...), content: str = Form(...), tags: str = Form("")):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        payload = NoteCreate(title=title, content=content, tags=tags)
    except Exception as exc:
        notes = database.list_notes(int(user["id"]))
        return _templates(request).TemplateResponse(
            request,
            "notes.html",
            template_context(request, page_title="Notes", notes=notes, editing_note=None, error=str(exc), q=""),
            status_code=400,
        )
    note_id = database.create_note(int(user["id"]), payload.title, payload.content, payload.tags)
    database.log_activity(int(user["id"]), "note.create", f"note_id={note_id}")
    return _redirect("/notes")


@router.get("/notes/{note_id}/edit")
def edit_note_page(request: Request, note_id: int, q: str = ""):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    note = database.get_note(note_id, int(user["id"]))
    if not note:
        return _redirect("/notes")
    notes = database.list_notes(int(user["id"]), query=q)
    return _templates(request).TemplateResponse(
        request,
        "notes.html",
        template_context(request, page_title="Notes", notes=notes, q=q, editing_note=note),
    )


@router.post("/notes/{note_id}/edit")
def update_note(request: Request, note_id: int, title: str = Form(...), content: str = Form(...), tags: str = Form("")):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    database.update_note(note_id, int(user["id"]), title, content, tags)
    database.log_activity(int(user["id"]), "note.update", f"note_id={note_id}")
    return _redirect("/notes")


@router.post("/notes/{note_id}/delete")
def delete_note(request: Request, note_id: int):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    database.delete_note(note_id, int(user["id"]))
    database.log_activity(int(user["id"]), "note.delete", f"note_id={note_id}")
    return _redirect("/notes")


@router.get("/tasks")
def tasks_page(request: Request, q: str = "", status: str = ""):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    tasks = database.list_tasks(int(user["id"]), status=status or None, query=q)
    return _templates(request).TemplateResponse(
        request,
        "tasks.html",
        template_context(request, page_title="Tasks", tasks=tasks, q=q, status=status, editing_task=None),
    )


@router.post("/tasks")
def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    priority: str = Form("medium"),
    due_date: str = Form(""),
):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        payload = TaskCreate(
            title=title,
            description=description,
            status=status,
            priority=priority,
            due_date=due_date or None,
        )
    except Exception as exc:
        tasks = database.list_tasks(int(user["id"]))
        return _templates(request).TemplateResponse(
            request,
            "tasks.html",
            template_context(request, page_title="Tasks", tasks=tasks, editing_task=None, error=str(exc), q="", status=""),
            status_code=400,
        )
    task_id = database.create_task(
        int(user["id"]),
        payload.title,
        payload.description,
        payload.status,
        payload.priority,
        payload.due_date,
    )
    database.log_activity(int(user["id"]), "task.create", f"task_id={task_id}")
    return _redirect("/tasks")


@router.get("/tasks/{task_id}/edit")
def edit_task_page(request: Request, task_id: int, q: str = "", status: str = ""):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    task = database.get_task(task_id, int(user["id"]))
    if not task:
        return _redirect("/tasks")
    tasks = database.list_tasks(int(user["id"]), status=status or None, query=q)
    return _templates(request).TemplateResponse(
        request,
        "tasks.html",
        template_context(request, page_title="Tasks", tasks=tasks, q=q, status=status, editing_task=task),
    )


@router.post("/tasks/{task_id}/edit")
def update_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    priority: str = Form("medium"),
    due_date: str = Form(""),
):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    database.update_task(task_id, int(user["id"]), title, description, status, priority, due_date or None)
    database.log_activity(int(user["id"]), "task.update", f"task_id={task_id}")
    return _redirect("/tasks")


@router.post("/tasks/{task_id}/delete")
def delete_task(request: Request, task_id: int):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    database.delete_task(task_id, int(user["id"]))
    database.log_activity(int(user["id"]), "task.delete", f"task_id={task_id}")
    return _redirect("/tasks")


@router.get("/files")
def files_page(request: Request, q: str = ""):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    files = database.list_files(int(user["id"]), query=q)
    return _templates(request).TemplateResponse(
        request,
        "files.html",
        template_context(request, page_title="Files", files=files, q=q),
    )


@router.post("/files")
def upload_file(request: Request, file: UploadFile = File(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    stored_name, size, extracted_text = save_upload(file)
    file_id = database.create_file_record(
        int(user["id"]),
        file.filename or stored_name,
        stored_name,
        file.content_type or "application/octet-stream",
        size,
        extracted_text,
    )
    database.log_activity(int(user["id"]), "file.upload", f"file_id={file_id}")
    return _redirect("/files")


@router.get("/files/{file_id}/download")
def download_file(request: Request, file_id: int):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    file_record = database.get_file(file_id, int(user["id"]))
    if not file_record:
        return _redirect("/files")
    path = settings.upload_dir / file_record["stored_name"]
    if not path.exists():
        return _redirect("/files")
    return FileResponse(path=path, filename=file_record["original_name"], media_type=file_record["content_type"])


@router.post("/files/{file_id}/delete")
def delete_file(request: Request, file_id: int):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    file_record = database.get_file(file_id, int(user["id"]))
    if file_record:
        path = settings.upload_dir / file_record["stored_name"]
        if Path(path).exists():
            Path(path).unlink(missing_ok=True)
        database.delete_file_record(file_id, int(user["id"]))
        database.log_activity(int(user["id"]), "file.delete", f"file_id={file_id}")
    return _redirect("/files")


@router.get("/assistant")
def assistant_page(request: Request):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    history = database.list_assistant_messages(int(user["id"]), limit=30)
    return _templates(request).TemplateResponse(
        request,
        "assistant.html",
        template_context(request, page_title="Assistant", history=history, assistant_enabled=bool(settings.openai_api_key)),
    )


@router.post("/assistant")
def assistant_action(request: Request, message: str = Form(...)):
    user, redirect = _require_user(request)
    if redirect:
        return redirect
    assistant_service.reply(int(user["id"]), message)
    database.log_activity(int(user["id"]), "assistant.message", message[:80])
    return _redirect("/assistant")
