<div align="center">

# AI Workspace Assistant

### A clean, self-hosted productivity workspace powered by FastAPI, SQLite, OpenAI tool-calling, and optional MCP integrations.

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/SQLite-Local%20Storage-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Ready" />
</p>

<p>
  <a href="#features">Features</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#api-overview">API</a> ·
  <a href="#mcp-integration">MCP</a>
</p>

</div>

---

## Overview

**AI Workspace Assistant** is a full-stack workspace app built with **FastAPI** and **Python**. It helps users manage notes, tasks, uploaded files, workspace search, and AI-assisted productivity workflows from one lightweight web application.

The app works even without an AI provider. With an `OPENAI_API_KEY`, it unlocks natural-language assistant behavior, tool-calling, and automation over workspace data. It also supports optional **MCP servers**, allowing the assistant to call external tools through the Model Context Protocol.

---

## Features

### Workspace Dashboard

- Personal dashboard after login
- Recent notes, tasks, files, and activity logs
- Unified search across notes, tasks, and uploaded text files
- Clean responsive UI with Jinja templates and custom CSS

### Authentication

- User registration and login
- Secure password hashing using `hashlib.scrypt`
- Signed session cookies with `itsdangerous`
- Per-user data isolation

### Notes

- Create, edit, delete, and search notes
- Add tags for better organization
- Track creation and update timestamps

### Tasks

- Create, edit, delete, filter, and search tasks
- Supports status:
  - `todo`
  - `in_progress`
  - `done`
- Supports priority:
  - `low`
  - `medium`
  - `high`
- Optional due dates

### File Uploads

- Upload and manage files
- Download or delete uploaded files
- Extract searchable text from supported text-based files
- Upload size limit controlled by environment variable

Supported searchable text formats include:

- `.txt`
- `.md`
- `.csv`
- `.json`
- `.xml`
- `.html`
- `.py`
- `.js`
- `.ts`

### AI Assistant

The assistant can work in two modes:

#### Without OpenAI

The app still supports useful fallback commands such as:

```text
create task: Prepare roadmap
create note: Launch Plan | Finalize launch checklist
search roadmap
```

#### With OpenAI

When `OPENAI_API_KEY` is configured, the assistant can use tool-calling to:

- Search the workspace
- Create tasks
- Create notes
- List tasks
- Read recent activity
- Call configured MCP tools

### MCP Integration

The app can load MCP server definitions from a JSON config file and expose MCP tools to the AI assistant.

Example MCP server config is included in:

```text
data.mcp_servers.example.json
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Templates | Jinja2 |
| Database | SQLite |
| Auth | Signed cookies + scrypt password hashing |
| AI | OpenAI Chat Completions API |
| Tooling | Internal tools + optional MCP tools |
| HTTP Client | httpx |
| Testing | pytest |
| Deployment | Docker + Docker Compose |

---

## Project Structure

```text
ai-workspace-assistant/
├── app/
│   ├── routers/
│   │   ├── api.py              # JSON API routes
│   │   ├── auth.py             # Login, register, logout
│   │   └── ui.py               # Web UI routes
│   ├── services/
│   │   ├── assistant_service.py # AI assistant and fallback logic
│   │   ├── file_storage.py      # Upload handling and text extraction
│   │   ├── mcp_client.py        # Stdio MCP client
│   │   └── tool_executor.py     # Internal and MCP tool execution
│   ├── static/
│   │   └── style.css            # App styling
│   ├── templates/               # Jinja2 pages
│   ├── config.py                # App settings
│   ├── database.py              # SQLite schema and queries
│   ├── dependencies.py          # Auth dependencies and template context
│   ├── main.py                  # FastAPI app factory
│   ├── schemas.py               # Pydantic models
│   └── security.py              # Password hashing and session cookies
├── data/
│   └── .gitkeep
├── scripts/
│   └── seed_demo_data.py
├── tests/
│   └── test_app.py
├── .env.example
├── data.mcp_servers.example.json
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/raghu-py/ai-workspace-assistant.git
cd ai-workspace-assistant
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

### 4. Create your environment file

```bash
cp .env.example .env
```

Update `.env` if needed:

```env
APP_NAME=AI Workspace Assistant
APP_SECRET_KEY=replace-this-with-a-long-random-secret
APP_DATA_DIR=./data
APP_DATABASE_PATH=./data/workspace.db
APP_SESSION_COOKIE=workspace_session
APP_MAX_UPLOAD_MB=10

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini

APP_MCP_CONFIG_PATH=./data/mcp_servers.json
```

### 5. Run the app

```bash
uvicorn app.main:app --reload
```

Open the app in your browser:

```text
http://localhost:8000
```

---

## Demo Data

You can seed the database with demo content:

```bash
python scripts/seed_demo_data.py
```

Demo account:

```text
Email: raghu@example.com
Password: password123
```

---

## Run with Docker

### 1. Create `.env`

```bash
cp .env.example .env
```

### 2. Start the app

```bash
docker compose up --build
```

The app will be available at:

```text
http://localhost:8000
```

The `data/` directory is mounted as a volume, so your SQLite database and uploads persist locally.

---

## Configuration

| Variable | Default | Description |
|---|---:|---|
| `APP_NAME` | `AI Workspace Assistant` | Display name for the app |
| `APP_SECRET_KEY` | `change-me-in-production` | Secret used for signing session cookies |
| `APP_DATA_DIR` | `./data` | Directory for database, uploads, and config |
| `APP_DATABASE_PATH` | `./data/workspace.db` | SQLite database path |
| `APP_SESSION_COOKIE` | `workspace_session` | Session cookie name |
| `APP_MAX_UPLOAD_MB` | `10` | Maximum upload size in MB |
| `OPENAI_API_KEY` | empty | Enables AI assistant tool-calling |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI model used by the assistant |
| `APP_MCP_CONFIG_PATH` | `./data/mcp_servers.json` | MCP server configuration path |

> Important: change `APP_SECRET_KEY` before deploying this app.

---

## MCP Integration

To enable MCP tools, create a config file at:

```text
data/mcp_servers.json
```

You can start from the included example:

```bash
cp data.mcp_servers.example.json data/mcp_servers.json
```

Example:

```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "./data"],
      "cwd": ".",
      "env": {}
    }
  ]
}
```

When OpenAI is enabled, tools from configured MCP servers are exposed to the assistant with names like:

```text
mcp__filesystem__tool_name
```

---

## API Overview

All `/api/*` routes require authentication through the session cookie.

### User

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/me` | Get current user profile |

### Search

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/search?query=release` | Search notes, tasks, and uploaded files |

### Notes

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/notes` | List notes |
| `POST` | `/api/notes` | Create note |
| `PUT` | `/api/notes/{note_id}` | Update note |
| `DELETE` | `/api/notes/{note_id}` | Delete note |

Example note payload:

```json
{
  "title": "Launch plan",
  "content": "Ship the full workspace app this week",
  "tags": "release,launch"
}
```

### Tasks

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/tasks` | List tasks |
| `POST` | `/api/tasks` | Create task |
| `PUT` | `/api/tasks/{task_id}` | Update task |
| `DELETE` | `/api/tasks/{task_id}` | Delete task |

Example task payload:

```json
{
  "title": "Prepare release checklist",
  "description": "Verify Docker, tests, and README",
  "status": "todo",
  "priority": "high",
  "due_date": "2026-04-20"
}
```

### Files

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/files` | List uploaded files |
| `POST` | `/api/files` | Upload a file |
| `GET` | `/api/files/{file_id}/download` | Download a file |
| `DELETE` | `/api/files/{file_id}` | Delete a file |

### Assistant

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/assistant/history` | Get recent assistant messages |
| `POST` | `/api/assistant` | Send a message to the assistant |

Example assistant payload:

```json
{
  "message": "search launch"
}
```

---

## Web Routes

| Route | Description |
|---|---|
| `/` | Landing page |
| `/register` | Create an account |
| `/login` | Sign in |
| `/dashboard` | Workspace dashboard |
| `/notes` | Manage notes |
| `/tasks` | Manage tasks |
| `/files` | Manage uploads |
| `/assistant` | Chat with the assistant |
| `/health` | Health check endpoint |

---

## Running Tests

```bash
python -m pytest
```

The test suite covers:

- Registration and dashboard access
- Notes and tasks API flows
- Workspace search
- File upload
- Assistant fallback behavior

---

## Security Notes

This project includes sensible defaults for local development, but production deployments should harden the following:

- Set a strong `APP_SECRET_KEY`
- Use HTTPS
- Set secure cookies behind TLS
- Restrict upload types and scan files when needed
- Keep dependencies updated
- Protect `.env` and local database files
- Use a production-grade reverse proxy if deploying publicly

---

## Development Notes

The app uses an application factory:

```python
from app.main import create_app

app = create_app()
```

On startup, it:

1. Ensures required data directories exist
2. Initializes the SQLite database schema
3. Mounts static assets
4. Registers auth, UI, and API routers

The assistant service stores user and assistant messages in the database, then either:

- Uses OpenAI tool-calling when `OPENAI_API_KEY` is configured
- Falls back to simple local command parsing when OpenAI is not configured

---

## License

This project is licensed under the MIT License.

---

<div align="center">

Built with FastAPI, Python, SQLite, and MCP-ready assistant tooling.

</div>
