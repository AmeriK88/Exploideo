(async function () {
  const input = document.querySelector(".js-booking-date");
  const cfg = document.getElementById("booking-calendar-config");
  if (!input || !cfg) return;

  const urlBase = cfg.dataset.disabledDatesUrl;
  if (!urlBase) return;

  if (!window.flatpickr) return;
  if (input._flatpickr) input._flatpickr.destroy();

  // Si quieres que cuando haya blocked_by el usuario NO pueda elegir fecha:
  const LOCK_DATE_INPUT_WHEN_BLOCKED = false;

  function ymd(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  let disabledSet = new Set();
  let hasLoadedOnce = false;

  const statusEl = document.getElementById("calendar-status");
  function setStatus(msg) {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("hidden", !msg);
  }

  function parseIntSafe(selector, fallback) {
    const v = parseInt(document.querySelector(selector)?.value ?? "", 10);
    return Number.isFinite(v) ? v : fallback;
  }

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

  function applyDisable(instance) {
    instance.set("disable", [(date) => disabledSet.has(ymd(date))]);
    instance.redraw();
  }

  // Abort para evitar respuestas viejas pisando a nuevas
  let currentAbort = null;

  async function loadDisabledDates(year, month, instance) {
    // abort request anterior si existe
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

      // Mensaje (pero NO rompas el calendario)
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

      // Aplica disabled SIEMPRE (aunque haya blocked_by)
      const arr = Array.isArray(data.disabled) ? data.disabled : [];
      disabledSet = new Set(arr);
      hasLoadedOnce = true;
      applyDisable(instance);
    } catch (e) {
      // Abort es normal, no lo trates como error
      if (e?.name === "AbortError") return;

      console.warn("Could not load disabled dates", e);

      if (hasLoadedOnce) {
        applyDisable(instance);
      } else {
        instance.set("disable", []);
        instance.redraw();
      }

      setStatus("No se pudo cargar disponibilidad. Reintenta abriendo el calendario o recarga la página.");
    }
  }

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

  // Debounce para no spamear requests al cambiar números
  let debounceTimer = null;
  function scheduleReload() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadDisabledDates(fp.currentYear, fp.currentMonth, fp);
    }, 250);
  }

  ["adults", "children", "infants"].forEach((name) => {
    const el = document.querySelector(`[name="${name}"]`);
    if (!el) return;

    el.addEventListener("change", scheduleReload);
    el.addEventListener("input", scheduleReload);
  });
})();