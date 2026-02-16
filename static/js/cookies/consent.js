(() => {
  "use strict";

  // --- Config ---
  const STORAGE_KEY = "lx_cookie_consent_v1";
  const DEFAULTS = {
    decided: false,
    functional: false,
    analytics: false,
    marketing: false,
    timestamp: null,
  };

  // --- DOM helpers ---
  const $ = (sel, root = document) => root.querySelector(sel);
  const banner = $("#cookie-banner");
  const modal = $("#cookie-modal");
  if (!banner || !modal) return;

  const overlay = modal.querySelector(".absolute.inset-0"); // backdrop
  const toggles = {
    functional: $('[data-cookie-toggle="functional"]', modal),
    analytics: $('[data-cookie-toggle="analytics"]', modal),
    marketing: $('[data-cookie-toggle="marketing"]', modal),
  };

  // --- State ---
  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { ...DEFAULTS };
      const parsed = JSON.parse(raw);
      return { ...DEFAULTS, ...parsed };
    } catch (e) {
      return { ...DEFAULTS };
    }
  }

  function writeState(next) {
    const state = {
      ...DEFAULTS,
      ...next,
      decided: true,
      timestamp: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return state;
  }

  function hasDecision(state) {
    return !!state?.decided;
  }

  // --- UI (ahora con .is-open, no con hidden) ---
  function open(el) {
    el.classList.add("is-open");
    el.setAttribute("aria-hidden", "false");
  }

  function close(el) {
    el.classList.remove("is-open");
    el.setAttribute("aria-hidden", "true");
  }

  function isOpen(el) {
    return el.classList.contains("is-open");
  }

  function syncTogglesFromState(state) {
    if (toggles.functional) toggles.functional.checked = !!state.functional;
    if (toggles.analytics) toggles.analytics.checked = !!state.analytics;
    if (toggles.marketing) toggles.marketing.checked = !!state.marketing;
  }

  function getTogglesValue() {
    return {
      functional: !!toggles.functional?.checked,
      analytics: !!toggles.analytics?.checked,
      marketing: !!toggles.marketing?.checked,
    };
  }

  function openModal() {
    // Siempre sincroniza con el estado actual
    const state = readState();
    syncTogglesFromState(state);

    // Ojo: si el banner está abierto, lo cerramos para evitar overlays raros
    close(banner);
    open(modal);

    // Focus accesible: intenta enfocar el primer toggle
    const firstFocusable =
      toggles.functional ||
      $('[data-cookie-action="save"]', modal) ||
      $('[data-cookie-action="close"]', modal);
    firstFocusable?.focus?.();
  }

  function closeModal() {
    close(modal);
  }

  function showBannerIfNeeded() {
    const state = readState();
    if (!hasDecision(state)) open(banner);
    else close(banner);
  }

  // --- Consent actions ---
  function acceptAll() {
    const state = writeState({ functional: true, analytics: true, marketing: true });
    syncTogglesFromState(state);
    close(banner);
    closeModal();
    window.dispatchEvent(new CustomEvent("lx:cookies:consent", { detail: state }));
  }

  function rejectAll() {
    const state = writeState({ functional: false, analytics: false, marketing: false });
    syncTogglesFromState(state);
    close(banner);
    closeModal();
    window.dispatchEvent(new CustomEvent("lx:cookies:consent", { detail: state }));
  }

  function savePreferences() {
    const prefs = getTogglesValue();
    const state = writeState(prefs);
    close(banner);
    closeModal();
    window.dispatchEvent(new CustomEvent("lx:cookies:consent", { detail: state }));
  }

  // --- Event bindings ---
  function handleAction(action) {
    switch (action) {
      case "accept":
        acceptAll();
        break;
      case "reject":
        rejectAll();
        break;
      case "manage":
        openModal();
        break;
      case "save":
        savePreferences();
        break;
      case "close":
        closeModal();
        break;
      default:
        break;
    }
  }

  // Clicks en botones con data-cookie-action (banner + modal)
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-cookie-action]");
    if (!btn) return;

    const action = btn.getAttribute("data-cookie-action");
    if (!action) return;

    e.preventDefault();
    handleAction(action);
  });

  // Botón footer: "Preferencias de cookies"
  document.addEventListener("click", (e) => {
    const openBtn = e.target.closest("[data-cookie-open]");
    if (!openBtn) return;

    e.preventDefault();
    openModal();
  });

  // Cerrar modal al click fuera (backdrop)
  if (overlay) {
    overlay.addEventListener("click", () => closeModal());
  }

  // Cerrar con ESC
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (isOpen(modal)) closeModal();
  });

  // Al cargar
  close(modal);
  showBannerIfNeeded();
})();
