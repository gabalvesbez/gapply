"""HTTP do perfil; delega as operações aos serviços."""
from fastapi import APIRouter, Depends
from app.core.database import get_session
from app.domains.profiles.schemas import ProfileData, ProfileUpdate, ChatInput
from app.domains.profiles import services

router = APIRouter(prefix="/profiles", tags=["Perfil e entrevista"])


@router.post('', status_code=201)
def create_profile(payload: ProfileData, db=Depends(get_session)):
    return services.create_profile(payload, db)


@router.get('')
def profiles(db=Depends(get_session)):
    return services.profiles(db)


@router.get('/{id}')
def profile(id: str, db=Depends(get_session)):
    return services.profile(id, db)


@router.put('/{id}')
def update(id: str, payload: ProfileUpdate, db=Depends(get_session)):
    return services.update(id, payload, db)


@router.get('/{id}/messages')
def messages(id: str, db=Depends(get_session)):
    return services.messages(id, db)


@router.post('/{id}/messages')
async def interview(id: str, payload: ChatInput):
    return await services.interview(id, payload)
