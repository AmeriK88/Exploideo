(() => {
  "use strict";

  const GA_ID = window.GA_ID;
  console.log("[GA] window.GA_ID =", GA_ID);

  if (!GA_ID) {
    console.warn("[GA] No hay GA_ID");
    return;
  }

  const STORAGE_KEY = "lx_cookie_consent_v1";

  function loadGoogleAnalytics() {
    if (window.__gaLoaded) {
      console.log("[GA] Ya cargado");
      return;
    }

    window.__gaLoaded = true;
    console.log("[GA] Cargando Google Analytics...");

    const script = document.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };

    window.gtag("js", new Date());
    window.gtag("config", GA_ID, { debug_mode: true });

    console.log("[GA] Config enviado");
  }

  function hasAnalyticsConsent() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      console.log("[GA] Consent raw =", raw);

      if (!raw) return false;
      const state = JSON.parse(raw);
      console.log("[GA] Consent parsed =", state);

      return state.decided === true && state.analytics === true;
    } catch (e) {
      console.error("[GA] Error leyendo consentimiento", e);
      return false;
    }
  }

  if (hasAnalyticsConsent()) {
    loadGoogleAnalytics();
  } else {
    console.warn("[GA] Sin consentimiento de analytics");
  }

  window.addEventListener("lx:cookies:consent", (event) => {
    const state = event.detail || {};
    console.log("[GA] Evento consentimiento =", state);

    if (state.analytics === true) {
      loadGoogleAnalytics();
    }
  });
})();