"""Создать бота «Синтропия» в Mattermost через API. Запускать НА СЕРВЕРЕ:
  python3 mm_bot_setup.py <временный токен админа> <team-name>
Печатает токен бота в файл /var/www/syntropy.test-rms.ru/.mm_bot_token (chmod 600)."""
import json, sys, urllib.request

BASE = "http://127.0.0.1:3500/api/v4"
admin_tok, team_name = sys.argv[1], sys.argv[2]


def api(method, path, tok, data=None):
    req = urllib.request.Request(BASE + path, method=method, headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
                                 data=json.dumps(data).encode() if data is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise SystemExit(f"{method} {path} -> {e.code}: {body}")


bots = api("GET", "/bots?include_deleted=false", admin_tok)
bot = next((b for b in bots if b["username"] == "syntropy"), None)
if not bot:
    bot = api("POST", "/bots", admin_tok, {"username": "syntropy", "display_name": "Синтропия",
                                           "description": "Наблюдатель проекта: предлагает строки в таблицу требований"})
    print("бот создан")
else:
    print("бот уже есть")
uid = bot["user_id"]

team = api("GET", f"/teams/name/{team_name}", admin_tok)
api("POST", f"/teams/{team['id']}/members", admin_tok, {"team_id": team["id"], "user_id": uid})
ch = api("GET", f"/teams/{team['id']}/channels/name/town-square", admin_tok)
api("POST", f"/channels/{ch['id']}/members", admin_tok, {"user_id": uid})
print("бот в команде", team_name, "и в общем канале")

tok = api("POST", f"/users/{uid}/tokens", admin_tok, {"description": "observer"})
open("/var/www/syntropy.test-rms.ru/.mm_bot_token", "w").write(tok["token"])
import os; os.chmod("/var/www/syntropy.test-rms.ru/.mm_bot_token", 0o600)
print("токен бота записан в .mm_bot_token")

api("POST", f"/posts", tok["token"], {"channel_id": ch["id"], "message": "Привет! Я наблюдатель Синтропии. Пока только слушаю; строки в таблицу требований начну предлагать, когда подключат модель."})
print("приветствие отправлено")
