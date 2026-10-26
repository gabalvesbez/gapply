"""Operações reutilizadas por rotas e tarefas."""
import hashlib
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from fastapi import HTTPException
from sqlalchemy import select
from app.database import Job

def require(db, model, id):
    item = db.get(model, id)
    if item is None:
        raise HTTPException(404, "Registro não encontrado.")
    return item

def save_job(db, data: dict) -> Job:
    parts = urlsplit(data["url"])
    tracking = {"source", "ref", "refid", "lever-source", "lever-origin", "gh_src", "trk"}
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.startswith("utm_") and k not in tracking]
    canonical = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(sorted(query)), ""))
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    job = db.scalar(select(Job).where(Job.fingerprint == fingerprint))
    if job:
        job.data = {**job.data, **data}
    else:
        job = Job(fingerprint=fingerprint, data=data)
        db.add(job)
        db.flush()
    return job
