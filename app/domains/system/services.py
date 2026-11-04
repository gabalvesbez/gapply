"""Verifica o banco e informa capacidades sem expor credenciais."""
from sqlalchemy import text
from app.core.config import settings, MAX_UPLOAD_BYTES
from app.core.database import Session


def health():
    with Session() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}


def capabilities():
    return {
        "deepseek_configured": bool(settings.deepseek_api_key),
        "jev_configured": bool(settings.jev_api_key),
        "mode": "personal_local",
        "upload_limit_bytes": MAX_UPLOAD_BYTES,
        "resume_formats": ["pdf", "docx"],
        "browser": "local_assisted",
        "automatic_submission_confirmation": False,
    }
