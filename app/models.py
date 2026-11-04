"""Registro de todas as tabelas para a aplicação e o Alembic.

Importar este módulo preenche Base.metadata; não cria tabelas no banco.
"""
from app.domains.profiles.models import Profile, Message
from app.domains.resumes.models import Resume
from app.domains.jobs.models import Source, Job, SearchRun, Evaluation, Cache
from app.domains.applications.models import Application

__all__ = ['Profile', 'Message', 'Resume', 'Source', 'Job', 'SearchRun', 'Evaluation', 'Cache', 'Application']
