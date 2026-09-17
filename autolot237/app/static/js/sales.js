document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("checklistTable");
  if (!table) return;

  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

  table.querySelectorAll(".sold-checkbox").forEach(function (checkbox) {
    checkbox.addEventListener("change", function () {
      if (!checkbox.checked) return;

      const productId = checkbox.dataset.productId;
      const qtyInput = document.getElementById(`qty-${productId}`);
      const priceInput = document.getElementById(`price-${productId}`);
      const overrideInput = document.getElementById(`override-${productId}`);
      const statusRow = document.getElementById(`status-row-${productId}`);
      const statusSpan = document.getElementById(`status-${productId}`);
      const stockSpan = document.getElementById(`stock-${productId}`);

      const quantity = parseInt(qtyInput.value, 10) || 0;
      const sellingPrice = parseFloat(priceInput.value) || 0;

      checkbox.disabled = true;
      statusRow.style.display = "table-row";
      statusSpan.textContent = "Recording sale…";
      statusSpan.style.color = "var(--ink-muted)";

      fetch("/sales/quick-sale", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          product_id: productId,
          quantity: quantity,
          selling_price: sellingPrice,
          allow_below_min: overrideInput ? overrideInput.checked : false,
        }),
      })
        .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
          if (ok && data.success) {
            statusSpan.textContent = "✓ " + data.message;
            statusSpan.style.color = "var(--accent-dark)";
            if (stockSpan) {
              stockSpan.textContent = data.stock;
              stockSpan.classList.toggle("stock-low", data.stock <= 5);
              stockSpan.classList.toggle("stock-ok", data.stock > 5);
            }
          } else {
            statusSpan.textContent = "✕ " + (data.message || "Could not record this sale.");
            statusSpan.style.color = "var(--danger)";
          }
        })
        .catch(() => {
          statusSpan.textContent = "✕ Network error — please try again.";
          statusSpan.style.color = "var(--danger)";
        })
        .finally(() => {
          checkbox.checked = false;
          checkbox.disabled = false;
          setTimeout(function () {
            statusRow.style.display = "none";
          }, 5000);
        });
    });
  });
});
