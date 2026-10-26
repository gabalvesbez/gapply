import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import Session, Source, Profile, SearchRun, Job, Evaluation, get_session, row_dict
from app.contracts import SourceInput, SearchInput, JobInput, EvaluationInput, EvaluationResult
from app.repository import require, save_job
from app.modules.jobs.service import search, heuristic
from app.clients.ai import deepseek, jev

router = APIRouter(tags=["Busca e vagas"])

@router.get("/sources")
def sources(db=Depends(get_session)):
    return {"built_in": [{"provider": "remotive", "coverage": "Vagas remotas, cache de 6 horas; não é todo o mercado."}],
            "boards": [row_dict(s) for s in db.scalars(select(Source))]}

@router.post("/sources", status_code=201)
def add_source(payload: SourceInput, db=Depends(get_session)):
    source = Source(**payload.model_dump())
    db.add(source)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Fonte já cadastrada.")
    return row_dict(source)

@router.delete("/sources/{id}", status_code=204)
def delete_source(id: str, db=Depends(get_session)):
    db.delete(require(db, Source, id))
    db.commit()

@router.post("/searches", status_code=202)
async def create_search(payload: SearchInput, request: Request, db=Depends(get_session)):
    profile = require(db, Profile, payload.profile_id)
    if not profile.confirmed:
        raise HTTPException(409, "Revise e confirme o perfil primeiro.")
    if not any(k.strip() for k in payload.keywords):
        raise HTTPException(422, "Informe pelo menos um termo não vazio.")
    if not (payload.include_remotive or payload.source_ids or payload.browser_sources):
        raise HTTPException(422, "Selecione ao menos uma fonte.")
    for id in payload.source_ids:
        require(db, Source, id)
    # Evita disputa de cache e excesso de chamadas no uso pessoal.
    if db.scalar(select(SearchRun).where(SearchRun.status.in_(["queued", "running"]))):
        raise HTTPException(409, "Há uma busca em andamento.")
    run = SearchRun(profile_id=payload.profile_id, request=payload.model_dump())
    db.add(run)
    db.commit()
    task = asyncio.create_task(search(run.id))
    request.app.state.tasks.add(task)
    task.add_done_callback(request.app.state.tasks.discard)
    return row_dict(run)

@router.get("/searches")
def searches(db=Depends(get_session)):
    return [row_dict(r) for r in db.scalars(select(SearchRun).order_by(SearchRun.created_at.desc()).limit(100))]

@router.get("/searches/{id}")
def get_search(id: str, db=Depends(get_session)):
    run = require(db, SearchRun, id)
    result = row_dict(run)
    result["jobs"] = [row_dict(j) for job_id in run.result.get("job_ids", []) if (j := db.get(Job, job_id))]
    return result

@router.get("/jobs")
def jobs(offset: int = 0, limit: int = 50, db=Depends(get_session)):
    if offset < 0 or not 1 <= limit <= 200:
        raise HTTPException(422, "Use offset >= 0 e limit entre 1 e 200.")
    return [row_dict(j) for j in db.scalars(select(Job).order_by(Job.created_at.desc()).offset(offset).limit(limit))]

@router.post("/jobs/import", status_code=201)
def import_job(payload: JobInput, db=Depends(get_session)):
    item = payload.model_dump(mode="json")
    item.update(provider="manual", apply_url=item["url"])
    job = save_job(db, item)
    db.commit()
    return row_dict(job)

@router.get("/jobs/{id}")
def job(id: str, db=Depends(get_session)):
    return row_dict(require(db, Job, id))

@router.post("/jobs/{id}/evaluate")
async def evaluate(id: str, payload: EvaluationInput):
    with Session() as db:
        profile = require(db, Profile, payload.profile_id)
        if not profile.confirmed:
            raise HTTPException(409, "Confirme seu perfil antes de avaliar.")
        data, job = profile.data, require(db, Job, id).data
    if payload.provider == "jev":
        result = await jev(data, job)
    elif payload.provider == "deepseek":
        result = (await deepseek([{"role": "user", "content": "Avalie esta vaga para o candidato, citando somente fatos dos dados: " +
                   json.dumps({"profile": data, "job": job}, ensure_ascii=False)}], EvaluationResult)).model_dump()
        result["provider"] = "deepseek"
    else:
        result = heuristic(data, job)
    with Session() as db:
        record = Evaluation(profile_id=payload.profile_id, job_id=id, data={**result, "profile_snapshot": data})
        db.add(record)
        db.commit()
        return row_dict(record)

@router.get("/profiles/{id}/evaluations")
def evaluations(id: str, db=Depends(get_session)):
    require(db, Profile, id)
    return [row_dict(e) for e in db.scalars(select(Evaluation).where(Evaluation.profile_id == id).order_by(Evaluation.created_at.desc()))]
