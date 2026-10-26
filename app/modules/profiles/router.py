from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.database import Session, Profile, Resume, Message, get_session, row_dict
from app.contracts import ProfileData, ProfileUpdate, ChatInput, InterviewResult
from app.repository import require
from app.clients.ai import deepseek
import json

router = APIRouter(prefix="/profiles", tags=["Perfil e entrevista"])

@router.post("", status_code=201)
def create_profile(payload: ProfileData, db=Depends(get_session)):
    profile = Profile(data=payload.model_dump())
    db.add(profile)
    db.commit()
    return row_dict(profile)

@router.get("")
def profiles(db=Depends(get_session)):
    return [row_dict(p) for p in db.scalars(select(Profile).order_by(Profile.created_at))]

@router.get("/{id}")
def profile(id: str, db=Depends(get_session)):
    return row_dict(require(db, Profile, id))

@router.put("/{id}")
def update(id: str, payload: ProfileUpdate, db=Depends(get_session)):
    p = require(db, Profile, id)
    if payload.confirmed and not payload.data.titles:
        raise HTTPException(422, "Defina pelo menos um título/cargo antes de confirmar.")
    p.data, p.confirmed = payload.data.model_dump(), payload.confirmed
    db.commit()
    return row_dict(p)

@router.get("/{id}/messages")
def messages(id: str, db=Depends(get_session)):
    require(db, Profile, id)
    return [row_dict(m) for m in db.scalars(select(Message).where(Message.profile_id == id).order_by(Message.created_at, Message.id))]

@router.post("/{id}/messages")
async def interview(id: str, payload: ChatInput):
    # A transação termina antes da chamada remota; não prendemos uma conexão por 90s.
    with Session() as db:
        p = require(db, Profile, id)
        resume = db.scalar(select(Resume).where(Resume.profile_id == id).order_by(Resume.created_at.desc()))
        history = list(db.scalars(select(Message).where(Message.profile_id == id).order_by(Message.created_at.desc(), Message.id.desc()).limit(20)))
        context = json.dumps({"profile": p.data, "resume": resume.text[:45000] if resume else ""}, ensure_ascii=False)
        past = [{"role": m.role, "content": m.content} for m in reversed(history)]
    instructions = ("Conduza uma entrevista de carreira. Faça até 3 perguntas relevantes por vez, "
                    "aprofunde lacunas e proponha títulos de busca e mercados a partir de respostas reais. "
                    "Separe interesses de competências. Preserve valores confirmados quando não houver nova informação. "
                    "Proponha um perfil completo para revisão, sem inventar contatos. Contexto: " + context)
    result = await deepseek([{"role": "user", "content": instructions}, *past,
                             {"role": "user", "content": payload.message}], InterviewResult)
    with Session() as db:
        db.add_all([Message(profile_id=id, role="user", content=payload.message),
                    Message(profile_id=id, role="assistant", content=result.model_dump_json())])
        db.commit()
    return {**result.model_dump(), "requires_profile_confirmation": True}
