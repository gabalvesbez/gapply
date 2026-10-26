"""Conectores oficiais e normalização. Remotive é consultado no máximo a cada 6h."""
import asyncio
import time
import httpx
from bs4 import BeautifulSoup
from app.database import Cache, Session

remotive_lock = asyncio.Lock()

def plain(value: str) -> str:
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)

async def get_json(client, url, params=None):
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()

async def fetch_jobs(provider: str, board: str = "", region: str = "global") -> list[dict]:
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "CareerAssistant/0.1 (personal project)"}) as client:
        if provider == "remotive":
            async with remotive_lock:
                with Session() as db:
                    cache = db.get(Cache, "remotive")
                    if cache and time.time() - cache.fetched_at < 21600:
                        return cache.data
                payload = await get_json(client, "https://remotive.com/api/remote-jobs")
                jobs = [{"provider": provider, "external_id": str(j["id"]), "title": j["title"],
                         "company": j.get("company_name", ""), "location": j.get("candidate_required_location", ""),
                         "description": plain(j.get("description", "")), "url": j["url"], "apply_url": j["url"],
                         "remote": True, "attribution": "Remotive", "salary": j.get("salary", "")}
                        for j in payload["jobs"]]
                with Session() as db:
                    cache = db.get(Cache, "remotive")
                    if cache:
                        cache.data, cache.fetched_at = jobs, time.time()
                    else:
                        db.add(Cache(key="remotive", data=jobs, fetched_at=time.time()))
                    db.commit()
                return jobs
        if provider == "greenhouse":
            payload = await get_json(client, f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", {"content": "true"})
            return [{"provider": provider, "external_id": str(j["id"]), "title": j["title"], "company": board,
                     "location": j.get("location", {}).get("name", ""), "description": plain(j.get("content", "")),
                     "url": j["absolute_url"], "apply_url": j["absolute_url"]}
                    for j in payload["jobs"]]
        host = "api.eu.lever.co" if region == "eu" else "api.lever.co"
        jobs, skip = [], 0
        for _ in range(50):
            payload = await get_json(client, f"https://{host}/v0/postings/{board}", {"mode": "json", "limit": 100, "skip": skip})
            for j in payload:
                extra = " ".join(plain(x.get("content", "")) for x in j.get("lists", []))
                jobs.append({"provider": "lever", "external_id": j["id"], "title": j["text"], "company": board,
                             "location": j.get("categories", {}).get("location", ""), "description": plain(j.get("description", "")) + " " + extra,
                             "url": j["hostedUrl"], "apply_url": j["applyUrl"]})
            if len(payload) < 100:
                return jobs
            skip += 100
        raise ValueError("Limite de paginação excedido; busca desta empresa não foi concluída.")
