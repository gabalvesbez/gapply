import secrets
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from app.config import settings

header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_key(value: str | None = Depends(header)):
    if not settings.api_key:
        raise HTTPException(503, "Configure API_KEY no .env para usar a API.")
    if not value or not secrets.compare_digest(value, settings.api_key):
        raise HTTPException(401, "Chave local inválida. Use X-API-Key.")
