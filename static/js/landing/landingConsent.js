(() => {
  "use strict";

  // Aislado del base:
  // - Key distinta
  // - Selectores con prefijo lx-landing
  const STORAGE_KEY = "lx_landing_cookie_consent_v1";

  const DEFAULTS = {
    decided: false,
    functional: false,
    analytics: false,
    marketing: false,
    timestamp: null,
  };

  // DOM helpers
  const $ = (sel, root = document) => root.querySelector(sel);

  const banner = $("#lx-landing-cookie-banner");
  const modal = $("#lx-landing-cookie-modal");
  if (!banner || !modal) return;

  const backdrop = modal.querySelector("[data-lx-landing-cookie-backdrop]");

  const toggles = {
    functional: $('[data-lx-landing-cookie-toggle="functional"]', modal),
    analytics: $('[data-lx-landing-cookie-toggle="analytics"]', modal),
    marketing: $('[data-lx-landing-cookie-toggle="marketing"]', modal),
  };

  // --- State ---
  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { ...DEFAULTS };
      const parsed = JSON.parse(raw);
      return { ...DEFAULTS, ...parsed };
    } catch {
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

  // --- UI helpers (sin liarla con aria-hidden + focus) ---
  function show(el) {
    el.hidden = false;
    el.removeAttribute("aria-hidden");
    if ("inert" in el) el.inert = false;
  }

  function hide(el) {
    // Primero quitamos foco si está dentro (evita el warning que viste)
    if (el.contains(document.activeElement)) {
      document.activeElement.blur?.();
    }
    el.hidden = true;
    el.setAttribute("aria-hidden", "true");
    if ("inert" in el) el.inert = true;
  }

  function syncTogglesFromState(state) {
    if (toggles.functional) toggles.functional.checked = !!state.functional;
    if (toggles.analytics) toggles.analytics.checked = !!state.analytics;
    if (toggles.marketing) toggles.marketing.checked = !!state.marketing;
  }

  function getTogglesValue() {
    return {
      functional: !!toggles.functional?.checked,
      analytics: !!toglesSafe(toggles.analytics),
      marketing: !!toglesSafe(toggles.marketing),
    };
  }

  function toBool(x) {
    return !!x;
  }

  function togI(t) {
    return toBool(t?.checked);
  }

  function toglesSafe(t) {
    return t?.checked ? true : false;
  }

  // --- Modal control ---
  function openModal() {
    const state = readState();
    syncTogglesFromState(state);

    // No escondemos el banner con aria-hidden (da warnings si tiene foco).
    // Simplemente lo ocultamos con hidden/inert.
    hide(banner);

    show(modal);

    // Focus accesible: primer control útil
    const firstFocusable =
      toggles.functional ||
      $('[data-lx-landing-cookie-action="save"]', modal) ||
      $('[data-lx-landing-cookie-action="close"]', modal);

    firstFocusable?.focus?.();
  }

  function closeModal() {
    hide(modal);

    // Si aún no decidió, vuelve a mostrar el banner
    const state = readState();
    if (!hasDecision(state)) show(banner);
  }

  function showBannerIfNeeded() {
    const state = readState();
    if (!hasDecision(state)) show(banner);
    else hide(banner);
  }

  // --- Consent actions ---
  function acceptAll() {
    const state = writeState({ functional: true, analytics: true, marketing: true });
    syncTogglesFromState(state);
    hide(banner);
    hide(modal);
    window.dispatchEvent(new CustomEvent("lx:landing:cookies:consent", { detail: state }));
  }

  function rejectAll() {
    const state = writeState({ functional: false, analytics: false, marketing: false });
    syncTogglesFromState(state);
    hide(banner);
    hide(modal);
    window.dispatchEvent(new CustomEvent("lx:landing:cookies:consent", { detail: state }));
  }

  function savePreferences() {
    const state = writeState({
      functional: togI(toggles.functional),
      analytics: togI(toggles.analytics),
      marketing: togI(toggles.marketing),
    });
    hide(banner);
    hide(modal);
    window.dispatchEvent(new CustomEvent("lx:landing:cookies:consent", { detail: state }));
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
    }
  }

  // Clicks en botones del banner + modal
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lx-landing-cookie-action]");
    if (!btn) return;

    const action = btn.getAttribute("data-lx-landing-cookie-action");
    if (!action) return;

    e.preventDefault();
    handleAction(action);
  });

  // Botón footer: "Preferencias de cookies"
  document.addEventListener("click", (e) => {
    const openBtn = e.target.closest("[data-lx-landing-cookie-open]");
    if (!openBtn) return;

    e.preventDefault();
    openModal();
  });

  // Cerrar modal al click fuera
  backdrop?.addEventListener("click", closeModal);

  // Cerrar con ESC
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!modal.hidden) closeModal();
  });

  // Init
  hide(modal);
  showBannerIfNeeded();
})();
