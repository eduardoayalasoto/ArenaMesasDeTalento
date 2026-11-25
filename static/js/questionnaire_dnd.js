/**
 * Reordenar por arrastre en el editor de cuestionarios (drag & drop nativo, sin librerías).
 *
 * - Asa `[data-grip="section"]` → reordena secciones; asa `[data-grip="question"]` → reordena preguntas y
 *   permite pasarlas a otra sección (listas `[data-qlist]`).
 * - Al soltar se envía el orden completo por htmx (POST a `data-reorder-url`); si el servidor rechaza,
 *   se recarga la página para volver al orden real. El token CSRF lo agrega htmx_csrf.js.
 */
(function () {
  var root = document.getElementById("sections-root");
  if (!root || !root.dataset.dnd) return;

  var dragged = null;

  function toast(message, variant) {
    window.dispatchEvent(new CustomEvent("toast", { detail: { message: message, variant: variant } }));
  }

  // Elemento (hermano) antes del cual cae el arrastrado según la posición vertical del puntero.
  function insertionPoint(container, selector, y) {
    var items = Array.prototype.filter.call(container.children, function (el) {
      return el !== dragged && el.matches(selector);
    });
    for (var i = 0; i < items.length; i++) {
      var box = items[i].getBoundingClientRect();
      if (y < box.top + box.height / 2) return items[i];
    }
    return null;
  }

  function renumber() {
    root.querySelectorAll(":scope > [data-section-id]").forEach(function (section, i) {
      var badge = section.querySelector("[data-section-badge]");
      if (badge) badge.textContent = "Sección " + (i + 1);
    });
    root.querySelectorAll("[data-qlist]").forEach(function (list) {
      list.querySelectorAll(":scope > [data-question-id] [data-q-number]").forEach(function (n, i) { n.textContent = i + 1; });
    });
  }

  function send(values) {
    htmx.ajax("POST", root.dataset.reorderUrl, { values: values, swap: "none" }).then(
      function () { renumber(); toast("Guardé el nuevo orden.", "success"); },
      function () { toast("No pude guardar el orden; recargo la página.", "error"); window.location.reload(); }
    );
  }

  function sectionsOrder() {
    return Array.prototype.map.call(root.querySelectorAll(":scope > [data-section-id]"), function (el) { return Number(el.dataset.sectionId); });
  }

  function questionsLayout() {
    var layout = {};
    root.querySelectorAll("[data-qlist]").forEach(function (list) {
      layout[list.dataset.sectionId] = Array.prototype.map.call(
        list.querySelectorAll(":scope > [data-question-id]"), function (el) { return Number(el.dataset.questionId); });
    });
    return layout;
  }

  // El elemento solo es arrastrable mientras el puntero está sobre su asa (así no estorba al texto/inputs).
  root.addEventListener("pointerdown", function (e) {
    var grip = e.target.closest("[data-grip]");
    if (!grip) return;
    var item = grip.dataset.grip === "section" ? grip.closest("[data-section-id]") : grip.closest("[data-question-id]");
    if (item) item.draggable = true;
  });
  document.addEventListener("pointerup", function () {
    if (dragged) return;
    root.querySelectorAll("[draggable='true']").forEach(function (el) { el.draggable = false; });
  });
  root.addEventListener("dragstart", function (e) {
    var item = e.target.closest("[data-question-id], [data-section-id]");
    if (!item || !item.draggable) return;
    // Una pregunta dentro de una sección: el arrastre es de la pregunta, no de la sección.
    dragged = e.target.closest("[data-question-id]") || item;
    dragged.dataset.kind = dragged.hasAttribute("data-question-id") ? "question" : "section";
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", "reorder");
    dragged.classList.add("opacity-40");
    e.stopPropagation();
  });
  root.addEventListener("dragover", function (e) {
    if (!dragged) return;
    if (dragged.dataset.kind === "question") {
      var list = e.target.closest("[data-qlist]");
      if (!list) return;
      e.preventDefault();
      var before = insertionPoint(list, "[data-question-id]", e.clientY);
      if (before) list.insertBefore(dragged, before); else list.appendChild(dragged);
    } else {
      e.preventDefault();
      var before2 = insertionPoint(root, "[data-section-id]", e.clientY);
      if (before2) root.insertBefore(dragged, before2); else root.appendChild(dragged);
    }
  });
  root.addEventListener("drop", function (e) { if (dragged) e.preventDefault(); });
  root.addEventListener("dragend", function () {
    if (!dragged) return;
    var kind = dragged.dataset.kind;
    dragged.classList.remove("opacity-40");
    dragged.draggable = false;
    dragged = null;
    if (kind === "question") send({ kind: "questions", layout: JSON.stringify(questionsLayout()) });
    else send({ kind: "sections", order: JSON.stringify(sectionsOrder()) });
  });
})();
