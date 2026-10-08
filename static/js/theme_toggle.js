/**
 * Persistencia de tema claro/oscuro -- localStorage.arena_talento_theme.
 *
 * Se corre lo antes posible (script sincrono, sin defer, en <head>)
 * para aplicar la clase `dark` antes del primer paint y evitar un
 * parpadeo de tema incorrecto (FOUC, ver specs/002-design-system-import
 * SC-006). Ver research.md punto 3 para el razonamiento del mecanismo.
 */
(function () {
  var STORAGE_KEY = "arena_talento_theme";

  function getStoredTheme() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      // localStorage puede no estar disponible (modo privado estricto,
      // política del navegador) -- degrada a preferencia del sistema.
      return null;
    }
  }

  function systemPrefersDark() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    );
  }

  function applyTheme(theme) {
    var isDark = theme === "dark";
    // .dark / clase Tailwind heredada -- sigue viva mientras dure la
    // migracion incremental de vistas viejas a daisyUI (ver
    // DESIGN_SYSTEM.md Seccion 7). data-theme es el mecanismo real de
    // daisyUI: sus colores semanticos (bg-primary, text-base-content...)
    // cambian solos con este atributo, nunca con la variante `dark:`.
    document.documentElement.classList.toggle("dark", isDark);
    document.documentElement.setAttribute("data-theme", isDark ? "business" : "arena");
  }

  function currentTheme() {
    var stored = getStoredTheme();
    if (stored === "light" || stored === "dark") {
      return stored;
    }
    return systemPrefersDark() ? "dark" : "light";
  }

  // Aplicar de inmediato, antes de que Alpine/htmx terminen de cargar.
  applyTheme(currentTheme());

  window.arenaTheme = {
    get: currentTheme,
    set: function (theme) {
      applyTheme(theme);
      try {
        window.localStorage.setItem(STORAGE_KEY, theme);
      } catch (e) {
        // Sin persistencia disponible -- el tema igual se aplica para
        // esta carga de página, solo no sobrevive a un refresh.
      }
    },
    toggle: function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      this.set(next);
      return next;
    },
  };
})();
