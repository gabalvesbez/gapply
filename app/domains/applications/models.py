"""Tabelas do domínio applications."""
from sqlalchemy import String, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, identifier, now


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id"))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(default=now)
    __table_args__ = (UniqueConstraint("profile_id", "job_id"),)
