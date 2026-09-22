// Окно выбора эпика: выпадающий список инициатив и эпиков + поле нового эпика.
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
