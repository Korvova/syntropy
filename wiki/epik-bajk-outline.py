"""Эпик «Байк» в Outline: коллекция «Синтропия» → «⌛Эпик. Байк» → вложенные Т. страницы.
Тексты берутся из wiki/epik-bajk.py (общий источник для всех движков)."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(here), "tools"))
import outline

src = open(os.path.join(here, "epik-bajk.py"), encoding="utf-8").read()
src = src[:src.index("print(wikijs.publish")]
ns = {"__file__": os.path.join(here, "epik-bajk.py")}
exec(compile(src, "epik-bajk", "exec"), ns)
epic, req, etapy, E = ns["epic"], ns["req"], ns["etapy"], ns["E"]

col = outline.collection("Синтропия")
# эпик: если пользователь уже создал «Эпик. Байк» руками — переиспользуем его, чтобы не плодить копии
existing = outline.find_doc(col["id"], "Эпик. Байк") or outline.find_doc(col["id"], "⌛Эпик. Байк")
ep = outline.publish(col["id"], "⌛Эпик. Байк", epic, doc_id=existing["id"] if existing else None)
p1 = outline.publish(col["id"], "⚠️Т. Требования к велосипеду", req, parent_id=ep["id"])
p2 = outline.publish(col["id"], "⌛Т. Этапы работ", etapy, parent_id=ep["id"])
# оглавление эпика — настоящими ссылками Outline
epic_o = epic.replace(f"(/ru/{E}/t-velosiped)", f"({outline.link(p1)})").replace(f"(/ru/{E}/t-etapy)", f"({outline.link(p2)})")
ep = outline.publish(col["id"], "⌛Эпик. Байк", epic_o, doc_id=ep["id"])
print(outline.link(ep)); print(outline.link(p1)); print(outline.link(p2))
