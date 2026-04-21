from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app import database
from app.config import settings
from app.dependencies import get_current_user
from app.schemas import AssistantPrompt, NoteCreate, SearchResponse, TaskCreate, TaskUpdate
from app.services.assistant_service import AssistantService
from app.services.file_storage import save_upload

router = APIRouter(prefix="/api", tags=["api"])
assistant_service = AssistantService()


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {"id": user["id"], "full_name": user["full_name"], "email": user["email"]}


@router.get("/search", response_model=SearchResponse)
def search(query: str, user=Depends(get_current_user)):
    return database.search_workspace(int(user["id"]), query)


@router.get("/notes")
def list_notes(query: str = "", user=Depends(get_current_user)):
    return [dict(row) for row in database.list_notes(int(user["id"]), query=query)]


@router.post("/notes", status_code=201)
def create_note(payload: NoteCreate, user=Depends(get_current_user)):
    note_id = database.create_note(int(user["id"]), payload.title, payload.content, payload.tags)
    database.log_activity(int(user["id"]), "note.create", f"note_id={note_id}")
    return {"id": note_id}


@router.put("/notes/{note_id}")
def update_note(note_id: int, payload: NoteCreate, user=Depends(get_current_user)):
    updated = database.update_note(note_id, int(user["id"]), payload.title, payload.content, payload.tags)
    if not updated:
        raise HTTPException(status_code=404, detail="Note not found")
    database.log_activity(int(user["id"]), "note.update", f"note_id={note_id}")
    return {"ok": True}


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, user=Depends(get_current_user)):
    deleted = database.delete_note(note_id, int(user["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    database.log_activity(int(user["id"]), "note.delete", f"note_id={note_id}")
    return {"ok": True}


@router.get("/tasks")
def list_tasks(query: str = "", status_filter: str | None = None, user=Depends(get_current_user)):
    return [dict(row) for row in database.list_tasks(int(user["id"]), status=status_filter, query=query)]


@router.post("/tasks", status_code=201)
def create_task(payload: TaskCreate, user=Depends(get_current_user)):
    task_id = database.create_task(
        int(user["id"]),
        payload.title,
        payload.description,
        payload.status,
        payload.priority,
        payload.due_date,
    )
    database.log_activity(int(user["id"]), "task.create", f"task_id={task_id}")
    return {"id": task_id}


@router.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, user=Depends(get_current_user)):
    updated = database.update_task(
        task_id,
        int(user["id"]),
        payload.title,
        payload.description,
        payload.status,
        payload.priority,
        payload.due_date,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    database.log_activity(int(user["id"]), "task.update", f"task_id={task_id}")
    return {"ok": True}


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, user=Depends(get_current_user)):
    deleted = database.delete_task(task_id, int(user["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    database.log_activity(int(user["id"]), "task.delete", f"task_id={task_id}")
    return {"ok": True}


@router.get("/files")
def list_files(query: str = "", user=Depends(get_current_user)):
    return [dict(row) for row in database.list_files(int(user["id"]), query=query)]


@router.post("/files", status_code=201)
def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
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
    return {"id": file_id}


@router.get("/files/{file_id}/download")
def download_file(file_id: int, user=Depends(get_current_user)):
    file_record = database.get_file(file_id, int(user["id"]))
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    path = settings.upload_dir / file_record["stored_name"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
    return FileResponse(path=path, filename=file_record["original_name"], media_type=file_record["content_type"])


@router.delete("/files/{file_id}")
def delete_file(file_id: int, user=Depends(get_current_user)):
    file_record = database.get_file(file_id, int(user["id"]))
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    path = settings.upload_dir / file_record["stored_name"]
    if Path(path).exists():
        Path(path).unlink(missing_ok=True)
    database.delete_file_record(file_id, int(user["id"]))
    database.log_activity(int(user["id"]), "file.delete", f"file_id={file_id}")
    return {"ok": True}


@router.get("/assistant/history")
def assistant_history(user=Depends(get_current_user)):
    return [dict(row) for row in database.list_assistant_messages(int(user["id"]), limit=30)]


@router.post("/assistant")
def assistant_prompt(payload: AssistantPrompt, user=Depends(get_current_user)):
    response = assistant_service.reply(int(user["id"]), payload.message)
    database.log_activity(int(user["id"]), "assistant.message", payload.message[:80])
    return response
