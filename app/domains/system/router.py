"""Rotas operacionais: saúde e recursos configurados."""
from fastapi import APIRouter, Depends
from app.core.security import require_key
from app.domains.system import services

router = APIRouter(tags=["Sistema"])


@router.get("/health")
def health():
    return services.health()


@router.get("/api/v1/capabilities", dependencies=[Depends(require_key)])
def capabilities():
    return services.capabilities()
