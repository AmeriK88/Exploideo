(function () {
  console.log("loader.js loaded ✅");

  const loader = document.getElementById("app-loader");
  if (!loader) {
    console.warn("AppLoader: #app-loader not found");
    return;
  }

  const labelEl = loader.querySelector(".loader-label");

  function show(label) {
    if (labelEl) labelEl.textContent = label || "Cargando…";
    loader.classList.add("is-open");
    loader.setAttribute("aria-hidden", "false");
  }

  function hide() {
    loader.classList.remove("is-open");
    loader.setAttribute("aria-hidden", "true");
  }

  window.AppLoader = { show, hide };

  document.addEventListener(
    "submit",
    function (e) {
      const form = e.target;
      if (form && form.matches("[data-no-loader]")) return;
      show("Procesando…");
    },
    true
  );

  document.addEventListener(
    "click",
    function (e) {
      const link = e.target.closest("a");
      if (link) {
        const href = link.getAttribute("href");
        if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;
        if (href.startsWith("mailto:") || href.startsWith("tel:")) return;
        if (link.hasAttribute("data-no-loader")) return;
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

      const btn = e.target.closest('button[type="submit"], input[type="submit"]');
      if (btn) show("Procesando…");
    },
    true
  );

  window.addEventListener("pageshow", hide);
  window.addEventListener("pagehide", hide);
})();
