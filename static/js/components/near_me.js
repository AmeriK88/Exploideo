(function () {
  function __(str) {
    return typeof gettext === "function" ? gettext(str) : str;
  }

  // Temporary debug switch for location diagnostics.
  const NEAR_ME_DEBUG = true;

  // Use stricter options while diagnosing incorrect coordinates.
  const GEOLOCATION_OPTIONS = {
    enableHighAccuracy: true,
    timeout: 15000,
    maximumAge: 0,
  };

  /**
   * Shows a feedback message near the trigger element.
   * It looks for an element with [data-near-me-feedback] inside the same form.
   */
  function setFeedback(trigger, message) {
    const form = trigger.closest("form");
    const feedback = form ? form.querySelector("[data-near-me-feedback]") : null;
    if (!feedback) return;
    feedback.textContent = message;
  }

  /**
   * Builds the query parameters based on the form inputs.
   * - Trims values
   * - Skips empty values
   * - Ignores location-related fields because they are added later
   */
  function buildSearchParams(form) {
    const params = new URLSearchParams();
    if (!form) return params;

    const data = new FormData(form);

    for (const [key, value] of data.entries()) {
      const normalized = String(value || "").trim();

      if (!normalized) continue;

      // These parameters are injected later when geolocation succeeds
      if (key === "near_me" || key === "user_lat" || key === "user_lng") continue;

      params.set(key, normalized);
    }

    return params;
  }

  /**
   * Handles geolocation errors and provides a user-friendly message.
   */
  function handlePositionError(trigger, error) {
    if (!error) {
      setFeedback(trigger, __("No se pudo obtener tu ubicación ahora. Puedes seguir usando filtros normales."));
      return;
    }

    if (error.code === error.PERMISSION_DENIED) {
      setFeedback(trigger, __("Permiso de ubicación denegado. Puedes seguir filtrando de forma manual."));
      return;
    }

    if (error.code === error.POSITION_UNAVAILABLE) {
      setFeedback(trigger, __("Tu ubicación no está disponible temporalmente. Inténtalo de nuevo en unos segundos."));
      return;
    }

    if (error.code === error.TIMEOUT) {
      setFeedback(trigger, __("La ubicación tardó demasiado. Inténtalo de nuevo."));
      return;
    }

    setFeedback(trigger, __("No se pudo activar Cerca de mí ahora mismo."));
  }

  /**
   * Attaches the click handler to the "Near me" trigger.
   * When clicked:
   * 1. Collects existing filters
   * 2. Requests the user's geolocation
   * 3. Redirects to the target URL with location parameters
   */
  function attachNearMeHandler(trigger) {
    trigger.addEventListener("click", function () {

      // If the browser does not support geolocation, fallback to normal filtering
      if (!navigator.geolocation) {
        setFeedback(trigger, __("Este navegador no soporta geolocalización. Usa los filtros normales."));
        return;
      }

      const form = trigger.closest("form");

      // Target URL can be defined via data attribute or fallback to the form action
      const targetUrl =
        trigger.dataset.nearMeTarget ||
        (form && form.action) ||
        "/experiences/";

      const params = buildSearchParams(form);

      setFeedback(trigger, __("Obteniendo tu ubicación..."));

      navigator.geolocation.getCurrentPosition(
        function (position) {
          const latitude = Number(position.coords.latitude);
          const longitude = Number(position.coords.longitude);
          const accuracy = Number(position.coords.accuracy);
          const timestamp = Number(position.timestamp);

          if (NEAR_ME_DEBUG) {
            console.group("[Near me] Geolocation debug");
            console.log("Raw position:", position);
            console.log("Latitude:", latitude);
            console.log("Longitude:", longitude);
            console.log("Accuracy (m):", accuracy);
            console.log("Timestamp (ms):", timestamp);
            console.log("Timestamp (ISO):", Number.isFinite(timestamp) ? new Date(timestamp).toISOString() : "invalid");
            console.log("Geolocation options:", GEOLOCATION_OPTIONS);
            console.log("Target URL:", targetUrl);
            console.groupEnd();

            setFeedback(
              trigger,
              "Ubicacion detectada: "
                + latitude.toFixed(6)
                + ", "
                + longitude.toFixed(6)
                + " (precision aprox. "
                + Math.round(accuracy)
                + " m)"
            );
          }

          // Inject location parameters
          params.set("near_me", "1");
          params.set("user_lat", latitude.toFixed(6));
          params.set("user_lng", longitude.toFixed(6));

          // Redirect to the filtered results page
          window.location.assign(targetUrl + "?" + params.toString());
        },
        function (error) {
          if (NEAR_ME_DEBUG) {
            console.group("[Near me] Geolocation error");
            console.log("Error code:", error && error.code);
            console.log("Error message:", error && error.message);
            console.log("Geolocation options:", GEOLOCATION_OPTIONS);
            console.groupEnd();
          }
          handlePositionError(trigger, error);
        },
        GEOLOCATION_OPTIONS
      );
    });
  }

  /**
   * Initializes the feature once the DOM is ready.
   * Finds all elements marked as "near me triggers".
   */
  document.addEventListener("DOMContentLoaded", function () {
    const triggers = document.querySelectorAll("[data-near-me-trigger]");
    triggers.forEach(attachNearMeHandler);
  });
})();