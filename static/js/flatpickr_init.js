/**
 * Inicializa flatpickr (ya vendorizado, static/vendor/flatpickr/) en todo
 * input con clase `js-flatpickr` -- convención reusable por cualquier
 * feature futura que necesite un date picker (spec 006 es la primera).
 * Se re-corre tras cada swap de htmx, igual que initIcons() en base.html.
 */
(function () {
  // Inputs dentro de un <dialog> (components/_modal.html / _drawer.html):
  // showModal() pone el diálogo en el "top layer" y vuelve inerte el resto
  // del documento, así que el calendario que flatpickr agrega por default
  // a <body> queda DETRÁS del diálogo y no se puede clickear (2026-09-25,
  // modal "Agregar actividad"). `static: true` lo monta junto al input,
  // dentro del propio diálogo.
  function dialogOptions(el) {
    return el.closest("dialog") ? { static: true } : {};
  }

  // Django (es-MX) renderiza el valor inicial como "17/04/2023" [+ " 10:30"],
  // pero flatpickr lo interpreta con `dateFormat` ("Y-m-d") y lo convierte en
  // otra fecha (bug real 2026-09-30: al editar, "17/04/2023" aparecía como
  // "01/01/2023" y se guardaba mal). Se reescribe a ISO antes de inicializar.
  function isoValue(el) {
    var m = /^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{1,2}:\d{2}))?/.exec(el.value.trim());
    if (m) el.value = m[3] + "-" + m[2] + "-" + m[1] + (m[4] ? " " + m[4] : "");
  }

  function initFlatpickr() {
    if (!window.flatpickr) return;
    var locale = window.flatpickr.l10ns && window.flatpickr.l10ns.es ? "es" : undefined;

    document.querySelectorAll(".js-flatpickr").forEach(function (el) {
      // `el._flatpickr` evita reinicializar el input ORIGINAL ya
      // procesado. Pero con `altInput:true` flatpickr crea un segundo
      // <input> VISIBLE que hereda el className completo del original
      // (incluida esta misma clase `js-flatpickr`, ver altInputClass en
      // flatpickr.min.js) -- sin este segundo check, una re-ejecución de
      // initFlatpickr() (dispara en CADA htmx:afterSwap de la página,
      // incluso uno ajeno como el panel de notificaciones que se
      // autocarga en cada carga) inicializa flatpickr UNA SEGUNDA VEZ
      // sobre ese altInput recién creado, produciendo un tercer input
      // fantasma y rompiendo la sincronización del valor real (bug real
      // reportado: "cuando cambio de campo se pierde el valor"). Todo
      // altInput generado por flatpickr lleva la clase marcador
      // `form-control` (default `altInputClass`, nunca usada en el CSS
      // propio de este repo) -- se excluye explícitamente.
      if (el._flatpickr || el.classList.contains("form-control")) return;
      isoValue(el);
      window.flatpickr(el, Object.assign({
        locale: locale,
        dateFormat: "Y-m-d",
        altInput: true,
        altFormat: "d/m/Y",
        allowInput: true,
      }, dialogOptions(el)));
    });

    // Fecha + hora (spec 007: Activity.occurs_at) -- mismo patrón, con
    // enableTime en vez de un segundo input de hora separado.
    document.querySelectorAll(".js-flatpickr-datetime").forEach(function (el) {
      if (el._flatpickr || el.classList.contains("form-control")) return; // ver comentario arriba
      isoValue(el);
      window.flatpickr(el, Object.assign({
        locale: locale,
        enableTime: true,
        time_24hr: true,
        dateFormat: "Y-m-d H:i",
        altInput: true,
        altFormat: "d/m/Y H:i",
        allowInput: true,
      }, dialogOptions(el)));
    });
  }

  document.addEventListener("DOMContentLoaded", initFlatpickr);
  document.body.addEventListener("htmx:afterSwap", initFlatpickr);
})();
