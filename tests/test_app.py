from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def build_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("APP_DATABASE_PATH", str(tmp_path / "data" / "workspace.db"))
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    main = importlib.import_module("app.main")
    app = main.create_app()
    return TestClient(app)


def register_and_login(client: TestClient) -> None:
    response = client.post(
        "/register",
        data={
            "full_name": "Raghu Soni",
            "email": "raghu@example.com",
            "password": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"



def test_register_login_dashboard(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    register_and_login(client)

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Welcome, Raghu Soni" in response.text



def test_notes_tasks_and_search(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    register_and_login(client)

    note_response = client.post(
        "/api/notes",
        json={"title": "Launch plan", "content": "Ship the full workspace app this week", "tags": "release,launch"},
    )
    assert note_response.status_code == 201

    task_response = client.post(
        "/api/tasks",
        json={
            "title": "Prepare release checklist",
            "description": "Verify Docker, tests, and README",
            "status": "todo",
            "priority": "high",
            "due_date": "2026-04-20",
        },
    )
    assert task_response.status_code == 201

    search_response = client.get("/api/search", params={"query": "release"})
    assert search_response.status_code == 200
    payload = search_response.json()
    assert len(payload["notes"]) == 1
    assert len(payload["tasks"]) == 1



def test_file_upload_and_assistant_fallback(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    register_and_login(client)

    upload_response = client.post(
        "/api/files",
        files={"file": ("notes.txt", b"project alpha launch checklist", "text/plain")},
    )
    assert upload_response.status_code == 201

    assistant_response = client.post("/api/assistant", json={"message": "search launch"})
    assert assistant_response.status_code == 200
    body = assistant_response.json()
    assert "Found" in body["reply"]
    assert "search_workspace" in body["used_tools"]
