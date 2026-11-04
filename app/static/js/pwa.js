(function () {
  // ---- service worker (needed for install) ----
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  }

  var fab = document.getElementById("pwaFab");
  if (!fab) return;
  var installBtn = document.getElementById("pwaInstall"), closeBtn = document.getElementById("pwaClose");
  var sheet = document.getElementById("pwaSheet"), sheetTitle = document.getElementById("pwaSheetTitle");
  var sheetText = document.getElementById("pwaSheetText"), sheetSteps = document.getElementById("pwaSheetSteps");
  var sheetOk = document.getElementById("pwaSheetOk");

  var ua = navigator.userAgent || "";
  var isIOS = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var isAndroid = /android/i.test(ua);
  var isFirefox = /firefox|fxios/i.test(ua);
  var isSafari = /safari/i.test(ua) && !/chrome|crios|fxios|edgios|android/i.test(ua);
  var standalone = (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || window.navigator.standalone === true;
  var deferred = null;

  function dismissed() { try { return sessionStorage.getItem("pwaFabHidden") === "1"; } catch (e) { return false; } }
  function show() { if (!standalone && !dismissed()) fab.hidden = false; }
  function hide() { fab.hidden = true; }

  window.addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferred = e; show(); });
  window.addEventListener("appinstalled", function () { hide(); });
  show();   // always visible (unless already installed) so iPhone and PC users see it too

  function openSheet(title, text, steps) {
    sheetTitle.textContent = title; sheetText.textContent = text;
    sheetSteps.innerHTML = steps.map(function (s) { return "<li>" + s + "</li>"; }).join("");
    sheet.hidden = false;
  }
  function closeSheet() { sheet.hidden = true; }
  sheetOk.addEventListener("click", closeSheet);
  sheet.addEventListener("click", function (e) { if (e.target === sheet) closeSheet(); });

  installBtn.addEventListener("click", function () {
    if (deferred) {                                   // Android + Chrome/Edge on PC: real install prompt
      deferred.prompt();
      deferred.userChoice.finally(function () { deferred = null; });
      return;
    }
    if (isIOS) {
      openSheet("Install on iPhone / iPad", "Apple only allows installing from the Share menu.",
        isSafari ? ["Tap the <b>Share</b> button (square with an arrow) at the bottom of Safari.",
                    "Scroll down and tap <b>Add to Home Screen</b>.", "Tap <b>Add</b>. The AutoLot237 icon appears on your home screen."]
                 : ["Open this page in <b>Safari</b> (copy the address into Safari).",
                    "Tap the <b>Share</b> button, then <b>Add to Home Screen</b>.", "Tap <b>Add</b>."]);
    } else if (isAndroid) {
      openSheet("Install on Android", "Use your browser menu to install the app.",
        ["Tap the <b>&#8942; menu</b> at the top right of Chrome.", "Tap <b>Install app</b> or <b>Add to Home screen</b>.", "Confirm with <b>Install</b>."]);
    } else if (isFirefox) {
      openSheet("Install on a computer", "Firefox cannot install web apps on computers.",
        ["Open this page in <b>Google Chrome</b> or <b>Microsoft Edge</b>.", "Click the <b>install icon</b> in the address bar, or choose <b>Install AutoLot237</b> from the menu."]);
    } else if (isSafari) {
      openSheet("Install on Mac", "Safari adds the app to your Dock.",
        ["Open the <b>File</b> menu in Safari.", "Click <b>Add to Dock</b>.", "Click <b>Add</b>."]);
    } else {
      openSheet("Install on a computer", "Look for the install option in your browser.",
        ["Click the <b>install icon</b> at the right end of the address bar,", "or open the browser menu and choose <b>Install AutoLot237</b>.", "Then confirm with <b>Install</b>."]);
    }
  });

  closeBtn.addEventListener("click", function () {
    hide(); try { sessionStorage.setItem("pwaFabHidden", "1"); } catch (e) {}
  });
})();
