"""Endpoints de vagas, fontes, pesquisas e avaliações."""
from fastapi import APIRouter, Depends, Request
from app.core.database import get_session
from app.domains.jobs.schemas import SourceInput, SearchInput, JobInput, EvaluationInput
from app.domains.jobs import services

router = APIRouter(tags=["Busca e vagas"])


@router.get('/sources')
def sources(db=Depends(get_session)):
    return services.sources(db)


@router.post('/sources', status_code=201)
def add_source(payload: SourceInput, db=Depends(get_session)):
    return services.add_source(payload, db)


@router.delete('/sources/{id}', status_code=204)
def delete_source(id: str, db=Depends(get_session)):
    return services.delete_source(id, db)


@router.post('/searches', status_code=202)
async def create_search(payload: SearchInput, request: Request, db=Depends(get_session)):
    return await services.create_search(payload, request.app.state.tasks, db)


@router.get('/searches')
def searches(db=Depends(get_session)):
    return services.searches(db)


@router.get('/searches/{id}')
def get_search(id: str, db=Depends(get_session)):
    return services.get_search(id, db)


@router.get('/jobs')
def jobs(offset: int = 0, limit: int = 50, db=Depends(get_session)):
    return services.jobs(offset, limit, db)


@router.post('/jobs/import', status_code=201)
def import_job(payload: JobInput, db=Depends(get_session)):
    return services.import_job(payload, db)


@router.get('/jobs/{id}')
def job(id: str, db=Depends(get_session)):
    return services.job(id, db)


@router.post('/jobs/{id}/evaluate')
async def evaluate(id: str, payload: EvaluationInput):
    return await services.evaluate(id, payload)


@router.get('/profiles/{id}/evaluations')
def evaluations(id: str, db=Depends(get_session)):
    return services.evaluations(id, db)
