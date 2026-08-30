(function () {
  // Main loader element
  const loader = document.getElementById("app-loader");

  // If the loader container does not exist, stop the script
  if (!loader) {
    console.warn("AppLoader: #app-loader not found");
    return;
  }

  const labelEl = loader.querySelector(".loader-label");

  function __(str) {
    return typeof gettext === "function" ? gettext(str) : str;
  }

  /**
   * Shows the loader and optionally updates the label text.
   */
  function show(label) {
    if (labelEl) labelEl.textContent = label || __("Cargando…");
    loader.classList.add("is-open");
    loader.setAttribute("aria-hidden", "false");
  }

  /**
   * Hides the loader.
   */
  function hide() {
    loader.classList.remove("is-open");
    loader.setAttribute("aria-hidden", "true");
  }

  /**
   * Expose a small public API so other scripts can manually
   * control the loader (e.g. AppLoader.show("Saving…")).
   */
  window.AppLoader = { show, hide };

  /**
   * Intercepts form submissions and shows the loader.
   * Forms marked with [data-no-loader] are ignored.
   */
  document.addEventListener(
    "submit",
    function (e) {
      const form = e.target;
      if (form && form.matches("[data-no-loader]")) return;
      show(__("Procesando…"));
    },
    true
  );

  /**
   * Intercepts clicks that trigger navigation.
   * If the click leads to a real page navigation, show the loader.
   */
  document.addEventListener(
    "click",
    function (e) {
      const link = e.target.closest("a");

      if (link) {
        const href = link.getAttribute("href");

        // Ignore empty links, anchors, javascript links, mail and tel links
        if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;
        if (href.startsWith("mailto:") || href.startsWith("tel:")) return;

        // Allow opting out via attribute
        if (link.hasAttribute("data-no-loader")) return;

        // Ignore links opening in a new tab
        if (link.target === "_blank") return;

        // Ignore same-document hash navigations (e.g. /es/#waitlist).
        // They update scroll/fragment without a full navigation, so keeping
        // the loader open would freeze the UI.
        try {
          const targetUrl = new URL(link.href, window.location.href);

          const isSameDocument =
            targetUrl.origin === window.location.origin &&
            targetUrl.pathname === window.location.pathname &&
            targetUrl.search === window.location.search;

          if (isSameDocument && targetUrl.hash) return;
        } catch (_) {
          // If URL parsing fails, fall through to normal loader behavior.
        }

        show("Cargando…");
        return;
      }

      // Handle submit buttons that may not trigger the form listener yet
      const btn = e.target.closest('button[type="submit"], input[type="submit"]');
      if (btn) show("Procesando…");
    },
    true
  );

  /**
   * Ensure the loader is hidden when navigating with browser cache
   * (back/forward navigation).
   */
  window.addEventListener("pageshow", hide);
  window.addEventListener("pagehide", hide);
})();