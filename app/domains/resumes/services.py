"""Extração local, armazenamento do original e consultas de currículos."""
from pathlib import Path, PurePosixPath
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from app.core.config import settings, MAX_UPLOAD_BYTES, ALLOWED_EXTENSIONS
from app.core.database import row_dict
from app.core.repository import require
from app.domains.profiles.models import Profile
from app.domains.resumes.models import Resume
from app.domains.resumes.errors import FileTooLargeError, UnsupportedFormatError, InvalidDocumentError, NoTextFoundError
from app.domains.resumes.extractors.pdf import extract_pdf_text
from app.domains.resumes.extractors.docx import extract_docx_text
from app.domains.resumes.schemas import ResumeTextResponse

def extract_resume_text(filename: str, content: bytes) -> ResumeTextResponse:
    name = PurePosixPath(filename.replace("\\", "/")).name
    extension = PurePosixPath(name).suffix.lower()
    if not content:
        raise InvalidDocumentError("O arquivo está vazio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise FileTooLargeError("O arquivo deve ter no máximo 10 MiB.")
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError("Envie um arquivo .pdf ou .docx.")
    text, warnings = (extract_pdf_text if extension == ".pdf" else extract_docx_text)(content)
    if not text.strip():
        raise NoTextFoundError("Não encontramos texto. O documento pode precisar de OCR.")
    return ResumeTextResponse(filename=name, format=extension[1:], text=text.strip(), warnings=warnings)


async def upload(profile_id: str, filename: str, content: bytes, db):
    require(db, Profile, profile_id)
    result = await run_in_threadpool(extract_resume_text, filename, content)
    folder = settings.data_dir / "resumes"
    folder.mkdir(parents=True, exist_ok=True)
    id = str(uuid4())
    path = (folder / f"{id}.{result.format}").resolve()
    await run_in_threadpool(path.write_bytes, content)
    try:
        record = Resume(id=id, profile_id=profile_id, filename=result.filename[:255], path=str(path),
                        text=result.text, warnings=result.warnings)
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return row_dict(record)


def resumes(profile_id: str, db):
    require(db, Profile, profile_id)
    return [row_dict(r) for r in db.scalars(
        select(Resume).where(Resume.profile_id == profile_id).order_by(Resume.created_at.desc()))]


def download(id: str, db):
    record = require(db, Resume, id)
    path = Path(record.path)
    if not path.is_file():
        raise HTTPException(410, "Arquivo original não está mais disponível.")
    return path, record.filename
