"""Contratos de entrada e validação do domínio profiles."""
from pydantic import Field
from app.core.schemas import Input


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
