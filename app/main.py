"""Servidor local. Execute com um worker: navegador e tarefas pertencem ao processo."""
import asyncio
from contextlib import asynccontextmanager
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from starlette.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from starlette.exceptions import HTTPException
from app.config import settings, MAX_REQUEST_BYTES
from app.database import Session, SearchRun
from app.browser import BrowserWorker
from app.security import require_key
from app.modules.resumes.router import router as resumes
from app.modules.profiles.router import router as profiles
from app.modules.jobs.router import router as jobs
from app.modules.applications.router import router as applications
from app.modules.resumes.errors import ResumeError, FileTooLargeError, UnsupportedFormatError

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

    @app.get("/health", tags=["Sistema"])
    def health():
        with Session() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/api/v1/capabilities", dependencies=[Depends(require_key)], tags=["Sistema"])
    def capabilities():
        return {"deepseek_configured": bool(settings.deepseek_api_key), "jev_configured": bool(settings.jev_api_key),
                "mode": "personal_local", "upload_limit_bytes": 10 * 1024 * 1024,
                "resume_formats": ["pdf", "docx"], "browser": "local_assisted",
                "automatic_submission_confirmation": False}

    for router in (resumes, profiles, jobs, applications):
        app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_key)])
    return app

app = create_app()
