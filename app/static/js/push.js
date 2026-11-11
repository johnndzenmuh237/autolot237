// Phone / desktop notifications that arrive even when the app is closed (Web Push).
(function () {
  if (!document.getElementById("notifRoot")) return;          // signed-in pages only
  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  var ua = navigator.userAgent || "";
  var isIOS = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var standalone = (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || window.navigator.standalone === true;
  var supported = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  var btn = document.getElementById("notifEnable");
  var DISMISS = "pushBannerDismissed";

  function b64(s) {
    var p = "=".repeat((4 - s.length % 4) % 4), r = (s + p).replace(/-/g, "+").replace(/_/g, "/"), raw = atob(r), out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }
  function post(url, body) {
    return fetch(url, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: JSON.stringify(body || {}) });
  }

  function enable() {
    if (!supported) return Promise.resolve(false);
    return fetch("/push/config", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (cfg) {
      if (!cfg.enabled) return false;
      return Notification.requestPermission().then(function (perm) {
        if (perm !== "granted") return false;
        return navigator.serviceWorker.ready.then(function (reg) {
          return reg.pushManager.getSubscription().then(function (sub) {
            return sub || reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(cfg.publicKey) });
          });
        }).then(function (sub) { return post("/push/subscribe", sub.toJSON()); }).then(function () { return true; });
      });
    }).catch(function () { return false; });
  }

  function removeBanner() { var b = document.getElementById("pushBanner"); if (b) b.remove(); }
  function iosInstallFirst() {
    var fab = document.getElementById("pwaInstall"); if (fab) fab.click();
  }

  function showBanner(text, actionLabel, action) {
    try { if (sessionStorage.getItem(DISMISS) === "1") return; } catch (e) {}
    var host = document.querySelector(".content") || document.body;
    var b = document.createElement("div");
    b.className = "push-banner"; b.id = "pushBanner";
    b.innerHTML = "<p></p><button class='btn btn-primary' type='button'></button><button class='btn btn-secondary' type='button'>Not now</button>";
    b.querySelector("p").textContent = text;
    var ok = b.querySelectorAll("button")[0], no = b.querySelectorAll("button")[1];
    ok.textContent = actionLabel;
    ok.addEventListener("click", action);
    no.addEventListener("click", function () { try { sessionStorage.setItem(DISMISS, "1"); } catch (e) {} removeBanner(); });
    host.insertBefore(b, host.firstChild);
  }

  function setPanelButton(label, handler) {
    if (!btn) return;
    if (!label) { btn.hidden = true; return; }
    btn.textContent = label; btn.hidden = false; btn.onclick = handler;
  }

  function turnOn() {
    enable().then(function (done) {
      if (done) { removeBanner(); setPanelButton(null); post("/push/test"); }
      else if (Notification.permission === "denied") { alert("Notifications are blocked for this site. Open your browser or phone settings, allow notifications for AutoLot237, then try again."); }
    });
  }

  if (!supported) {
    if (isIOS && !standalone) {
      setPanelButton("Phone alerts: install the app first", iosInstallFirst);
      showBanner("To get alerts on your iPhone even when the app is closed, first add AutoLot237 to your Home Screen, then open it from there.", "How to install", iosInstallFirst);
    }
    return;
  }

  if (Notification.permission === "granted") {
    enable();                                           // quietly keep this device registered
  } else if (Notification.permission === "denied") {
    setPanelButton("Phone alerts are blocked — how to allow", function () { alert("Open your browser or phone settings, allow notifications for AutoLot237, then reload this page."); });
  } else {
    setPanelButton("Turn on phone alerts", turnOn);
    showBanner("Get alerts on your phone or computer — even when the app is closed — for new messages, sales and updates.", "Turn on alerts", turnOn);
  }
})();
