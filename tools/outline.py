"""Клиент Outline API: коллекция → документ → вложенные документы (инициатива → эпик → Т. страницы).

Токен: OUTLINE_TOKEN или файл .secrets/outline_token. Текст документов — markdown.
"""
from __future__ import annotations
import json, os, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = os.environ.get("OUTLINE_URL", "https://wiki.syntropy.test-rms.ru")


def _token() -> str:
    t = os.environ.get("OUTLINE_TOKEN")
    if t:
        return t
    p = os.path.join(ROOT, ".secrets", "outline_token")
    if os.path.exists(p):
        return open(p).read().strip()
    raise RuntimeError("нет OUTLINE_TOKEN")


def api(method: str, data: dict | None = None) -> dict:
    req = urllib.request.Request(URL + "/api/" + method, data=json.dumps(data or {}).encode(),
                                 headers={"Authorization": "Bearer " + _token(), "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method}: {e.code} {e.read().decode()[:300]}")


def collection(name: str, description: str = "") -> dict:
    for c in api("collections.list", {"limit": 100})["data"]:
        if c["name"] == name:
            return c
    return api("collections.create", {"name": name, "description": description})["data"]


def find_doc(collection_id: str, title: str, parent_id: str | None = None) -> dict | None:
    docs = api("documents.list", {"collectionId": collection_id, "parentDocumentId": parent_id, "limit": 100})["data"]
    return next((d for d in docs if d["title"] == title), None)


def publish(collection_id: str, title: str, text: str, parent_id: str | None = None, doc_id: str | None = None) -> dict:
    """Создать или обновить документ (по id, иначе по заголовку внутри родителя). Возвращает документ с url."""
    d = api("documents.info", {"id": doc_id})["data"] if doc_id else find_doc(collection_id, title, parent_id)
    if d:
        return api("documents.update", {"id": d["id"], "title": title, "text": text, "publish": True})["data"]
    return api("documents.create", {"collectionId": collection_id, "parentDocumentId": parent_id, "title": title, "text": text, "publish": True})["data"]


def link(doc: dict) -> str:
    return URL + doc["url"]


if __name__ == "__main__":
    for c in api("collections.list")["data"]:
        print("коллекция", c["id"], c["name"])
    for d in api("documents.list", {"limit": 100})["data"]:
        print("документ", d["id"], d["title"], "→", d.get("parentDocumentId"))
