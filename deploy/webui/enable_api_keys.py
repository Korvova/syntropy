"""Включить API-ключи пользователей в Open WebUI через таблицу config."""
import json, sqlite3, time
con = sqlite3.connect("/app/backend/data/webui.db")
keys = [r[0] for r in con.execute("SELECT key FROM config WHERE key LIKE '%api_key%'")]
print("ключи:", keys)
for k, v in (("auth.enable_api_keys", True), ("auth.api_key.endpoint_restrictions", False)):
    if con.execute("SELECT 1 FROM config WHERE key=?", (k,)).fetchone():
        con.execute("UPDATE config SET value=?, updated_at=? WHERE key=?", (json.dumps(v), int(time.time()), k))
    else:
        con.execute("INSERT INTO config (key, value, updated_at) VALUES (?, ?, ?)", (k, json.dumps(v), int(time.time())))
con.commit()
con.execute("DELETE FROM config WHERE key='auth.api_key.enable'"); con.commit(); print({r[0]: r[1] for r in con.execute("SELECT key, value FROM config WHERE key LIKE 'auth.%api_key%'")})
