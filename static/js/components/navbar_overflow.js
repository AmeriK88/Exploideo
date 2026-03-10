(function () {
  "use strict";

  // Select all navbars that should support overflow behavior
  var navbars = document.querySelectorAll(".c-nav[data-nav-overflow]");
  if (!navbars.length) return;

  // Breakpoint where the desktop navigation layout starts
  var BREAKPOINT_MD = 768;

  /**
   * Checks if the navigation items overflow the available space
   * and toggles the overflow class when necessary.
   */
  function updateNavbarOverflow(navbar) {
    var inner = navbar.querySelector(".c-nav__inner");
    if (!inner) return;

    // On small screens we disable overflow behavior completely
    if (window.innerWidth < BREAKPOINT_MD) {
      navbar.classList.remove("c-nav--overflow");
      return;
    }

    /**
     * Measure the natural width first.
     * We temporarily remove the overflow class so we can compare
     * the real scroll width vs the visible container width.
     */
    navbar.classList.remove("c-nav--overflow");

    var needsOverflow = inner.scrollWidth > inner.clientWidth + 2;

    // Apply overflow mode if content exceeds the available space
    navbar.classList.toggle("c-nav--overflow", needsOverflow);
  }

  /**
   * Updates all navbars on the page.
   */
  function updateAll() {
    navbars.forEach(updateNavbarOverflow);
  }

  /**
   * Schedules an update using requestAnimationFrame.
   * This prevents multiple expensive layout calculations
   * during rapid resize events.
   */
  var scheduled = false;
  function scheduleUpdate() {
    if (scheduled) return;

    scheduled = true;

    window.requestAnimationFrame(function () {
      scheduled = false;
      updateAll();
    });
  }

  // Recalculate on viewport changes
  window.addEventListener("resize", scheduleUpdate, { passive: true });
  window.addEventListener("orientationchange", scheduleUpdate, { passive: true });

  /**
   * Fonts can change text width after loading,
   * so we re-check the layout once fonts are ready.
   */
  if (document.fonts && typeof document.fonts.ready === "object") {
    document.fonts.ready.then(scheduleUpdate).catch(function () {});
  }

  /**
   * Observe container size changes (for example when layout shifts).
   * This is more precise than relying only on window resize.
   */
  if (window.ResizeObserver) {
    var observer = new ResizeObserver(scheduleUpdate);

    navbars.forEach(function (navbar) {
      var container = navbar.querySelector(".c-nav__container") || navbar;
      observer.observe(container);
    });
  }

  // Initial calculation
  scheduleUpdate();
})();