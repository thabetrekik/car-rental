document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.querySelector("[data-password-toggle]");
  const passwordField = document.getElementById("password-field");
  const toggleIcon = document.getElementById("toggle-icon");

  if (!toggle || !passwordField || !toggleIcon) {
    return;
  }

  toggle.addEventListener("click", function () {
    const shouldShow = passwordField.type === "password";
    passwordField.type = shouldShow ? "text" : "password";
    toggleIcon.classList.toggle("fa-eye", shouldShow);
    toggleIcon.classList.toggle("fa-eye-slash", !shouldShow);
  });
});
