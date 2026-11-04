"""Operações de sessão do navegador, independentes do objeto HTTP Request."""
from app.domains.browser.schemas import OpenBrowser


async def open_browser(payload: OpenBrowser, browser):
    return await browser.call("open", str(payload.url))


async def collect(id: str, browser):
    return await browser.call("collect", id)


async def page(id: str, browser):
    return await browser.call("page_text", id)


async def close(id: str, browser):
    return await browser.call("close", id)
