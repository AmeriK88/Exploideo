(() => {
  "use strict";

  const STORAGE_KEY = "lx_cookie_consent_v1";
  const DEFAULT_STATE = {
    decided: false,
    functional: false,
    analytics: false,
    marketing: false,
  };

  const banner = document.getElementById("cookie-banner");
  const modal = document.getElementById("cookie-modal");
  if (!banner || !modal) {
    return;
  }

  const root = document.documentElement;
  const backdrop = modal.querySelector(".cookie-modal__backdrop");
  const functionalToggle = modal.querySelector('[data-cookie-toggle="functional"]');
  const analyticsToggle = modal.querySelector('[data-cookie-toggle="analytics"]');
  const marketingToggle = modal.querySelector('[data-cookie-toggle="marketing"]');

  function emitConsent(state) {
    window.dispatchEvent(new CustomEvent("lx:cookies:consent", { detail: state }));
  }

  function normalizeState(raw) {
    return {
      decided: raw?.decided === true,
      functional: raw?.functional === true,
      analytics: raw?.analytics === true,
      marketing: raw?.marketing === true,
      timestamp: raw?.timestamp || null,
    };
  }

  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return { ...DEFAULT_STATE };
      }
      return normalizeState(JSON.parse(raw));
    } catch {
      return { ...DEFAULT_STATE };
    }
  }

  function writeState(state) {
    const payload = {
      ...normalizeState(state),
      decided: true,
      timestamp: new Date().toISOString(),
    };

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch {
      // Storage can fail in private mode or strict browser policies.
    }

    emitConsent(payload);
    return payload;
  }

  function syncToggles(state) {
    if (functionalToggle) functionalToggle.checked = state.functional === true;
    if (analyticsToggle) analyticsToggle.checked = state.analytics === true;
    if (marketingToggle) marketingToggle.checked = state.marketing === true;
  }

  function openBanner() {
    banner.classList.add("is-open");
  }

  function closeBanner() {
    banner.classList.remove("is-open");
  }

  function openModal() {
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    root.classList.add("is-modal-open");
  }

  function closeModal() {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    root.classList.remove("is-modal-open");
  }

  function saveCurrentToggles() {
    return writeState({
      functional: functionalToggle?.checked === true,
      analytics: analyticsToggle?.checked === true,
      marketing: marketingToggle?.checked === true,
    });
  }

  function acceptAll() {
    writeState({ functional: true, analytics: true, marketing: true });
    closeBanner();
    closeModal();
  }

  function rejectAll() {
    writeState({ functional: false, analytics: false, marketing: false });
    closeBanner();
    closeModal();
  }

  function initialize() {
    const state = readState();
    syncToggles(state);

    if (state.decided) {
      closeBanner();
      emitConsent(state);
    } else {
      openBanner();
    }
  }

  document.addEventListener("click", (event) => {
    const actionElement = event.target.closest("[data-cookie-action]");
    if (actionElement) {
      const action = actionElement.getAttribute("data-cookie-action");

      if (action === "accept") {
        acceptAll();
        return;
      }

      if (action === "reject") {
        rejectAll();
        return;
      }

      if (action === "manage") {
        syncToggles(readState());
        openModal();
        return;
      }

      if (action === "save") {
        saveCurrentToggles();
        closeBanner();
        closeModal();
        return;
      }

      if (action === "close") {
        closeModal();
        return;
      }
    }

    const openElement = event.target.closest("[data-cookie-open]");
    if (openElement) {
      syncToggles(readState());
      openModal();
      return;
    }

    if (backdrop && event.target === backdrop) {
      closeModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.classList.contains("is-open")) {
      closeModal();
    }
  });

  initialize();
})();
