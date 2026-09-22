"""
title: Синтропия
author: Корнилов Владимир
version: 0.1.2
description: Чат в рамках эпика. Первое сообщение нового чата — окно «Выберите эпик» со списком из базы знаний Outline; без эпика модель не вызывается. Дальше в каждый запрос подкладываются эпик и его страницы требований.
"""
from __future__ import annotations
import json
import os
import time

import requests
from pydantic import BaseModel, Field


EPIC_DIALOG_JS = r"""// Окно выбора эпика с выпадающим списком. Выполняется в браузере через событие execute.
// Подстановка из функции: __EPICS__ — JSON [{id, title}]; возвращает Promise<string>: "<номер>" | "новый: <название>" | "".
(function () {
  const epics = __EPICS__;
  return new Promise((resolve) => {
    const old = document.getElementById("syntropy-epic-dialog");
    if (old) old.remove();
    const wrap = document.createElement("div");
    wrap.id = "syntropy-epic-dialog";
    wrap.style.cssText = "position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;font-family:inherit";
    const box = document.createElement("div");
    box.style.cssText = "background:#fff;color:#111;border-radius:16px;padding:22px 24px;width:min(520px,92vw);box-shadow:0 20px 60px rgba(0,0,0,.35)";
    const dark = document.documentElement.classList.contains("dark");
    if (dark) box.style.cssText += ";background:#1f2023;color:#eee";
    const field = dark ? "background:#2a2b2f;color:#eee;border:1px solid #444" : "background:#fff;color:#111;border:1px solid #ccc";
    box.innerHTML =
      '<div style="font-size:18px;font-weight:600;margin-bottom:6px">В рамках какого эпика работаем?</div>' +
      '<div style="font-size:13px;opacity:.75;margin-bottom:14px">Без эпика Синтропия не работает: всё, что обсуждается, ложится в его структуру.</div>' +
      '<label style="font-size:13px;display:block;margin-bottom:4px">Эпик</label>' +
      '<select id="syn-sel" style="width:100%;padding:10px 12px;border-radius:10px;font-size:15px;' + field + '"></select>' +
      '<div id="syn-newwrap" style="display:none;margin-top:12px"><label style="font-size:13px;display:block;margin-bottom:4px">Название нового эпика</label>' +
      '<input id="syn-new" placeholder="Байк, Батарея, Перчатка…" style="width:100%;padding:10px 12px;border-radius:10px;font-size:15px;box-sizing:border-box;' + field + '"></div>' +
      '<div style="display:flex;gap:10px;justify-content:flex-end;margin-top:18px">' +
      '<button id="syn-cancel" style="padding:9px 18px;border-radius:999px;border:1px solid #bbb;background:transparent;color:inherit;cursor:pointer">Отменить</button>' +
      '<button id="syn-ok" style="padding:9px 18px;border-radius:999px;border:0;background:#111;color:#fff;cursor:pointer">Работать</button></div>';
    wrap.appendChild(box);
    document.body.appendChild(wrap);
    const sel = box.querySelector("#syn-sel");
    epics.forEach((e, i) => { const o = document.createElement("option"); o.value = String(i + 1); o.textContent = e.title; sel.appendChild(o); });
    const on = document.createElement("option"); on.value = "0"; on.textContent = "＋ Создать новый эпик…"; sel.appendChild(on);
    const neww = box.querySelector("#syn-newwrap"), inp = box.querySelector("#syn-new");
    sel.onchange = () => { neww.style.display = sel.value === "0" ? "block" : "none"; if (sel.value === "0") inp.focus(); };
    const done = (v) => { wrap.remove(); resolve(v); };
    box.querySelector("#syn-cancel").onclick = () => done("");
    box.querySelector("#syn-ok").onclick = () => done(sel.value === "0" ? (inp.value.trim() ? "новый: " + inp.value.trim() : "") : sel.value);
    inp.onkeydown = (ev) => { if (ev.key === "Enter") box.querySelector("#syn-ok").click(); };
    sel.focus();
  });
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
        cid = self._collection_id()
        docs = self._ol("documents.list", {"collectionId": cid, "parentDocumentId": None, "limit": 100})["data"]
        return [d for d in docs if "Эпик" in d["title"] and not d.get("template") and not d["title"].startswith("Шаблон")]

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
            menu = "\n".join([f"{i + 1}. {d['title']}" for i, d in enumerate(epics)] + ["0. Создать новый эпик"])

            # 1) ответ уже в тексте сообщения: «3» или «новый: Батарея»
            choice, new_name = "", ""
            if user_msg.isdigit():
                choice = user_msg
            elif user_msg.lower().startswith("новый:"):
                choice, new_name = "0", user_msg.split(":", 1)[1].strip()
            # 2) иначе — своё окно с выпадающим списком (скрипт в браузере), запас — стандартное поле
            if not choice and __event_call__ and in_ui:
                res = None
                try:
                    code = EPIC_DIALOG_JS.replace("__EPICS__", json.dumps([{"id": d["id"], "title": d["title"]} for d in epics], ensure_ascii=False))
                    res = await __event_call__({"type": "execute", "data": {"code": code}})
                except Exception:
                    res = None
                if isinstance(res, dict):
                    res = None
                if isinstance(res, str):
                    res = res.strip()
                    if res.isdigit():
                        choice = res
                    elif res.lower().startswith("новый:"):
                        choice, new_name = "0", res.split(":", 1)[1].strip()
                    else:
                        res = None
                if res is None and not choice:
                    try:
                        res = await __event_call__({"type": "input", "data": {
                        "title": "В рамках какого эпика работаем?",
                        "message": "Без эпика Синтропия не работает: всё, что обсуждается, ложится в его структуру.\n\n" + menu,
                            "placeholder": "номер эпика или «новый: название»"}})
                    except Exception:
                        res = None
                    if isinstance(res, str):
                        res = res.strip()
                        if res.isdigit():
                            choice = res
                        elif res.lower().startswith("новый:"):
                            choice, new_name = "0", res.split(":", 1)[1].strip()
                        elif res:
                            choice, new_name = "0", res      # написали просто название
            if not choice:
                return "**Выберите эпик**, без него работать нельзя. Напишите номер из списка или «новый: название»:\n\n" + menu
            if not in_ui:
                return "Привязать эпик можно только к чату в интерфейсе. Список эпиков:\n\n" + menu

            if choice == "0":
                if not new_name and __event_call__:
                    res = await __event_call__({"type": "input", "data": {"title": "Название нового эпика", "message": "Коротко, как проект: «Байк», «Батарея», «Перчатка».", "placeholder": "название"}})
                    new_name = res.strip() if isinstance(res, str) else ""
                if not new_name:
                    return "Название не задано. Напишите «новый: название» или номер эпика из списка:\n\n" + menu
                d = self._create_epic(new_name)
                bound = {"id": d["id"], "title": d["title"], "url": self.valves.OUTLINE_URL + d["url"], "since": int(time.time())}
                st[chat_id] = bound
                self._save(st)
                return (f"Создан эпик **{d['title']}**: {bound['url']}\n\nЧат привязан к нему. Заполните на странице суть и точки проекта, "
                        f"а требования начнут появляться по ходу работы. Что делаем?")

            idx = int(choice) - 1
            if idx < 0 or idx >= len(epics):
                return "Такого номера нет. Список эпиков:\n\n" + menu
            d = epics[idx]
            bound = {"id": d["id"], "title": d["title"], "url": self.valves.OUTLINE_URL + d["url"], "since": int(time.time())}
            st[chat_id] = bound
            self._save(st)
            if __event_emitter__:
                await __event_emitter__({"type": "status", "data": {"description": f"Эпик: {d['title']}", "done": True}})
            if not user_msg or user_msg.isdigit():
                return f"Работаем в рамках **{d['title']}** ({bound['url']}). Что делаем?"

        # ---- работа в рамках эпика: контекст + модель ----
        try:
            ctx = self._epic_context(bound["id"])
        except Exception as e:
            ctx = f"(не удалось прочитать эпик: {e})"
        system = (
            "Ты — агент Синтропии, ведёшь проект вместе с человеком. Всё обсуждение идёт в рамках эпика ниже. "
            "Отвечай по делу, по-русски. Если в разговоре появляется новое требование, решение, урок (грабли) или смена статуса — "
            "в конце ответа добавь блок «Для таблицы требований:» со строками вида "
            "«<раздел> | <требование до 80 символов> | <описание до 250> | <урок до 300 или пусто> | <статус>». "
            "Не выдумывай требований, которых не было в разговоре.\n\n"
            f"Эпик: {bound['title']} — {bound['url']}\n\n=== СОДЕРЖИМОЕ ЭПИКА И СТРАНИЦ ===\n{ctx}"
        )
        llm_messages = [{"role": "system", "content": system}] + [m for m in messages if m.get("role") != "system"]
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": f"Эпик: {bound['title']}", "done": False}})

        def gen():
            for chunk in self._stream(llm_messages):
                yield chunk
        return gen()
