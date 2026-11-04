"""Servidor local. Execute com um worker: navegador e tarefas pertencem ao processo."""
import asyncio
from contextlib import asynccontextmanager
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from starlette.exceptions import HTTPException
from app import models  # Registra todas as tabelas na metadata do SQLAlchemy.
from app.core.config import settings, MAX_REQUEST_BYTES
from app.core.database import Session
from app.core.security import require_key
from app.domains.jobs.models import SearchRun
from app.domains.browser.client import BrowserWorker
from app.domains.resumes.router import router as resumes
from app.domains.profiles.router import router as profiles
from app.domains.jobs.router import router as jobs
from app.domains.applications.router import router as applications
from app.domains.browser.router import router as browser
from app.domains.system.router import router as system
from app.domains.resumes.errors import ResumeError, FileTooLargeError, UnsupportedFormatError

def migrate():
    command.upgrade(Config("alembic.ini"), "head")

@asynccontextmanager
async def lifespan(app):
    await run_in_threadpool(migrate)
    with Session() as db:
        for run in db.scalars(select(SearchRun).where(SearchRun.status.in_(["queued", "running"]))):
            run.status = "interrupted"
        db.commit()
    app.state.tasks = set()
    app.state.browser = BrowserWorker()
    yield
    tasks = list(app.state.tasks)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await app.state.browser.call("shutdown")
    app.state.browser.executor.shutdown(wait=True)

def create_app():
    app = FastAPI(title="Assistente de candidaturas", version="0.2.0", lifespan=lifespan,
        description="Backend pessoal: currículo, entrevista, busca e candidatura assistida. X-API-Key em todas as operações de dados.")
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=MAX_REQUEST_BYTES)
    # CORS externo ao limite: o React consegue ler inclusive respostas de erro de upload.
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type"])

    @app.exception_handler(ResumeError)
    async def extraction_error(request: Request, exc: ResumeError):
        code = 413 if isinstance(exc, FileTooLargeError) else 415 if isinstance(exc, UnsupportedFormatError) else 422
        return JSONResponse({"detail": str(exc)}, status_code=code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = [{"location": list(e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse({"detail": "Dados inválidos.", "errors": errors}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    app.include_router(system)
    for router in (resumes, profiles, jobs, applications, browser):
        app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_key)])
    return app

app = create_app()
