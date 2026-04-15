from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = Path(os.getenv("APP_DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Workspace Assistant")
    secret_key: str = os.getenv("APP_SECRET_KEY", "change-me-in-production")
    session_cookie_name: str = os.getenv("APP_SESSION_COOKIE", "workspace_session")
    database_path: Path = Path(os.getenv("APP_DATABASE_PATH", DATA_DIR / "workspace.db"))
    data_dir: Path = DATA_DIR
    upload_dir: Path = UPLOAD_DIR
    templates_dir: Path = APP_DIR / "templates"
    static_dir: Path = APP_DIR / "static"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    mcp_config_path: Path = Path(os.getenv("APP_MCP_CONFIG_PATH", DATA_DIR / "mcp_servers.json"))
    max_upload_size_mb: int = int(os.getenv("APP_MAX_UPLOAD_MB", "10"))

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()


def ensure_directories() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
