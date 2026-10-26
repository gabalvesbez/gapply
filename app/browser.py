"""Playwright síncrono em uma única thread, inclusive no Windows.

O browser pertence ao usuário local. CAPTCHA/login são resolvidos por ele.
Nenhuma ação de envio é repetida automaticamente.
"""
import asyncio
import hashlib
import ipaddress
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from fastapi import HTTPException
from playwright.sync_api import sync_playwright, Error as BrowserError
from app.config import settings

HOSTS = ("linkedin.com", "indeed.com", "greenhouse.io", "greenhouse.com", "lever.co", "remotive.com")

def allowed_navigation(url):
    p = urlsplit(url)
    return p.scheme == "https" and not p.username and p.port in (None, 443) and any(
        (p.hostname or "").lower() == h or (p.hostname or "").lower().endswith("." + h) for h in HOSTS
    )

class BrowserWorker:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="career-browser")
        self.context = None
        self.playwright = None
        self.sessions = {}
        self.public_hosts = {}

    async def call(self, operation, *args):
        try:
            return await asyncio.get_running_loop().run_in_executor(self.executor, getattr(self, operation), *args)
        except HTTPException:
            raise
        except BrowserError as exc:
            raise HTTPException(409, "Navegador/página indisponível. Instale Chromium, reabra a sessão ou conclua login/verificação e inspecione novamente.") from exc

    def public_resource(self, url):
        p = urlsplit(url)
        if p.scheme in ("data", "blob", "about"):
            return True
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        host = p.hostname.lower()
        if host not in self.public_hosts:
            try:
                self.public_hosts[host] = all(ipaddress.ip_address(info[4][0]).is_global
                                              for info in socket.getaddrinfo(host, p.port or 443))
            except (OSError, ValueError):
                self.public_hosts[host] = False
        return self.public_hosts[host]

    def guard(self, route):
        request = route.request
        if not self.public_resource(request.url):
            return route.abort()
        if request.is_navigation_request() and request.frame.parent_frame is None and not allowed_navigation(request.url):
            return route.abort()
        route.continue_()

    def start(self):
        if self.context is None:
            self.playwright = sync_playwright().start()
            try:
                self.context = self.playwright.chromium.launch_persistent_context(
                    str((settings.data_dir / "browser").resolve()), headless=False,
                    accept_downloads=False, service_workers="block")
                self.context.route("**/*", self.guard)
                self.context.set_default_timeout(3000)
            except Exception:
                self.playwright.stop()
                self.playwright = None
                raise

    def open(self, url):
        if not allowed_navigation(url):
            raise HTTPException(422, "Navegador aceita LinkedIn, Indeed, Greenhouse, Lever e Remotive via HTTPS.")
        if len(self.sessions) >= 10:
            raise HTTPException(409, "Feche uma sessão antes de abrir outra (máximo 10).")
        self.start()
        page = self.context.new_page()
        id = str(uuid4())
        self.sessions[id] = {"page": page, "controls": {}, "submitted": False}
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except BrowserError:
            # Mantém a janela para o usuário resolver navegação/login manualmente.
            pass
        return {"session_id": id, "url": page.url, "status": "awaiting_user",
                "instruction": "Conclua login/CAPTCHA, navegue até o formulário e execute inspect."}

    def get(self, id):
        session = self.sessions.get(id)
        if not session or session["page"].is_closed():
            raise HTTPException(409, "Sessão encerrada. Abra novamente; login persistido no perfil local.")
        if not allowed_navigation(session["page"].url):
            raise HTTPException(409, "Navegue para uma página HTTPS suportada antes de continuar.")
        return session

    def inspect(self, id):
        session = self.get(id)
        page = session["page"]
        controls, fields, buttons = {}, [], []
        for frame_index, frame in enumerate(page.frames):
            if not allowed_navigation(frame.url):
                continue
            locator = frame.locator("input, textarea, select, button, [role=button]")
            for index in range(min(locator.count(), 250)):
                element = locator.nth(index)
                try:
                    info = element.evaluate("""e => ({
                        tag:e.tagName.toLowerCase(), type:(e.type||'').toLowerCase(),
                        label:((e.labels && [...e.labels].map(x=>x.innerText).join(' ')) || e.getAttribute('aria-label') || e.placeholder || e.name || e.innerText || '').trim().slice(0,300),
                        name:e.name||'', required:!!e.required, disabled:!!e.disabled,
                        value:e.type==='checkbox'||e.type==='radio'?e.checked:(e.type==='file'?'':e.value||''),
                        files:e.type==='file'?[...e.files].map(f=>({name:f.name,size:f.size})):[],
                        options:e.tagName==='SELECT'?[...e.options].map(o=>({value:o.value,label:o.text})):[],
                        invalid: e.willValidate && !e.validity.valid
                    })""")
                    if info["type"] in ("hidden", "password"):
                        continue
                    is_button = info["tag"] == "button" or info["type"] in ("submit", "button") or element.get_attribute("role") == "button"
                    if not element.is_visible() and info["type"] != "file":
                        continue
                    token = f"f{frame_index}-e{index}"
                    controls[token] = element
                    if is_button:
                        buttons.append({"button_id": token, "label": info["label"], "disabled": info["disabled"]})
                    else:
                        fields.append({"field_id": token, **info})
                except BrowserError:
                    continue
        snapshot = {"url": page.url, "fields": fields, "buttons": buttons}
        token = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
        session["controls"] = controls
        session["review_token"] = token
        snapshot.update(session_id=id, review_token=token, status="awaiting_review",
                        instruction="Verifique todos os campos e consents. Campos não detectados podem ser preenchidos na janela.")
        return snapshot

    def fill(self, id, values, resume_field_id, resume_path):
        session = self.get(id)
        if session["submitted"]:
            raise HTTPException(409, "Envio já tentado; verifique o resultado antes de qualquer nova ação.")
        filled, skipped = [], []
        for item in values:
            element = session["controls"].get(item["field_id"])
            if element is None:
                skipped.append({"field_id": item["field_id"], "reason": "Inspecione a página novamente."})
                continue
            try:
                tag = element.evaluate("e=>e.tagName.toLowerCase()")
                kind = (element.get_attribute("type") or "").lower()
                if tag == "select":
                    element.select_option(str(item["value"]))
                elif kind in ("checkbox", "radio"):
                    if not isinstance(item["value"], bool):
                        raise ValueError("Checkbox/radio precisa de booleano.")
                    element.set_checked(item["value"])
                elif tag == "textarea" or (tag == "input" and kind not in ("file", "hidden", "password", "submit", "button")):
                    element.fill(str(item["value"]))
                else:
                    raise ValueError("Controle não preenchível.")
                filled.append(item["field_id"])
            except (BrowserError, ValueError):
                skipped.append({"field_id": item["field_id"], "reason": "Campo mudou ou exige ação manual."})
        if resume_field_id:
            element = session["controls"].get(resume_field_id)
            if element is None or element.get_attribute("type") != "file":
                skipped.append({"field_id": resume_field_id, "reason": "Campo de arquivo indisponível."})
            elif not Path(resume_path).is_file():
                raise HTTPException(410, "Currículo original indisponível.")
            else:
                element.set_input_files(resume_path)
                filled.append(resume_field_id)
        return {**self.inspect(id), "filled": filled, "skipped": skipped}

    def submit(self, id, button_id, review_token):
        session = self.get(id)
        if session["submitted"]:
            raise HTTPException(409, "Envio já tentado nesta sessão. Verifique manualmente o resultado.")
        snapshot = self.inspect(id)
        if review_token != snapshot["review_token"]:
            raise HTTPException(409, "A página mudou. Revise novamente antes de enviar.")
        if not any(b["button_id"] == button_id and not b["disabled"] for b in snapshot["buttons"]):
            raise HTTPException(422, "Escolha um botão habilitado da última inspeção.")
        invalid = [f["label"] for f in snapshot["fields"] if f["invalid"]]
        if invalid:
            raise HTTPException(422, "Campos inválidos/obrigatórios: " + ", ".join(invalid)[:500])
        # Marcamos antes do clique: falha de rede não autoriza uma repetição automática.
        session["submitted"] = True
        try:
            session["controls"][button_id].click(timeout=10000)
        except BrowserError:
            return {"status": "submission_unknown", "url": session["page"].url,
                    "note": "Resultado do clique incerto. Verifique a janela; não reenviamos automaticamente."}
        return {"status": "submission_unknown", "url": session["page"].url,
                "note": "Clique realizado. Confirme manualmente a mensagem de sucesso; clique não prova candidatura enviada."}

    def collect(self, id):
        page = self.get(id)["page"]
        links = page.locator("a[href]").evaluate_all("""items=>items.map(a=>({url:a.href,title:a.innerText.trim()})).filter(x=>x.title)""")
        seen, result = set(), []
        for item in links:
            url = item["url"]
            path = urlsplit(url).path
            if not allowed_navigation(url) or url in seen:
                continue
            if not any(x in url for x in ("/jobs/view/", "/viewjob", "/rc/clk", "/jobs/", "jobs.lever.co/", "jobs.eu.lever.co/", "job-boards.greenhouse.io/")):
                continue
            if "search" in path or not item["title"]:
                continue
            seen.add(url)
            result.append({**item, "description": "", "company": "", "location": ""})
        return {"session_id": id, "url": page.url, "candidates": result[:100],
                "note": "Somente links visíveis na página carregada. Escolha e importe as vagas; sem coleta de áreas bloqueadas."}

    def page_text(self, id):
        page = self.get(id)["page"]
        return {"url": page.url, "title": page.title(), "text": page.locator("body").inner_text()[:60000],
                "note": "Texto da página inteira; revise e selecione a descrição antes de importar."}

    def close(self, id):
        session = self.sessions.pop(id, None)
        if session:
            session["page"].close()
        return {"closed": True}

    def shutdown(self):
        if self.context:
            self.context.close()
            self.context = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        self.sessions.clear()
