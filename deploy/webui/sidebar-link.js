// Пункт «База знаний» в боковой панели Open WebUI. Подставляется nginx-ом, исходники чата не меняются.
(function () {
  const URL_KB = "__WIKI_URL__";
  const LABEL = "База знаний";
  function inject() {
    if (document.getElementById("syntropy-kb-link")) return;
    const notes = Array.from(document.querySelectorAll("a[href]")).find((a) => /\/notes\/?$/.test(a.getAttribute("href") || ""));
    if (!notes || !notes.parentElement) return;
    const a = notes.cloneNode(true);
    a.id = "syntropy-kb-link";
    a.href = URL_KB;
    a.target = "_blank";
    a.rel = "noopener";
    a.removeAttribute("aria-current");
    a.removeAttribute("data-state");
    // меняем только подпись: самый глубокий элемент, чей текст совпадает с подписью «Заметки»/«Notes»
    const oldLabel = (notes.textContent || "").trim();
    let target = null;
    a.querySelectorAll("*").forEach((el) => {
      if ((el.textContent || "").trim() === oldLabel && el.children.length === 0) target = el;
    });
    if (target) target.textContent = LABEL;
    else if (!oldLabel) a.appendChild(document.createTextNode(LABEL));
    else a.textContent = LABEL;
    // убрать активную подсветку, если «Заметки» были выбраны
    a.classList.remove("bg-gray-100", "dark:bg-gray-900");
    notes.parentElement.insertBefore(a, notes.nextSibling);
  }
  const mo = new MutationObserver(() => inject());
  mo.observe(document.documentElement, { childList: true, subtree: true });
  inject();
})();
