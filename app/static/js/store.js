document.addEventListener("DOMContentLoaded", function () {
  /* ---------- scroll-reveal animations (decorative only — never gates
     product content on JS/IntersectionObserver actually firing) ---------- */
  var revealEls = document.querySelectorAll(".reveal");
  if (revealEls.length) {
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            io.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });
      revealEls.forEach(function (el) { io.observe(el); });
    }
    // Safety net: whatever happens with the observer (unsupported browser,
    // in-app webview quirks, a JS error elsewhere on the page), nothing
    // stays invisible for more than a second.
    setTimeout(function () {
      revealEls.forEach(function (el) { el.classList.add("in-view"); });
    }, 1200);
  }

  var toggle = document.getElementById("navToggle");
  var nav = document.getElementById("storeNav");
  var overlay = document.getElementById("navOverlay");
  var lockedScrollY = 0;

  function openNav() {
    nav.classList.add("open");
    overlay.classList.add("open");
    toggle.classList.add("active");
    toggle.setAttribute("aria-expanded", "true");
    // iOS Safari ignores plain `overflow: hidden` on the body and still lets
    // the page "rubber-band" scroll behind a fixed drawer — pinning the body
    // in place with position:fixed is the reliable cross-browser fix.
    lockedScrollY = window.scrollY || window.pageYOffset || 0;
    document.body.style.position = "fixed";
    document.body.style.top = "-" + lockedScrollY + "px";
    document.body.style.left = "0";
    document.body.style.right = "0";
    document.body.style.width = "100%";
  }
  function closeNav() {
    nav.classList.remove("open");
    overlay.classList.remove("open");
    toggle.classList.remove("active");
    toggle.setAttribute("aria-expanded", "false");
    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.left = "";
    document.body.style.right = "";
    document.body.style.width = "";
    window.scrollTo(0, lockedScrollY);
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

  /* ---------- cookie consent + analytics ---------- */
  var CONSENT_KEY = "autolot_cookie_consent"; // "accepted" | "declined"

  function loadAnalytics() {
    var gaId = window.AUTOLOT_GA_ID;
    if (!gaId || window.gtag) return; // no GA configured, or already loaded
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + gaId;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", gaId, { anonymize_ip: true });
  }

  function trackEvent(name, params) {
    if (typeof window.gtag === "function") {
      window.gtag("event", name, params || {});
    }
  }
  window.autolotTrack = trackEvent; // exposed so other scripts/inline handlers can fire events

  var cookieBanner = document.getElementById("cookieBanner");
  var consent = null;
  try { consent = localStorage.getItem(CONSENT_KEY); } catch (e) { /* storage blocked — treat as no consent recorded */ }

  if (consent === "accepted") {
    loadAnalytics();
  } else if (consent !== "declined" && cookieBanner) {
    cookieBanner.classList.add("open");
  }

  var acceptBtn = document.getElementById("cookieAccept");
  var declineBtn = document.getElementById("cookieDecline");
  if (acceptBtn) {
    acceptBtn.addEventListener("click", function () {
      try { localStorage.setItem(CONSENT_KEY, "accepted"); } catch (e) {}
      cookieBanner.classList.remove("open");
      loadAnalytics();
    });
  }
  if (declineBtn) {
    declineBtn.addEventListener("click", function () {
      try { localStorage.setItem(CONSENT_KEY, "declined"); } catch (e) {}
      cookieBanner.classList.remove("open");
    });
  }

  /* ---------- conversion tracking: clicks on key actions ---------- */
  document.querySelectorAll("[data-wa-button]").forEach(function (btn) {
    btn.addEventListener("click", function () { trackEvent("whatsapp_click", {}); });
  });
  document.querySelectorAll('a[href^="tel:"]').forEach(function (el) {
    el.addEventListener("click", function () { trackEvent("phone_click", {}); });
  });
  document.querySelectorAll('a[href^="mailto:"]').forEach(function (el) {
    el.addEventListener("click", function () { trackEvent("email_click", {}); });
  });
  var checkoutForm = document.getElementById("checkout-form");
  if (checkoutForm) {
    checkoutForm.addEventListener("submit", function () { trackEvent("checkout_submit", {}); });
  }
});
