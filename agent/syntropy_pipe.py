"""
title: Синтропия
author: Корнилов Владимир
version: 0.2.2
description: Чат в рамках эпика. Первое сообщение нового чата — окно «Выберите эпик» со списком из базы знаний Outline; без эпика модель не вызывается. Дальше в каждый запрос подкладываются эпик и его страницы требований.
"""
from __future__ import annotations
import json
import os
import time

import requests
from pydantic import BaseModel, Field


EPIC_DIALOG_JS = r"""// Окно выбора эпика: выпадающий список инициатив и эпиков + поле нового эпика.
// Выполняется в браузере (событие execute). Выбор отправляется в чат как сообщение — ответ окна чат не ждёт.
(function () {
  const epics = __EPICS__;   // [{title, initiative}]
  const old = document.getElementById("syntropy-epic-dialog");
  if (old) old.remove();
  const dark = document.documentElement.classList.contains("dark");
  const field = dark ? "background:#2a2b2f;color:#eee;border:1px solid #444" : "background:#fff;color:#111;border:1px solid #ccc";
  const wrap = document.createElement("div");
  wrap.id = "syntropy-epic-dialog";
  wrap.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;font-family:inherit";
  const box = document.createElement("div");
  box.style.cssText = "border-radius:16px;padding:22px 24px;width:min(560px,92vw);box-shadow:0 20px 60px rgba(0,0,0,.35);" + (dark ? "background:#1f2023;color:#eee" : "background:#fff;color:#111");
  const inits = Array.from(new Set(epics.map((e) => e.initiative))).sort();
  box.innerHTML =
    '<div style="font-size:18px;font-weight:600;margin-bottom:6px">В рамках какого эпика работаем?</div>' +
    '<div style="font-size:13px;opacity:.75;margin-bottom:14px">Без эпика Синтропия не работает: всё, что обсуждается, ложится в его структуру.</div>' +
    '<label style="font-size:13px;display:block;margin-bottom:4px">Инициатива</label>' +
    '<select id="syn-init" style="width:100%;padding:10px 12px;border-radius:10px;font-size:15px;margin-bottom:12px;' + field + '"></select>' +
    '<label style="font-size:13px;display:block;margin-bottom:4px">Эпик</label>' +
    '<select id="syn-sel" style="width:100%;padding:10px 12px;border-radius:10px;font-size:15px;' + field + '"></select>' +
    '<div id="syn-newwrap" style="display:none;margin-top:12px"><label style="font-size:13px;display:block;margin-bottom:4px">Название нового эпика</label>' +
    '<input id="syn-new" placeholder="Байк, Батарея, Перчатка…" style="width:100%;padding:10px 12px;border-radius:10px;font-size:15px;box-sizing:border-box;' + field + '"></div>' +
    '<div style="display:flex;gap:10px;justify-content:flex-end;margin-top:18px">' +
    '<button id="syn-cancel" style="padding:9px 18px;border-radius:999px;border:1px solid #bbb;background:transparent;color:inherit;cursor:pointer">Отменить</button>' +
    '<button id="syn-ok" style="padding:9px 18px;border-radius:999px;border:0;background:#111;color:#fff;cursor:pointer">Работать</button></div>';
  wrap.appendChild(box);
  document.body.appendChild(wrap);
  const initSel = box.querySelector("#syn-init"), sel = box.querySelector("#syn-sel");
  const neww = box.querySelector("#syn-newwrap"), inp = box.querySelector("#syn-new");
  const oAll = document.createElement("option"); oAll.value = ""; oAll.textContent = "Все инициативы"; initSel.appendChild(oAll);
  inits.forEach((i) => { const o = document.createElement("option"); o.value = i; o.textContent = i; initSel.appendChild(o); });
  function fill() {
    sel.innerHTML = "";
    epics.filter((e) => !initSel.value || e.initiative === initSel.value).forEach((e) => {
      const o = document.createElement("option"); o.value = e.title; o.textContent = (initSel.value ? "" : e.initiative.replace("Инициатива. ", "") + " · ") + e.title; sel.appendChild(o);
    });
    const on = document.createElement("option"); on.value = "__new__"; on.textContent = "＋ Создать новый эпик…"; sel.appendChild(on);
    neww.style.display = "none";
  }
  initSel.onchange = fill; fill();
  sel.onchange = () => { neww.style.display = sel.value === "__new__" ? "block" : "none"; if (sel.value === "__new__") inp.focus(); };
  function send(text) {
    wrap.remove();
    if (!text) return;
    const el = document.getElementById("chat-input");
    if (!el) { alert("Не нашёл поле ввода. Напишите в чат: " + text); return; }
    el.focus();
    if (el.tagName === "TEXTAREA") { el.value = text; el.dispatchEvent(new Event("input", { bubbles: true })); }
    else { document.execCommand("selectAll", false, null); document.execCommand("insertText", false, text); }
    setTimeout(() => {
      const btn = document.getElementById("send-message-button");
      if (btn) btn.click();
      else el.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true }));
    }, 150);
  }
  box.querySelector("#syn-cancel").onclick = () => wrap.remove();
  box.querySelector("#syn-ok").onclick = () => send(sel.value === "__new__" ? (inp.value.trim() ? "новый: " + inp.value.trim() : "") : sel.value);
  inp.onkeydown = (ev) => { if (ev.key === "Enter") box.querySelector("#syn-ok").click(); };
  sel.focus();
})();
"""


class Pipe:
    class Valves(BaseModel):
        OUTLINE_URL: str = Field(default="https://wiki.syntropy.test-rms.ru", description="Адрес Outline")
        OUTLINE_TOKEN: str = Field(default="", description="API-ключ Outline")
        COLLECTION: str = Field(default="Синтропия", description="Коллекция, где лежат эпики")
        LITELLM_URL: str = Field(default="http://litellm:4000/v1", description="Шлюз к моделям (OpenAI-совместимый)")
        LITELLM_KEY: str = Field(default="", description="Ключ шлюза (LITELLM_MASTER_KEY)")
        MODEL: str = Field(default="astra", description="Модель в шлюзе")
        STATE_FILE: str = Field(default="/app/backend/data/syntropy_chats.json", description="Привязки чат → эпик")
        MAX_CONTEXT_CHARS: int = Field(default=24000, description="Сколько символов эпика и страниц подкладывать модели")

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        return [{"id": "syntropy", "name": "Синтропия"}]

    # ---------- состояние: чат → эпик ----------
    def _load(self) -> dict:
        try:
            with open(self.valves.STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, st: dict) -> None:
        os.makedirs(os.path.dirname(self.valves.STATE_FILE), exist_ok=True)
        with open(self.valves.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)

    # ---------- Outline ----------
    def _ol(self, method: str, data: dict | None = None) -> dict:
        r = requests.post(f"{self.valves.OUTLINE_URL}/api/{method}", json=data or {},
                          headers={"Authorization": f"Bearer {self.valves.OUTLINE_TOKEN}"}, timeout=30)
        r.raise_for_status()
        return r.json()

    def _collection_id(self) -> str:
        for c in self._ol("collections.list", {"limit": 100})["data"]:
            if c["name"] == self.valves.COLLECTION:
                return c["id"]
        raise RuntimeError(f"в Outline нет коллекции «{self.valves.COLLECTION}»")

    def _epics(self) -> list[dict]:
        """Все эпики по всем инициативам: [{id, title, url, initiative}]."""
        out = []
        for c in self._ol("collections.list", {"limit": 100})["data"]:
            docs = self._ol("documents.list", {"collectionId": c["id"], "parentDocumentId": None, "limit": 100})["data"]
            for d in docs:
                if "Эпик" in d["title"] and not d.get("template") and not d["title"].startswith("Шаблон"):
                    out.append({"id": d["id"], "title": d["title"], "url": d["url"], "initiative": c["name"]})
        return out

    def _epic_context(self, epic_id: str) -> str:
        ep = self._ol("documents.info", {"id": epic_id})["data"]
        parts = [f"# {ep['title']}\n{ep['text']}"]
        for ch in self._ol("documents.list", {"parentDocumentId": epic_id, "limit": 50})["data"]:
            parts.append(f"\n# {ch['title']}\n{ch['text']}")
        return "\n".join(parts)[: self.valves.MAX_CONTEXT_CHARS]

    def _create_epic(self, name: str) -> dict:
        cid = self._collection_id()
        text = ("**Что это.** (два абзаца: что за проект, для кого, чем отличается)\n\n**Зачем.** (какой результат и по какому признаку поймём, что получилось)\n\n"
                "## Текущее состояние\n\n| Узел | Состояние |\n|---|---|\n| … | ⬜ Не начато |\n\n"
                "## Точки проекта\n\n| Точка | Где | Что там |\n|---|---|---|\n| Чат с ИИ | Синтропия | обсуждение с агентом |\n\n"
                "## Команда\n\n| Имя | Роль | Битрикс24 | Telegram | Куда писать |\n|---|---|---|---|---|\n\n"
                "## Оглавление\n\n* Т. Требования — появятся по мере работы\n")
        return self._ol("documents.create", {"collectionId": cid, "title": f"⌛Эпик. {name}", "text": text, "publish": True})["data"]

    # ---------- модель ----------
    def _stream(self, messages: list[dict]):
        r = requests.post(f"{self.valves.LITELLM_URL}/chat/completions",
                          headers={"Authorization": f"Bearer {self.valves.LITELLM_KEY}", "Content-Type": "application/json"},
                          json={"model": self.valves.MODEL, "messages": messages, "stream": True}, stream=True, timeout=300)
        if r.status_code != 200:
            yield f"\n\n_Модель недоступна ({r.status_code}): {r.text[:300]}_"
            return
        for line in r.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            payload = line[6:]
            if payload.strip() == b"[DONE]":
                break
            try:
                delta = json.loads(payload)["choices"][0]["delta"].get("content")
            except Exception:
                continue
            if delta:
                yield delta

    @staticmethod
    def _text(content) -> str:
        if isinstance(content, list):
            return " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        return content or ""

    # ---------- главный вход ----------
    async def pipe(self, body: dict, __user__: dict | None = None, __metadata__: dict | None = None,
                   __event_emitter__=None, __event_call__=None):
        md = __metadata__ or {}
        chat_id = md.get("chat_id") or ""
        in_ui = bool(chat_id)
        messages = body.get("messages", [])
        user_msg = self._text(next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")).strip()
        st = self._load()
        bound = st.get(chat_id) if in_ui else None

        if user_msg.lower() in ("/эпик", "/epic", "сменить эпик"):
            bound = None

        if not bound:
            try:
                epics = self._epics()
            except Exception as e:
                return f"Не могу прочитать список эпиков из базы знаний: {e}"
            pend = st.get(f"{chat_id}:pending", {}) if in_ui else {}
            low = user_msg.lower()

            async def buttons(items):
                if __event_emitter__ and in_ui:
                    await __event_emitter__({"type": "chat:message:follow_ups", "data": {"follow_ups": items[:16]}})

            def bind(d):
                b = {"id": d["id"], "title": d["title"], "url": self.valves.OUTLINE_URL + d["url"], "initiative": d["initiative"], "since": int(time.time())}
                st[chat_id] = b
                st.pop(f"{chat_id}:pending", None)
                self._save(st)
                return b

            # 1) прямое попадание: кнопка с названием эпика, «найти: …», «новый: …»
            hit = [d for d in epics if user_msg == d["title"]]
            if len(hit) == 1:
                bound = bind(hit[0])
                if __event_emitter__:
                    await __event_emitter__({"type": "status", "data": {"description": f"Эпик: {bound['title']}", "done": True}})
                return f"Работаем в рамках **{bound['title']}** ({bound['url']}), инициатива «{bound['initiative']}». Что делаем?"
            if low.startswith("новый:"):
                if not in_ui:
                    return "Создавать эпик можно только из чата в интерфейсе."
                name = user_msg.split(":", 1)[1].strip()
                if not name:
                    return "Как назовём новый эпик? Напишите «новый: название», например «новый: Батарея»."
                d = self._create_epic(name)
                bound = bind({"id": d["id"], "title": d["title"], "url": d["url"], "initiative": self.valves.COLLECTION})
                return (f"Создан эпик **{d['title']}**: {bound['url']}\n\nЧат привязан к нему. Заполните на странице суть и точки проекта, "
                        f"а требования начнут появляться по ходу работы. Что делаем?")
            if low in ("создать новый эпик", "новый эпик"):
                return "Как назовём новый эпик? Напишите «новый: название», например «новый: Батарея»."
            if low.startswith("найти:") or low.startswith("поиск:"):
                q = user_msg.split(":", 1)[1].strip().lower()
                found = [d for d in epics if q and q in d["title"].lower()]
                if not found:
                    return f"По «{q}» ничего не нашёл. Напишите иначе или выберите инициативу."
                await buttons([d["title"] for d in found])
                return "Нашёл:\n\n" + "\n".join(f"• {d['title']} — {d['initiative']}" for d in found[:30])

            # 2) инициатива выбрана (кнопкой или ранее) — показать её эпики
            initiatives = sorted({d["initiative"] for d in epics})
            chosen = pend.get("initiative")
            if user_msg in initiatives:
                chosen = user_msg
            if chosen:
                if in_ui:
                    st[f"{chat_id}:pending"] = {"initiative": chosen}
                    self._save(st)
                mine = [d for d in epics if d["initiative"] == chosen]
                await buttons([d["title"] for d in mine] + ["Другая инициатива", "Создать новый эпик"])
                return (f"**{chosen}**: выберите эпик кнопкой ниже, напишите его название или «новый: название».\n\n"
                        + "\n".join(f"• {d['title']}" for d in mine))

            # 3) начало: своё окно со списком (в браузере) — выбор придёт следующим сообщением; кнопки под ответом как запас
            if __event_call__ and in_ui:
                try:
                    code = EPIC_DIALOG_JS.replace("__EPICS__", json.dumps([{"title": d["title"], "initiative": d["initiative"]} for d in epics], ensure_ascii=False))
                    await __event_call__({"type": "execute", "data": {"code": code}})
                except Exception:
                    pass
            if len(epics) <= 8:
                await buttons([d["title"] for d in epics] + ["Создать новый эпик"])
                return ("**В рамках какого эпика работаем?** Без эпика Синтропия не работает: всё, что обсуждается, ложится в его структуру.\n\n"
                        "Нажмите кнопку ниже или напишите название эпика, либо «новый: название».\n\n"
                        + "\n".join(f"• {d['title']}" for d in epics) + "\n• Создать новый эпик")
            counts = {i: sum(1 for d in epics if d["initiative"] == i) for i in initiatives}
            await buttons(initiatives + ["Создать новый эпик"])
            return ("**В рамках какого эпика работаем?** Без эпика Синтропия не работает: всё, что обсуждается, ложится в его структуру.\n\n"
                    f"Эпиков сейчас {len(epics)}. Сначала выберите инициативу кнопкой ниже, или напишите «найти: часть названия», или «новый: название».\n\n"
                    + "\n".join(f"• {i} — {counts[i]}" for i in initiatives))

        # ---- работа в рамках эпика: контекст + модель ----
        try:
            ctx = self._epic_context(bound["id"])
        except Exception as e:
            ctx = f"(не удалось прочитать эпик: {e})"
        system = (
            "Ты — агент Синтропии, ведёшь проект вместе с человеком. Всё обсуждение идёт в рамках эпика ниже. "
            "Отвечай по делу, по-русски. Если в разговоре появляется новое требование, решение, урок (грабли) или смена статуса — "
            "в конце ответа добавь блок «Для таблицы требований:» со строками вида "
            "«<раздел> | <требование до 80 символов> | <описание до 250> | <урок до 300 или пусто> ↳ чат с ИИ, <имя>, <дата> | <статус>». "
            "ПРАВИЛО: нет решения — нет требования. Блок добавляй только когда человек явно принял решение, зафиксировал факт или отказался от чего-то. "
            "Вопросы, варианты, «подумаем», незавершённое обсуждение, переписка без итога — блок НЕ добавляется вообще. "
            "Одно реальное решение — одна строка; если требование уже есть в таблице, предлагай изменение существующей строки, а не новую. "
            "Сомневаешься — не пиши строку, а спроси одним вопросом, фиксировать ли.\n\n"
            f"Эпик: {bound['title']} — {bound['url']}\n\n=== СОДЕРЖИМОЕ ЭПИКА И СТРАНИЦ ===\n{ctx}"
        )
        llm_messages = [{"role": "system", "content": system}] + [m for m in messages if m.get("role") != "system"]
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": f"Эпик: {bound['title']}", "done": False}})

        def gen():
            for chunk in self._stream(llm_messages):
                yield chunk
        return gen()
