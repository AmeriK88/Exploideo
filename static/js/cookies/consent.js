(() => {
  "use strict";

  const GA_ID = window.GA_ID;
  if (!GA_ID) return;
  const STORAGE_KEY = "lx_cookie_consent_v1";

  function loadGoogleAnalytics() {
    if (window.__gaLoaded) return;
    window.__gaLoaded = true;

    const script = document.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };

    window.gtag("js", new Date());
    window.gtag("config", GA_ID);
  }

  function hasAnalyticsConsent() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      const state = JSON.parse(raw);
      return state.decided === true && state.analytics === true;
    } catch {
      return false;
    }
  }

  if (hasAnalyticsConsent()) {
    loadGoogleAnalytics();
  }

  window.addEventListener("lx:cookies:consent", (event) => {
    const state = event.detail || {};
    if (state.analytics === true) {
      loadGoogleAnalytics();
    }
  });
})();