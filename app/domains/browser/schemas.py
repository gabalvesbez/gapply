"""Contratos de entrada e validação do domínio browser."""
from pydantic import HttpUrl
from app.core.schemas import Input


class OpenBrowser(Input):
    url: HttpUrl
