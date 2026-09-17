document.addEventListener("DOMContentLoaded", function () {
  const chips = document.querySelectorAll(".category-chip");
  chips.forEach((chip) => {
    chip.addEventListener("click", function (e) {
      // Native navigation via href; this just gives instant visual feedback
      chips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
    });
  });
});
