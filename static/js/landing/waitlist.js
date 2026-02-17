/**
 * Lanzaxperience - Waitlist dynamic fields
 * Controls conditional visibility of:
 * - Island (only if region = canarias)
 * - Official guide checkbox (only if role = guide or both)
 */

document.addEventListener("DOMContentLoaded", function () {
  const regionSelect = document.getElementById("waitlist_region");
  const roleSelect = document.getElementById("waitlist_role");

  const islandWrap = document.getElementById("waitlist_island_wrap");
  const islandSelect = document.getElementById("waitlist_island");

  const officialWrap = document.getElementById("waitlist_official_wrap");
  const officialCheckbox = document.getElementById("waitlist_official");

  if (!regionSelect || !roleSelect) return;

  function syncWaitlistFields() {
    // ----- ISLAND -----
    const isCanarias = regionSelect.value === "canarias";

    if (isCanarias) {
      islandWrap.classList.remove("hidden");
    } else {
      islandWrap.classList.add("hidden");
      if (islandSelect) islandSelect.value = "";
    }

    // ----- OFFICIAL GUIDE -----
    const isGuide = roleSelect.value === "guide" || roleSelect.value === "both";

    if (isGuide) {
      officialWrap.classList.remove("hidden");
    } else {
      officialWrap.classList.add("hidden");
      if (officialCheckbox) officialCheckbox.checked = false;
    }
  }

  regionSelect.addEventListener("change", syncWaitlistFields);
  roleSelect.addEventListener("change", syncWaitlistFields);

  // Initial sync (important if page reloads with values)
  syncWaitlistFields();
});
