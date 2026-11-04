"""Contratos de entrada e validação do domínio jobs."""
from typing import Literal
from pydantic import Field, HttpUrl
from app.core.schemas import Input


class SourceInput(Input):
    provider: Literal["greenhouse", "lever"]
    board: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    region: Literal["global", "eu"] = "global"


class SearchInput(Input):
    profile_id: str
    keywords: list[str] = Field(min_length=1, max_length=10)
    markets: list[str] = Field(default_factory=list, max_length=20)
    include_remotive: bool = True
    source_ids: list[str] = Field(default_factory=list, max_length=30)
    browser_sources: list[Literal["linkedin", "indeed"]] = Field(default_factory=list, max_length=2)
    limit: int = Field(default=100, ge=1, le=200)


class JobInput(Input):
    title: str = Field(min_length=1, max_length=300)
    company: str = Field(default="", max_length=300)
    location: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=60000)
    url: HttpUrl


class EvaluationInput(Input):
    profile_id: str
    provider: Literal["rules", "jev", "deepseek"] = "rules"


class EvaluationResult(Input):
    priority: Literal["prioritize", "consider", "low", "unknown"]
    reasons: list[str] = Field(max_length=20)
    missing_information: list[str] = Field(max_length=20)
