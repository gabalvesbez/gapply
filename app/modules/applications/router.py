from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import Application, Profile, Resume, Job, get_session, row_dict, now
from app.contracts import ApplicationInput, FillInput, SubmitInput, ApplicationStatus, OpenBrowser
from app.repository import require

router = APIRouter(tags=["Candidaturas e navegador"])

def suggestion(label, profile):
    text = label.casefold()
    names = profile.get("name", "").split()
    if any(k in text for k in ["e-mail", "email"]):
        return profile.get("email")
    if any(k in text for k in ["phone", "telefone", "celular"]):
        return profile.get("phone")
    if any(k in text for k in ["first name", "primeiro nome"]):
        return names[0] if names else None
    if any(k in text for k in ["last name", "sobrenome", "apelido"]):
        return " ".join(names[1:]) if len(names) > 1 else None
    if text.strip() in ["name", "nome", "full name", "nome completo"]:
        return profile.get("name")
    if "linkedin" in text:
        return profile.get("linkedin")
    if any(k in text for k in ["portfolio", "portfólio", "personal website"]):
        return profile.get("portfolio")
    return None

def browser_id(record):
    id = record.data.get("browser_session_id")
    if not id:
        raise HTTPException(409, "Abra a candidatura no navegador primeiro.")
    return id

def record_event(record, status, **values):
    record.status = status
    history = record.data.get("history", [])
    record.data = {**record.data, **values, "history": [*history, {"at": now(), "status": status}]}

@router.post("/applications", status_code=201)
def create(payload: ApplicationInput, db=Depends(get_session)):
    profile = require(db, Profile, payload.profile_id)
    if not profile.confirmed:
        raise HTTPException(409, "Confirme o perfil antes de candidatar-se.")
    require(db, Job, payload.job_id)
    resume = require(db, Resume, payload.resume_id)
    if resume.profile_id != payload.profile_id:
        raise HTTPException(422, "O currículo pertence a outro perfil.")
    record = Application(**payload.model_dump(), data={"profile_snapshot": profile.data, "history": []})
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe candidatura deste perfil para esta vaga.")
    return row_dict(record)

@router.get("/applications")
def applications(profile_id: str | None = None, db=Depends(get_session)):
    query = select(Application).order_by(Application.created_at.desc())
    if profile_id:
        query = query.where(Application.profile_id == profile_id)
    return [row_dict(a) for a in db.scalars(query.limit(200))]

@router.get("/applications/{id}")
def application(id: str, db=Depends(get_session)):
    return row_dict(require(db, Application, id))

@router.post("/applications/{id}/open")
async def open_application(id: str, request: Request, db=Depends(get_session)):
    record = require(db, Application, id)
    if record.status not in ("draft", "not_submitted", "awaiting_user", "awaiting_review"):
        raise HTTPException(409, "Candidatura já processada ou envio incerto. Confira o resultado antes de reenviar.")
    job = require(db, Job, record.job_id)
    result = await request.app.state.browser.call("open", job.data.get("apply_url", job.data["url"]))
    record_event(record, "awaiting_user", browser_session_id=result["session_id"])
    db.commit()
    return result

@router.get("/applications/{id}/form")
async def inspect(id: str, request: Request, db=Depends(get_session)):
    record = require(db, Application, id)
    result = await request.app.state.browser.call("inspect", browser_id(record))
    profile = record.data["profile_snapshot"]
    for field in result["fields"]:
        if field["type"] not in ("checkbox", "radio", "file") and field["tag"] != "select":
            field["suggested_value"] = suggestion(field["label"], profile)
    result["note"] = "Sugestões não são preenchidas automaticamente. Revise valores e consentimentos."
    return result

@router.post("/applications/{id}/fill")
async def fill(id: str, payload: FillInput, request: Request, db=Depends(get_session)):
    record = require(db, Application, id)
    if record.status not in ("awaiting_user", "awaiting_review"):
        raise HTTPException(409, "Abra uma candidatura ainda não enviada.")
    resume = require(db, Resume, record.resume_id)
    result = await request.app.state.browser.call("fill", browser_id(record),
        [f.model_dump() for f in payload.fields], payload.resume_field_id, resume.path)
    record_event(record, "awaiting_review")
    db.commit()
    return result

@router.post("/applications/{id}/submit")
async def submit(id: str, payload: SubmitInput, request: Request, db=Depends(get_session)):
    record = require(db, Application, id)
    if record.status not in ("awaiting_review", "awaiting_user"):
        raise HTTPException(409, "Candidatura não está disponível para envio.")
    # Persiste ANTES do clique: queda do processo não transforma um possível envio em rascunho.
    record_event(record, "submission_unknown")
    db.commit()
    try:
        result = await request.app.state.browser.call("submit", browser_id(record), payload.button_id, payload.review_token)
    except HTTPException as exc:
        # Validações 422/409 acontecem antes do clique; falhas do browser continuam incertas.
        if exc.status_code == 422 or "página mudou" in str(exc.detail) or "Escolha" in str(exc.detail):
            record_event(record, "awaiting_review")
            db.commit()
        raise
    record_event(record, result["status"], submission_note=result["note"])
    db.commit()
    return result

@router.patch("/applications/{id}/status")
def status(id: str, payload: ApplicationStatus, db=Depends(get_session)):
    record = require(db, Application, id)
    record_event(record, payload.status, user_confirmation=payload.note)
    db.commit()
    return row_dict(record)

@router.post("/browser/sessions", status_code=201)
async def open_browser(payload: OpenBrowser, request: Request):
    return await request.app.state.browser.call("open", str(payload.url))

@router.get("/browser/sessions/{id}/jobs")
async def collect(id: str, request: Request):
    return await request.app.state.browser.call("collect", id)

@router.get("/browser/sessions/{id}/page")
async def page(id: str, request: Request):
    return await request.app.state.browser.call("page_text", id)

@router.delete("/browser/sessions/{id}")
async def close(id: str, request: Request):
    return await request.app.state.browser.call("close", id)
