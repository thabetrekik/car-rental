document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("deposit-reservation-search");
  const reservationSelect = searchInput ? searchInput.parentElement.querySelector("select") : null;

  if (!searchInput || !reservationSelect) {
    return;
  }

  const originalOptions = Array.from(reservationSelect.options).map(function (option) {
    return {
      value: option.value,
      text: option.text,
      selected: option.selected,
    };
  });

  const renderOptions = function (query) {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    const currentValue = reservationSelect.value;
    reservationSelect.innerHTML = "";
    let hasMatch = false;

    originalOptions.forEach(function (optionData) {
      const haystack = optionData.text.toLowerCase();
      const matches = words.length === 0 || words.every(function (word) {
        return haystack.includes(word);
      });

      if (!matches) {
        return;
      }

      hasMatch = true;
      const option = document.createElement("option");
      option.value = optionData.value;
      option.textContent = optionData.text;
      if (optionData.value === currentValue || (!currentValue && optionData.selected)) {
        option.selected = true;
      }
      reservationSelect.appendChild(option);
    });

    if (!hasMatch) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No reservation found";
      option.selected = true;
      reservationSelect.appendChild(option);
    }
  };

  searchInput.addEventListener("input", function (event) {
    renderOptions(event.target.value);
  });
});
