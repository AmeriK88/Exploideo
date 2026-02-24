(function () {
  const input = document.querySelector(".js-booking-date");
  const cfg = document.getElementById("booking-calendar-config");
  const hint = document.getElementById("calendar-hint");
  if (!input || !cfg) return;

  const urlBase = cfg.dataset.disabledDatesUrl;
  if (!urlBase) return;

  if (!window.flatpickr) return;

  // Evitar doble init
  if (input._flatpickr) input._flatpickr.destroy();

  // ---- local formatter (NO UTC) ----
  function ymd(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  function setHint(text) {
    if (!hint) return;
    const msg = (text || "").trim();
    if (!msg) {
      hint.textContent = "";
      hint.classList.add("hidden");
      return;
    }
    hint.textContent = msg;
    hint.classList.remove("hidden");
  }

  let disabledSet = new Set();

  function getPeople() {
    const a = parseInt(document.querySelector('[name="adults"]')?.value || "1", 10);
    const c = parseInt(document.querySelector('[name="children"]')?.value || "0", 10);
    const i = parseInt(document.querySelector('[name="infants"]')?.value || "0", 10);
    const total = a + c + i;
    return total > 0 ? total : 1;
  }

  async function loadDisabledDates(year, month, instance) {
    try {
      const start = new Date(year, month, 1);
      const end = new Date(year, month + 1, 0);

      const startISO = ymd(start);
      const endISO = ymd(end);

      const url = `${urlBase}?start=${startISO}&end=${endISO}&people=${getPeople()}`;
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) throw new Error(`Bad response ${res.status}`);

      const data = await res.json();

      // 👇 Si el backend manda un bloqueo "global" (no depende de fechas),
      // mostramos el mensaje y NO bloqueamos el calendario entero.
      if (data && data.blocked_by) {
        setHint(data.message || "No se puede reservar con esos datos.");
        disabledSet = new Set(); // NO deshabilites todo el mes
      } else {
        setHint(""); // limpia
        const arr = Array.isArray(data.disabled) ? data.disabled : [];
        disabledSet = new Set(arr);
      }

      if (instance) {
        instance.set("disable", [(date) => disabledSet.has(ymd(date))]);
        instance.redraw();
      }
    } catch (e) {
      disabledSet = new Set();
      console.warn("Could not load disabled dates", e);
      setHint(""); // no metas sustos si falla el endpoint
      if (instance) {
        instance.set("disable", []); // en error, NO bloquees nada
        instance.redraw();
      }
    }
  }

  const fp = window.flatpickr(input, {
    dateFormat: "Y-m-d",
    minDate: "today", // o new Date().fp_incr(2) si quieres 48h real
    disableMobile: true,
    allowInput: true,

    disable: [(date) => disabledSet.has(ymd(date))],

    onReady: async (_s, _d, instance) => {
      await loadDisabledDates(instance.currentYear, instance.currentMonth, instance);
    },
    onOpen: async (_s, _d, instance) => {
      await loadDisabledDates(instance.currentYear, instance.currentMonth, instance);
    },
    onMonthChange: async (_s, _d, instance) => {
      await loadDisabledDates(instance.currentYear, instance.currentMonth, instance);
    },
    onYearChange: async (_s, _d, instance) => {
      await loadDisabledDates(instance.currentYear, instance.currentMonth, instance);
    },
  });

  ["adults", "children", "infants"].forEach((name) => {
    const el = document.querySelector(`[name="${name}"]`);
    if (!el) return;
    el.addEventListener("change", async () => {
      await loadDisabledDates(fp.currentYear, fp.currentMonth, fp);
    });
  });
})();