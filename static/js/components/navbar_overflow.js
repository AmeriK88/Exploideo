(function () {
  "use strict";

  var navbars = document.querySelectorAll(".c-nav[data-nav-overflow]");
  if (!navbars.length) return;

  var BREAKPOINT_MD = 768;

  function updateNavbarOverflow(navbar) {
    var inner = navbar.querySelector(".c-nav__inner");
    if (!inner) return;

    if (window.innerWidth < BREAKPOINT_MD) {
      navbar.classList.remove("c-nav--overflow");
      return;
    }

    // Measure natural width first, then toggle overflow mode if needed.
    navbar.classList.remove("c-nav--overflow");
    var needsOverflow = inner.scrollWidth > inner.clientWidth + 2;
    navbar.classList.toggle("c-nav--overflow", needsOverflow);
  }

  function updateAll() {
    navbars.forEach(updateNavbarOverflow);
  }

  var scheduled = false;
  function scheduleUpdate() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(function () {
      scheduled = false;
      updateAll();
    });
  }

  window.addEventListener("resize", scheduleUpdate, { passive: true });
  window.addEventListener("orientationchange", scheduleUpdate, { passive: true });

  if (document.fonts && typeof document.fonts.ready === "object") {
    document.fonts.ready.then(scheduleUpdate).catch(function () {});
  }

  if (window.ResizeObserver) {
    var observer = new ResizeObserver(scheduleUpdate);
    navbars.forEach(function (navbar) {
      var container = navbar.querySelector(".c-nav__container") || navbar;
      observer.observe(container);
    });
  }

  scheduleUpdate();
})();
