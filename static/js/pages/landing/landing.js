(function () {
  // Marca que hay JS (para el fallback CSS si lo usas)
  document.documentElement.classList.add("js");

  function setStaggerDelays() {
    document.querySelectorAll("[data-stagger]").forEach((parent) => {
      const items = parent.querySelectorAll("[data-animate]");
      items.forEach((el, idx) => {
        el.style.setProperty("--delay", `${idx * 70}ms`);
      });
    });
  }

  function initScrollReveal() {
    setStaggerDelays();

    const els = document.querySelectorAll("[data-animate]");
    if (!els.length) return;

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      els.forEach((el) => el.classList.add("is-in"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-in");
          obs.unobserve(entry.target);
        });
      },
      { root: null, threshold: 0.12, rootMargin: "0px 0px -10% 0px" }
    );

    els.forEach((el) => observer.observe(el));
  }

  function initSmoothAnchors() {
    document.querySelectorAll('a[href^="#"]').forEach((a) => {
      a.addEventListener("click", (e) => {
        const href = a.getAttribute("href");
        const target = document.querySelector(href);
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  // ====== NEW: Landing demo carousel ======
  function initLandingDemo() {
    const stage = document.getElementById("stage");
    const screens = Array.from(document.querySelectorAll(".screen"));
    const tabs = Array.from(document.querySelectorAll(".c-tab"));
    const toggleAutoBtn = document.getElementById("toggleAuto");
    const pointer = document.getElementById("pointer");
    const pulse = document.getElementById("pulse");

    // Si no existe el bloque demo, no hacemos nada
    if (!stage || screens.length === 0 || tabs.length === 0 || !toggleAutoBtn || !pointer || !pulse) return;

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let idx = 0;
    let auto = !prefersReduced; // si reduce motion, autoplay off
    let timer = null;
    let busy = false;

    // Ajusta estos puntos a tus screenshots (porcentaje del stage)
    const clickPoints = [
      { x: 74, y: 82 }, // Explorar
      { x: 78, y: 28 }, // Guía
      { x: 76, y: 58 }, // Reserva
    ];

    function setActive(i) {
      idx = i;
      screens.forEach((el, k) => el.classList.toggle("is-active", k === i));
      tabs.forEach((t, k) => t.setAttribute("aria-selected", String(k === i)));
      positionPointerFor(i);
    }

    function positionPointerFor(i) {
      const p = clickPoints[i] ?? clickPoints[0];
      const rect = stage.getBoundingClientRect();
      const x = rect.width * (p.x / 100);
      const y = rect.height * (p.y / 100);

      // Ajuste de la punta del cursor
      const tipOffsetX = 18;
      const tipOffsetY = 16;

      pointer.style.left = (x - tipOffsetX) + "px";
      pointer.style.top = (y - tipOffsetY) + "px";

      pulse.style.left = (x - 6) + "px";
      pulse.style.top = (y - 6) + "px";
    }

    function triggerClickFX() {
      if (prefersReduced) return;

      pointer.classList.remove("is-clicking");
      void pointer.offsetWidth; // reflow
      pointer.classList.add("is-clicking");

      pulse.classList.remove("is-burst");
      void pulse.offsetWidth;
      pulse.classList.add("is-burst");
    }

    function sleep(ms) {
      return new Promise((r) => setTimeout(r, ms));
    }

    async function goTo(nextIndex, { user = false } = {}) {
      if (busy) return;
      busy = true;

      pointer.classList.remove("is-floating");
      positionPointerFor(nextIndex);
      triggerClickFX();

      await sleep(prefersReduced ? 0 : 180);
      setActive(nextIndex);

      await sleep(prefersReduced ? 0 : 120);
      if (!prefersReduced) pointer.classList.add("is-floating");

      if (user) restartAuto();
      busy = false;
    }

    function startAuto() {
      stopAuto();
      timer = setInterval(async () => {
        const next = (idx + 1) % screens.length;
        await goTo(next);
      }, 3200);
    }

    function stopAuto() {
      if (timer) clearInterval(timer);
      timer = null;
    }

    function restartAuto() {
      if (auto) startAuto();
    }

    tabs.forEach((t) => {
      t.addEventListener("click", async () => {
        await goTo(Number(t.dataset.i), { user: true });
      });
    });

    toggleAutoBtn.addEventListener("click", () => {
      auto = !auto;
      toggleAutoBtn.textContent = auto ? "Pausar demo" : "Reproducir demo";
      if (auto) startAuto();
      else stopAuto();
    });

    // Init
    setActive(0);
    if (!prefersReduced) pointer.classList.add("is-floating");
    if (auto) startAuto();
    else stopAuto();

    // Reposition pointer on resize
    let resizeTO = null;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTO);
      resizeTO = setTimeout(() => positionPointerFor(idx), 80);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initScrollReveal();
    initSmoothAnchors();
    initLandingDemo();
  });
})();