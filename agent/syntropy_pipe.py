"""
title: Синтропия
author: Корнилов Владимир
version: 0.1.0
description: Чат в рамках эпика. Первое сообщение нового чата — окно «Выберите эпик» со списком из базы знаний Outline; без эпика модель не вызывается. Дальше в каждый запрос подкладываются эпик и его страницы требований.
"""
from __future__ import annotations
import json
import os
import re
import time
from typing import AsyncGenerator, Optional

import requests
from pydantic import BaseModel, Field


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
        return [d for d in docs if "Эпик" in d["title"] and not d.get("template")]

    def _epic_context(self, epic_id: str) -> str:
        ep = self._ol("documents.info", {"id": epic_id})["data"]
        parts = [f"# {ep['title']}\n{ep['text']}"]
        for ch in self._ol("documents.list", {"parentDocumentId": epic_id, "limit": 50})["data"]:
            parts.append(f"\n# {ch['title']}\n{ch['text']}")
        ctx = "\n".join(parts)
        return ctx[: self.valves.MAX_CONTEXT_CHARS]

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

    # ---------- главный вход ----------
    async def pipe(self, body: dict, __user__: dict | None = None, __metadata__: dict | None = None,
                   __event_emitter__=None, __event_call__=None):
        md = __metadata__ or {}
        chat_id = md.get("chat_id") or "no-chat"
        messages = body.get("messages", [])
        user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if isinstance(user_msg, list):  # мультимодальные сообщения
            user_msg = " ".join(p.get("text", "") for p in user_msg if isinstance(p, dict))
        st = self._load()
        bound = st.get(chat_id)

        # смена эпика по команде
        if user_msg.strip().lower() in ("/эпик", "/epic", "сменить эпик"):
            bound = None

        if not bound:
            try:
                epics = self._epics()
            except Exception as e:
                return f"Не могу прочитать список эпиков из базы знаний: {e}"
            lines = [f"{i + 1}. {d['title']}" for i, d in enumerate(epics)]
            lines.append("0. Создать новый эпик")
            menu = "\n".join(lines)
            choice = None
            if __event_call__:
                try:
                    choice = await __event_call__({"type": "input", "data": {
                        "title": "В рамках какого эпика работаем?",
                        "message": "Без эпика Синтропия не работает: всё, что обсуждается, ложится в его структуру.\n\n" + menu,
                        "placeholder": "номер эпика"}})
                except Exception:
                    choice = None
            if choice is None or str(choice).strip() == "":
                return "**Выберите эпик**, без него работать нельзя. Напишите номер из списка:\n\n" + menu
            choice = str(choice).strip()
            if choice == "0" or not choice.isdigit():
                name = choice if not choice.isdigit() else None
                if not name and __event_call__:
                    name = await __event_call__({"type": "input", "data": {"title": "Название нового эпика", "message": "Коротко, как проект: «Байк», «Батарея», «Перчатка».", "placeholder": "название"}})
                if not name:
                    return "Название не задано. Напишите номер эпика из списка или название нового:\n\n" + menu
                d = self._create_epic(str(name).strip())
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
            if not user_msg.strip() or user_msg.strip().isdigit():
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
