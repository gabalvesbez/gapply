from typing import Literal
from pydantic import BaseModel, Field

class ResumeTextResponse(BaseModel):
    filename: str
    format: Literal["pdf", "docx"]
    text: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)

class ErrorResponse(BaseModel):
    detail: str
