"""HTTP das candidaturas; o serviço controla as transições de estado."""
from fastapi import APIRouter, Depends, Request
from app.core.database import get_session
from app.domains.applications.schemas import ApplicationInput, FillInput, SubmitInput, ApplicationStatus
from app.domains.applications import services

router = APIRouter(tags=["Candidaturas e navegador"])


@router.post('/applications', status_code=201)
def create(payload: ApplicationInput, db=Depends(get_session)):
    return services.create(payload, db)


@router.get('/applications')
def applications(profile_id: str | None = None, db=Depends(get_session)):
    return services.applications(profile_id, db)


@router.get('/applications/{id}')
def application(id: str, db=Depends(get_session)):
    return services.application(id, db)


@router.post('/applications/{id}/open')
async def open_application(id: str, request: Request, db=Depends(get_session)):
    return await services.open_application(id, request.app.state.browser, db)


@router.get('/applications/{id}/form')
async def inspect(id: str, request: Request, db=Depends(get_session)):
    return await services.inspect(id, request.app.state.browser, db)


@router.post('/applications/{id}/fill')
async def fill(id: str, payload: FillInput, request: Request, db=Depends(get_session)):
    return await services.fill(id, payload, request.app.state.browser, db)


@router.post('/applications/{id}/submit')
async def submit(id: str, payload: SubmitInput, request: Request, db=Depends(get_session)):
    return await services.submit(id, payload, request.app.state.browser, db)


@router.patch('/applications/{id}/status')
def status(id: str, payload: ApplicationStatus, db=Depends(get_session)):
    return services.status(id, payload, db)
