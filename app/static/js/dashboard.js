document.addEventListener("DOMContentLoaded", function () {
  const canvas = document.getElementById("trendChart");
  if (!canvas || typeof Chart === "undefined") return;

  const labels = JSON.parse(canvas.dataset.labels || "[]");
  const revenue = JSON.parse(canvas.dataset.revenue || "[]");
  const profit = JSON.parse(canvas.dataset.profit || "[]");

  new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Revenue",
          data: revenue,
          borderColor: "#1E7A5B",
          backgroundColor: "rgba(30, 122, 91, 0.08)",
          tension: 0.3,
          fill: true,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "Profit",
          data: profit,
          borderColor: "#B0791A",
          backgroundColor: "rgba(176, 121, 26, 0.06)",
          tension: 0.3,
          fill: true,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", align: "end", labels: { boxWidth: 10, font: { family: "Inter", size: 11 } } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { family: "IBM Plex Mono", size: 10 } } },
        y: { grid: { color: "#EBF1EE" }, ticks: { font: { family: "IBM Plex Mono", size: 10 } } },
      },
    },
  });
});
