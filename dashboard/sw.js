// panel sürümü: 2026-11-28c (hızlı stüdyo tekrar soru düzeltmesi)
self.addEventListener("install", (e) => self.skipWaiting());
self.addEventListener("activate", (e) => self.clients.claim());
self.addEventListener("fetch", () => {});
// telefona bildirim: video hazır, iş hata verdi vs.
self.addEventListener("push", (e) => {
  let d = {}; try { d = e.data.json(); } catch { d = { baslik: "Animasyon Tarih", metin: e.data?.text() || "" }; }
  e.waitUntil(self.registration.showNotification(d.baslik || "Animasyon Tarih", { body: d.metin || "", icon: "/icon-192.png", badge: "/icon-192.png", data: { url: d.url || "/" }, tag: d.url || "genel" }));
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close(); const url = e.notification.data?.url || "/";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
    for (const c of cs) if ("focus" in c) { c.navigate(url).catch(() => {}); return c.focus(); }
    return self.clients.openWindow(url);
  }));
});
