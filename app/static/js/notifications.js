(function () {
  var root = document.getElementById("notifRoot");
  if (!root) return;
  var bell = document.getElementById("notifBell"), panel = document.getElementById("notifPanel");
  var countEl = document.getElementById("notifCount"), list = document.getElementById("notifItems");
  var readAll = document.getElementById("notifReadAll");
  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  var lastUnread = null;

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

  function render(data) {
    if (data.unread > 0) { countEl.textContent = data.unread > 99 ? "99+" : data.unread; countEl.hidden = false; }
    else { countEl.hidden = true; }
    if (!data.items.length) { list.innerHTML = '<p class="notif-empty">No notifications yet.</p>'; return; }
    list.innerHTML = data.items.map(function (n) {
      return '<a class="notif-item ' + (n.is_read ? "" : "unread") + '" href="' + esc(n.open_url) + '">' +
        '<span class="notif-dot"></span><span class="notif-body"><strong>' + esc(n.title) + '</strong><span>' +
        esc(n.message) + '</span></span><span class="notif-time">' + esc(n.when) + '</span></a>';
    }).join("");
  }

  function poll() {
    if (document.hidden) return;
    fetch(root.dataset.api, { credentials: "same-origin", headers: { "Accept": "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        render(data);
        if (lastUnread !== null && data.unread > lastUnread && document.title.indexOf("(") !== 0) {
          document.title = "(" + data.unread + ") " + document.title;
        }
        lastUnread = data.unread;
      }).catch(function () {});
  }

  bell.addEventListener("click", function (e) {
    e.stopPropagation();
    panel.hidden = !panel.hidden;
    bell.setAttribute("aria-expanded", String(!panel.hidden));
    if (!panel.hidden) poll();
  });
  document.addEventListener("click", function (e) { if (!root.contains(e.target)) panel.hidden = true; });
  readAll.addEventListener("click", function () {
    fetch(root.dataset.readall, { method: "POST", credentials: "same-origin",
      headers: { "X-CSRFToken": csrf, "Accept": "application/json" } }).then(poll);
  });

  poll();
  setInterval(poll, 20000);                       // automatic refresh every 20 s
  document.addEventListener("visibilitychange", function () { if (!document.hidden) poll(); });
})();
