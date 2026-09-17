document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("refreshInsightsForm");
  if (!form) return;
  form.addEventListener("submit", function () {
    const btn = form.querySelector("button[type=submit]");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Analyzing…";
    }
  });
});
