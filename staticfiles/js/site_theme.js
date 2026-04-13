"use strict";

(function () {
  const storageKey = "car_rental_theme";
  const root = document.body;
  const toggle = document.querySelector("[data-theme-toggle]");

  if (!toggle) {
    return;
  }

  const label = toggle.querySelector("[data-theme-label]");
  const icon = toggle.querySelector("i");

  function applyTheme(theme) {
    const isDark = theme === "dark";
    root.setAttribute("data-theme", theme);
    toggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");

    if (label) {
      label.textContent = isDark ? "Light mode" : "Dark mode";
    }

    if (icon) {
      icon.className = isDark ? "fa-solid fa-sun" : "fa-solid fa-moon";
    }
  }

  const storedTheme = localStorage.getItem(storageKey);
  if (storedTheme === "dark" || storedTheme === "light") {
    applyTheme(storedTheme);
  } else {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(prefersDark ? "dark" : "light");
  }

  toggle.addEventListener("click", function () {
    const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
    localStorage.setItem(storageKey, nextTheme);
  });
})();
