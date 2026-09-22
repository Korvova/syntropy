"""Клиент Wiki.js (GraphQL): создать/обновить страницу по пути, список страниц.

Токен: переменная WIKIJS_TOKEN или файл .secrets/wikijs_token рядом с репозиторием.
Путь страницы задаёт вложенность: `epik-bajk` — эпик, `epik-bajk/t-velosiped` — его подстраница.
"""
from __future__ import annotations
import json, os, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = os.environ.get("WIKIJS_URL", "https://wiki.syntropy.test-rms.ru")
LOCALE = "ru"


def _token() -> str:
    t = os.environ.get("WIKIJS_TOKEN")
    if t:
        return t
    p = os.path.join(ROOT, ".secrets", "wikijs_token")
    if os.path.exists(p):
        return open(p).read().strip()
    raise RuntimeError("нет WIKIJS_TOKEN")


def gql(query: str, variables: dict | None = None) -> dict:
    req = urllib.request.Request(URL + "/graphql", data=json.dumps({"query": query, "variables": variables or {}}).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + _token()})
    out = json.load(urllib.request.urlopen(req, timeout=120))
    if out.get("errors"):
        raise RuntimeError(out["errors"][0]["message"])
    return out["data"]


def list_pages() -> list[dict]:
    return gql("{ pages { list { id path locale title updatedAt } } }")["pages"]["list"]


def find(path: str) -> dict | None:
    return next((p for p in list_pages() if p["path"] == path and p["locale"] == LOCALE), None)


def publish(path: str, title: str, content: str, description: str = "", tags: list[str] | None = None) -> str:
    """Создать или обновить страницу. Возвращает публичный URL."""
    page = find(path)
    if page:
        m = """mutation($id:Int!,$content:String!,$title:String!,$description:String!,$tags:[String]!){ pages { update(id:$id, content:$content, title:$title, description:$description, tags:$tags, isPublished:true, editor:"markdown") { responseResult { succeeded message } } } }"""
        res = gql(m, {"id": page["id"], "content": content, "title": title, "description": description, "tags": tags or []})["pages"]["update"]
    else:
        m = """mutation($path:String!,$content:String!,$title:String!,$description:String!,$tags:[String]!){ pages { create(path:$path, locale:"ru", content:$content, title:$title, description:$description, tags:$tags, isPublished:true, isPrivate:false, editor:"markdown") { responseResult { succeeded message } } } }"""
        res = gql(m, {"path": path, "content": content, "title": title, "description": description, "tags": tags or []})["pages"]["create"]
    if not res["responseResult"]["succeeded"]:
        raise RuntimeError(res["responseResult"]["message"])
    return f"{URL}/{LOCALE}/{path}"


def delete(path: str) -> bool:
    page = find(path)
    if not page:
        return False
    gql("mutation($id:Int!){ pages { delete(id:$id) { responseResult { succeeded } } } }", {"id": page["id"]})
    return True


if __name__ == "__main__":
    for p in list_pages():
        print(p["id"], p["locale"], p["path"], "—", p["title"])
