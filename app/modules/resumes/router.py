from pathlib import Path
from typing import Annotated
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from app.config import settings, MAX_UPLOAD_BYTES
from app.database import Resume, Profile, get_session, row_dict
from app.repository import require
from app.modules.resumes.service import extract_resume_text
from app.modules.resumes.schemas import ResumeTextResponse

router = APIRouter(tags=["Currículos"])

async def read_upload(file: UploadFile):
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        result = await run_in_threadpool(extract_resume_text, file.filename or "", content)
        return content, result
    finally:
        await file.close()

@router.post("/resumes/extract", response_model=ResumeTextResponse)
async def extract(file: Annotated[UploadFile, File()]):
    _, result = await read_upload(file)
    return result

@router.post("/profiles/{profile_id}/resumes", status_code=201)
async def upload(profile_id: str, file: Annotated[UploadFile, File()], db=Depends(get_session)):
    require(db, Profile, profile_id)
    content, result = await read_upload(file)
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
        path.unlink(missing_ok=True)
        raise
    return row_dict(record)

@router.get("/profiles/{profile_id}/resumes")
def resumes(profile_id: str, db=Depends(get_session)):
    require(db, Profile, profile_id)
    return [row_dict(r) for r in db.scalars(select(Resume).where(Resume.profile_id == profile_id).order_by(Resume.created_at.desc()))]

@router.get("/resumes/{id}/file")
def download(id: str, db=Depends(get_session)):
    record = require(db, Resume, id)
    path = Path(record.path)
    if not path.is_file():
        raise HTTPException(410, "Arquivo original não está mais disponível.")
    return FileResponse(path, filename=record.filename)
