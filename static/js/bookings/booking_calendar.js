(async function () {
  // Main booking date input and config element
  const input = document.querySelector(".js-booking-date");
  const cfg = document.getElementById("booking-calendar-config");
  if (!input || !cfg) return;

  const urlBase = cfg.dataset.disabledDatesUrl;
  if (!urlBase) return;

  // Flatpickr is required for this script
  if (!window.flatpickr) return;

  // Destroy any previous flatpickr instance before creating a new one
  if (input._flatpickr) input._flatpickr.destroy();

  // Whether the date input should be locked when the backend reports a blocked state
  const LOCK_DATE_INPUT_WHEN_BLOCKED = false;

  /**
   * Formats a Date object as YYYY-MM-DD.
   */
  function ymd(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  // Cached disabled dates for the currently loaded calendar view
  let disabledSet = new Set();

  // Tracks whether we have successfully loaded availability at least once
  let hasLoadedOnce = false;

  const statusEl = document.getElementById("calendar-status");

  /**
   * Updates the status message shown near the calendar.
   */
  function setStatus(msg) {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("hidden", !msg);
  }

  /**
   * Safely reads an integer value from an input.
   * Falls back to a default when the value is missing or invalid.
   */
  function parseIntSafe(selector, fallback) {
    const v = parseInt(document.querySelector(selector)?.value ?? "", 10);
    return Number.isFinite(v) ? v : fallback;
  }

  /**
   * Builds the current guest configuration from the form inputs.
   * Ensures people count is always at least 1.
   */
  function getGroup() {
    const adults = parseIntSafe('[name="adults"]', 1);
    const children = parseIntSafe('[name="children"]', 0);
    const infants = parseIntSafe('[name="infants"]', 0);
    const people = Math.max(1, adults + children + infants);

    return {
      adults: Math.max(0, adults),
      children: Math.max(0, children),
      infants: Math.max(0, infants),
      people,
    };
  }

  /**
   * Applies the current disabled dates to the flatpickr instance.
   */
  function applyDisable(instance) {
    instance.set("disable", [(date) => disabledSet.has(ymd(date))]);
    instance.redraw();
  }

  // AbortController used to prevent outdated responses from overriding newer ones
  let currentAbort = null;

  /**
   * Loads disabled dates for the visible month and current guest configuration.
   * If a previous request is still in flight, it is cancelled first.
   */
  async function loadDisabledDates(year, month, instance) {
    // Cancel the previous request if a newer one is triggered
    if (currentAbort) currentAbort.abort();
    currentAbort = new AbortController();

    try {
      const start = new Date(year, month, 1);
      const end = new Date(year, month + 1, 0);

      const g = getGroup();

      const url =
        `${urlBase}?start=${ymd(start)}&end=${ymd(end)}` +
        `&people=${g.people}&adults=${g.adults}&children=${g.children}&infants=${g.infants}`;

      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        signal: currentAbort.signal,
        cache: "no-store",
      });

      if (!res.ok) throw new Error(`Bad response ${res.status}`);

      const data = await res.json();

      // Show backend status messages without breaking the calendar UI
      if (data.blocked_by) {
        setStatus(data.message || "No se puede reservar con esta configuración.");

        if (LOCK_DATE_INPUT_WHEN_BLOCKED) {
          input.disabled = true;
          instance.close();
        }
      } else {
        setStatus(data.message || "");
        input.disabled = false;
      }

      // Always apply disabled dates, even if the response includes a blocked state
      const arr = Array.isArray(data.disabled) ? data.disabled : [];
      disabledSet = new Set(arr);
      hasLoadedOnce = true;
      applyDisable(instance);
    } catch (e) {
      // Request aborts are expected and should not be treated as real errors
      if (e?.name === "AbortError") return;

      console.warn("Could not load disabled dates", e);

      // If availability was loaded before, keep the last known state
      if (hasLoadedOnce) {
        applyDisable(instance);
      } else {
        // On first-load failure, leave the calendar usable with no disabled dates
        instance.set("disable", []);
        instance.redraw();
      }

      setStatus("No se pudo cargar disponibilidad. Reintenta abriendo el calendario o recarga la página.");
    }
  }

  /**
   * Initializes flatpickr and refreshes availability whenever:
   * - the calendar is ready
   * - the user opens it
   * - the month changes
   * - the year changes
   */
  const fp = window.flatpickr(input, {
    dateFormat: "Y-m-d",
    disableMobile: true,
    allowInput: true,
    minDate: "today",
    disable: [(date) => disabledSet.has(ymd(date))],

    onReady: (_selectedDates, _dateStr, instance) => {
      loadDisabledDates(instance.currentYear, instance.currentMonth, instance);
    },
    onOpen: (_selectedDates, _dateStr, instance) => {
      loadDisabledDates(instance.currentYear, instance.currentMonth, instance);
    },
    onMonthChange: (_selectedDates, _dateStr, instance) => {
      loadDisabledDates(instance.currentYear, instance.currentMonth, instance);
    },
    onYearChange: (_selectedDates, _dateStr, instance) => {
      loadDisabledDates(instance.currentYear, instance.currentMonth, instance);
    },
  });

  // Debounce guest-count changes to avoid firing too many requests in a row
  let debounceTimer = null;

  function scheduleReload() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadDisabledDates(fp.currentYear, fp.currentMonth, fp);
    }, 250);
  }

  /**
   * Reload availability whenever guest counts change.
   */
  ["adults", "children", "infants"].forEach((name) => {
    const el = document.querySelector(`[name="${name}"]`);
    if (!el) return;

    el.addEventListener("change", scheduleReload);
    el.addEventListener("input", scheduleReload);
  });
})();