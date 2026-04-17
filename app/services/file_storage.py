from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import settings

TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/xml",
    "text/html",
}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".py", ".js", ".ts"}


def save_upload(upload: UploadFile) -> tuple[str, int, str]:
    data = upload.file.read()
    size = len(data)
    if size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {settings.max_upload_size_mb} MB.",
        )

    suffix = Path(upload.filename or "").suffix
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = settings.upload_dir / stored_name
    target.write_bytes(data)
    extracted_text = extract_text(upload.content_type, upload.filename or "", data)
    return stored_name, size, extracted_text


def extract_text(content_type: str | None, filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if (content_type or "") in TEXT_TYPES or suffix in TEXT_EXTENSIONS:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
    return ""
