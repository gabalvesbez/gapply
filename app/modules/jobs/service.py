import asyncio
import unicodedata
from urllib.parse import urlencode
from sqlalchemy import select
from app.clients.jobs import fetch_jobs
from app.database import Session, SearchRun, Source
from app.repository import save_job

def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))

def matches(job, query):
    haystack = normalized(job["title"] + " " + job.get("description", ""))
    keywords = [normalized(k.strip()) for k in query["keywords"] if k.strip()]
    if not any(k in haystack for k in keywords):
        return False
    markets = [normalized(m.strip()) for m in query["markets"] if m.strip()]
    location = normalized(job.get("location", ""))
    global_location = any(x in location for x in ["worldwide", "anywhere", "global"])
    return not markets or global_location or any(m in location for m in markets)

def browser_links(query):
    keyword = " OR ".join(query["keywords"])
    location = ", ".join(query["markets"])
    links = []
    for source in dict.fromkeys(query["browser_sources"]):
        if source == "linkedin":
            url = "https://www.linkedin.com/jobs/search/?" + urlencode({"keywords": keyword, "location": location})
        else:
            url = "https://www.indeed.com/jobs?" + urlencode({"q": keyword, "l": location})
        links.append({"provider": source, "url": url, "status": "awaiting_user",
                      "instruction": "Abra no navegador assistido; faça login/verificação e importe vagas visíveis."})
    return links

async def search(run_id: str):
    with Session() as db:
        run = db.get(SearchRun, run_id)
        query = run.request
        sources = list(db.scalars(select(Source).where(Source.id.in_(query["source_ids"]))))
        connectors = [(s.provider, s.board, s.region) for s in sources]
        if query["include_remotive"]:
            connectors.insert(0, ("remotive", "", "global"))
        run.status = "running"
        run.result = {"job_ids": [], "sources": [], "browser_tasks": browser_links(query)}
        db.commit()
    try:
        semaphore = asyncio.Semaphore(4)
        async def one(connector):
            async with semaphore:
                name = ":".join(connector)
                try:
                    jobs = await fetch_jobs(*connector)
                    matches_found = [j for j in jobs if matches(j, query)]
                    return name, matches_found, None
                except Exception as exc:
                    # Mensagens remotas podem conter dados; só persistimos o tipo da falha.
                    return name, [], type(exc).__name__
        pending = [asyncio.create_task(one(c)) for c in connectors]
        try:
            for task in asyncio.as_completed(pending):
                name, jobs, error = await task
                with Session() as db:
                    run = db.get(SearchRun, run_id)
                    result = dict(run.result)
                    ids = list(result["job_ids"])
                    for item in jobs:
                        if len(ids) >= query["limit"]:
                            break
                        job = save_job(db, item)
                        if job.id not in ids:
                            ids.append(job.id)
                    result["job_ids"] = ids
                    result["sources"] = [*result["sources"], {"source": name, "matches": len(jobs), "error": error}]
                    run.result = result
                    db.commit()
        finally:
            for task in pending:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        with Session() as db:
            run = db.get(SearchRun, run_id)
            errors = [s for s in run.result["sources"] if s["error"]]
            run.status = "partial" if errors else "completed"
            db.commit()
    except asyncio.CancelledError:
        with Session() as db:
            run = db.get(SearchRun, run_id)
            run.status = "interrupted"
            db.commit()
        raise
    except Exception:
        with Session() as db:
            run = db.get(SearchRun, run_id)
            run.status = "failed"
            db.commit()

def heuristic(profile, job):
    text = normalized(job.get("title", "") + " " + job.get("description", ""))
    hits = [s for s in profile.get("skills", []) if normalized(s) in text]
    missing = []
    if not job.get("description"):
        missing.append("Descrição da vaga ausente.")
    if not job.get("salary"):
        missing.append("Salário não informado.")
    return {"provider": "rules", "priority": "consider" if hits else "unknown",
            "reasons": ["Termos encontrados: " + ", ".join(hits)] if hits else ["Nenhum termo do perfil encontrado."],
            "missing_information": missing,
            "note": "Correspondência textual simples; não comprova aderência nem chance de contratação."}
