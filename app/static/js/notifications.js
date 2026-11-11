(function () {
  var root = document.getElementById("notifRoot");
  if (!root) return;
  var bell = document.getElementById("notifBell"), panel = document.getElementById("notifPanel");
  var countEl = document.getElementById("notifCount"), list = document.getElementById("notifItems");
  var readAll = document.getElementById("notifReadAll");
  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  var lastUnread = null, baseline = null, stack = null;

  function toast(n) {
    if (!stack) { stack = document.createElement("div"); stack.className = "toast-stack"; stack.setAttribute("aria-live", "polite"); document.body.appendChild(stack); }
    var a = document.createElement("a");
    a.className = "toast"; a.href = n.open_url;
    a.innerHTML = '<span><strong>' + esc(n.title) + '</strong><span class="t-msg">' + esc(n.message) + '</span></span>';
    var x = document.createElement("button");
    x.type = "button"; x.className = "toast-x"; x.setAttribute("aria-label", "Dismiss"); x.innerHTML = "&times;";
    x.addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); a.remove(); });
    a.appendChild(x); stack.appendChild(a);
    setTimeout(function () { a.remove(); }, 9000);
    while (stack.children.length > 3) stack.removeChild(stack.firstChild);
  }

  function announce(data) {
    var key = "notifBaseline_" + data.user_id, saved = null;
    try { saved = sessionStorage.getItem(key); } catch (e) {}
    if (baseline === null) baseline = saved === null ? data.latest_id : parseInt(saved, 10);
    data.items.slice().reverse().forEach(function (n) {
      if (n.id > baseline && !n.is_read) toast(n);
    });
    baseline = Math.max(baseline, data.latest_id);
    try { sessionStorage.setItem(key, String(baseline)); } catch (e) {}
  }

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
        announce(data);
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
  setInterval(poll, 15000);                       // automatic refresh every 15 s
  document.addEventListener("visibilitychange", function () { if (!document.hidden) poll(); });
})();
