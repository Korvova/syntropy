// Окно выбора эпика с выпадающим списком. Выполняется в браузере через событие execute.
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
