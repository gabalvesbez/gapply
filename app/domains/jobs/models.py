"""Tabelas do domínio jobs."""
from sqlalchemy import String, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, identifier, now


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    provider: Mapped[str] = mapped_column(String(20))
    board: Mapped[str] = mapped_column(String(100))
    region: Mapped[str] = mapped_column(String(10), default="global")
    __table_args__ = (UniqueConstraint("provider", "board", "region"),)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)


class SearchRun(Base):
    __tablename__ = "search_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    status: Mapped[str] = mapped_column(String(30), default="queued")
    request: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(default=now)


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)


class Cache(Base):
    __tablename__ = "source_cache"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[list] = mapped_column(JSON)
    fetched_at: Mapped[float]
