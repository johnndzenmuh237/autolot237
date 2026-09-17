document.addEventListener("DOMContentLoaded", function () {
  const canvas = document.getElementById("categoryChart");
  if (!canvas || typeof Chart === "undefined") return;

  const labels = JSON.parse(canvas.dataset.labels || "[]");
  const values = JSON.parse(canvas.dataset.values || "[]");

  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: ["#1E7A5B", "#B0791A", "#35618C", "#B2382F", "#7C9187", "#145A43"],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "right", labels: { font: { family: "Inter", size: 11 }, boxWidth: 10 } } },
    },
  });
});
