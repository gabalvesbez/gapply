"""Upload e download HTTP; validação e persistência ficam nos serviços."""
from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from app.core.config import MAX_UPLOAD_BYTES
from app.core.database import get_session
from app.domains.resumes import services
from app.domains.resumes.schemas import ResumeTextResponse

router = APIRouter(tags=["Currículos"])


async def read_upload(file: UploadFile):
    # UploadFile pertence ao transporte HTTP; os serviços recebem bytes comuns.
    try:
        return file.filename or "", await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()


@router.post("/resumes/extract", response_model=ResumeTextResponse)
async def extract(file: Annotated[UploadFile, File()]):
    filename, content = await read_upload(file)
    return await run_in_threadpool(services.extract_resume_text, filename, content)


@router.post("/profiles/{profile_id}/resumes", status_code=201)
async def upload(profile_id: str, file: Annotated[UploadFile, File()], db=Depends(get_session)):
    filename, content = await read_upload(file)
    return await services.upload(profile_id, filename, content, db)


@router.get("/profiles/{profile_id}/resumes")
def resumes(profile_id: str, db=Depends(get_session)):
    return services.resumes(profile_id, db)


@router.get("/resumes/{id}/file")
def download(id: str, db=Depends(get_session)):
    path, filename = services.download(id, db)
    return FileResponse(path, filename=filename)
