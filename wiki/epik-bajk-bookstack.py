"""Тот же эпик «Байк» в BookStack: полка «Пилот Политех» → книга «⌛Эпик. Байк» → страницы.
Текст страниц берётся из wiki/epik-bajk.py, чтобы сравнивать движки на одном материале."""
import os, sys, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(here), "tools"))
import bookstack

# подгружаем тексты из соседнего скрипта без публикации в Wiki.js
src = open(os.path.join(here, "epik-bajk.py"), encoding="utf-8").read()
src = src[:src.index("print(wikijs.publish")]
ns = {"__file__": os.path.join(here, "epik-bajk.py")}
exec(compile(src, "epik-bajk", "exec"), ns)
epic, req, etapy, E = ns["epic"], ns["req"], ns["etapy"], ns["E"]

# ссылки оглавления в BookStack другие: страницы книги
epic_bs = epic.replace(f"(/ru/{E}/t-velosiped)", "(#)").replace(f"(/ru/{E}/t-etapy)", "(#)")

b = bookstack.book("⌛Эпик. Байк", "Курьерский электровелосипед — пример проекта в структуре", shelf_name="Пилот Политех")
p0 = bookstack.page(b["id"], "Эпик", epic_bs, [{"name": "статус", "value": "в работе"}])
p1 = bookstack.page(b["id"], "⚠️Т. Требования к велосипеду", req, [{"name": "статус", "value": "частично"}])
p2 = bookstack.page(b["id"], "⌛Т. Этапы работ", etapy, [{"name": "статус", "value": "в работе"}])
# оглавление эпика — настоящими ссылками на страницы книги
base = bookstack.URL
epic_bs = epic.replace(f"(/ru/{E}/t-velosiped)", f"({base}/books/{b['slug']}/page/{p1['slug']})").replace(f"(/ru/{E}/t-etapy)", f"({base}/books/{b['slug']}/page/{p2['slug']})")
bookstack.page(b["id"], "Эпик", epic_bs, [{"name": "статус", "value": "в работе"}])
print(f"{base}/books/{b['slug']}")
