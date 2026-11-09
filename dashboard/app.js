const DEMO = new URLSearchParams(location.search).has("demo");
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let TOKEN = localStorage.getItem("at_token") || "";

const AGENTS = [
  { k: "arastirmaci", ic: "🔎", ad: "Araştırmacı", is: "Her pazar 20.00'de haftanın konularını çıkarır" },
  { k: "senarist", ic: "✍️", ad: "Senarist + Kontrol", is: "60 sn metin, sahneler, açıklama; bilgileri doğrular" },
  { k: "gorsel", ic: "🎨", ad: "Görsel + Ses", is: "Gemini ile sahne görselleri ve seslendirme" },
  { k: "kurgucu", ic: "🎬", ad: "Kurgucu", is: "Harita, çizelge, efektlerle videoyu çıkarır" },
];

function toast(t) { const d = document.createElement("div"); d.className = "toast"; d.textContent = t; document.body.append(d); setTimeout(() => d.remove(), 2600); }
async function api(action, body = {}, raw = false) {
  if (DEMO) return demo(action, body);
  const r = await fetch("/api", { method: "POST", headers: { "content-type": "application/json", "x-panel-token": TOKEN }, body: JSON.stringify({ action, ...body }) });
  if (r.status === 401 && action !== "login") { localStorage.removeItem("at_token"); showLogin(); throw new Error("Giriş gerekli"); }
  if (raw) return r;
  const j = await r.json(); if (!r.ok) throw new Error(j.hata || "Hata"); return j;
}
const ago = (iso) => { if (!iso) return "hiç çalışmadı"; const m = Math.round((Date.now() - new Date(iso)) / 60000); return m < 1 ? "az önce" : m < 60 ? `${m} dk önce` : m < 1440 ? `${Math.round(m / 60)} saat önce` : `${Math.round(m / 1440)} gün önce`; };
function stOf(run, st) {
  if (run && (run.durum === "in_progress" || run.durum === "queued")) return ["run", "Çalışıyor"];
  if (run && run.sonuc === "failure") return ["err", "Hata"];
  if (st?.durum === "bekliyor") return ["wait", "Bekliyor"];
  if (run && run.sonuc === "success") return ["ok", "Tamam"];
  return ["wait", "Hazır"];
}

function showLogin() { $("#app").classList.add("hide"); $("#login").classList.remove("hide"); }
$("#go").onclick = async () => {
  try { const j = await api("login", { sifre: $("#pw").value }); TOKEN = j.token; localStorage.setItem("at_token", TOKEN); start(); }
  catch (e) { $("#lerr").textContent = e.message; }
};
$("#pw").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#go").click(); });
$("#refresh").onclick = () => load();

async function start() { $("#login").classList.add("hide"); $("#app").classList.remove("hide"); load(); }
let O = null;
async function load() {
  try { O = await api("overview"); render(); } catch (e) { $("#main").innerHTML = `<div class="card" style="color:var(--err)">${esc(e.message)}</div>`; }
}

function render() {
  const h = O.harcama, pct = Math.min(100, (h.aylik / h.butce) * 100);
  const srv = Object.entries(h.servis || {}).map(([k, v]) => `<span class="tag">${esc(k)} $${v.toFixed(2)}</span>`).join("");
  let html = `<div class="card spend"><div class="row"><span class="mut">Bu ay harcama</span><span class="mut">Bütçe $${h.butce}</span></div>
    <b>$${h.aylik.toFixed(2)}</b><div class="bar"><i style="width:${pct}%"></i></div><div class="chips">${srv || '<span class="mut">Henüz harcama yok</span>'}</div></div>
    <h2>Ajanlar</h2><div class="agents">`;
  for (const a of AGENTS) {
    const run = O.runs[a.k], st = O.status[a.k]; const [c, l] = stOf(run, st);
    html += `<div class="card agent"><div class="ic">${a.ic}</div><h3>${a.ad}</h3><span class="st ${c}">${l}</span>
      <p>${esc(st?.mesaj || a.is)}</p><div class="mut" style="font-size:11.5px;margin-bottom:10px">Son çalışma: ${ago(run?.zaman || st?.zaman)}</div>
      <button data-run="${a.k}">${a.k === "arastirmaci" ? "Şimdi araştır" : a.k === "senarist" ? "Yeni konu" : "Çalıştır"}</button></div>`;
  }
  html += `</div>`;
  const r = O.report;
  html += `<h2>Haftanın raporu ${r ? `<span class="mut" style="font-family:Mont;font-size:12px">· ${esc(r.hafta)}</span>` : ""}</h2>`;
  if (!r) html += `<div class="card mut">Henüz rapor yok. Araştırmacıyı çalıştır ya da pazar akşamını bekle.</div>`;
  else {
    html += `<div class="card">`;
    for (const g of r.gunler || []) {
      html += `<div class="day"><div class="d">${esc(g.gun?.toUpperCase())} · ${esc(g.tarih)}</div>`;
      for (const o of g.olaylar || []) html += evRow(o);
      html += `</div>`;
    }
    html += `</div>`;
    if (r.savas_onerisi) html += `<div class="card war" style="margin-top:12px"><div class="d" style="color:var(--gold);font-size:12px;font-weight:700;letter-spacing:.08em">⚔️ HAFTANIN SAVAŞ ÖNERİSİ</div>${evRow(r.savas_onerisi)}</div>`;
  }
  html += `<h2>Projeler</h2>`;
  html += O.projeler.length ? O.projeler.map((p) => `<div class="card proj" data-p="${esc(p)}"><div class="th" data-th="${esc(p)}"></div><div><b>${esc(p)}</b><span class="mut">Aç →</span></div></div>`).join("") : `<div class="card mut">Henüz proje yok.</div>`;
  html += `<h2>Son harcamalar</h2><div class="card">${(h.son || []).map((x) => `<div class="mut" style="display:flex;justify-content:space-between;padding:4px 0"><span>${esc(x.ajan)} · ${esc(x.detay)}</span><span>$${x.usd.toFixed(3)}</span></div>`).join("") || '<span class="mut">Kayıt yok</span>'}</div>`;
  $("#main").innerHTML = html;
  document.querySelectorAll("[data-run]").forEach((b) => (b.onclick = () => runAgent(b.dataset.run)));
  document.querySelectorAll("[data-karar]").forEach((b) => (b.onclick = () => decide(b.dataset.baslik, b.dataset.karar)));
  document.querySelectorAll("[data-p]").forEach((b) => (b.onclick = () => openProject(b.dataset.p)));
  document.querySelectorAll("[data-th]").forEach(async (d) => { const u = await fileUrl(`projects/${d.dataset.th}/images/${DEMO ? "img01.jpg" : "s01.jpg"}`); if (u) d.style.backgroundImage = `url(${u})`; });
}
function evRow(o) {
  const stars = "★".repeat(o.yildiz || 0) + "☆".repeat(5 - (o.yildiz || 0));
  const karar = o.durum === "yap" ? `<span class="tag yap">Yapılıyor</span>` : o.durum === "gec" ? `<span class="tag gec">Geçildi</span>` :
    `<div class="acts"><button class="gold" data-karar="yap" data-baslik="${esc(o.baslik)}">Yap</button><button data-karar="gec" data-baslik="${esc(o.baslik)}">Geç</button></div>`;
  return `<div class="ev"><div class="t"><b>${o.yil ? esc(o.yil) + " · " : ""}${esc(o.baslik)}</b><span>${esc(o.ozet || "")}</span><div class="stars">${stars}</div></div>${karar}</div>`;
}
async function decide(baslik, karar) { await api("decide", { baslik, karar }); toast(karar === "yap" ? "Senarist çalışmaya başladı" : "Geçildi"); load(); }
async function runAgent(k) {
  let inputs = {};
  if (k === "senarist") { const konu = prompt("Konu? (ör. Mohaç Meydan Muharebesi 1526)"); if (!konu) return; inputs = { konu }; }
  if (k === "gorsel" || k === "kurgucu") { const slug = prompt("Hangi proje?\n" + O.projeler.join("\n")); if (!slug) return; inputs = { slug }; }
  await api("run", { agent: k, inputs }); toast("Ajan çalıştırıldı"); setTimeout(load, 4000);
}
const urlCache = {};
async function fileUrl(path) {
  if (DEMO) return `../${path}`;
  if (urlCache[path]) return urlCache[path];
  const r = await api("file", { path }, true); if (!r.ok) return null;
  return (urlCache[path] = URL.createObjectURL(await r.blob()));
}

async function openProject(slug) {
  const P = await api("project", { slug }); const sc = P.script; const d = $("#detail");
  $("#main").classList.add("hide"); d.classList.remove("hide");
  let h = `<button class="ghost" id="back">← Geri</button><h2 style="margin-top:14px">${esc(sc?.baslik || P.project?.title || slug)}</h2>`;
  if (sc) {
    const st = sc.durum === "onaylandi" ? `<span class="st ok">Onaylandı</span>` : `<span class="st wait">Onay bekliyor</span>`;
    h += `<div class="card">${st}<h3 style="font-size:14px;margin:12px 0 6px">Seslendirme metni</h3><pre>${esc(sc.seslendirme_metni)}</pre>
      <div class="flex"><button data-copy="${esc(sc.seslendirme_metni)}">Metni kopyala</button>${sc.durum !== "onaylandi" ? `<button class="gold" id="approve">Onayla → görsel + ses üret</button>` : ""}</div></div>`;
  }
  const scenes = sc?.sahneler || (P.project?.scenes || []).map((s) => ({ image: s.image, big: s.big }));
  h += `<h2>Sahneler</h2><div class="scenes">`;
  scenes.forEach((s, i) => { const has = P.gorseller.includes(s.image.split("/").pop()); h += `<div class="sc" data-img="${has ? esc(s.image) : ""}" data-i="${i + 1}"><i>${i + 1}</i>${has ? "" : "Yükle"}</div>`; });
  h += `</div>`;
  if (sc) h += `<details class="card" style="margin-top:12px"><summary>Gemini promptları (kopyala)</summary>${sc.sahneler.map((s, i) => `<div class="flex" style="align-items:center"><span class="mut">${i + 1}</span><button data-copy="${esc(s.prompt_tam)}">${esc(s.big || "Sahne")} promptunu kopyala</button></div>`).join("")}</details>`;
  const hasVoice = P.dosyalar.includes("ses.wav");
  h += `<h2>Ses</h2><div class="card">${hasVoice ? `<audio id="aud" controls style="width:100%"></audio>` : `<span class="mut">Ses yok.</span>`}<div class="flex"><label class="btn">Ses yükle (.wav)<input type="file" accept="audio/wav" id="up-ses" hidden></label></div></div>`;
  h += `<h2>Video</h2><div class="card">${P.video ? `<video id="vid" controls playsinline></video><div class="mut" style="margin-top:8px">${(P.video.boyut / 1e6).toFixed(1)} MB · ${ago(P.video.zaman)}</div>` : `<span class="mut">Henüz video yok.</span>`}
    <div class="flex"><button class="gold" id="render">${P.video ? "Videoyu yeniden üret" : "Videoyu üret"}</button>${P.video ? `<button id="dl">İndir</button>` : ""}</div></div>`;
  if (sc?.aciklama) { const t = sc.aciklama + "\n\n" + (sc.hashtagler || []).map((x) => (x.startsWith("#") ? x : "#" + x)).join(" ");
    h += `<h2>Paylaşım açıklaması</h2><div class="card"><pre>${esc(t)}</pre><div class="flex"><button data-copy="${esc(t)}">Kopyala</button></div></div>`; }
  d.innerHTML = h;
  $("#back").onclick = () => { d.classList.add("hide"); $("#main").classList.remove("hide"); };
  d.querySelectorAll("[data-copy]").forEach((b) => (b.onclick = () => { navigator.clipboard.writeText(b.dataset.copy); toast("Kopyalandı"); }));
  d.querySelectorAll(".sc").forEach(async (el) => {
    if (el.dataset.img) { const u = await fileUrl(`projects/${slug}/${el.dataset.img}`); if (u) el.style.backgroundImage = `url(${u})`; }
    el.onclick = () => { const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/jpeg"; inp.onchange = () => upload(slug, `images/s${String(el.dataset.i).padStart(2, "0")}.jpg`, inp.files[0]); inp.click(); };
  });
  if (hasVoice) $("#aud").src = await fileUrl(`projects/${slug}/ses.wav`);
  $("#up-ses").onchange = (e) => upload(slug, "ses.wav", e.target.files[0]);
  if ($("#approve")) $("#approve").onclick = async () => { await api("approve", { slug }); toast("Onaylandı, görseller üretiliyor"); openProject(slug); };
  $("#render").onclick = async () => { await api("run", { agent: "kurgucu", inputs: { slug } }); toast("Kurgucu çalışıyor (5-10 dk)"); };
  if (P.video) {
    const u = DEMO ? "../demo.mp4" : (await api("video_url", { id: P.video.id })).url; $("#vid").src = u;
    $("#dl").onclick = () => { const a = document.createElement("a"); a.href = u; a.download = `${slug}.mp4`; a.click(); };
  }
}
async function upload(slug, name, file) {
  if (!file) return; if (file.size > 4.2e6) return toast("Dosya 4 MB'tan büyük olamaz");
  const b64 = await new Promise((res) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.readAsDataURL(file); });
  await api("upload", { slug, name, base64: b64 }); toast("Yüklendi"); openProject(slug);
}

// ── demo verisi (?demo=1) ──
function demo(action) {
  const now = new Date().toISOString();
  if (action === "login") return { token: "demo" };
  if (action === "overview") return {
    status: { arastirmaci: { durum: "tamam", mesaj: "2026-W47 raporu hazır", zaman: now }, senarist: { durum: "tamam", mesaj: "'Malazgirt 1071' metni onay bekliyor", zaman: now },
      gorsel: { durum: "bekliyor", mesaj: "Gemini anahtarı yok: görselleri elle yükle", zaman: now }, kurgucu: { durum: "calisiyor", mesaj: "osmanli-1299-1923 videosu üretiliyor", zaman: now } },
    runs: { arastirmaci: { durum: "completed", sonuc: "success", zaman: now }, senarist: { durum: "completed", sonuc: "success", zaman: now }, gorsel: null, kurgucu: { durum: "in_progress", zaman: now } },
    projeler: ["osmanli-1299-1923", "malazgirt-1071"],
    harcama: { aylik: 1.84, butce: 15, servis: { claude: 0.62, "gemini-gorsel": 1.09, "gemini-ses": 0.13 }, son: [{ ajan: "senarist", detay: "Malazgirt metni", usd: 0.21 }, { ajan: "arastirmaci", detay: "haftalık rapor", usd: 0.38 }] },
    report: { hafta: "2026-W47", gunler: [
      { tarih: "2026-11-17", gun: "Salı", olaylar: [{ yil: 1922, baslik: "Son padişah Vahdettin İstanbul'dan ayrıldı", ozet: "Vahdettin 17 Kasım'da bir İngiliz gemisiyle şehri terk etti.", yildiz: 4 }] },
      { tarih: "2026-11-18", gun: "Çarşamba", olaylar: [{ yil: 1928, baslik: "Mickey Mouse'un ilk sesli filmi", ozet: "Steamboat Willie gösterime girdi.", yildiz: 2, durum: "gec" }] },
      { tarih: "2026-11-19", gun: "Perşembe", olaylar: [{ yil: 1863, baslik: "Gettysburg Söylevi", ozet: "Lincoln'ün 2 dakikalık tarihi konuşması.", yildiz: 3 }] },
      { tarih: "2026-11-20", gun: "Cuma", olaylar: [{ yil: 1945, baslik: "Nürnberg Davaları başladı", ozet: "Nazi liderleri yargılanmaya başlandı.", yildiz: 4, durum: "yap" }] }],
      savas_onerisi: { yil: 1071, baslik: "Malazgirt Meydan Muharebesi", ozet: "Alparslan'ın zaferiyle Anadolu'nun kapıları Türklere açıldı. Harita animasyonuna çok uygun.", yildiz: 5, durum: "yap" } } };
  if (action === "project") return { script: { baslik: "Malazgirt 1071", durum: "onay-bekliyor", seslendirme_metni: "Bin yetmiş bir. Ağustosun son günleri...\nAlparslan'ın ordusu Malazgirt ovasında Bizans'ın karşısındaydı...", sahneler: [{ image: "images/img01.jpg", big: "1071", prompt_tam: "..." }, { image: "images/img02.jpg", big: "ALPARSLAN", prompt_tam: "..." }, { image: "images/s03.jpg", big: "MALAZGİRT", prompt_tam: "..." }, { image: "images/s04.jpg", big: "ZAFER", prompt_tam: "..." }], aciklama: "Anadolu'nun kapısını açan savaş...", hashtagler: ["tarih", "malazgirt"] }, gorseller: ["img01.jpg", "img02.jpg"], dosyalar: ["ses.wav"], video: null };
  return { ok: true };
}

if (DEMO || TOKEN) start(); else showLogin();
if ("serviceWorker" in navigator && !DEMO) navigator.serviceWorker.register("sw.js").catch(() => {});
