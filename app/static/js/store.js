document.addEventListener("DOMContentLoaded", function () {
  /* ---------- mobile nav (drawer) ---------- */
  var toggle = document.getElementById("navToggle");
  var nav = document.getElementById("storeNav");
  var overlay = document.getElementById("navOverlay");

  function openNav() {
    nav.classList.add("open");
    overlay.classList.add("open");
    toggle.classList.add("active");
    toggle.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }
  function closeNav() {
    nav.classList.remove("open");
    overlay.classList.remove("open");
    toggle.classList.remove("active");
    toggle.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }
  if (toggle && nav && overlay) {
    toggle.addEventListener("click", function () {
      nav.classList.contains("open") ? closeNav() : openNav();
    });
    overlay.addEventListener("click", closeNav);
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", closeNav);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeNav();
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 860) closeNav();
    });
  }

  /* ---------- gallery ---------- */
  var mainImg = document.querySelector(".gallery-main img");
  document.querySelectorAll(".gallery-thumbs img").forEach(function (thumb) {
    thumb.addEventListener("click", function () {
      if (mainImg) mainImg.src = thumb.src.replace(/w=\d+/, "w=1000");
      document.querySelectorAll(".gallery-thumbs img").forEach(function (t) { t.classList.remove("active"); });
      thumb.classList.add("active");
    });
  });

  /* ---------- filters: auto-submit on change ---------- */
  var filterForm = document.querySelector("#filter-form");
  if (filterForm) {
    filterForm.querySelectorAll("select").forEach(function (el) {
      el.addEventListener("change", function () { filterForm.submit(); });
    });
  }

  /* ---------- WhatsApp click-to-chat: log a lead, then open wa.me ---------- */
  document.querySelectorAll("[data-wa-button]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var carSlug = btn.getAttribute("data-car-slug") || "";
      fetch("/api/whatsapp-lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ car_slug: carSlug, source: "whatsapp_button" }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.whatsapp_url) {
            window.open(data.whatsapp_url, "_blank");
          } else {
            alert("WhatsApp isn't configured yet — set WHATSAPP_NUMBER in your environment.");
          }
        })
        .catch(function () {
          window.open("https://wa.me/", "_blank");
        });
    });
  });

  /* ---------- AI chat widget ---------- */
  var launcher = document.querySelector("#ai-chat-launcher");
  var panel = document.querySelector("#ai-chat-panel");
  var body = document.querySelector("#ai-chat-body");
  var form = document.querySelector("#ai-chat-form");
  var input = document.querySelector("#ai-chat-input");
  var history = [];

  function addMsg(role, text) {
    var div = document.createElement("div");
    div.className = "chat-msg " + (role === "user" ? "user" : "bot");
    div.textContent = text;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  if (launcher && panel) {
    launcher.addEventListener("click", function () {
      panel.classList.toggle("open");
      if (panel.classList.contains("open") && body.children.length === 0) {
        addMsg("bot", "Hi! I'm the AutoLot237 assistant. Ask me about a car, price, financing, or book a test drive.");
      }
    });
  }

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = input.value.trim();
      if (!text) return;
      addMsg("user", text);
      history.push({ role: "user", content: text });
      input.value = "";

      var typing = document.createElement("div");
      typing.className = "chat-msg bot";
      typing.textContent = "...";
      body.appendChild(typing);
      body.scrollTop = body.scrollHeight;

      fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: history }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          typing.remove();
          addMsg("bot", data.reply || "Sorry, I didn't catch that — try again?");
          history.push({ role: "assistant", content: data.reply || "" });
        })
        .catch(function () {
          typing.remove();
          addMsg("bot", "I'm having trouble connecting right now — try WhatsApp instead.");
        });
    });
  }
});
