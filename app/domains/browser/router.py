"""HTTP das sessões de navegação assistida."""
from fastapi import APIRouter, Request
from app.domains.browser.schemas import OpenBrowser
from app.domains.browser import services

router = APIRouter(tags=["Candidaturas e navegador"])


@router.post('/browser/sessions', status_code=201)
async def open_browser(payload: OpenBrowser, request: Request):
    return await services.open_browser(payload, request.app.state.browser)


@router.get('/browser/sessions/{id}/jobs')
async def collect(id: str, request: Request):
    return await services.collect(id, request.app.state.browser)


@router.get('/browser/sessions/{id}/page')
async def page(id: str, request: Request):
    return await services.page(id, request.app.state.browser)


@router.delete('/browser/sessions/{id}')
async def close(id: str, request: Request):
    return await services.close(id, request.app.state.browser)
