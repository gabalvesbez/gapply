"""Contratos de entrada para o React e respostas estruturadas da IA."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class ProfileData(Input):
    name: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=60)
    location: str = Field(default="", max_length=200)
    linkedin: str = Field(default="", max_length=500)
    portfolio: str = Field(default="", max_length=500)
    skills: list[str] = Field(default_factory=list, max_length=100)
    interests: list[str] = Field(default_factory=list, max_length=50)
    titles: list[str] = Field(default_factory=list, max_length=20)
    markets: list[str] = Field(default_factory=list, max_length=20)
    languages: list[str] = Field(default_factory=list, max_length=20)
    remote: bool = True
    seniority: str = Field(default="", max_length=100)
    summary: str = Field(default="", max_length=5000)

class ProfileUpdate(Input):
    data: ProfileData
    confirmed: bool = False

class ChatInput(Input):
    message: str = Field(min_length=1, max_length=6000)

class InterviewResult(Input):
    answer: str = Field(min_length=1, max_length=12000)
    proposed_profile: ProfileData
    ready_for_search: bool

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

class ApplicationInput(Input):
    profile_id: str
    job_id: str
    resume_id: str

class FieldValue(Input):
    field_id: str
    value: str | bool

class FillInput(Input):
    fields: list[FieldValue] = Field(default_factory=list, max_length=100)
    resume_field_id: str | None = None

class SubmitInput(Input):
    button_id: str
    review_token: str
    confirmed: Literal[True]

class ApplicationStatus(Input):
    status: Literal["submitted", "not_submitted", "rejected", "interview", "offer", "withdrawn"]
    note: str = Field(min_length=1, max_length=3000)

class OpenBrowser(Input):
    url: HttpUrl
