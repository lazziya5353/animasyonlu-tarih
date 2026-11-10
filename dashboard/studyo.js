// Kurgu Stüdyosu: projenin zaman çizelgesi + ajanların canlı imleçleri.
// Olaylar: ajanlar GitHub'da çalışırken /api'ye "olay" yollar (scripts/olay.py); burası 2,5 sn'de bir yenilerini çeker.
const Q = new URLSearchParams(location.search);
const DEMO = Q.has("demo"), SLUG = (Q.get("p") || "").replace(/[^a-z0-9-]/g, "");
const TOKEN = localStorage.getItem("at_token") || "";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fmt = (t) => { t = Math.max(0, t || 0); const m = Math.floor(t / 60), s = (t % 60).toFixed(1).padStart(4, "0"); return `0${m}:${s}`; };

const AJAN = {
  arastirmaci: { ad: "araştırmacı", c: "#b6a6ff" }, senarist: { ad: "senarist", c: "#7fb4f5" }, ses: { ad: "ses", c: "#7fd6a4" },
  kurgucu: { ad: "kurgucu", c: "#f0c46a" }, efekt: { ad: "efekt", c: "#ef8fb0" }, kontrol: { ad: "kontrolcü", c: "#ff7b86" },
  yayinci: { ad: "yayıncı", c: "#5fd0b0" }, sen: { ad: "sen", c: "#ffffff" },
};

async function api(action, body = {}) {
  const r = await fetch("/api", { method: "POST", headers: { "content-type": "application/json", "x-panel-token": TOKEN }, body: JSON.stringify({ action, ...body }) });
  if (r.status === 401) { $("#giris").classList.remove("hide"); throw new Error("Giriş gerekli"); }
  const j = await r.json(); if (!r.ok) throw new Error(j.hata || "Hata"); return j;
}
const urlCache = {};
async function fileUrl(path) {
  if (DEMO) return `../${path}`;
  if (urlCache[path]) return urlCache[path];
  const r = await fetch("/api", { method: "POST", headers: { "content-type": "application/json", "x-panel-token": TOKEN }, body: JSON.stringify({ action: "file", path }) });
  return r.ok ? (urlCache[path] = URL.createObjectURL(await r.blob())) : null;
}
async function demoProje() {
  const g = (p) => fetch(`../projects/${SLUG}/${p}`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const [script, timed, ...k] = await Promise.all([g("script.json"), g("project.timed.json"), ...["senaryo", "ses", "gorsel", "kurgu"].map((x) => g(`kontrol/${x}.json`))]);
  return { script, timed, project: null, video: null, gorseller: (script?.sahneler || []).map((s) => s.image.split("/").pop()), dosyalar: ["ses.wav"],
    kontrol: Object.fromEntries(["senaryo", "ses", "gorsel", "kurgu"].map((x, i) => [x, k[i]])) };
}

// ───────── zaman çizelgesi verisi ─────────
let P, T, X, W = 1000;
function zamanCizelgesi(P) {
  const tm = P.timed;
  if (tm?.scenes?.[0]?.start != null) {
    const off = tm.voice_offset ?? 0.3;
    const sc = tm.scenes.map((s) => ({ ...s, start: s.start + off, end: s.end + off }));
    return { off, sc, cap: (tm.captions || []).map((c) => ({ ...c, start: c.start + off, end: c.end + off })),
      maps: (tm.maps || []).map((m) => ({ ...m, start: m.start + off, end: m.end + off })), cards: (tm.cards || []).map((c) => ({ ...c, start: c.start + off, end: c.end + off })),
      jumps: (tm.jumps || []).map((j) => ({ ...j, t: j.t + off })), ay: tm.ayyildiz ? tm.ayyildiz.map((x) => x + off) : null, eras: tm.eras || [],
      dur: tm.duration || sc[sc.length - 1].end, tahmini: false, muzik: !!tm.music?.aktif };
  }
  // henüz kurgulanmadı: cümle uzunluklarından tahmini zamanlar
  const S = P.script?.sahneler || P.project?.scenes || []; let t = 0.3; const sc = [], cap = [];
  S.forEach((s) => { const st = t; for (const l of s.lines || []) { const d = Math.max(1.2, l.length / 11.3); cap.push({ start: t, end: t + d, text: l }); t += d + 0.35; } sc.push({ ...s, start: st, end: t }); });
  return { off: 0.3, sc, cap, maps: [], cards: [], jumps: [], ay: null, eras: P.script?.eras || [], dur: t + 2, tahmini: true, muzik: !!P.project?.music?.aktif };
}

// ───────── çizim ─────────
const track = (k) => document.querySelector(`.track[data-tr="${k}"]`);
function clip(k, a, b, html, cls = "", veri = {}) {
  const el = document.createElement("div"); el.className = `clip c-${k} ${cls}`;
  el.style.left = X(a) + "px"; if (k !== "kontrol") el.style.width = Math.max(5, X(b) - X(a) - 2) + "px";
  el.innerHTML = html; Object.assign(el.dataset, veri); track(k).append(el); return el;
}
function temizle() { document.querySelectorAll(".track .clip").forEach((c) => c.remove()); }
async function dalga() {
  const cv = $("#wave"); cv.width = W; cv.height = 30; const g = cv.getContext("2d"); g.clearRect(0, 0, W, 30);
  try {
    const u = await fileUrl(`projects/${SLUG}/ses.wav`); if (!u) return;
    const buf = await new AudioContext().decodeAudioData(await (await fetch(u)).arrayBuffer());
    const d = buf.getChannelData(0), adim = Math.floor(buf.sampleRate / 20); let mx = 0; const e = [];
    for (let i = 0; i < d.length; i += adim) { let s = 0; for (let j = i; j < Math.min(d.length, i + adim); j += 8) s += d[j] * d[j]; e.push(Math.sqrt(s / (adim / 8))); mx = Math.max(mx, e[e.length - 1]); }
    g.fillStyle = "#8fd47a"; e.forEach((v, i) => { const x = X(T.off + i / 20), h = Math.max(1, (v / mx) * 28); g.fillRect(x, 15 - h / 2, Math.max(1, X(0.05) - X(0)), h); });
  } catch {}
}
function sahneKlibi(i, yeni) {
  const s = T.sc[i]; const im = $(`#pool [data-i="${i + 1}"]`)?.style.backgroundImage || "";
  return clip("gorsel", s.start, s.end, im ? `<img src=${im.slice(4, -1)}>` : `<span style="color:#9aa1b2;padding:4px;display:block">${i + 1}</span>`, yeni ? "yeni" : "", { sahne: i + 1 });
}
function hepsiniCiz() {
  temizle();
  T.cap.forEach((c) => clip("yazi", c.start, c.end, esc(c.text)));
  T.sc.forEach((s, i) => { sahneKlibi(i); const fx = [...(s.fx || []), ...(s.effect ? [s.effect] : [])]; if (fx.length) clip("efekt", s.start, Math.min(s.end, s.start + 2.6), esc(fx.join(" · "))); });
  T.cards.forEach((c) => clip("efekt", c.start, c.end, `sayaç ${esc(c.value)} ${esc(c.unit || "")}`));
  T.jumps.forEach((j) => clip("efekt", j.t, j.t + 1.4, `+${esc(j.value)} yıl`));
  if (T.ay) clip("efekt", T.ay[0], T.ay[3], "ay yıldız");
  T.maps.forEach((m) => clip("harita", m.start, m.end, esc(m.title || "harita")));
  if (T.muzik) clip("muzik", 0, T.dur, "♪ müzik · sese göre otomatik kısılır");
  kontrolIsaretleri();
}
function kontrolIsaretleri() {
  for (const [as, r] of Object.entries(P.kontrol || {})) for (const m of r?.maddeler || []) {
    if (m.seviye === "bilgi") continue; const s = T.sc[(m.sahne || 1) - 1] || T.sc[0];
    clip("kontrol", (s.start + s.end) / 2, 0, "", m.seviye, { sahne: m.sahne || "" }).title = `${as}: ${m.mesaj}`;
  }
}

// ───────── oynatma / denetçi ─────────
let cur = -1;
function era(i) { const e = (T.eras || []).find((e) => i >= e.from && i <= e.to); return e ? e.name : "—"; }
function anaGuncelle(t) {
  $("#tc").textContent = fmt(t); $("#ph").style.left = 92 + X(t) + "px";
  const i = T.sc.findIndex((s) => t >= s.start && t < s.end); if (i >= 0 && i !== cur) sahneSec(i);
  const c = T.cap.find((c) => t >= c.start - 0.05 && t <= c.end + 0.25); $("#icap").textContent = c ? c.text : "";
  $("#alt").textContent = P.video ? "" : c ? c.text : "";
  document.querySelectorAll(".c-yazi").forEach((el) => el.classList.toggle("sec", c && el.textContent === c.text));
}
function sahneSec(i) {
  cur = i; const s = T.sc[i];
  document.querySelectorAll("#pool div").forEach((d, k) => d.classList.toggle("on", k === i));
  $("#ibig").textContent = s.big || "—"; $("#isub").textContent = s.sub || "";
  $("#ifx").textContent = [...(s.fx || []), ...(s.effect ? [s.effect] : [])].join(", ") || "—"; $("#iera").textContent = era(i);
  $("#st").textContent = `Sahne ${i + 1} / ${T.sc.length}${s.year ? " · " + s.year : ""}`;
  const im = $(`#pool [data-i="${i + 1}"]`)?.style.backgroundImage; if (im && !P.video) $("#still").src = im.slice(5, -2);
  const md = Object.entries(P.kontrol || {}).flatMap(([as, r]) => (r?.maddeler || []).filter((m) => m.sahne === i + 1 && m.seviye !== "bilgi").map((m) => ({ ...m, as })));
  $("#ikon").innerHTML = md.length ? md.map((m) => `<div class="${m.seviye}">• ${esc(m.mesaj)}</div>`).join("") : `<div class="yok">Sorun yok ✓</div>`;
}
let oynuyor = false, sesEl = null;
function zaman() { return P.video ? $("#v").currentTime : sesEl ? sesEl.currentTime + T.off : 0; }
function dongu() { anaGuncelle(zaman()); if (oynuyor) requestAnimationFrame(dongu); }
function ara(t) { t = Math.max(0, Math.min(T.dur, t)); if (P.video) $("#v").currentTime = t; else if (sesEl) sesEl.currentTime = Math.max(0, t - T.off); anaGuncelle(t); }

// ───────── ajan imleçleri ─────────
const imlec = {};
function imlecAl(a) {
  if (imlec[a]) return imlec[a];
  const d = document.createElement("div"); d.className = "imlec"; d.style.setProperty("--c", AJAN[a]?.c || "#fff");
  d.innerHTML = `<svg viewBox="0 0 24 24"><path d="M3 2l7 19 2.5-7.5L20 11z" fill="${AJAN[a]?.c || "#fff"}" stroke="#000" stroke-width="1.3"/></svg><span>${esc(AJAN[a]?.ad || a)}</span>`;
  const ch = $(`.chip[data-a="${a}"]`)?.getBoundingClientRect(); const x = ch ? ch.left + scrollX + 20 : innerWidth - 60, y = ch ? ch.bottom + scrollY : 60;
  d.style.transform = `translate(${x}px,${y}px)`; $("#imlecler").append(d); return (imlec[a] = d);
}
function hedef(o) {
  const tr = { yazi: "yazi", gorsel: "gorsel", efekt: "efekt", harita: "harita", ses: "ses", muzik: "muzik", kontrol: "kontrol", ilerleme: "gorsel" }[o.tur];
  if (!tr) { const r = $("#log").getBoundingClientRect(); return [r.left + scrollX + 40 + Math.random() * 120, r.bottom + scrollY - 30]; }
  let t = o.t0 ?? (o.sahne && T.sc[o.sahne - 1] ? (T.sc[o.sahne - 1].start + T.sc[o.sahne - 1].end) / 2 : T.dur * 0.1);
  if (o.t1 != null && o.tur !== "ilerleme") t = (t + Math.min(o.t1, t + 3)) / 2;
  const r = track(tr).getBoundingClientRect(); return [r.left + scrollX + X(t) + 4, r.top + scrollY + 14];
}
function chipCiz(aktif) {
  $("#chips").innerHTML = Object.entries(AJAN).filter(([k]) => k !== "sen" || aktif[k]).map(([k, a]) => `<span class="chip ${aktif[k] ? "aktif" : ""}" data-a="${k}" style="--c:${a.c}"><i></i>${a.ad}</span>`).join("");
}

// ───────── olay işleme ─────────
const kuyruk = []; let hiz = 1, isleniyor = false, sonI = 0, sonOlayZ = 0, aktifler = {};
function logYaz(o) {
  const d = document.createElement("div"); const zt = o.z ? new Date(o.z * 1000).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "";
  d.innerHTML = `<span class="t">${zt}</span> <span class="a" style="color:${AJAN[o.ajan]?.c}">${esc(AJAN[o.ajan]?.ad || o.ajan)}</span> ${esc(o.mesaj)}`;
  $("#log").append(d); while ($("#log").children.length > 40) $("#log").firstChild.remove();
}
function uygula(o) {
  const t0 = o.t0, t1 = o.t1 ?? (t0 != null ? t0 + 1.5 : null);
  if (o.tur === "gorsel" && o.sahne && T.sc[o.sahne - 1]) {
    document.querySelectorAll(`.c-gorsel[data-sahne="${o.sahne}"]`).forEach((e) => e.remove()); sahneKlibi(o.sahne - 1, true);
    const p = $(`#pool [data-i="${o.sahne}"]`); if (p) { p.classList.add("flash"); setTimeout(() => p.classList.remove("flash"), 600); }
    sahneSec(o.sahne - 1);
  } else if (o.tur === "yazi" && t0 != null) clip("yazi", t0, t1, esc(o.mesaj.replace(/^“|” sese hizalandı$/g, "")), "yeni");
  else if (o.tur === "efekt" && t0 != null) clip("efekt", t0, t1, esc(o.mesaj.replace(/^Sahne \d+: /, "")), "yeni");
  else if (o.tur === "harita" && t0 != null) clip("harita", t0, t1, esc(o.mesaj.replace(/^Harita: /, "")), "yeni");
  else if (o.tur === "muzik") { document.querySelectorAll(".c-muzik").forEach((e) => e.remove()); clip("muzik", 0, T.dur, "♪ müzik · sese göre otomatik kısılır", "yeni"); }
  else if (o.tur === "ses" && t1 != null) { document.querySelectorAll(".c-ses").forEach((e) => e.remove()); dalga(); }
  else if (o.tur === "kontrol") { const s = T.sc[(o.sahne || 1) - 1] || T.sc[0]; clip("kontrol", (s.start + s.end) / 2, 0, "", (o.seviye || "") + " yeni").title = o.mesaj; }
  else if (o.tur === "ilerleme") {
    $("#rh").classList.add("on"); $("#rh").style.left = 92 + X(o.t0 || 0) + "px";
    $("#rbar").classList.add("on"); $("#rbar i").style.width = (o.yuzde || 0) + "%"; $("#rbar span").textContent = `Kurgucu kareleri işliyor %${o.yuzde || 0}`;
  }
  if (o.yuzde === 100) { $("#rh").classList.remove("on"); $("#rbar span").textContent = "Video hazır ✓"; setTimeout(() => $("#rbar").classList.remove("on"), 4000); }
}
async function isle() {
  if (isleniyor) return; isleniyor = true;
  while (kuyruk.length) {
    const o = kuyruk.shift(); const im = imlecAl(o.ajan);
    aktifler[o.ajan] = Date.now(); chipCiz(Object.fromEntries(Object.entries(aktifler).filter(([, v]) => Date.now() - v < 15000)));
    const [x, y] = hedef(o); im.style.transitionDuration = `${0.75 / hiz}s`; im.style.transform = `translate(${x}px,${y}px)`;
    await sleep(780 / hiz);
    im.classList.remove("tik"); void im.offsetWidth; im.classList.add("tik");
    uygula(o); logYaz(o);
    await sleep((kuyruk.length > 30 ? 120 : 260) / hiz);
  }
  isleniyor = false;
}
function canliGoster() {
  const on = Date.now() / 1000 - sonOlayZ < 90;
  $("#canli").className = "canli" + (on ? " on" : ""); $("#canli").textContent = on ? "● CANLI" : sonOlayZ ? `○ Son iş ${new Date(sonOlayZ * 1000).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}` : "○ Bekleniyor";
}
async function cek() {
  if (DEMO) return;
  try {
    const r = await api("olaylar", { slug: SLUG, den: sonI });
    for (const o of r.olaylar) { sonI = Math.max(sonI, o.i); sonOlayZ = Math.max(sonOlayZ, o.z || 0); kuyruk.push(o); }
    if (r.olaylar.length) { hiz = kuyruk.length > 20 ? 3 : 1; isle(); }
    if (r.olaylar.some((o) => o.yuzde === 100)) setTimeout(yenidenYukle, 6000);
  } catch {}
  canliGoster();
}
function sentetikOlaylar() { // hiç kayıt yoksa (eski projeler) zaman çizelgesinden süreci canlandır
  const L = [{ ajan: "ses", tur: "ses", mesaj: `Ses analiz ediliyor: ${T.cap.length} cümle`, t0: 0, t1: T.dur }];
  T.sc.forEach((s, i) => {
    L.push({ ajan: "kurgucu", tur: "gorsel", mesaj: `Sahne ${i + 1} · ${s.big || ""} yerleştirildi`, t0: s.start, t1: s.end, sahne: i + 1 });
    T.cap.filter((c) => c.start >= s.start - 0.05 && c.start < s.end).forEach((c) => L.push({ ajan: "kurgucu", tur: "yazi", mesaj: `“${c.text.slice(0, 48)}” sese hizalandı`, t0: c.start, t1: c.end, sahne: i + 1 }));
    const fx = [...(s.fx || []), ...(s.effect ? [s.effect] : [])]; if (fx.length) L.push({ ajan: "efekt", tur: "efekt", mesaj: `Sahne ${i + 1}: ${fx.join(", ")}`, t0: s.start, t1: Math.min(s.end, s.start + 2.6), sahne: i + 1 });
  });
  T.maps.forEach((m) => L.push({ ajan: "kurgucu", tur: "harita", mesaj: `Harita: ${m.title || ""}`, t0: m.start, t1: m.end }));
  T.cards.forEach((c) => L.push({ ajan: "efekt", tur: "efekt", mesaj: `Sayaç kartı: ${c.value} ${c.unit || ""}`, t0: c.start, t1: c.end }));
  if (T.ay) L.push({ ajan: "efekt", tur: "efekt", mesaj: "Ay yıldız finali", t0: T.ay[0], t1: T.ay[3] });
  if (T.muzik) L.push({ ajan: "kurgucu", tur: "muzik", mesaj: "Müzik besteleniyor", t0: 0, t1: T.dur });
  for (let k = 0; k <= 10; k++) L.push({ ajan: "kurgucu", tur: "ilerleme", mesaj: `Kareler işleniyor %${k * 10}`, t0: (T.dur * k) / 10, yuzde: k * 10 });
  for (const [as, r] of Object.entries(P.kontrol || {})) for (const m of r?.maddeler || []) if (m.seviye !== "bilgi") L.push({ ajan: "kontrol", tur: "kontrol", mesaj: `${as}: ${m.mesaj.slice(0, 110)}`, sahne: m.sahne, seviye: m.seviye });
  L.push({ ajan: "kurgucu", tur: "bilgi", mesaj: "Video hazır ✓", yuzde: 100 });
  return L;
}
let tumOlaylar = [];
async function tekrarOynat() {
  kuyruk.length = 0; temizle(); $("#log").innerHTML = ""; hiz = 2.2;
  const son = tumOlaylar.length ? sonOturum(tumOlaylar) : sentetikOlaylar();
  kuyruk.push(...son.map((o) => ({ ...o, z: o.z }))); isle();
}
function sonOturum(L) { // son çalışma: aralarında 15 dk'dan uzun boşluk olmayan son olaylar
  let i = L.length - 1; while (i > 0 && (L[i].z || 0) - (L[i - 1].z || 0) < 900) i--; return L.slice(i);
}

// ───────── başlat ─────────
async function yenidenYukle() { P = DEMO ? await demoProje() : await api("project", { slug: SLUG, studyo: true }); T = zamanCizelgesi(P); kur(false); }
async function kur(ilk) {
  $("#proj").textContent = `/ Kurgu Stüdyosu · ${P.script?.baslik || SLUG}${T.tahmini ? " (tahmini zamanlar)" : ""}`;
  W = $("#tl").clientWidth - 92 - 12 - 12; X = (t) => (t / T.dur) * W;
  $("#ruler").innerHTML = ""; for (let t = 0; t <= T.dur; t += 5) { const s = document.createElement("span"); s.style.left = X(t) + "px"; s.textContent = fmt(t).slice(0, 5); $("#ruler").append(s); }
  $("#pool").innerHTML = "";
  for (const [i, s] of T.sc.entries()) {
    const d = document.createElement("div"); d.dataset.i = i + 1; d.innerHTML = `<b>${i + 1}</b>`; d.onclick = () => ara(s.start + 0.1); $("#pool").append(d);
    const ad = (s.image || "").split("/").pop();
    if ((P.gorseller || []).includes(ad)) fileUrl(`projects/${SLUG}/${s.image}`).then((u) => { if (u) { d.style.backgroundImage = `url("${u}")`; document.querySelectorAll(`.c-gorsel[data-sahne="${i + 1}"]`).forEach((c) => (c.innerHTML = `<img src="${u}">`)); if (i === cur && !P.video) $("#still").src = u; } });
  }
  hepsiniCiz(); dalga(); sahneSec(0); anaGuncelle(0);
  if (P.video && !DEMO) { const r = await api("video_url", { id: P.video.id }); $("#v").src = r.url; $("#v").classList.remove("hide"); $("#still").classList.add("hide"); }
  else { $("#v").classList.add("hide"); if ((P.dosyalar || []).includes("ses.wav")) fileUrl(`projects/${SLUG}/ses.wav`).then((u) => { if (u) sesEl = new Audio(u); }); }
  if (ilk && !DEMO) {
    const r = await api("olaylar", { slug: SLUG, den: 0 }).catch(() => ({ olaylar: [] }));
    tumOlaylar = r.olaylar; sonI = r.olaylar.reduce((m, o) => Math.max(m, o.i), 0); sonOlayZ = r.olaylar.reduce((m, o) => Math.max(m, o.z || 0), 0);
    if (Date.now() / 1000 - sonOlayZ < 600) { temizle(); kuyruk.push(...sonOturum(r.olaylar)); hiz = 3; isle(); } // şu an çalışan bir ajan var: oturumu hızlıca kur, sonra canlı devam
    else r.olaylar.slice(-12).forEach(logYaz);
    setInterval(cek, 2500);
  }
  canliGoster(); chipCiz({});
}
$("#tekrar").onclick = tekrarOynat;
$("#oynat").onclick = () => {
  const m = P.video ? $("#v") : sesEl; if (!m) return;
  if (oynuyor) { m.pause(); oynuyor = false; $("#oynat").textContent = "▶ Oynat"; } else { m.play(); oynuyor = true; $("#oynat").textContent = "⏸ Durdur"; dongu(); }
};
$("#ses").onclick = () => { const v = $("#v"); v.muted = !v.muted; $("#ses").textContent = v.muted ? "🔇" : "🔊"; };
$("#tl").addEventListener("click", (e) => { const r = $("#tl").getBoundingClientRect(); const x = e.clientX - r.left - 92 - 12; if (x >= 0) ara((x / W) * T.dur); });
addEventListener("resize", () => { if (T) kur(false); });

(async () => {
  if (!SLUG) { document.body.innerHTML = '<p style="padding:30px">Proje seçilmedi. <a href="./" style="color:#e8c478">Panele dön</a></p>'; return; }
  if (!DEMO && !TOKEN) { $("#giris").classList.remove("hide"); return; }
  try { P = DEMO ? await demoProje() : await api("project", { slug: SLUG, studyo: true }); T = zamanCizelgesi(P); await kur(true); if (DEMO) setTimeout(tekrarOynat, 800); }
  catch (e) { $("#log").innerHTML = `<div style="color:#ff7b86">${esc(e.message)}</div>`; }
})();
