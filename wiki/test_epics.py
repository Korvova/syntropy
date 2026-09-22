"""Тестовые данные для проверки выбора на объёме: 4 инициативы (коллекции) × ~7 эпиков.
Все помечены описанием «тестовый» — удаляются скриптом с ключом --delete."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import outline

DATA = {
    "Инициатива. Политех": ["⌛Эпик. Батарея МКП", "✅Эпик. Проверка речевых навыков", "⌛Эпик. ИИ-портал", "❓Эпик. Обработка обращений",
                           "💤Эпик. Опросы", "⌛Эпик. Каналы ДПО", "🥶Эпик. Транскрипция речи"],
    "Инициатива. Разработка": ["🚀Эпик. Рука гитара", "⌛Эпик. Перчатка пианино", "⌛Эпик. Сердце", "💤Эпик. Стилус", "💤Эпик. Вибробраслет",
                              "✅Эпик. E-ink RMS", "⌛Эпик. Стелларатор", "🤬Эпик. Голос"],
    "Инициатива. Производство": ["⌛Эпик. Производство плат", "✅Эпик. Vibro-Box", "⌛Эпик. Esp-voice-pen", "💤Эпик. Haptic mouse", "✅Эпик. ЧПУ-носитель",
                                "⌛Эпик. Корпуса под FAB", "❓Эпик. Литьё"],
    "Инициатива. ИТ": ["✅Эпик. hmau-vote", "⌛Эпик. AV-over-IP", "💤Эпик. ZeeVee", "⌛Эпик. RMS демо-комплект", "❓Эпик. ВКС-кодек",
                      "⌛Эпик. Счётчик людей", "✅Эпик. Сайт колледжа", "💤Эпик. Экодер"],
}

def create():
    for col_name, epics in DATA.items():
        col = outline.collection(col_name, "тестовая инициатива для проверки выбора эпика")
        for t in epics:
            d = outline.find_doc(col["id"], t)
            if not d:
                time.sleep(1.2)   # лимит запросов Outline
                outline.api("documents.create", {"collectionId": col["id"], "title": t, "publish": True,
                                                 "text": "_тестовый эпик для проверки выбора на объёме_\n\n## Текущее состояние\n\n| Узел | Состояние |\n|---|---|\n| … | ⬜ |\n"})
        print(col_name, len(epics))

def delete():
    for col_name in DATA:
        for c in outline.api("collections.list", {"limit": 100})["data"]:
            if c["name"] == col_name:
                outline.api("collections.delete", {"id": c["id"]}); print("удалена", col_name)

if __name__ == "__main__":
    delete() if "--delete" in sys.argv else create()
