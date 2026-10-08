/*
 * Apertura de modales (components/_modal.html) -- patrón OFICIAL de daisyUI 5
 * (https://daisyui.com/components/modal/): el clic llama directamente
 * `dialog.showModal()` sobre el <dialog> por su id.
 *
 * 2026-09-28 (bug real, varias rondas): antes cada botón despachaba un
 * CustomEvent a `window` y un listener de Alpine en OTRO componente era quien
 * llamaba `showModal()`. Si ese listener no estaba vivo, el clic no hacía nada
 * y no quedaba ningún error. Ahora el <dialog> se abre sin depender de Alpine;
 * Alpine solo recibe el "detalle" (título/ícono/tipo) vía el evento
 * `modal-detail`, que burbujea desde el <dialog> hasta el wrapper de
 * _modal.html.
 *
 * Uso en un disparador (siempre con `data-modal-open`, que es lo que usa la
 * verificación automática scripts/e2e/modals.mjs para encontrarlos todos):
 *   <button type="button" data-modal-open="mi-modal"
 *           onclick="openModal('mi-modal', {title: 'Título', icon: 'phone'})">
 */
(function () {
  window.openModal = function (id, detail) {
    var dialog = document.getElementById(id);
    if (!dialog || typeof dialog.showModal !== "function") {
      console.error("[modal] No existe un <dialog> con id #" + id);
      return false;
    }
    dialog.dispatchEvent(new CustomEvent("modal-detail", { detail: detail || {}, bubbles: true }));
    if (!dialog.open) {
      dialog.showModal();
    }
    return true;
  };

  window.closeModal = function (id) {
    var dialog = document.getElementById(id);
    if (dialog && dialog.open) {
      dialog.close();
    }
  };
})();
