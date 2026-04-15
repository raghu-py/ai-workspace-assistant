from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import ensure_directories, settings
from app.database import init_db
from app.routers import api, auth, ui


def create_app() -> FastAPI:
    ensure_directories()
    init_db()

    app = FastAPI(
        title="AI Workspace Assistant",
        description="An AI workspace assistant built with FastAPI and Python, using MCP tools for automation, search, and productivity workflows.",
        version="1.0.0",
    )
    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
    app.state.templates = Jinja2Templates(directory=str(settings.templates_dir))

    app.include_router(auth.router)
    app.include_router(ui.router)
    app.include_router(api.router)

    @app.get("/health", tags=["system"])
    def healthcheck():
        return {"status": "ok"}

    return app


app = create_app()
