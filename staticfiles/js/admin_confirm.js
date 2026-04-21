document.addEventListener("submit", function (event) {
  const form = event.target;
  const message = form.dataset.confirm;

  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});
