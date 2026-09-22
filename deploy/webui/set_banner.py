"""Баннер со ссылкой на базу знаний в Open WebUI — через таблицу config (key/value JSON), без входа в админку.
Запуск на сервере: docker exec -i syntropy-webui python3 - < set_banner.py; затем docker restart syntropy-webui
"""
import json, sqlite3, time, uuid

DB = "/app/backend/data/webui.db"
BANNER = {"id": str(uuid.uuid4()), "type": "info", "title": "База знаний",
          "content": "База знаний проектов: [wiki.syntropy.test-rms.ru](https://wiki.syntropy.test-rms.ru)",
          "dismissible": False, "timestamp": int(time.time())}

con = sqlite3.connect(DB)
keys = [r[0] for r in con.execute("SELECT key FROM config WHERE key LIKE '%banner%'")]
print("ключи с banner:", keys)
key = keys[0] if keys else "ui.banners"
row = con.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
banners = [b for b in (json.loads(row[0]) if row else []) if b.get("title") != "База знаний"]
banners.append(BANNER)
if row:
    con.execute("UPDATE config SET value=?, updated_at=? WHERE key=?", (json.dumps(banners), int(time.time()), key))
else:
    con.execute("INSERT INTO config (key, value, updated_at) VALUES (?, ?, ?)", (key, json.dumps(banners), int(time.time())))
con.commit()
print(key, "→", [b["title"] for b in banners])
