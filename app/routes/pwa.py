from flask import Blueprint, jsonify, url_for, Response

pwa_bp = Blueprint("pwa", __name__)

SERVICE_WORKER = r"""
// AutoLot237 service worker: makes the app installable and keeps static files
// fast. Pages and API calls always go to the network, so nobody ever sees
// stale or another user's data.
const CACHE = "autolot237-static-v1";
self.addEventListener("install", (e) => { self.skipWaiting(); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin && url.pathname.startsWith("/static/")) {
    e.respondWith(caches.open(CACHE).then(async (c) => {
      const hit = await c.match(req);
      const net = fetch(req).then((r) => { if (r.ok) c.put(req, r.clone()); return r; }).catch(() => hit);
      return hit || net;
    }));
    return;
  }
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => new Response(
      "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><title>Offline</title>" +
      "<body style='font-family:sans-serif;text-align:center;padding:15vh 24px;color:#1A1A2E'>" +
      "<h2>You are offline</h2><p>AutoLot237 needs an internet connection. Please reconnect and try again.</p></body>",
      { headers: { "Content-Type": "text/html" } })));
  }
});
"""


@pwa_bp.route("/manifest.webmanifest")
def manifest():
    data = {
        "name": "AutoLot237 Business Manager",
        "short_name": "AutoLot237",
        "description": "Sales, inventory, finance and staff management for AutoLot237.",
        "start_url": "/staff",
        "scope": "/",
        "display": "standalone",
        "background_color": "#1A1A2E",
        "theme_color": "#1A1A2E",
        "icons": [
            {"src": url_for("static", filename="images/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": url_for("static", filename="images/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": url_for("static", filename="images/icon-512-maskable.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    resp = jsonify(data)
    resp.headers["Content-Type"] = "application/manifest+json"
    return resp


@pwa_bp.route("/sw.js")
def service_worker():
    resp = Response(SERVICE_WORKER, mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp
