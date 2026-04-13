document.addEventListener("DOMContentLoaded", () => {
  const tabs = document.querySelectorAll(".tab");
  const sections = document.querySelectorAll(".form-section");

  const setActive = (targetId) => {
    tabs.forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.target === targetId);
    });
    sections.forEach((section) => {
      section.classList.toggle("active", section.id === targetId);
    });
  };

  const resolveTarget = () => {
    const hash = window.location.hash.replace("#", "");
    if (!hash) {
      return null;
    }
    if (hash === "clients") {
      return "client-form";
    }
    if (hash === "vehicles") {
      return "vehicle-form";
    }
    if (hash === "maintenance") {
      return "maintenance-form";
    }
    if (hash === "client-form" || hash === "vehicle-form") {
      return hash;
    }
    if (hash === "maintenance-form") {
      return hash;
    }
    return null;
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      event.preventDefault();
      setActive(tab.dataset.target);
    });
  });

  const applyHash = () => {
    const target = resolveTarget();
    if (target) {
      setActive(target);
    }
  };

  window.addEventListener("hashchange", applyHash);
  applyHash();
});
