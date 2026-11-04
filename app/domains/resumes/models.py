"""Tabelas do domínio resumes."""
from sqlalchemy import String, JSON, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, identifier, now


class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    warnings: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)
