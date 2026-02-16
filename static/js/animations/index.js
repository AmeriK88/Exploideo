// Marca que JS está activo (para animaciones y fallbacks)
document.documentElement.classList.add("js");

import { initPageTransitions } from "./page_transitions.js";
import { initScrollReveal } from "./scroll_reveal.js";

document.addEventListener("DOMContentLoaded", () => {
  initPageTransitions();
  initScrollReveal();
});
