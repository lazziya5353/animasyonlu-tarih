const DEMO = new URLSearchParams(location.search).has("demo");
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let TOKEN = localStorage.getItem("at_token") || "";
const HANDLE = "@animasyon.tarih";

const AGENTS = [
  { k: "arastirmaci", ic: "🔎", ad: "Araştırmacı", is: "Her pazar 20.00'de haftanın konularını çıkarır", btn: "Şimdi araştır", ucret: true },
  { k: "senarist", ic: "✍️", ad: "Senarist", is: "60 sn metin, sahneler, açıklama yazar", btn: "Yeni konu", ucret: true },
  { k: "gorsel", ic: "🎙️", ad: "Ses + Görsel", is: "Gemini ile seslendirme (ücretsiz)", btn: "Çalıştır" },
  { k: "kurgucu", ic: "🎬", ad: "Kurgucu", is: "Harita, çizelge, efekt ve filigranla videoyu çıkarır", btn: "Çalıştır" },
  { k: "kontrol", ic: "🛡️", ad: "Kontrolcüler", is: "Senaryo, ses, görsel ve kurguyu denetler", btn: "Kontrol et" },
  { k: "yayinci", ic: "📤", ad: "Yayıncı", is: "Instagram'a Reels olarak paylaşır", btn: "Bağlantıyı test et" },
  { k: "analist", ic: "📊", ad: "Analist", is: "Her pazartesi izlenme istatistiklerini toplar", btn: "Şimdi topla" },
  { k: "yorumcu", ic: "💬", ad: "Yorum ajanı", is: "Yorumları toplar, cevap taslağı yazar", btn: "Yorumları topla" },
];
const ASAMA_AD = { senaryo: "Senaryo", ses: "Ses", gorsel: "Görseller", kurgu: "Kurgu" };

function toast(t) { const d = document.createElement("div"); d.className = "toast"; d.textContent = t; document.body.append(d); setTimeout(() => d.remove(), 2800); }
async function api(action, body = {}, raw = false) {
  if (DEMO) return demo(action, body);
  const r = await fetch("/api", { method: "POST", headers: { "content-type": "application/json", "x-panel-token": TOKEN }, body: JSON.stringify({ action, ...body }) });
  if (r.status === 401 && action !== "login") { localStorage.removeItem("at_token"); showLogin(); throw new Error("Giriş gerekli"); }
  if (raw) return r;
  const j = await r.json(); if (!r.ok) throw new Error(j.hata || "Hata"); return j;
}
async function guvenli(fn, ok) { try { const r = await fn(); if (ok) toast(ok); return r; } catch (e) { toast(e.message || "Hata"); throw e; } }
const ago = (iso) => { if (!iso) return "hiç çalışmadı"; const m = Math.round((Date.now() - new Date(iso)) / 60000); return m < 1 ? "az önce" : m < 60 ? `${m} dk önce` : m < 1440 ? `${Math.round(m / 60)} saat önce` : `${Math.round(m / 1440)} gün önce`; };
const tarihTR = (iso) => new Date(iso).toLocaleString("tr-TR", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
function stOf(run, st) {
  if (run && (run.durum === "in_progress" || run.durum === "queued")) return ["run", "Çalışıyor"];
  if (st?.durum === "hata" || (run && run.sonuc === "failure")) return ["err", "Hata"];
  if (st?.durum === "bekliyor") return ["wait", "Bekliyor"];
  if (run && run.sonuc === "success") return ["ok", "Tamam"];
  return ["wait", "Hazır"];
}
const pill = (d) => d === "tamam" ? `<span class="st ok">Temiz</span>` : d === "uyari" ? `<span class="st wait">Uyarı</span>` : d === "hata" ? `<span class="st err">Hata</span>` : `<span class="st">Bekliyor</span>`;

function showLogin() { $("#app").classList.add("hide"); $("#login").classList.remove("hide"); }
$("#go").onclick = async () => {
  try { const j = await api("login", { sifre: $("#pw").value }); TOKEN = j.token; localStorage.setItem("at_token", TOKEN); start(); }
  catch (e) { $("#lerr").textContent = e.message; }
};
$("#pw").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#go").click(); });
$("#refresh").onclick = () => (CUR ? openProject(CUR) : load());

async function start() { $("#login").classList.add("hide"); $("#app").classList.remove("hide"); load(); }
const projeAdi = (p) => { if (O?.basliklar?.[p]) return O.basliklar[p]; const t = String(p).replace(/-/g, " ").trim(); return t.charAt(0).toLocaleUpperCase("tr") + t.slice(1); };
// ajan mesajlarındaki klasör adlarını (uskudar-in-tarihi-...) okunur başlıkla değiştir
const adlandir = (t) => { let x = String(t || ""); for (const p of [...(O?.projeler || [])].sort((a, b) => b.length - a.length)) if (x.includes(p)) x = x.split("projects/" + p).join(projeAdi(p)).split(p).join(projeAdi(p)); return x; };
let O = null, CUR = null, ARSIV_ACIK = false;
async function arsivle(slug, cikar) {
  const once = (O.arsiv || []).filter((x) => x !== slug); O.arsiv = cikar ? once : [slug, ...once]; if (CUR !== slug) render(); // hemen göster
  try { const r = await api("arsiv", { slug, cikar, liste: once }); O.arsiv = r.arsiv; toast(cikar ? `"${projeAdi(slug)}" arşivden çıktı` : `"${projeAdi(slug)}" arşive atıldı 📦`); if (CUR === slug) openProject(slug, true); else render(); }
  catch (e) { toast(e.message || "Hata"); }
} const GIZLI = new Set(); // silinmekte olan projeler (iş bitene kadar listede görünmesin)
async function load() {
  try { O = await api("overview"); O.projeler = O.projeler.filter((p) => !GIZLI.has(p)); render();
    if (!load.ilk) { load.ilk = 1; const m = location.hash.match(/^#p=(.+)/);   // sayfa #p=... ile açıldıysa (ör. Canlı ilerleme'den geri dönüş) o projeyi aç
      if (m) { const p = decodeURIComponent(m[1]); if (O.projeler.includes(p)) { history.replaceState({ p }, "", location.hash); openProject(p, true); } else history.replaceState(null, "", location.pathname + location.search); } } } catch (e) { $("#main").innerHTML = `<div class="card" style="color:var(--err)">${esc(e.message)}</div>`; }
}

// ───────── ana sayfa ─────────
function render() {
  const h = O.harcama, pct = Math.min(100, (h.aylik / h.butce) * 100);
  const srv = Object.entries(h.servis || {}).filter(([, v]) => v > 0).map(([k, v]) => `<span class="tag">${esc(k)} $${v.toFixed(2)}</span>`).join("");
  let html = komutKart() + `<div class="card spend"><div class="row"><span class="mut">Bu ay harcama (Claude API)</span><span class="mut">Bütçe $${h.butce}</span></div>
    <b>$${h.aylik.toFixed(2)}</b><div class="bar"><i style="width:${pct}%"></i></div><div class="chips">${srv || '<span class="mut">Henüz harcama yok</span>'}</div></div>
    <h2>Ajanlar</h2><div class="agents">`;
  for (const a of AGENTS) {
    const run = O.runs[a.k], st = O.status[a.k]; const [c, l] = stOf(run, st);
    html += `<div class="card agent"><div class="ic">${a.ic}</div><h3>${a.ad}</h3><span class="st ${c}">${l}</span>
      <p>${esc(adlandir(st?.mesaj) || a.is)}</p><div class="mut" style="font-size:11.5px;margin-bottom:10px">Son çalışma: ${ago(run?.zaman || st?.zaman)}${a.ucret ? " · <span title='Claude API kredisi harcar'>💳</span>" : ""}</div>
      <button data-run="${a.k}">${a.btn}</button> <button class="ghost" data-detay="${a.k}">Detay</button>${c === "err" && /projects\/[a-z0-9-]+/.test(st?.cikti || st?.mesaj || "") ? ` <button class="duzelt" data-hduzelt="${esc((st.cikti || st.mesaj).match(/projects\/([a-z0-9-]+)/)[1])}" data-hmesaj="${esc(a.ad + ": " + (st.mesaj || ""))}">🔧 Düzelt</button>` : ""}</div>`;
  }
  html += `</div>`;
  html += renderYorumlar() + renderAnaliz();
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
  const fk = O.yorumlar?.fikirler || [];
  if (fk.length) html += `<div class="card" style="margin-top:12px"><div class="d" style="color:var(--gold);font-size:12px;font-weight:700;letter-spacing:.08em">💡 İZLEYİCİ ÖNERİLERİ</div>${fk.map((f) => `<div class="mut" style="padding:5px 0">${esc(f.konu)} · <span style="opacity:.7">${esc(f.kaynak)}</span></div>`).join("")}</div>`;
  html += `<h2>Projeler</h2>`;
  const ARS = new Set(O.arsiv || []), aktif = O.projeler.filter((p) => !ARS.has(p)), arsivde = (O.arsiv || []).filter((p) => O.projeler.includes(p));
  const kart = (p, ars) => `<div class="card proj" data-p="${esc(p)}"><div class="th" data-th="${esc(p)}"></div><div class="ad"><b>${esc(projeAdi(p))}</b><span class="mut">Aç →</span></div><button class="cop ars" data-ars="${esc(p)}" data-cikar="${ars ? 1 : ""}" title="${ars ? "Arşivden çıkar" : "Arşive at"}">${ars ? "↩" : "📦"}</button><button class="cop" data-cop="${esc(p)}" title="Projeyi sil" aria-label="Projeyi sil">🗑</button></div>`;
  html += aktif.length ? aktif.map((p) => kart(p, false)).join("") : `<div class="card mut">${arsivde.length ? "Aktif proje yok, hepsi arşivde." : "Henüz proje yok."}</div>`;
  if (arsivde.length) html += `<details class="arsiv" ${ARSIV_ACIK ? "open" : ""}><summary><h2 style="display:inline">📦 Arşiv <span class="mut" style="font-size:14px">(${arsivde.length})</span></h2></summary>${arsivde.map((p) => kart(p, true)).join("")}</details>`;
  html += `<h2>Son harcamalar</h2><div class="card">${(h.son || []).filter((x) => x.usd > 0).map((x) => `<div class="mut" style="display:flex;justify-content:space-between;padding:4px 0"><span>${esc(x.ajan)} · ${esc(x.detay)}</span><span>$${x.usd.toFixed(3)}</span></div>`).join("") || '<span class="mut">Kayıt yok</span>'}</div>`;
  const SEK = [["anim", "🎬 ANİMASYON TARİH VİDEO"], ["spor", "⚽ SPOR TARİHİ VİDEO"], ["ig", "📊 İNSTAGRAM ANALİZ"]];
  let sek = "anim"; try { const k = localStorage.getItem("sekme"); if (SEK.some((x) => x[0] === k)) sek = k; } catch {}
  const QZ = (t) => (typeof quizSekmeHtml === "function" ? quizSekmeHtml(t) : "");
  html = QZ("tarih") + html;
  const spor = `<h2>SPOR TARİHİ VİDEO</h2>${QZ("spor")}<div class="card"><b style="color:var(--gold)">Yakında</b><div class="mut" style="margin-top:4px">Maç animasyonları ve maç öncesi hikâyeler burada olacak. Spor quizleri yukarıdaki QUIZ bölümünden üretilebilir.</div></div>`;
  $("#main").innerHTML = `<nav class="sekmeler">${SEK.map(([k, l]) => `<button class="sekme${k === sek ? " on" : ""}" data-sekme="${k}">${l}</button>`).join("")}</nav>
    <section data-bolum="anim"${sek === "anim" ? "" : " hidden"}>${html}</section><section data-bolum="spor"${sek === "spor" ? "" : " hidden"}>${spor}</section><section data-bolum="ig"${sek === "ig" ? "" : " hidden"}>${typeof igSekmeHtml === "function" ? igSekmeHtml() : renderTokenKart() + (renderInstagram() || "")}</section>`;
  document.querySelectorAll("[data-sekme]").forEach((b) => (b.onclick = () => {
    const k = b.dataset.sekme; try { localStorage.setItem("sekme", k); } catch {}
    document.querySelectorAll("[data-sekme]").forEach((x) => x.classList.toggle("on", x === b));
    document.querySelectorAll("[data-bolum]").forEach((x) => (x.hidden = x.dataset.bolum !== k)); window.scrollTo(0, 0);
  }));
  baglaToken(); if (typeof baglaQuiz === "function") baglaQuiz();
  document.querySelectorAll("[data-run]").forEach((b) => (b.onclick = () => runAgent(b.dataset.run)));
  baglaInstagram(); if (typeof baglaIgEk === "function") baglaIgEk();
  document.querySelectorAll("[data-detay]").forEach((b) => (b.onclick = () => ajanDetay(b.dataset.detay)));
  document.querySelectorAll("[data-hduzelt]").forEach((b) => (b.onclick = async () => {
    if (b.disabled) return; b.disabled = true; b.textContent = "Gönderiliyor…";
    try { await api("duzelt", { slug: b.dataset.hduzelt, maddeler: [{ asama: "is", mesaj: b.dataset.hmesaj }] }); b.textContent = "✓ Ajan düzeltiyor"; toast("Yönetici ajan düzeltiyor, cevabı 'Ajana yaz' kutusunda"); }
    catch (e) { b.disabled = false; b.textContent = "🔧 Düzelt"; toast(e.message || "Hata"); }
  }));
  document.querySelectorAll("[data-karar]").forEach((b) => (b.onclick = () => decide(b.dataset.baslik, b.dataset.karar)));
  document.querySelectorAll("[data-p]").forEach((b) => (b.onclick = () => openProject(b.dataset.p)));
  const ad = document.querySelector("details.arsiv"); if (ad) ad.ontoggle = () => (ARSIV_ACIK = ad.open);
  document.querySelectorAll("[data-ars]").forEach((b) => (b.onclick = (e) => { e.stopPropagation(); arsivle(b.dataset.ars, !!b.dataset.cikar); }));
  document.querySelectorAll("[data-cop]").forEach((b) => (b.onclick = async (e) => {
    e.stopPropagation(); const slug = b.dataset.cop;
    if (!confirm(`"${projeAdi(slug)}" projesi tamamen silinsin mi?\n\nMetin, görseller, ses ve video gider. Geri alınamaz.`)) return;
    b.disabled = true; b.textContent = "…";
    try { await api("sil", { slug, tur: "hepsi", onay: slug }); GIZLI.add(slug); toast("Proje siliniyor, 30 sn içinde tamamen kalkar"); load(); setTimeout(load, 40000); }
    catch (err) { b.disabled = false; b.textContent = "🗑"; toast(err.message || "Hata"); }
  }));
  document.querySelectorAll("[data-th]").forEach(async (d) => { const u = await fileUrl(`projects/${d.dataset.th}/images/${DEMO ? "img01.jpg" : "s01.jpg"}`); if (u) d.style.backgroundImage = `url(${u})`; });
  baglaYorumlar(); baglaKomut();
}

// ───────── "Ajana yaz": serbest mesajla yönetici ajan ─────────
let KOMUT_BEKLE = null;
function komutKart() {
  return `<div class="card" id="komut"><div class="row"><b>🤖 Ajana yaz</b><span class="mut" style="font-size:11.5px">Ne istediğini yaz, ajanlar ona göre çalışsın · 💳 mesaj başı birkaç kuruş</span></div>
    <div id="kmsg" style="max-height:300px;overflow:auto;margin:10px 0;display:flex;flex-direction:column;gap:8px"><span class="mut">Yükleniyor…</span></div>
    <textarea id="kin" rows="3" style="width:100%;box-sizing:border-box;border-radius:12px;padding:10px;background:rgba(255,255,255,.05);color:inherit;border:1px solid rgba(255,255,255,.12);font:inherit"
      placeholder="Ör: Üsküdar'ın adının hikâyesini 35 saniyelik kısa video yap · Galatasaray videosunun kapanışını değiştir · 3. sahnenin görselini daha karanlık yap"></textarea>
    <div class="row" style="margin-top:8px"><span class="mut" id="kdurum" style="font-size:12px"></span><button class="gold" id="kgo">Gönder</button></div></div>`;
}
function komutCiz(m) {
  const box = $("#kmsg"); if (!box) return;
  if (!m.length) { box.innerHTML = `<span class="mut">Henüz mesaj yok. İlk isteğini yaz.</span>`; return; }
  box.innerHTML = m.map((x) => {
    const sen = x.kim === "sen";
    const ek = sen ? "" : [...(x.islemler || []).map((i) => `✅ ${esc(adlandir(i))}`), ...(x.hatalar || []).map((h) => `⚠️ ${esc(adlandir(h))}`)].join("<br>");
    return `<div style="align-self:${sen ? "flex-end" : "flex-start"};max-width:88%;padding:9px 12px;border-radius:14px;background:${sen ? "rgba(232,196,120,.18)" : "rgba(255,255,255,.06)"};white-space:pre-wrap">${esc(x.metin)}${ek ? `<div class="mut" style="font-size:12px;margin-top:6px">${ek}</div>` : ""}<div class="mut" style="font-size:10.5px;margin-top:4px">${ago(x.zaman)}</div></div>`;
  }).join("");
  box.scrollTop = box.scrollHeight;
}
async function komutYukle() {
  try {
    const r = await api("komut_gecmis"); komutCiz(r.mesajlar || []);
    const son = (r.mesajlar || []).slice(-1)[0];
    if (KOMUT_BEKLE && son && son.kim === "ajan" && new Date(son.zaman) >= KOMUT_BEKLE) { KOMUT_BEKLE = null; $("#kdurum").textContent = ""; toast("Ajan cevap verdi"); }
    if (KOMUT_BEKLE) { $("#kdurum").textContent = "⏳ Ajan düşünüyor… (yaklaşık 30-60 sn)"; setTimeout(komutYukle, 8000); }
  } catch (e) { const b = $("#kmsg"); if (b) b.innerHTML = `<span class="mut">${esc(e.message)}</span>`; }
}
function baglaKomut() {
  const go = $("#kgo"); if (!go) return;
  go.onclick = async () => {
    const mesaj = $("#kin").value.trim(); if (!mesaj) return;
    go.disabled = true;
    try {
      await guvenli(() => api("komut", { mesaj }), "Mesaj ajana gitti");
      $("#kin").value = ""; KOMUT_BEKLE = new Date(Date.now() - 5000);
      const box = $("#kmsg"); box.insertAdjacentHTML("beforeend", `<div style="align-self:flex-end;max-width:88%;padding:9px 12px;border-radius:14px;background:rgba(232,196,120,.18);white-space:pre-wrap">${esc(mesaj)}</div>`); box.scrollTop = box.scrollHeight;
      setTimeout(komutYukle, 10000); $("#kdurum").textContent = "⏳ Ajan düşünüyor… (yaklaşık 30-60 sn)";
    } finally { go.disabled = false; }
  };
  komutYukle();
}
function evRow(o) {
  const stars = "★".repeat(o.yildiz || 0) + "☆".repeat(5 - (o.yildiz || 0));
  const karar = o.durum === "yap" ? `<span class="tag yap">Yapılacak</span>` : o.durum === "gec" ? `<span class="tag gec">Geçildi</span>` :
    `<div class="acts"><button class="gold" data-karar="yap" data-baslik="${esc(o.baslik)}">Yap</button><button data-karar="gec" data-baslik="${esc(o.baslik)}">Geç</button></div>`;
  return `<div class="ev"><div class="t"><b>${o.yil ? esc(o.yil) + " · " : ""}${esc(o.baslik)}</b><span>${esc(o.ozet || "")}</span><div class="stars">${stars}</div></div>${karar}</div>`;
}
async function decide(baslik, karar) {
  let apiIle = false;
  if (karar === "yap") apiIle = confirm("Senaryoyu Claude API mi yazsın? (~$0,30 kredi harcar)\n\nTamam → API yazar\nİptal → sadece 'yapılacak' diye işaretle, metni sohbette birlikte yazarız (ücretsiz)");
  await guvenli(() => api("decide", { baslik, karar, api: apiIle }), karar === "yap" ? (apiIle ? "Senarist çalışmaya başladı" : "Yapılacak olarak işaretlendi") : "Geçildi");
  load();
}
// ───────── Ajan detayı: ne yaptı, durdur, devre dışı bırak, kayıt sil ─────────
async function ajanDetay(k) {
  const a = AGENTS.find((x) => x.k === k); let m = $("#ajanm");
  if (!m) { m = document.createElement("div"); m.id = "ajanm"; m.className = "modal"; document.body.append(m); m.onclick = (e) => { if (e.target === m) m.remove(); }; }
  m.innerHTML = `<div class="kutu"><div class="mut">Yükleniyor…</div></div>`;
  let D; try { D = await api("ajan_detay", { k }); } catch (e) { m.innerHTML = `<div class="kutu"><b>${esc(a.ad)}</b><p style="color:var(--err)">${esc(e.message)}</p><button id="mk">Kapat</button></div>`; $("#mk").onclick = () => m.remove(); return; }
  const canli = D.calismalar.filter((x) => x.durum !== "completed").length;
  const etiket = (x) => x.durum !== "completed" ? ["run", x.durum === "queued" ? "Sırada" : "Çalışıyor"] : x.sonuc === "success" ? ["ok", "Tamamlandı"] : x.sonuc === "cancelled" ? ["wait", "Durduruldu"] : ["err", "Hata"];
  const sure = (n) => n >= 60 ? `${Math.floor(n / 60)} dk ${n % 60} sn` : `${n} sn`;
  m.innerHTML = `<div class="kutu"><div class="flex" style="justify-content:space-between;align-items:center"><b style="font-size:16px">${a.ic} ${esc(a.ad)}</b><button class="ghost" id="mk">✕</button></div>
    <div class="mut" style="margin:6px 0 12px">${esc(a.is)} · <b style="color:var(--${D.aktif ? "ok" : "err"})">${D.aktif ? "Açık" : "Devre dışı"}</b></div>
    <div class="flex" style="flex-wrap:wrap;gap:8px"><button id="mdur" ${canli ? "" : "disabled"}>⏹ Durdur${canli ? ` (${canli})` : ""}</button><button id="mmod">${D.aktif ? "⏸ Devre dışı bırak" : "▶ Yeniden aç"}</button><button class="silb" id="mhepsi" ${D.calismalar.some((x) => x.durum === "completed") ? "" : "disabled"}>🗑 Tüm kayıtları sil</button></div>
    <h3 style="margin:16px 0 6px;font-size:13px">Son çalışmalar</h3>
    ${D.calismalar.map((x) => { const [c, l] = etiket(x); return `<div class="kayit"><span class="st ${c}">${l}</span><span class="mut">${ago(x.zaman)} · ${sure(x.sure)}</span><a href="${esc(x.url)}" target="_blank" rel="noopener">Ayrıntı</a>${x.durum === "completed" ? `<button class="cop" data-ksil="${x.id}" title="Bu kaydı sil">🗑</button>` : "<span></span>"}</div>`; }).join("") || '<div class="mut">Henüz çalışma yok.</div>'}
    <div class="mut" style="font-size:11.5px;margin-top:10px">Kayıt silmek sadece çalışma geçmişini temizler; projelere, videolara dokunmaz.</div></div>`;
  const is = async (btn, fn, ok) => { btn.disabled = true; try { const r = await fn(); toast(typeof ok === "function" ? ok(r) : ok); setTimeout(() => { ajanDetay(k); load(); }, 1500); } catch (e) { btn.disabled = false; toast(e.message || "Hata"); } };
  $("#mk").onclick = () => m.remove();
  $("#mdur").onclick = (e) => is(e.target, () => api("ajan_durdur", { k }), (r) => r.n ? `${r.n} iş durduruldu` : "Çalışan iş yoktu");
  $("#mmod").onclick = (e) => { if (D.aktif && !confirm(`${a.ad} devre dışı kalsın mı?\n\nYeniden açana kadar ne elle ne de otomatik çalışır.`)) return; is(e.target, () => api("ajan_mod", { k, aktif: !D.aktif }), D.aktif ? "Devre dışı bırakıldı" : "Yeniden açıldı"); };
  $("#mhepsi").onclick = (e) => { if (!confirm(`${a.ad} ajanının bitmiş tüm çalışma kayıtları silinsin mi?`)) return; is(e.target, () => api("ajan_kayit_sil", { k }), (r) => `${r.n} kayıt silindi`); };
  m.querySelectorAll("[data-ksil]").forEach((b) => (b.onclick = () => is(b, () => api("ajan_kayit_sil", { k, id: b.dataset.ksil }), "Kayıt silindi")));
}

async function runAgent(k) {
  let inputs = {};
  const a = AGENTS.find((x) => x.k === k);
  if (k === "senarist") {
    const konu = prompt("Konu? (ör. Mohaç Meydan Muharebesi 1526)\n\nNot: Claude API ile yazar, ~$0,30 kredi harcar."); if (!konu) return; inputs = { konu };
  }
  if (k === "arastirmaci" && !confirm("Araştırmacı Claude API kredisi harcar (~$0,30). Devam edilsin mi?")) return;
  if (["gorsel", "kurgucu", "kontrol"].includes(k)) { const L = O.projeler; const c = prompt("Hangi proje? Numarasını yaz:\n\n" + L.map((p, i) => `${i + 1}. ${projeAdi(p)}`).join("\n"), "1"); if (!c) return;
    const slug = L[Number(c) - 1] || L.find((p) => p === c.trim() || projeAdi(p).toLocaleLowerCase("tr") === c.trim().toLocaleLowerCase("tr")); if (!slug) return toast("Böyle bir proje yok"); inputs = { slug }; if (k === "kontrol") inputs.asama = "hepsi"; }
  if (k === "yayinci") inputs = { test: "1" };
  if (k === "yorumcu") inputs = { mod: "topla" };
  await guvenli(() => api("run", { agent: k, inputs }), `${a.ad} çalıştırıldı`); setTimeout(load, 5000);
}

function renderYorumlar() {
  const y = O.yorumlar?.bekleyen || [];
  if (!y.length) return "";
  const tur = { soru: "❓ Soru", ovgu: "💛 Övgü", elestiri: "⚠️ Eleştiri", oneri: "💡 Öneri", spam: "🚫 Spam", hakaret: "⛔ Hakaret", diger: "💬" };
  return `<h2>Bekleyen yorumlar <span class="mut" style="font-family:Mont;font-size:12px">· ${y.length}</span></h2><div class="card" id="yorumlar">` + y.map((c) => `
    <div class="ym" data-id="${esc(c.id)}"><div class="mut" style="font-size:12px">${tur[c.tur] || "💬"} · @${esc(c.kullanici)} · ${esc(c.gonderi)}</div>
    <div style="margin:4px 0 6px">${esc(c.metin)}</div>
    ${["spam", "hakaret"].includes(c.tur) ? "" : `<textarea rows="2" placeholder="Cevabın…">${esc(c.taslak || "")}</textarea>`}
    <div class="acts">${["spam", "hakaret"].includes(c.tur) ? "" : `<button class="gold" data-y="onaylandi">Gönder</button>`}<button data-y="gizle">Gizle</button><button data-y="gecildi">Geç</button></div></div>`).join("") + `</div>`;
}
function baglaYorumlar() {
  document.querySelectorAll("#yorumlar [data-y]").forEach((b) => (b.onclick = async () => {
    const box = b.closest(".ym"); const ta = box.querySelector("textarea");
    if (b.dataset.y === "onaylandi" && !ta?.value.trim()) return toast("Önce cevabı yaz");
    await guvenli(() => api("yorum_karar", { kararlar: [{ id: box.dataset.id, durum: b.dataset.y, taslak: ta?.value }] }), b.dataset.y === "onaylandi" ? "Cevap gönderiliyor" : b.dataset.y === "gizle" ? "Yorum gizleniyor" : "Geçildi");
    box.remove();
  }));
}
// ───────── INSTAGRAM ANALİZ ─────────
const sayi = (n) => (n === null || n === undefined ? "—" : Number(n).toLocaleString("tr-TR"));
function igGrafik(seri) {
  if (!seri || seri.length < 2) return `<div class="mut" style="padding:10px 0">Takipçi grafiği birkaç günlük veri birikince görünecek.</div>`;
  const W = 640, H = 150, P = 26, ys = seri.map((x) => x.y), mn = Math.min(...ys), mx = Math.max(...ys), r = mx - mn || 1;
  const X = (i) => P + (i * (W - 2 * P)) / (seri.length - 1), Y = (v) => H - P - ((v - mn) * (H - 2 * P)) / r;
  const yol = seri.map((x, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(x.y).toFixed(1)}`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block;margin-top:8px" role="img" aria-label="Takipçi büyümesi">
    <path d="${yol}L${X(seri.length - 1)},${H - P}L${P},${H - P}Z" fill="rgba(232,196,120,.12)"/><path d="${yol}" fill="none" stroke="var(--gold)" stroke-width="2.2" stroke-linejoin="round"/>
    <text x="${P}" y="${H - 6}" fill="var(--mut)" font-size="11">${esc(seri[0].x)}</text><text x="${W - P}" y="${H - 6}" fill="var(--mut)" font-size="11" text-anchor="end">${esc(seri.at(-1).x)}</text>
    <text x="${W - P}" y="${Y(seri.at(-1).y) - 8}" fill="var(--gold)" font-size="12" font-weight="700" text-anchor="end">${sayi(seri.at(-1).y)}</text></svg>`;
}
function renderInstagram() {
  const g = O.instagram; if (!g) return "";
  const h = g.hesap || {}, o = g.ozet30 || {};
  let seri = (g.gecmis || []).map((x) => ({ x: x.tarih.slice(5).split("-").reverse().join("."), y: x.takipci }));
  const fc = g.gunluk?.follower_count; let degisim = "";
  if (fc?.length) { const top = fc.reduce((s, x) => s + (x.deger || 0), 0); degisim = `<div class="mut" style="margin-top:4px">Son 30 günde net takipçi değişimi (Instagram): <b style="color:${top >= 0 ? "var(--ok)" : "var(--err)"}">${top >= 0 ? "+" : ""}${sayi(top)}</b></div>`;
    if (seri.length < 3) { let t = (h.takipci || 0) - top; seri = fc.map((x) => ({ x: x.tarih.slice(5).split("-").reverse().join("."), y: (t += x.deger || 0) })); } }
  const kpi = (v, l, k = "") => `<div${k ? ` data-lk="${k}"` : ""}><b>${sayi(v)}</b><span>${l}</span></div>`;
  const SIRA = { yeni: ["En yeni", (a, b) => new Date(b.zaman || 0) - new Date(a.zaman || 0)], izl: ["En çok izlenen", (a, b) => (b.izlenme || 0) - (a.izlenme || 0)], kay: ["En çok kaydedilen", (a, b) => (b.kaydetme || 0) - (a.kaydetme || 0)], pay: ["En çok paylaşılan", (a, b) => (b.paylasim || 0) - (a.paylasim || 0)] };
  let sira = "yeni"; try { const k = localStorage.getItem("igsira"); if (SIRA[k]) sira = k; } catch {}
  const vids = [...(g.medya || [])].sort(SIRA[sira][1]).slice(0, 15);
  const saat = (g.en_iyi_saatler || []).map((x) => `${String(x.saat).padStart(2, "0")}.00`).join(", ");
  let s = `<h2>INSTAGRAM ANALİZ <span class="mut" style="font-family:Mont;font-size:12px">· son güncelleme ${ago(g.zaman)}</span></h2><div class="card">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">${h.foto ? `<img src="${esc(h.foto)}" alt="" style="width:40px;height:40px;border-radius:50%" referrerpolicy="no-referrer">` : ""}
    <div style="flex:1"><b>${esc(h.ad || h.kullanici || "")}</b><div class="mut">@${esc(h.kullanici || "")} · ${sayi(h.gonderi)} gönderi</div></div><div class="igbtns"><button id="igguncelle">Şimdi güncelle</button><label class="anlik" title="Anlık güncelle"><input type="checkbox" id="iganlik"${typeof canliAnlikAcik === "function" && canliAnlikAcik() ? " checked" : ""}><i></i><span>Anlık güncelle</span></label></div></div>
    ${g.hata ? `<div style="color:var(--err);margin-bottom:8px">${esc(g.hata)}</div>` : ""}
    <div class="kpi kpi4">${kpi(h.takipci, "Takipçi", "takipci")}${kpi(o.views, "30 gün izlenme")}${kpi(o.reach, "30 gün erişim")}${kpi(o.profile_views, "Profil ziyareti")}</div>
    ${degisim}${igGrafik(seri)}
    ${saat ? `<div class="mut" style="margin-top:8px">⏰ En iyi paylaşım saatleri (İstanbul, ortalama izlenmeye göre): <b style="color:var(--gold)">${saat}</b>${g.en_iyi_gun ? ` · en iyi gün: <b style="color:var(--gold)">${esc(g.en_iyi_gun)}</b>` : ""}</div>` : ""}
    <div class="segm" role="group" aria-label="Sıralama">${Object.entries(SIRA).map(([k, [l]]) => `<button class="${k === sira ? "on" : ""}" data-igsira="${k}">${l}</button>`).join("")}</div>
    <div class="tblw" style="margin-top:8px"><table class="igtab vlist"><thead><tr><th>#</th><th></th><th>Video</th><th>▶ İzlenme</th><th>🔖 Kayıt</th><th>↗ Paylaşım</th><th>⏱ Ort. izleme</th></tr></thead><tbody>
    ${vids.map((v, i) => `<tr data-igid="${esc(v.id)}"><td class="ign">${i + 1}</td><td class="igk">${(v.kapak || v.thumbnail_url || v.media_url) ? `<img src="${esc(v.kapak || v.thumbnail_url || v.media_url)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'igph',textContent:'🎬'}))">` : `<span class="igph">🎬</span>`}</td><td class="igb">${esc(v.baslik || "(açıklamasız)")}<div class="mut" style="font-size:11px">${v.zaman ? `<b class="igzam">🕒 ${new Date(v.zaman).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</b> · ${ago(v.zaman)} · ` : ""}❤ <span data-lv="begeni">${sayi(v.begeni)}</span> · 💬 <span data-lv="yorum">${sayi(v.yorum)}</span></div></td><td data-l="▶ İzlenme" data-lv="izlenme">${sayi(v.izlenme)}</td><td data-l="🔖 Kayıt">${sayi(v.kaydetme)}</td><td data-l="↗ Paylaşım">${sayi(v.paylasim)}</td><td data-l="⏱ Ort. izleme">${v.ort_izleme_sn != null ? v.ort_izleme_sn + " sn" : "—"}</td></tr>`).join("") || `<tr><td colspan="7" class="mut">Henüz gönderi yok</td></tr>`}
    </tbody></table></div></div>`;
  return s;
}
function renderTokenKart() {
  const g = O.instagram || {}, h = g.hesap || {}, eksik = g.desteklenmeyen || [];
  const basari = g.zaman && !g.hata && h.kullanici;
  const insightsYok = eksik.length && eksik.some((x) => /reach|views|profile_views|follower_count/.test(x));
  const kayitli = O.igToken?.kayitli, authHata = /190|expired|invalid|süres|geçersiz|oauth/i.test(g.hata || "");
  const sorun = !kayitli || !basari || authHata || insightsYok;
  const tz = O.igToken?.zaman || g.zaman;
  const form = `<form id="tokform" class="tokform" autocomplete="off"><input id="toktxt" type="password" placeholder="Yeni token yapıştır" autocomplete="new-password"><button class="gold" type="submit">Kaydet</button></form><div id="tokmsg" class="mut" style="margin-top:6px"></div>`;
  if (!sorun) return `<h2>Instagram Bağlantısı / Token</h2><div class="card">
    <div class="tokok">✓ Instagram bağlı · token kayıtlı (…${esc(O.igToken.son4 || "")}) · son güncelleme ${tz ? ago(tz) : "—"} · <a href="#" id="tokdegis">Token'ı değiştir</a></div>
    <div id="tokalan" hidden>${form}</div></div>`;
  return `<h2>Instagram Bağlantısı / Token</h2><div class="card">
    <div class="row" style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><span class="st ${basari ? "ok" : "err"}">${basari ? "Son çekim başarılı" : "Son çekim başarısız"}</span><span class="mut">${g.zaman ? ago(g.zaman) : "Hiç çekilmedi"}</span></div>
    <div style="margin-top:8px">Hesap: <b>${esc(h.kullanici ? "@" + h.kullanici : "—")}</b> · Takipçi: <b>${h.takipci != null ? sayi(h.takipci) : "—"}</b></div>
    ${g.hata ? `<div style="color:var(--err);margin-top:6px">${esc(g.hata)}${authHata ? " — token süresi dolmuş veya geçersiz, yenisini yapıştır." : ""}</div>` : ""}
    ${insightsYok ? `<div class="uyari">⚠️ <b>İstatistik izni eksik:</b> Bu token istatistik izni olmadan oluşturulmuş. Meta'da izni ekleyip yeni token üret, buraya yapıştır.</div>` : ""}
    ${eksik.length ? `<div class="mut" style="margin-top:6px">Gelmeyen metrikler: ${eksik.map((x) => `<span class="tag">${esc(x)}</span>`).join(" ")}</div>` : ""}
    <div class="sep"></div><b style="font-size:14px">Token güncelle</b>
    ${kayitli ? `<div class="mut" style="margin-top:6px">Kayıtlı token: …${esc(O.igToken.son4 || "")}</div>` : `<div style="color:var(--err);margin-top:6px">Henüz token kaydedilmedi</div>`}
    ${form}
    <details class="nasil" open><summary>Token nasıl yenilenir? (insights izniyle)</summary><ol>
      <li><a href="https://developers.facebook.com/apps" target="_blank" rel="noopener">developers.facebook.com</a> → <b>Animasyon Tarih Ajan</b> uygulamasını aç</li>
      <li><b>Customize use case</b> → <b>Permissions and features</b></li>
      <li><b>instagram_business_manage_insights</b> iznini ekle</li>
      <li><b>API setup with Instagram login</b> (Unified login) bölümüne geç</li>
      <li><b>Generate token</b> ile yeni token oluştur, kopyala</li>
      <li>Yukarıdaki kutuya yapıştırıp <b>Kaydet</b>'e bas</li></ol></details></div>`;
}
function baglaToken() {
  const d = $("#tokdegis"); if (d) d.onclick = (e) => { e.preventDefault(); const a = $("#tokalan"); a.hidden = !a.hidden; if (!a.hidden) $("#toktxt").focus(); };
  const f = $("#tokform"); if (!f) return;
  f.onsubmit = async (e) => {
    e.preventDefault(); const i = $("#toktxt"), m = $("#tokmsg"), b = f.querySelector("button"), v = i.value.trim();
    if (v.length < 20) { m.textContent = "Token çok kısa görünüyor."; return; }
    b.disabled = true; m.style.color = ""; m.textContent = "Kaydediliyor…";
    try { const r = await api("ig_token", { token: v }); i.value = ""; if (r.igToken) O.igToken = r.igToken; m.style.color = "var(--ok)"; m.textContent = "✓ Token kaydedildi, Instagram verisi çekiliyor…"; await igYenile(); }
    catch (er) { m.style.color = "var(--err)"; const izin = /izin/.test(er.message || "");
      m.innerHTML = izin ? `GitHub anahtarına 'Secrets: Read and write' izni eklenmeli. Şimdilik token'ı elle ekleyebilirsin: <a href="https://github.com/lazziya5353/animasyonlu-tarih/settings/secrets/actions" target="_blank" rel="noopener">GitHub → Secrets → IG_TOKEN</a>` : esc(er.message || "Hata"); }
    finally { b.disabled = false; }
  };
}
async function igYenile() {
  const r = await api("ig_refresh");
  if (r.instagram) { O.instagram = r.instagram; render(); }
  else { alert("Kayıtlı token yok; veri GitHub üzerinden güncelleniyor (~1-2 dk)."); setTimeout(load, 90000); }
}
function baglaInstagram() {
  if ($("#igguncelle") && !window._igOto) { window._igOto = true; api("ig_refresh").then((r) => { if (r && r.instagram) { O.instagram = r.instagram; render(); } }).catch(() => {}); }
  if (typeof canliBagla === "function") canliBagla();
  document.querySelectorAll("[data-igsira]").forEach((x) => (x.onclick = () => { try { localStorage.setItem("igsira", x.dataset.igsira); } catch {} render(); }));
  const b = $("#igguncelle"); if (b) b.onclick = async () => { b.disabled = true; b.textContent = "Güncelleniyor…"; try { await igYenile(); } catch (e) { alert(e.message || "Hata"); } finally { b.disabled = false; b.textContent = "Şimdi güncelle"; } };
}
function renderAnaliz() {
  const a = O.analiz; if (!a || !(a.instagram || a.youtube)) return "";
  const ig = a.instagram; let h = `<h2>İstatistikler <span class="mut" style="font-family:Mont;font-size:12px">· ${ago(a.zaman)}</span></h2><div class="card">`;
  if (ig) h += `<div class="kpi"><div><b>${ig.takipci}</b><span>Takipçi</span></div><div><b>${ig.gonderi}</b><span>Gönderi</span></div><div><b>${a.en_iyi_zaman || "—"}</b><span>En iyi saat</span></div></div>` +
    (ig.videolar || []).slice(0, 5).map((v, i) => `<div class="mut" style="display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-top:1px solid var(--line)"><span>${i + 1}. ${esc(v.baslik)}</span><span style="white-space:nowrap">▶ ${v.izlenme} · 🔖 ${v.kaydetme}</span></div>`).join("");
  if (a.youtube) h += `<div class="mut" style="margin-top:10px">YouTube: ${a.youtube.abone} abone · ${a.youtube.videolar.reduce((s, v) => s + v.izlenme, 0)} toplam izlenme</div>`;
  if (a.notlar?.length) h += `<div class="mut" style="margin-top:10px">${a.notlar.map(esc).join("<br>")}</div>`;
  return h + `</div>`;
}

const urlCache = {};
async function fileUrl(path, taze) {
  if (DEMO) return `../${path}`;
  if (urlCache[path] && !taze) return urlCache[path];
  const r = await api("file", { path }, true); if (!r.ok) return null;
  return (urlCache[path] = URL.createObjectURL(await r.blob()));
}

// ───────── proje sayfası ─────────
function projeKapat() { CUR = null; $("#detail").classList.add("hide"); $("#main").classList.remove("hide"); load(); }
// Telefonun/tarayıcının geri tuşu proje sayfasından panele döner (siteden çıkmaz)
window.addEventListener("popstate", (e) => { const p = e.state?.p; if (p) openProject(p, true); else if (CUR) projeKapat(); });
async function openProject(slug, gecmisten) {
  if (!gecmisten && history.state?.p !== slug) history.pushState({ p: slug }, "", "#p=" + encodeURIComponent(slug));
  CUR = slug;
  const P = await api("project", { slug }); const sc = P.script; const d = $("#detail");
  $("#main").classList.add("hide"); d.classList.remove("hide");
  const scenes = sc?.sahneler || (P.project?.scenes || []).map((s) => ({ image: s.image, big: s.big }));
  const sahneSorun = {}; for (const m of P.kontrol?.gorsel?.maddeler || []) if (m.sahne && m.seviye !== "bilgi") (sahneSorun[m.sahne] ||= []).push(m);
  let h = `<div class="flex" style="justify-content:space-between;align-items:center"><button class="ghost" id="back">← Geri</button><button class="ghost" id="arsB">${(O?.arsiv || []).includes(slug) ? "↩ Arşivden çıkar" : "📦 Arşive at"}</button><a class="btn gold" href="studyo.html?p=${encodeURIComponent(slug)}${DEMO ? "&demo=1" : ""}">🎬 Canlı ilerleme</a></div><h2 style="margin-top:14px">${esc(sc?.baslik || P.project?.title || slug)}</h2>`;
  h += kontrolKart(P);
  if (sc) {
    const st = sc.durum === "onaylandi" ? `<span class="st ok">Onaylandı</span>` : `<span class="st wait">Onay bekliyor</span>`;
    const edit = sc.durum !== "onaylandi";
    const body = edit
      ? `<div class="mut" style="margin:8px 0">Onaylamadan önce metni burada düzenleyebilirsin. Her satır bir cümle.</div>` + sc.sahneler.map((s, i) => `<div class="ed"><span class="mut">${i + 1} · ${esc(s.big || "")}</span><textarea data-sc="${i}" rows="${Math.max(2, (s.lines || []).length)}">${esc((s.lines || []).join("\n"))}</textarea></div>`).join("")
      : `<pre>${esc(sc.seslendirme_metni)}</pre>`;
    h += `<h2>Metin</h2><div class="card">${st}<h3 style="font-size:14px;margin:12px 0 6px">Seslendirme metni</h3>${body}
      <div class="flex"><button data-copy="${esc(sc.seslendirme_metni)}">Metni kopyala</button>${edit ? `<button id="savetxt">Değişiklikleri kaydet</button><button class="gold" id="approve">Onayla → ses üret</button>` : ""}</div></div>`;
  }
  const eksik = scenes.filter((s) => !P.gorseller.includes(s.image.split("/").pop())).length;
  h += `<h2>Sahneler <span class="mut" style="font-family:Mont;font-size:12px">· ${scenes.length - eksik}/${scenes.length} görsel</span></h2>`;
  if (sc) h += `<div class="flex" style="margin-bottom:10px"><button class="gold" id="tumprompt">📋 Tüm promptları kopyala (${sc.sahneler.length})</button></div>`;
  h += `<div class="drop" id="drop"><b>Görselleri toplu yükle</b><span class="mut">Gemini'de ürettiğin görselleri buraya sürükle ya da dokunup hepsini birden seç</span><input type="file" accept="image/*" multiple id="toplu" hidden></div>`;
  h += `<div class="scenes">`;
  scenes.forEach((s, i) => { const has = P.gorseller.includes(s.image.split("/").pop()); const so = sahneSorun[i + 1];
    h += `<div class="sc" data-img="${has ? esc(s.image) : ""}" data-i="${i + 1}" title="${esc((so || []).map((m) => m.mesaj).join("\n"))}"><i>${i + 1}</i>${so ? `<em class="${so.some((m) => m.seviye === "hata") ? "e" : "w"}">!</em>` : ""}${has ? "" : "Yükle"}</div>`; });
  h += `</div><div class="mut" style="margin-top:6px">Tek bir görseli değiştirmek için karesine dokun.</div>`;
  if (sc) h += `<details class="card" style="margin-top:12px"><summary>Gemini promptları</summary>
    ${sc.sahneler.map((s, i) => `<div class="flex" style="align-items:center"><span class="mut">${i + 1}</span><button data-copy="${esc(s.prompt_tam)}">${esc(s.big || "Sahne")} promptunu kopyala</button></div>`).join("")}</details>`;
  const hasVoice = P.dosyalar.includes("ses.wav");
  h += `<h2>Ses</h2><div class="card">${hasVoice ? `<audio id="aud" controls style="width:100%"></audio>` : `<span class="mut">Ses yok.</span>`}<div class="flex"><label class="btn">Ses yükle (.wav)<input type="file" accept="audio/wav" id="up-ses" hidden></label></div></div>`;
  h += `<h2>Video</h2><div class="card">${P.video ? `<video id="vid" controls playsinline></video><div class="mut" style="margin-top:8px">${(P.video.boyut / 1e6).toFixed(1)} MB · ${ago(P.video.zaman)}</div>` : `<span class="mut">Henüz video yok.</span>`}
    <div class="flex"><button id="filtre" title="Kahverengi ton, kararan kenarlar ve kumlanma">${P.project?.sade ? "Film filtresi: kapalı" : "Film filtresi: açık"}</button><button class="gold" id="render">${P.video ? "Videoyu yeniden üret" : "Videoyu üret"}</button>${P.video ? `<button id="dl">İndir</button>` : ""}</div></div>`;
  if (sc) h += paylasimKart(P, sc);
  h += `<h2>Sil</h2><div class="card sil"><div class="mut" style="font-size:12.5px;margin-bottom:8px">Silinen geri gelmez. Instagram'da paylaşılmış gönderiye dokunmaz, onu Instagram'dan silmen gerekir.</div>
    <div class="flex">${P.video ? `<button class="silb" data-sil="video">🗑 Sadece videoyu sil</button>` : ""}<button class="silb kirmizi" data-sil="hepsi">🗑 Projeyi tamamen sil</button></div></div>`;
  d.innerHTML = h;
  window.scrollTo(0, 0);
  $("#back").onclick = () => (history.state?.p ? history.back() : projeKapat());
  if ($("#filtre")) $("#filtre").onclick = async (e) => { e.target.disabled = true; try { const r = await api("ayar", { slug, sade: !P.project?.sade }); toast(r.sade ? "Filtre kapatıldı. Görmek için videoyu yeniden üret." : "Filtre açıldı. Görmek için videoyu yeniden üret."); openProject(slug, true); } catch (err) { e.target.disabled = false; toast(err.message || "Hata"); } };
  if ($("#arsB")) $("#arsB").onclick = () => arsivle(slug, (O?.arsiv || []).includes(slug));
  d.querySelectorAll("[data-sil]").forEach((b) => (b.onclick = async () => {
    const hepsi = b.dataset.sil === "hepsi", ad = sc?.baslik || slug;
    if (!confirm(hepsi ? `"${ad}" projesi tamamen silinsin mi?\n\nMetin, görseller, ses ve video gider. Geri alınamaz.` : `"${ad}" videosu silinsin mi?\n\nMetin, görseller ve ses kalır; istersen videoyu yeniden üretebilirsin.`)) return;
    b.disabled = true; b.textContent = "Siliniyor…";
    try {
      await api("sil", { slug, tur: b.dataset.sil, onay: slug });
      toast(hepsi ? "Proje siliniyor, 30 sn içinde listeden kalkar" : "Video siliniyor, 30 sn sürer");
      if (hepsi) { GIZLI.add(slug); history.replaceState(null, "", location.pathname + location.search); projeKapat(); setTimeout(load, 40000); }
      else setTimeout(() => CUR === slug && openProject(slug), 40000);
    } catch (e) { b.disabled = false; b.textContent = hepsi ? "🗑 Projeyi tamamen sil" : "🗑 Sadece videoyu sil"; toast(e.message || "Hata"); }
  }));
  d.querySelectorAll("[data-copy]").forEach((b) => (b.onclick = () => { navigator.clipboard.writeText(b.dataset.copy); toast("Kopyalandı"); }));
  d.querySelectorAll("[data-kopya]").forEach((b) => (b.onclick = () => { navigator.clipboard.writeText(b.dataset.kopya); toast("Kopyalandı"); }));
  d.querySelectorAll("[data-acik]").forEach((b) => (b.onclick = () => { const L = [sc.aciklama, ...(sc.aciklama_alternatifleri || [])].filter(Boolean); const t = $("#caption"); if (!t) return; t.value = L[+b.dataset.acik] + ((sc.hashtagler || []).length ? "\n\n" + sc.hashtagler.join(" ") : ""); t.scrollIntoView({ behavior: "smooth", block: "center" }); toast("Açıklama kutuya geldi, beğendiysen Kaydet"); }));
  d.querySelectorAll(".sc").forEach(async (el) => {
    if (el.dataset.img) { const u = await fileUrl(`projects/${slug}/${el.dataset.img}`); if (u) el.style.backgroundImage = `url(${u})`; }
    el.onclick = () => { const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*"; inp.onchange = () => topluSecim(slug, scenes, P, [...inp.files], Number(el.dataset.i)); inp.click(); };
  });
  const dr = $("#drop"), tf = $("#toplu");
  dr.onclick = () => tf.click(); tf.onchange = () => topluSecim(slug, scenes, P, [...tf.files]);
  dr.ondragover = (e) => { e.preventDefault(); dr.classList.add("on"); }; dr.ondragleave = () => dr.classList.remove("on");
  dr.ondrop = (e) => { e.preventDefault(); dr.classList.remove("on"); topluSecim(slug, scenes, P, [...e.dataTransfer.files].filter((f) => f.type.startsWith("image/"))); };
  if ($("#tumprompt")) $("#tumprompt").onclick = () => {
    const t = `Aşağıdaki ${sc.sahneler.length} görseli sırayla üret. Her biri AYRI bir görsel olsun, hepsi dikey 9:16, gerçekçi sinematik film karesi. Görsellerde yazı olmasın.\n\n` +
      sc.sahneler.map((s, i) => `${i + 1}) ${s.prompt_tam}`).join("\n\n");
    navigator.clipboard.writeText(t); toast(`${sc.sahneler.length} prompt kopyalandı`);
  };
  if (hasVoice) $("#aud").src = await fileUrl(`projects/${slug}/ses.wav`);
  $("#up-ses").onchange = (e) => upload(slug, "ses.wav", e.target.files[0]).then(() => openProject(slug));
  const readEdits = () => [...d.querySelectorAll("textarea[data-sc]")].map((t) => t.value.split("\n").map((x) => x.trim()).filter(Boolean));
  const changed = () => sc && readEdits().some((l, i) => l.join("\n") !== (sc.sahneler[i].lines || []).join("\n"));
  const saveTxt = async () => { if (!changed()) return; await guvenli(() => api("save_text", { slug, sahneler: readEdits() }), "Metin kaydedildi, senaryo kontrol ediliyor"); };
  if ($("#savetxt")) $("#savetxt").onclick = async () => { await saveTxt(); openProject(slug); };
  if ($("#approve")) $("#approve").onclick = async () => { await saveTxt(); await guvenli(() => api("approve", { slug }), "Onaylandı, ses üretiliyor"); openProject(slug); };
  $("#render").onclick = async () => {
    if (eksik && !confirm(`${eksik} sahnenin görseli eksik. Yine de video üretilsin mi?`)) return;
    await guvenli(() => api("run", { agent: "kurgucu", inputs: { slug } }), "Kurgucu çalışıyor (5-10 dk), bitince kurgu kontrolü otomatik yapılır");
  };
  d.querySelectorAll("[data-duzelt]").forEach((b) => (b.onclick = async (e) => {
    e.preventDefault(); e.stopPropagation(); if (b.disabled) return; b.disabled = true; const eski = b.textContent; b.textContent = "Gönderiliyor…";
    try { await api("duzelt", { slug, maddeler: JSON.parse(b.dataset.duzelt) }); b.textContent = "✓ Ajan düzeltiyor"; toast("Yönetici ajan düzeltiyor. Canlı ilerleme'den izleyebilirsin, cevabı 'Ajana yaz' kutusunda."); }
    catch (er) { b.disabled = false; b.textContent = eski; toast(er.message || "Hata"); }
  }));
  if ($("#rekontrol")) $("#rekontrol").onclick = () => guvenli(() => api("run", { agent: "kontrol", inputs: { slug, asama: "hepsi" } }), "Kontrolcüler çalışıyor (~2 dk)");
  d.querySelectorAll("[data-kk]").forEach(async (b) => { const u = await fileUrl(`projects/${slug}/kontrol/kareler.jpg`); if (u) { b.src = u; b.onclick = () => window.open(u); } });
  if (P.video) {
    const u = DEMO ? "../demo.mp4" : (await api("video_url", { id: P.video.id })).url; $("#vid").src = u;
    // imzalı adres birkaç dakikada eskir: indirirken her seferinde yenisini al
    $("#dl").onclick = async () => {
      try { const r = DEMO ? { url: u } : await api("video_url", { id: P.video.id }); if (!r.url) throw 0; location.href = r.url; }
      catch { toast("Video adresi alınamadı, sayfayı yenileyip tekrar dene"); }
    };
  }
  if (sc) baglaPaylasim(slug, P, sc);
}

function kontrolKart(P) {
  const K = P.kontrol || {}; const var_ = Object.values(K).some(Boolean);
  let h = `<h2>Kontrolcüler</h2><div class="card">`;
  if (!var_) h += `<div class="mut">Henüz kontrol yapılmadı. Metin yazılınca, ses üretilince, görseller yüklenince ve video çıkınca otomatik çalışır.</div>`;
  for (const k of ["senaryo", "ses", "gorsel", "kurgu"]) {
    const r = K[k]; if (!r) { h += `<div class="krow"><b>${ASAMA_AD[k]}</b>${pill()}<span class="mut">—</span></div>`; continue; }
    const md = (r.maddeler || []).filter((m) => m.seviye !== "bilgi"), bilgi = (r.maddeler || []).filter((m) => m.seviye === "bilgi");
    h += `<details class="krow"${r.durum === "hata" ? " open" : ""}><summary><b>${ASAMA_AD[k]}</b>${pill(r.durum)}<span class="mut">${esc(r.ozet)} · ${ago(r.zaman)}</span></summary>
      ${md.length ? `<ul>${md.map((m) => `<li class="${m.seviye}">${m.sahne ? `<b>Sahne ${m.sahne}:</b> ` : ""}${esc(m.mesaj)} <button class="duzelt" data-duzelt='${esc(JSON.stringify([{ asama: k, sahne: m.sahne || 0, mesaj: m.mesaj }]))}'>🔧 Düzelt</button></li>`).join("")}</ul>` : `<div class="mut" style="padding:6px 0 4px">Sorun bulunmadı ✓</div>`}
      ${bilgi.length ? `<div class="mut" style="font-size:12px">${bilgi.map((m) => esc(m.mesaj)).join("<br>")}</div>` : ""}
      ${k === "kurgu" ? `<img data-kk class="kk" alt="Kontrol kareleri">` : ""}</details>`;
  }
  const tum = ["senaryo", "ses", "gorsel", "kurgu"].flatMap((k) => (K[k]?.maddeler || []).filter((m) => m.seviye === "hata" || m.seviye === "uyari").map((m) => ({ asama: k, sahne: m.sahne || 0, mesaj: m.mesaj })));
  return h + `<div class="flex">${tum.length ? `<button class="gold" data-duzelt='${esc(JSON.stringify(tum))}'>🔧 Hepsini düzelt (${tum.length})</button>` : ""}<button id="rekontrol">Hepsini yeniden kontrol et</button></div>
    <div class="mut" style="font-size:11.5px;margin-top:6px">Düzelt: yönetici ajan sorunu okur, gereken işi (metin, ses, görsel, video) sırayla yaptırır. Claude API'den birkaç kuruş harcar 💳</div></div>`;
}

function varsayilanMetin(sc) {
  if (sc.paylasim) return sc.paylasim;
  const hs = (sc.hashtagler || []).map((x) => (x.startsWith("#") ? x : "#" + x)).join(" ");
  return `${(sc.aciklama || "").trim()}\n\n🔔 Tarihin unutulmaz anları için takip et: ${HANDLE}\n\n${hs}`.trim();
}
function sonraki(saat = 19, dk = 0) { const t = new Date(); t.setSeconds(0, 0); t.setHours(saat, dk); if (t < Date.now() + 15 * 60e3) t.setDate(t.getDate() + 1); return t; }
const yerelISO = (t) => new Date(t - t.getTimezoneOffset() * 60e3).toISOString().slice(0, 16);

function paylasimKart(P, sc) {
  const ig = P.yayin?.instagram, plan = (P.plan || []).filter((x) => ["bekliyor", "gonderildi"].includes(x.durum)), son = (P.plan || []).slice(-1)[0];
  let h = `<h2>Paylaşım</h2><div class="card"><div class="mut" style="margin-bottom:6px">Instagram açıklaması (düzenleyebilirsin)</div>
    <textarea id="caption" rows="9" class="full">${esc(varsayilanMetin(sc))}</textarea>
    <div class="flex"><button id="capkaydet">Kaydet</button><button id="capkopya">Kopyala</button></div>`;
  const kancalar = [sc.hook, ...(sc.kanca_alternatifleri || [])].filter(Boolean), aciklamalar = [sc.aciklama, ...(sc.aciklama_alternatifleri || [])].filter(Boolean);
  if (kancalar.length > 1 || aciklamalar.length > 1) {
    h += `<div class="sep"></div><b style="font-size:14px">💡 Öneriler</b><div class="mut" style="font-size:12px;margin:4px 0 8px">Açıklamaya dokununca yukarıdaki kutuya gelir (etiketler eklenir), sonra Kaydet. Kancaya dokununca kopyalanır.</div>`;
    if (kancalar.length) h += `<div class="mut" style="font-size:12px">Kanca başlıklar</div>` + kancalar.map((x, i) => `<button class="oneri" data-kopya="${esc(x)}">${i === 0 ? "⭐ " : ""}${esc(x)}</button>`).join("");
    if (aciklamalar.length) h += `<div class="mut" style="font-size:12px;margin-top:8px">Açıklamalar</div>` + aciklamalar.map((x, i) => `<button class="oneri uzun" data-acik="${i}">${i === 0 ? "⭐ " : ""}${esc(x)}</button>`).join("");
    if ((sc.hashtagler || []).length) h += `<div class="mut" style="font-size:12px;margin-top:8px">Etiketler</div><button class="oneri" data-kopya="${esc(sc.hashtagler.join(" "))}">${esc(sc.hashtagler.join(" "))}</button>`;
  }
  h += `<div class="sep"></div><b style="font-size:14px">📸 Instagram</b>`;
  if (ig) h += `<div style="margin-top:8px"><span class="st ok">Yayında</span> <a href="${esc(ig.permalink)}" target="_blank" rel="noopener">Gönderiyi aç ↗</a> <span class="mut">· ${ig.zaman ? tarihTR(ig.zaman) : ""}</span></div>`;
  else {
    if (plan.length) h += plan.map((x) => `<div style="margin-top:8px"><span class="st ${x.durum === "bekliyor" ? "wait" : "run"}">${x.durum === "bekliyor" ? "Planlandı" : "Yükleniyor"}</span> <span class="mut">${tarihTR(x.zaman)}</span> ${x.durum === "bekliyor" ? `<button class="ghost" data-iptal="${esc(x.id)}">İptal</button>` : ""}</div>`).join("");
    else if (son?.durum === "hata") h += `<div style="margin-top:8px"><span class="st err">Paylaşılamadı</span> <span class="mut">${esc(son.mesaj || "")}</span></div>`;
    h += `<div class="flex" style="align-items:center"><input type="datetime-local" id="pzaman" value="${yerelISO(sonraki(19))}"><button class="gold" id="planla"${!P.video ? " disabled" : ""}>Planla</button><button id="simdi"${!P.video ? " disabled" : ""}>Şimdi paylaş</button></div>
      <div class="mut" style="margin-top:6px;font-size:12px">${P.video ? "Paylaşmadan önce kurgu kontrolüne bakılır; hata varsa paylaşmaz." : "Önce videoyu üret."} Instagram bağlı değilse kurulum: docs/YAYIN_KURULUM.md</div>`;
  }
  const baslik = `${(sc.baslik || "").slice(0, 88)} #Shorts`;
  const etiket = (sc.hashtagler || []).map((x) => x.replace(/^#/, "")).join(", ");
  h += `<div class="sep"></div><b style="font-size:14px">▶️ YouTube Shorts paketi</b>
    <div class="mut" style="margin:6px 0 8px;font-size:12px">YouTube, onaysız uygulamaların otomatik yüklediği videoları kalıcı olarak gizli bırakıyor; bu yüzden videoyu Studio'dan sen yüklersin, metinler hazır:</div>
    <div class="flex"><button data-copy="${esc(baslik)}">Başlığı kopyala</button><button data-copy="${esc(varsayilanMetin(sc))}">Açıklamayı kopyala</button><button data-copy="${esc(etiket)}">Etiketleri kopyala</button></div></div>`;
  return h;
}
function baglaPaylasim(slug, P, sc) {
  const cap = () => $("#caption").value;
  $("#capkaydet").onclick = () => guvenli(() => api("save_caption", { slug, metin: cap() }), "Açıklama kaydedildi");
  $("#capkopya").onclick = () => { navigator.clipboard.writeText(cap()); toast("Kopyalandı"); };
  const kaydetGerekirse = async () => { if (cap() !== varsayilanMetin(sc)) await api("save_caption", { slug, metin: cap() }); };
  if ($("#planla")) $("#planla").onclick = async () => {
    const t = new Date($("#pzaman").value); if (isNaN(t)) return toast("Tarih seç");
    await kaydetGerekirse(); await guvenli(() => api("planla", { slug, zaman: t.toISOString() }), `${tarihTR(t)} için planlandı`); openProject(slug);
  };
  if ($("#simdi")) $("#simdi").onclick = async () => {
    if (!confirm("Video şimdi Instagram'da paylaşılsın mı?")) return;
    await kaydetGerekirse(); await guvenli(() => api("run", { agent: "yayinci", inputs: { slug } }), "Yayıncı çalışıyor (~3 dk)"); setTimeout(() => openProject(slug), 4000);
  };
  document.querySelectorAll("[data-iptal]").forEach((b) => (b.onclick = async () => { await guvenli(() => api("plan_iptal", { id: b.dataset.iptal }), "Plan iptal edildi"); openProject(slug); }));
}

// ───────── toplu görsel yükleme ─────────
async function kucult(file) { // 1080×1920'yi aşmayacak şekilde JPEG'e çevirir (yükleme sınırı ve hız için)
  const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = URL.createObjectURL(file); });
  const k = Math.min(1, 1920 / img.naturalHeight, 1920 / img.naturalWidth);
  const c = document.createElement("canvas"); c.width = Math.round(img.naturalWidth * k); c.height = Math.round(img.naturalHeight * k);
  c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
  let q = 0.9, b; do { b = await new Promise((r) => c.toBlob(r, "image/jpeg", q)); q -= 0.1; } while (b.size > 3.6e6 && q > 0.4);
  return { blob: b, url: URL.createObjectURL(b), ad: file.name };
}
async function topluSecim(slug, scenes, P, files, baslangic) {
  if (!files.length) return;
  files.sort((a, b) => a.lastModified - b.lastModified || a.name.localeCompare(b.name, "tr", { numeric: true }));
  const bos = scenes.map((s, i) => i + 1).filter((i) => !P.gorseller.includes(scenes[i - 1].image.split("/").pop()));
  // tek karede dokunulduysa oradan başla; yoksa önce boş sahneleri doldur, hepsi doluysa 1'den başla
  let hedef = baslangic ? scenes.map((s, i) => i + 1).filter((i) => i >= baslangic) : (files.length <= bos.length ? bos : scenes.map((s, i) => i + 1));
  hedef = hedef.slice(0, files.length);
  const ogeler = await Promise.all(files.slice(0, hedef.length).map(kucult));
  const m = document.createElement("div"); m.className = "modal";
  const ciz = () => {
    m.innerHTML = `<div class="card mbox"><b>${ogeler.length} görsel yüklenecek</b><div class="mut" style="margin:4px 0 10px">Sıra indirme sırasına göre. Yer değiştirmek için iki görsele sırayla dokun.</div>
      <div class="scenes">${ogeler.map((o, k) => `<div class="sc sel" data-k="${k}" style="background-image:url(${o.url})"><i>${hedef[k]}</i><span class="cap">${esc(scenes[hedef[k] - 1].big || "")}</span></div>`).join("")}</div>
      <div class="prog hide"><i></i></div><div class="flex"><button class="gold" id="yuklebas">Yükle</button><button id="vazgec">Vazgeç</button></div></div>`;
    let secili = null;
    m.querySelectorAll("[data-k]").forEach((el) => (el.onclick = () => {
      const k = Number(el.dataset.k);
      if (secili === null) { secili = k; el.classList.add("on"); return; }
      [ogeler[secili], ogeler[k]] = [ogeler[k], ogeler[secili]]; secili = null; ciz();
    }));
    m.querySelector("#vazgec").onclick = () => m.remove();
    m.querySelector("#yuklebas").onclick = async () => {
      const bar = m.querySelector(".prog"); bar.classList.remove("hide"); m.querySelector("#yuklebas").disabled = true; m.querySelector("#vazgec").disabled = true;
      let hata = 0;
      for (let k = 0; k < ogeler.length; k++) {
        try { await upload(slug, `images/s${String(hedef[k]).padStart(2, "0")}.jpg`, ogeler[k].blob, true); delete urlCache[`projects/${slug}/images/s${String(hedef[k]).padStart(2, "0")}.jpg`]; }
        catch { hata++; }
        bar.firstElementChild.style.width = `${((k + 1) / ogeler.length) * 100}%`;
      }
      m.remove();
      if (hata) toast(`${hata} görsel yüklenemedi, tekrar dene`);
      else { toast("Görseller yüklendi, görsel kontrolcüsü çalışıyor"); await api("run", { agent: "kontrol", inputs: { slug, asama: "gorsel" } }).catch(() => {}); }
      openProject(slug);
    };
  };
  document.body.append(m); ciz();
}
async function upload(slug, name, file, sessiz) {
  if (!file) return; if (file.size > 4.2e6) { toast("Dosya 4 MB'tan büyük olamaz"); throw new Error("büyük"); }
  const b64 = await new Promise((res) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.readAsDataURL(file); });
  await api("upload", { slug, name, base64: b64 }); if (!sessiz) toast("Yüklendi");
}

// ───────── demo verisi (?demo=1) ─────────
function demo(action) {
  const now = new Date().toISOString(), saat = (h) => new Date(Date.now() - h * 3600e3).toISOString();
  if (action === "login") return { token: "demo" };
  if (action === "overview") return {
    status: { arastirmaci: { durum: "tamam", mesaj: "2026-W47 raporu hazır", zaman: now }, senarist: { durum: "tamam", mesaj: "'Malazgirt 1071' metni onay bekliyor", zaman: now },
      gorsel: { durum: "tamam", mesaj: "malazgirt-1071: ses hazır", zaman: now }, kurgucu: { durum: "calisiyor", mesaj: "osmanli-1299-1923 videosu üretiliyor", zaman: now },
      kontrol: { durum: "tamam", mesaj: "malazgirt-1071: senaryo ✓, ses ✓, gorsel !", zaman: saat(1) }, yayinci: { durum: "tamam", mesaj: "Instagram bağlı: @animasyon.tarih · 1.284 takipçi", zaman: saat(5) },
      analist: { durum: "tamam", mesaj: "Takipçi: 1284 (+212) · En çok izlenen: 10 Kasım", zaman: saat(30) }, yorumcu: { durum: "tamam", mesaj: "6 yeni yorum · 2 cevap bekliyor", zaman: saat(2) } },
    runs: { arastirmaci: { durum: "completed", sonuc: "success", zaman: now }, senarist: { durum: "completed", sonuc: "success", zaman: now }, gorsel: { durum: "completed", sonuc: "success", zaman: now }, kurgucu: { durum: "in_progress", zaman: now },
      kontrol: { durum: "completed", sonuc: "success", zaman: saat(1) }, yayinci: { durum: "completed", sonuc: "success", zaman: saat(5) }, analist: { durum: "completed", sonuc: "success", zaman: saat(30) }, yorumcu: { durum: "completed", sonuc: "success", zaman: saat(2) } },
    projeler: ["osmanli-1299-1923", "malazgirt-1071"],
    harcama: { aylik: 0.92, butce: 5, servis: { claude: 0.92 }, son: [{ ajan: "arastirmaci", detay: "haftalık rapor", usd: 0.31 }] },
    analiz: { zaman: saat(30), en_iyi_zaman: "Pazar 19.00", instagram: { takipci: 1284, gonderi: 6, videolar: [{ baslik: "Saat 09.05… Zaman bir an durdu. 🇹🇷", izlenme: 48210, kaydetme: 2140 }, { baslik: "1299'da Söğüt'te küçük bir beylik…", izlenme: 12904, kaydetme: 611 }, { baslik: "Malazgirt 1071", izlenme: 6120, kaydetme: 288 }] }, notlar: ["Takipçi: 1284 (+212 geçen kontrole göre)", "En iyi paylaşım zamanı şimdilik: Pazar 19.00"] },
    yorumlar: { bekleyen: [{ id: "1", tur: "soru", kullanici: "tarihsever_34", gonderi: "Saat 09.05…", metin: "Naaşı neden 15 yıl Etnografya Müzesi'nde kaldı?", taslak: "Anıtkabir'in yapımı 1953'te tamamlandığı için geçici olarak orada kaldı 🙏 Bunu ayrı bir videoda anlatabiliriz!" },
      { id: "2", tur: "oneri", kullanici: "mert.yilmaz", gonderi: "1299'da Söğüt'te…", metin: "Çanakkale'yi de yapın lütfen", taslak: "Harika fikir, listemize ekledik! 18 Mart'a özel hazırlıyoruz 🇹🇷" },
      { id: "3", tur: "spam", kullanici: "kazan_hemen99", gonderi: "Malazgirt 1071", metin: "Takipçi kazanmak için profilime gel!!!", taslak: "" }],
      fikirler: [{ konu: "Çanakkale Deniz Zaferi", kaynak: "@mert.yilmaz" }, { konu: "Anıtkabir'in yapım hikâyesi", kaynak: "@tarihsever_34" }] },
    report: { hafta: "2026-W47", gunler: [
      { tarih: "2026-11-17", gun: "Salı", olaylar: [{ yil: 1922, baslik: "Son padişah Vahdettin İstanbul'dan ayrıldı", ozet: "Vahdettin 17 Kasım'da bir İngiliz gemisiyle şehri terk etti.", yildiz: 4 }] },
      { tarih: "2026-11-20", gun: "Cuma", olaylar: [{ yil: 1945, baslik: "Nürnberg Davaları başladı", ozet: "Nazi liderleri yargılanmaya başlandı.", yildiz: 4, durum: "yap" }] }],
      savas_onerisi: { yil: 1071, baslik: "Malazgirt Meydan Muharebesi", ozet: "Alparslan'ın zaferiyle Anadolu'nun kapıları Türklere açıldı. Harita animasyonuna çok uygun.", yildiz: 5, durum: "yap" } } };
  if (action === "project") return {
    script: { baslik: "Malazgirt 1071", durum: "onaylandi", seslendirme_metni: "1071. Ağustosun son günleri...\nAlparslan'ın ordusu Malazgirt ovasında Bizans'ın karşısındaydı...",
      sahneler: [{ image: "images/img01.jpg", big: "1071", prompt_tam: "..." }, { image: "images/img02.jpg", big: "ALPARSLAN", prompt_tam: "..." }, { image: "images/img03.jpg", big: "MALAZGİRT", prompt_tam: "..." }, { image: "images/s04.jpg", big: "ZAFER", prompt_tam: "..." }],
      aciklama: "Anadolu'nun kapısını açan savaş: 26 Ağustos 1071.", hashtagler: ["tarih", "malazgirt", "alparslan"] },
    gorseller: ["img01.jpg", "img02.jpg", "img03.jpg"], dosyalar: ["ses.wav"], video: { id: 1, boyut: 6.6e7, zaman: saat(1) },
    kontrol: { senaryo: { durum: "tamam", ozet: "12 sahne, tahmini 71 sn · 0 not", maddeler: [], zaman: saat(3) },
      ses: { durum: "tamam", ozet: "72 sn, metinle %97 uyumlu", maddeler: [], zaman: saat(2) },
      gorsel: { durum: "uyari", ozet: "3/4 görsel, ortalama puan 8.6/10", maddeler: [{ seviye: "uyari", sahne: 2, mesaj: "Arka plandaki askerin elinde döneme uymayan tüfek benzeri bir silah var" }, { seviye: "hata", mesaj: "eksik görsel: sahne 4" }], zaman: saat(1) },
      kurgu: { durum: "tamam", ozet: "75 sn, -14 LUFS, senkron 24/24", maddeler: [{ seviye: "bilgi", mesaj: "sığmadığı için küçültüldü: “SAMSUN'DAN ANKARA'YA”" }], zaman: saat(1) } },
    yayin: {}, plan: [{ id: "x", slug: "malazgirt-1071", zaman: sonraki(19).toISOString(), durum: "bekliyor" }] };
  return { ok: true };
}

if (DEMO || TOKEN) start(); else showLogin();
if ("serviceWorker" in navigator && !DEMO) navigator.serviceWorker.register("sw.js").catch(() => {});

// ───────── 🔔 telefona bildirim: video bitince, iş hata verince ─────────
const b64u = (s) => { const p = "=".repeat((4 - (s.length % 4)) % 4); const r = atob((s + p).replace(/-/g, "+").replace(/_/g, "/")); return Uint8Array.from([...r].map((c) => c.charCodeAt(0))); };
async function zilDurum() {
  const z = $("#zil"); if (!z) return;
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) { z.textContent = "🔕"; return; }
  const reg = await navigator.serviceWorker.ready; const ab = await reg.pushManager.getSubscription();
  z.textContent = ab && Notification.permission === "granted" ? "🔔" : "🔕"; z.title = ab ? "Bildirimler açık (kapatmak için dokun)" : "Bildirimleri aç";
}
async function zilTikla() {
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent), kurulu = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  if (!("PushManager" in window) || !("serviceWorker" in navigator)) return alert(ios && !kurulu
    ? "iPhone'da bildirim için siteyi ana ekrana eklemen lazım:\n\n1. Safari'de alttaki Paylaş (□↑) düğmesine bas\n2. 'Ana Ekrana Ekle'ye bas\n3. Ana ekrandaki Animasyon Tarih simgesinden aç, sonra 🔕'ye dokun"
    : "Bu tarayıcı bildirim desteklemiyor. Chrome ya da Safari ile dene.");
  const reg = await navigator.serviceWorker.ready; const ab = await reg.pushManager.getSubscription();
  if (ab) { if (!confirm("Bildirimler kapatılsın mı?")) return; await api("push_abone", { abonelik: ab.toJSON(), cik: true }).catch(() => {}); await ab.unsubscribe(); toast("Bildirimler kapandı"); return zilDurum(); }
  if ((await Notification.requestPermission()) !== "granted") return alert("Bildirim izni verilmedi. Telefon ayarlarından bu site için bildirimlere izin verip tekrar dene.");
  try {
    const { anahtar } = await api("push_anahtar");
    const yeni = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64u(anahtar) });
    await api("push_abone", { abonelik: yeni.toJSON() }); toast("🔔 Bildirimler açık, deneme bildirimi gönderildi");
  } catch (e) { alert("Bildirim açılamadı: " + (e.message || e)); }
  zilDurum();
}
if (!DEMO && $("#zil")) { $("#zil").onclick = zilTikla; setTimeout(zilDurum, 1500); }
