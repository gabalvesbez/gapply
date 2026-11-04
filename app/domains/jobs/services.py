"""Fontes, buscas, vagas e avaliações: regras e transações."""
import asyncio
import json
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import Session, row_dict
from app.core.repository import require
from app.domains.profiles.models import Profile
from app.domains.jobs.models import Source, SearchRun, Job, Evaluation
from app.domains.jobs.schemas import SourceInput, SearchInput, JobInput, EvaluationInput, EvaluationResult
from app.domains.jobs.repository import save_job
from app.domains.jobs.search import search, normalized
from app.integrations.ai import deepseek, jev


def sources(db):
    return {"built_in": [{"provider": "remotive", "coverage": "Vagas remotas, cache de 6 horas; não é todo o mercado."}],
            "boards": [row_dict(s) for s in db.scalars(select(Source))]}


def add_source(payload: SourceInput, db):
    source = Source(**payload.model_dump())
    db.add(source)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Fonte já cadastrada.")
    return row_dict(source)


def delete_source(id: str, db):
    db.delete(require(db, Source, id))
    db.commit()


async def create_search(payload: SearchInput, tasks, db):
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
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return row_dict(run)


def searches(db):
    return [row_dict(r) for r in db.scalars(select(SearchRun).order_by(SearchRun.created_at.desc()).limit(100))]


def get_search(id: str, db):
    run = require(db, SearchRun, id)
    result = row_dict(run)
    result["jobs"] = [row_dict(j) for job_id in run.result.get("job_ids", []) if (j := db.get(Job, job_id))]
    return result


def jobs(offset: int, limit: int, db):
    if offset < 0 or not 1 <= limit <= 200:
        raise HTTPException(422, "Use offset >= 0 e limit entre 1 e 200.")
    return [row_dict(j) for j in db.scalars(select(Job).order_by(Job.created_at.desc()).offset(offset).limit(limit))]


def import_job(payload: JobInput, db):
    item = payload.model_dump(mode="json")
    item.update(provider="manual", apply_url=item["url"])
    job = save_job(db, item)
    db.commit()
    return row_dict(job)


def job(id: str, db):
    return row_dict(require(db, Job, id))


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


def evaluations(id: str, db):
    require(db, Profile, id)
    return [row_dict(e) for e in db.scalars(select(Evaluation).where(Evaluation.profile_id == id).order_by(Evaluation.created_at.desc()))]


def heuristic(profile, job):
    text = normalized(job.get("title", "") + " " + job.get("description", ""))
    hits = [s for s in profile.get("skills", []) if normalized(s) in text]
    missing = []
    if not job.get("description"):
        missing.append("Descrição da vaga ausente.")
    if not job.get("salary"):
        missing.append("Salário não informado.")
    return {"provider": "rules", "priority": "consider" if hits else "unknown",
            "reasons": ["Termos encontrados: " + ", ".join(hits)] if hits else ["Nenhum termo do perfil encontrado."],
            "missing_information": missing,
            "note": "Correspondência textual simples; não comprova aderência nem chance de contratação."}
