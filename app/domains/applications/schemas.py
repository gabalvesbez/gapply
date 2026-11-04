"""Contratos de entrada e validação do domínio applications."""
from typing import Literal
from pydantic import Field
from app.core.schemas import Input


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
