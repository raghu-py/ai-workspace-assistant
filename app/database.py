from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.database_path)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        tags TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'todo',
        priority TEXT NOT NULL DEFAULT 'medium',
        due_date TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        original_name TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        content_type TEXT DEFAULT 'application/octet-stream',
        size_bytes INTEGER NOT NULL,
        extracted_text TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS assistant_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        tool_name TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
    with get_connection() as connection:
        connection.executescript(schema)


# Users

def create_user(full_name: str, email: str, password_hash: str) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO users (full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (full_name.strip(), email.strip().lower(), password_hash, utc_now()),
        )
        return int(cursor.lastrowid)


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


# Activity

def log_activity(user_id: int, action: str, details: str = "") -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, details, utc_now()),
        )


def list_recent_activity(user_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM activity_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return list(rows)


# Notes

def create_note(user_id: int, title: str, content: str, tags: str = "") -> int:
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO notes (user_id, title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title.strip(), content.strip(), tags.strip(), now, now),
        )
        return int(cursor.lastrowid)


def list_notes(user_id: int, query: str = "") -> list[sqlite3.Row]:
    sql = "SELECT * FROM notes WHERE user_id = ?"
    params: list[Any] = [user_id]
    if query.strip():
        like = f"%{query.strip()}%"
        sql += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY updated_at DESC"
    with get_connection() as connection:
        return list(connection.execute(sql, params).fetchall())


def get_note(note_id: int, user_id: int) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM notes WHERE id = ? AND user_id = ?",
            (note_id, user_id),
        ).fetchone()


def update_note(note_id: int, user_id: int, title: str, content: str, tags: str = "") -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE notes SET title = ?, content = ?, tags = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (title.strip(), content.strip(), tags.strip(), utc_now(), note_id, user_id),
        )
        return cursor.rowcount > 0


def delete_note(note_id: int, user_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?",
            (note_id, user_id),
        )
        return cursor.rowcount > 0


# Tasks

def create_task(
    user_id: int,
    title: str,
    description: str = "",
    status: str = "todo",
    priority: str = "medium",
    due_date: str | None = None,
) -> int:
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (user_id, title, description, status, priority, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, title.strip(), description.strip(), status, priority, due_date, now, now),
        )
        return int(cursor.lastrowid)


def list_tasks(user_id: int, status: str | None = None, query: str = "") -> list[sqlite3.Row]:
    sql = "SELECT * FROM tasks WHERE user_id = ?"
    params: list[Any] = [user_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if query.strip():
        like = f"%{query.strip()}%"
        sql += " AND (title LIKE ? OR description LIKE ? OR priority LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY CASE status WHEN 'todo' THEN 1 WHEN 'in_progress' THEN 2 ELSE 3 END, COALESCE(due_date, '9999-12-31'), id DESC"
    with get_connection() as connection:
        return list(connection.execute(sql, params).fetchall())


def get_task(task_id: int, user_id: int) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()


def update_task(
    task_id: int,
    user_id: int,
    title: str,
    description: str,
    status: str,
    priority: str,
    due_date: str | None,
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, status = ?, priority = ?, due_date = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (title.strip(), description.strip(), status, priority, due_date, utc_now(), task_id, user_id),
        )
        return cursor.rowcount > 0


def delete_task(task_id: int, user_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        return cursor.rowcount > 0


# Files

def create_file_record(
    user_id: int,
    original_name: str,
    stored_name: str,
    content_type: str,
    size_bytes: int,
    extracted_text: str,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO files (user_id, original_name, stored_name, content_type, size_bytes, extracted_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, original_name, stored_name, content_type, size_bytes, extracted_text, utc_now()),
        )
        return int(cursor.lastrowid)


def list_files(user_id: int, query: str = "") -> list[sqlite3.Row]:
    sql = "SELECT * FROM files WHERE user_id = ?"
    params: list[Any] = [user_id]
    if query.strip():
        like = f"%{query.strip()}%"
        sql += " AND (original_name LIKE ? OR extracted_text LIKE ?)"
        params.extend([like, like])
    sql += " ORDER BY id DESC"
    with get_connection() as connection:
        return list(connection.execute(sql, params).fetchall())


def get_file(file_id: int, user_id: int) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()


def delete_file_record(file_id: int, user_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        )
        return cursor.rowcount > 0


# Search

def search_workspace(user_id: int, query: str) -> dict[str, list[dict[str, Any]]]:
    query = query.strip()
    if not query:
        return {"notes": [], "tasks": [], "files": []}

    like = f"%{query}%"
    with get_connection() as connection:
        notes = connection.execute(
            "SELECT id, title, content, tags, updated_at FROM notes WHERE user_id = ? AND (title LIKE ? OR content LIKE ? OR tags LIKE ?) ORDER BY updated_at DESC LIMIT 10",
            (user_id, like, like, like),
        ).fetchall()
        tasks = connection.execute(
            "SELECT id, title, description, status, priority, due_date, updated_at FROM tasks WHERE user_id = ? AND (title LIKE ? OR description LIKE ? OR priority LIKE ?) ORDER BY updated_at DESC LIMIT 10",
            (user_id, like, like, like),
        ).fetchall()
        files = connection.execute(
            "SELECT id, original_name, content_type, size_bytes, extracted_text, created_at FROM files WHERE user_id = ? AND (original_name LIKE ? OR extracted_text LIKE ?) ORDER BY created_at DESC LIMIT 10",
            (user_id, like, like),
        ).fetchall()

    return {
        "notes": [dict(row) for row in notes],
        "tasks": [dict(row) for row in tasks],
        "files": [dict(row) for row in files],
    }


# Assistant messages

def save_assistant_message(user_id: int, role: str, content: str, tool_name: str | None = None) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO assistant_messages (user_id, role, content, tool_name, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, role, content, tool_name, utc_now()),
        )
        return int(cursor.lastrowid)


def list_assistant_messages(user_id: int, limit: int = 20) -> list[sqlite3.Row]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM assistant_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return list(reversed(rows))
