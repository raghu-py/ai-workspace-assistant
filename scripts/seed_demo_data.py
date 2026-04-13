from __future__ import annotations

from app import database
from app.config import ensure_directories
from app.database import init_db
from app.security import hash_password


def main() -> None:
    ensure_directories()
    init_db()

    existing = database.get_user_by_email("raghu@example.com")
    if existing:
        user_id = int(existing["id"])
    else:
        user_id = database.create_user("Raghu Soni", "raghu@example.com", hash_password("password123"))

    if not database.list_notes(user_id):
        database.create_note(user_id, "Project launch", "Ship the full AI workspace assistant repository.", "launch,repo")
        database.create_note(user_id, "MCP ideas", "Connect filesystem, GitHub, and web tools through MCP.", "mcp,ideas")

    if not database.list_tasks(user_id):
        database.create_task(user_id, "Finalize README", "Add full setup and deployment guide.", "todo", "high", "2026-04-20")
        database.create_task(user_id, "Test Docker build", "Verify container startup and database persistence.", "in_progress", "medium", None)

    database.log_activity(user_id, "seed.complete", "Demo data created")
    print("Seeded demo data for raghu@example.com / password123")


if __name__ == "__main__":
    main()
