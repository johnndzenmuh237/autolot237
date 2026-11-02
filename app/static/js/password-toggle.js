// Adds a "Show / Hide" button to every password box so people can see what they type.
(function () {
  function enhance(input) {
    if (input.dataset.toggled) return;
    input.dataset.toggled = "1";
    var wrap = document.createElement("div");
    wrap.className = "pw-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pw-toggle";
    btn.textContent = "Show";
    btn.setAttribute("aria-label", "Show or hide password");
    btn.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "Hide" : "Show";
    });
    wrap.appendChild(btn);
  }
  function run() { document.querySelectorAll('input[type="password"]').forEach(enhance); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run); else run();
})();
