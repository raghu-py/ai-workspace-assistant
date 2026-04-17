from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app import database
from app.config import settings
from app.services.tool_executor import all_tools, execute_tool

SYSTEM_PROMPT = """
You are an AI workspace assistant.
Help users manage notes, tasks, uploaded files, and external MCP tools.
Be concise, practical, and action-oriented.
When a task or note should be created, call a tool instead of pretending it was saved.
When searching the workspace would improve the answer, call search_workspace.
""".strip()


class AssistantService:
    def __init__(self) -> None:
        self.model = settings.openai_model
        self.api_key = settings.openai_api_key

    def reply(self, user_id: int, message: str) -> dict[str, Any]:
        database.save_assistant_message(user_id, "user", message)
        if self.api_key:
            reply = self._reply_with_openai(user_id, message)
        else:
            reply = self._fallback_reply(user_id, message)
        database.save_assistant_message(user_id, "assistant", reply["reply"])
        return reply

    def _history_messages(self, user_id: int) -> list[dict[str, Any]]:
        history = database.list_assistant_messages(user_id, limit=12)
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in history[-10:]:
            messages.append({"role": item["role"], "content": item["content"]})
        return messages

    def _reply_with_openai(self, user_id: int, latest_message: str) -> dict[str, Any]:
        messages = self._history_messages(user_id)
        tools = all_tools()
        used_tools: list[str] = []

        with httpx.Client(timeout=30.0) as client:
            for _ in range(5):
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "tools": tools,
                        "tool_choice": "auto",
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                message = payload["choices"][0]["message"]

                if message.get("tool_calls"):
                    messages.append(message)
                    for tool_call in message["tool_calls"]:
                        tool_name = tool_call["function"]["name"]
                        arguments = json.loads(tool_call["function"].get("arguments") or "{}")
                        result = execute_tool(user_id, tool_name, arguments)
                        used_tools.append(tool_name)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": json.dumps(result),
                            }
                        )
                    continue

                content = message.get("content")
                if isinstance(content, str):
                    return {"reply": content, "used_tools": used_tools}
                if isinstance(content, list):
                    text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
                    return {"reply": "\n".join(part for part in text_parts if part), "used_tools": used_tools}

        return {
            "reply": "I could not complete the request cleanly. Please try again or use the dashboard tools directly.",
            "used_tools": used_tools,
        }

    def _fallback_reply(self, user_id: int, latest_message: str) -> dict[str, Any]:
        used_tools: list[str] = []
        lowered = latest_message.strip().lower()

        task_match = re.search(r"create task[:\- ]+(?P<title>.+)", lowered, re.IGNORECASE)
        if task_match:
            title = latest_message[task_match.start("title"):].strip()
            result = execute_tool(user_id, "create_task", {"title": title})
            used_tools.append("create_task")
            return {"reply": f"Task created successfully with ID {result.get('task_id')}.", "used_tools": used_tools}

        note_match = re.search(r"create note[:\- ]+(?P<title>.+?)\s*\|\s*(?P<content>.+)", latest_message, re.IGNORECASE)
        if note_match:
            result = execute_tool(
                user_id,
                "create_note",
                {"title": note_match.group("title").strip(), "content": note_match.group("content").strip()},
            )
            used_tools.append("create_note")
            return {"reply": f"Note created successfully with ID {result.get('note_id')}.", "used_tools": used_tools}

        search_match = re.search(r"(?:search|find)\s+(?P<query>.+)", latest_message, re.IGNORECASE)
        if search_match:
            query = search_match.group("query").strip()
            results = execute_tool(user_id, "search_workspace", {"query": query})
            used_tools.append("search_workspace")
            counts = results["results"]
            return {
                "reply": (
                    f"Search complete for '{query}'. "
                    f"Found {len(counts['notes'])} notes, {len(counts['tasks'])} tasks, and {len(counts['files'])} files. "
                    "Add OPENAI_API_KEY to enable natural-language planning and tool calling."
                ),
                "used_tools": used_tools,
            }

        return {
            "reply": (
                "The workspace is fully usable without an AI provider for notes, tasks, file uploads, and keyword search. "
                "To enable natural-language automation, set OPENAI_API_KEY in your environment. "
                "You can also type commands like 'create task: Prepare roadmap' or 'search roadmap'."
            ),
            "used_tools": used_tools,
        }
