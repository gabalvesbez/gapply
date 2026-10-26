"""Sessões curtas e modelos SQLAlchemy, compatíveis com SQLite e PostgreSQL."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, JSON, Text, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.config import settings

settings.data_dir.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.database_url, pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def sqlite_pragmas(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

Session = sessionmaker(engine, expire_on_commit=False)

def identifier() -> str:
    return str(uuid4())

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase):
    pass

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(default=now)

class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    warnings: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=now)

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

def get_session():
    with Session() as session:
        yield session

def row_dict(row) -> dict:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name != "path"}
