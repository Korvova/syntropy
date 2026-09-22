"""Клиент BookStack REST API: полка → книга → страницы (инициатива → эпик → Т. страницы).

Токен: WIKIJS-подобно, из .secrets/bookstack_token в виде «ID:SECRET» или переменной BOOKSTACK_TOKEN.
Страницы пишем в markdown — BookStack хранит его и рендерит сам.
"""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = os.environ.get("BOOKSTACK_URL", "https://syntropy.test-rms.ru/kb")


def _token() -> str:
    t = os.environ.get("BOOKSTACK_TOKEN")
    if t:
        return t
    p = os.path.join(ROOT, ".secrets", "bookstack_token")
    if os.path.exists(p):
        return open(p).read().strip()
    raise RuntimeError("нет BOOKSTACK_TOKEN (ID:SECRET)")


def api(method: str, path: str, data: dict | None = None) -> dict:
    req = urllib.request.Request(URL + "/api/" + path.lstrip("/"), method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Authorization": "Token " + _token(), "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode()[:300]}")


def _find(kind: str, name: str) -> dict | None:
    q = urllib.parse.quote(f'name:"{name}"')
    for it in api("GET", f"{kind}?filter[name]={urllib.parse.quote(name)}&count=100").get("data", []):
        if it["name"] == name:
            return it
    return None


def shelf(name: str, description: str = "") -> dict:
    return _find("shelves", name) or api("POST", "shelves", {"name": name, "description": description})


def book(name: str, description: str = "", shelf_name: str | None = None) -> dict:
    b = _find("books", name) or api("POST", "books", {"name": name, "description": description})
    if shelf_name:
        s = shelf(shelf_name)
        full = api("GET", f"shelves/{s['id']}")
        ids = [x["id"] for x in full.get("books", [])]
        if b["id"] not in ids:
            api("PUT", f"shelves/{s['id']}", {"books": ids + [b["id"]]})
    return b


def page(book_id: int, name: str, markdown: str, tags: list[dict] | None = None) -> dict:
    """Создать или обновить страницу книги по имени."""
    existing = next((p for p in api("GET", f"pages?filter[book_id]={book_id}&count=200").get("data", []) if p["name"] == name), None)
    payload = {"book_id": book_id, "name": name, "markdown": markdown, "tags": tags or []}
    if existing:
        return api("PUT", f"pages/{existing['id']}", payload)
    return api("POST", "pages", payload)


def rename(kind: str, item_id: int, name: str) -> dict:
    return api("PUT", f"{kind}/{item_id}", {"name": name})


if __name__ == "__main__":
    for s in api("GET", "shelves").get("data", []):
        print("полка", s["id"], s["name"])
    for b in api("GET", "books").get("data", []):
        print("книга", b["id"], b["name"])
