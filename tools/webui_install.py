"""Установка/обновление функции «Синтропия» в Open WebUI через API (ключ администратора в .secrets/webui_api_key).
Запуск: python tools/webui_install.py [--litellm-key KEY]
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = os.environ.get("WEBUI_URL", "https://syntropy.test-rms.ru")
KEY = open(os.path.join(ROOT, ".secrets", "webui_api_key")).read().strip()
FID = "syntropy"


def api(method: str, path: str, data: dict | None = None):
    req = urllib.request.Request(URL + path, method=method, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode()[:400]}")


code = open(os.path.join(ROOT, "agent", "syntropy_pipe.py"), encoding="utf-8").read()
meta = {"description": "Чат в рамках эпика: выбор эпика из Outline, контекст проекта, строки для таблицы требований", "manifest": {}}
try:
    existing = api("GET", f"/api/v1/functions/id/{FID}")
except RuntimeError:          # несуществующая функция отдаёт 401/404
    existing = None
if existing:
    api("POST", f"/api/v1/functions/id/{FID}/update", {"id": FID, "name": "Синтропия", "content": code, "meta": meta})
    print("функция обновлена")
else:
    api("POST", "/api/v1/functions/create", {"id": FID, "name": "Синтропия", "content": code, "meta": meta})
    print("функция создана")

# valves: ключи Outline и шлюза
litellm_key = ""
if "--litellm-key" in sys.argv:
    litellm_key = sys.argv[sys.argv.index("--litellm-key") + 1]
valves = {
    "OUTLINE_URL": os.environ.get("OUTLINE_URL", "https://wiki.syntropy.test-rms.ru"),
    "OUTLINE_TOKEN": open(os.path.join(ROOT, ".secrets", "outline_token")).read().strip(),
    "COLLECTION": "Синтропия",
    "LITELLM_URL": "http://litellm:4000/v1",
    "LITELLM_KEY": litellm_key,
    "MODEL": "astra",
}
api("POST", f"/api/v1/functions/id/{FID}/valves/update", valves)
print("valves записаны", "с ключом шлюза" if litellm_key else "без ключа шлюза")

# включить и сделать глобальной (видна всем)
f = api("GET", f"/api/v1/functions/id/{FID}")
if not f.get("is_active"):
    api("POST", f"/api/v1/functions/id/{FID}/toggle"); print("включена")
f = api("GET", f"/api/v1/functions/id/{FID}")
if not f.get("is_global"):
    api("POST", f"/api/v1/functions/id/{FID}/toggle/global"); print("глобальная")
print("готово:", {k: f.get(k) for k in ("id", "name", "type", "is_active", "is_global")})
