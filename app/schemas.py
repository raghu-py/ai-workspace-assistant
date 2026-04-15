from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["todo", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]


class RegisterForm(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=256)


class LoginForm(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=256)


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    tags: str = Field(default="", max_length=200)


class NoteUpdate(NoteCreate):
    pass


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    due_date: str | None = None


class TaskUpdate(TaskCreate):
    pass


class AssistantPrompt(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AssistantReply(BaseModel):
    reply: str
    used_tools: list[str] = []


class SearchResponse(BaseModel):
    notes: list[dict]
    tasks: list[dict]
    files: list[dict]
