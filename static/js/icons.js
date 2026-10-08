/*
 * Dibujo de íconos Lucide -- ÚNICO punto de entrada: `renderIcons(raiz)`.
 * Nunca llamar `lucide.createIcons()` directo.
 *
 * Bug real (2026-09-28, causa de "los modales dejan de abrir"): Lucide
 * reemplaza cada `<i data-lucide>` por un `<svg>` que COPIA todos sus
 * atributos, incluido `data-lucide` y cualquier `x-init` de Alpine. Por eso:
 *   1. cada `lucide.createIcons()` global volvía a reemplazar TODOS los
 *      `<svg>` ya dibujados de la página (siguen teniendo `data-lucide`), y
 *   2. cada `<svg>` recreado con `x-init="...createIcons()"` era un nodo
 *      nuevo para Alpine, que corría otra vez ese `x-init`...
 * Un ciclo sin fin (medido: 195+ llamadas en una sola apertura del modal de
 * detalle) que congelaba la pestaña; desde ahí ningún modal volvía a abrir.
 *
 * `renderIcons` solo convierte los `<i data-lucide>` todavía sin dibujar, y
 * solo dentro de `raiz` (default: todo el documento). Un `<svg>` ya dibujado
 * nunca vuelve a procesarse, así que ninguna llamada puede encadenar otra.
 */
(function () {
  var PENDING = "data-lucide-pending";

  window.renderIcons = function (root) {
    if (!window.lucide) {
      return;
    }
    root = root || document;
    var pending = root.querySelectorAll ? root.querySelectorAll("i[data-lucide]") : [];
    if (root.matches && root.matches("i[data-lucide]")) {
      pending = [root].concat(Array.prototype.slice.call(pending));
    }
    if (!pending.length) {
      return;
    }
    Array.prototype.forEach.call(pending, function (el) {
      el.setAttribute(PENDING, el.getAttribute("data-lucide"));
    });
    // `root` de un <i> suelto: Lucide busca DENTRO de root, así que se usa
    // su padre.
    var scope = root.matches && root.matches("i[data-lucide]") ? root.parentNode || document : root;
    window.lucide.createIcons({ root: scope, nameAttr: PENDING });
    // El <svg> resultante copió el marcador -- se quita para que ninguna
    // llamada futura lo vuelva a reemplazar.
    Array.prototype.forEach.call(scope.querySelectorAll("[" + PENDING + "]"), function (el) {
      el.removeAttribute(PENDING);
    });
  };
})();
