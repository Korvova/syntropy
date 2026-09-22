// Пункт «База знаний» в боковой панели Open WebUI. Подставляется nginx-ом, исходники чата не меняются.
(function () {
  const URL_KB = "https://wiki.syntropy.test-rms.ru";
  function inject() {
    if (document.getElementById("syntropy-kb-link")) return;
    // ищем пункт «Заметки»/«Notes» в панели и вставляем ссылку после него
    const items = Array.from(document.querySelectorAll("nav a, aside a, div a")).filter((a) => /\/notes$/.test(a.getAttribute("href") || ""));
    const notes = items[0];
    if (!notes || !notes.parentElement) return;
    const a = notes.cloneNode(true);
    a.id = "syntropy-kb-link";
    a.href = URL_KB;
    a.target = "_blank";
    a.rel = "noopener";
    a.removeAttribute("aria-current");
    const label = a.querySelector("div, span");
    if (label) label.textContent = "База знаний";
    else a.textContent = "База знаний";
    notes.parentElement.insertBefore(a, notes.nextSibling);
  }
  const mo = new MutationObserver(() => inject());
  mo.observe(document.documentElement, { childList: true, subtree: true });
  inject();
})();
