document.addEventListener("DOMContentLoaded", function () {
  const quoteRoot = document.querySelector("[data-daily-price]");
  const startInput = document.getElementById("id_start_date");
  const endInput = document.getElementById("id_end_date");
  const quoteDays = document.getElementById("quoteDays");
  const quoteTotal = document.getElementById("quoteTotal");

  if (!quoteRoot || !startInput || !endInput || !quoteDays || !quoteTotal) {
    return;
  }

  const dailyPrice = parseFloat(String(quoteRoot.dataset.dailyPrice).replace(",", "."));

  function updateQuote() {
    if (!startInput.value || !endInput.value) {
      quoteDays.textContent = "0";
      quoteTotal.textContent = "$0";
      return;
    }

    const startDate = new Date(startInput.value + "T00:00:00");
    const endDate = new Date(endInput.value + "T00:00:00");
    const days = Math.floor((endDate - startDate) / 86400000) + 1;

    if (days <= 0) {
      quoteDays.textContent = "0";
      quoteTotal.textContent = "$0";
      return;
    }

    quoteDays.textContent = String(days);
    quoteTotal.textContent = "$" + (dailyPrice * days).toFixed(0);
  }

  startInput.addEventListener("change", updateQuote);
  endInput.addEventListener("change", updateQuote);
  updateQuote();
});
