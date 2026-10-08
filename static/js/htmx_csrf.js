/**
 * Envía X-CSRFToken en todo request htmx que mute datos (POST/PUT/PATCH/DELETE).
 *
 * Sin esto, cualquier hx-post/htmx.ajax('POST', ...) responde 403 (Django
 * exige el header en toda mutación) -- ver constitución, Principio V:
 * "htmx envía X-CSRFToken automáticamente". Esa wiring no existía todavía
 * (ningún spec anterior a 006 hacía un POST vía htmx) -- se agrega aquí,
 * una sola vez para todo el proyecto (base.html), en vez de repetirla por
 * feature. Lee la cookie `csrftoken` que Django ya pone por default.
 */
(function () {
  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  document.body.addEventListener("htmx:configRequest", function (event) {
    if (event.detail.verb !== "get") {
      event.detail.headers["X-CSRFToken"] = getCookie("csrftoken");
    }
  });
})();
