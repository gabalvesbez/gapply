"""Casos de uso do perfil e da entrevista de carreira."""
import json
from fastapi import HTTPException
from sqlalchemy import select
from app.core.database import Session, row_dict
from app.core.repository import require
from app.domains.profiles.models import Profile, Message
from app.domains.resumes.models import Resume
from app.domains.profiles.schemas import ProfileData, ProfileUpdate, ChatInput, InterviewResult
from app.integrations.ai import deepseek


def create_profile(payload: ProfileData, db):
    profile = Profile(data=payload.model_dump())
    db.add(profile)
    db.commit()
    return row_dict(profile)


def profiles(db):
    return [row_dict(p) for p in db.scalars(select(Profile).order_by(Profile.created_at))]


def profile(id: str, db):
    return row_dict(require(db, Profile, id))


def update(id: str, payload: ProfileUpdate, db):
    p = require(db, Profile, id)
    if payload.confirmed and not payload.data.titles:
        raise HTTPException(422, "Defina pelo menos um título/cargo antes de confirmar.")
    p.data, p.confirmed = payload.data.model_dump(), payload.confirmed
    db.commit()
    return row_dict(p)


def messages(id: str, db):
    require(db, Profile, id)
    return [row_dict(m) for m in db.scalars(select(Message).where(Message.profile_id == id).order_by(Message.created_at, Message.id))]


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
