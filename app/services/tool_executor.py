from __future__ import annotations

import json
from typing import Any

from app import database
from app.services.mcp_client import MCPProtocolError, load_server_configs, with_client


def internal_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "search_workspace",
                "description": "Search notes, tasks, and uploaded files in the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query to run against the workspace."}
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_task",
                "description": "Create a task for the current user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                        "due_date": {"type": ["string", "null"], "description": "Due date in YYYY-MM-DD format"},
                    },
                    "required": ["title"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_note",
                "description": "Create a note for the current user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "tags": {"type": "string"},
                    },
                    "required": ["title", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_tasks",
                "description": "List tasks for the current user, optionally filtered by status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": ["string", "null"], "enum": ["todo", "in_progress", "done", None]}
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "recent_activity",
                "description": "List the user's most recent activity logs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20}
                    },
                },
            },
        },
    ]


def mcp_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for server in load_server_configs():
        try:
            client = with_client(server)
            try:
                for tool in client.list_tools():
                    descriptor = {
                        "type": "function",
                        "function": {
                            "name": f"mcp__{server.name}__{tool['name']}",
                            "description": tool.get("description", f"Tool from MCP server {server.name}"),
                            "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                        },
                    }
                    tools.append(descriptor)
            finally:
                client.close()
        except Exception:
            continue
    return tools


def all_tools() -> list[dict[str, Any]]:
    return internal_tools() + mcp_tools()


def execute_tool(user_id: int, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "search_workspace":
        results = database.search_workspace(user_id, str(arguments.get("query", "")))
        database.log_activity(user_id, "assistant.search", json.dumps({"query": arguments.get("query", "")}))
        return {"ok": True, "results": results}

    if tool_name == "create_task":
        task_id = database.create_task(
            user_id=user_id,
            title=str(arguments.get("title", "")),
            description=str(arguments.get("description", "")),
            priority=str(arguments.get("priority", "medium")),
            due_date=arguments.get("due_date") or None,
        )
        database.log_activity(user_id, "assistant.create_task", json.dumps({"task_id": task_id}))
        return {"ok": True, "task_id": task_id}

    if tool_name == "create_note":
        note_id = database.create_note(
            user_id=user_id,
            title=str(arguments.get("title", "")),
            content=str(arguments.get("content", "")),
            tags=str(arguments.get("tags", "")),
        )
        database.log_activity(user_id, "assistant.create_note", json.dumps({"note_id": note_id}))
        return {"ok": True, "note_id": note_id}

    if tool_name == "list_tasks":
        tasks = [dict(row) for row in database.list_tasks(user_id, status=arguments.get("status"))]
        return {"ok": True, "tasks": tasks}

    if tool_name == "recent_activity":
        limit = int(arguments.get("limit", 10))
        activity = [dict(row) for row in database.list_recent_activity(user_id, limit=limit)]
        return {"ok": True, "activity": activity}

    if tool_name.startswith("mcp__"):
        _, server_name, raw_tool_name = tool_name.split("__", 2)
        for server in load_server_configs():
            if server.name == server_name:
                client = with_client(server)
                try:
                    result = client.call_tool(raw_tool_name, arguments)
                    database.log_activity(user_id, "assistant.mcp_call", json.dumps({"server": server_name, "tool": raw_tool_name}))
                    return {"ok": True, "result": result}
                except MCPProtocolError as exc:
                    return {"ok": False, "error": str(exc)}
                finally:
                    client.close()
        return {"ok": False, "error": f"Unknown MCP server: {server_name}"}

    return {"ok": False, "error": f"Unknown tool: {tool_name}"}
