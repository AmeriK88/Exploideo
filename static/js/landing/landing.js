
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

    // Respeta "reducir movimiento"
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

  document.addEventListener("DOMContentLoaded", () => {
    initScrollReveal();
    initSmoothAnchors();
  });
})();
