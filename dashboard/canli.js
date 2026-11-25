// ───────── 🔴 Canlı panel + "Anlık güncelle": tek ortak poller (ig_live) ─────────
// app.js'teki $, esc, api, sayi, O kullanılır. Panel ve anahtar aynı zamanlayıcıyı paylaşır: API çağrısı asla ikiye katlanmaz.
const CL = { panel: false, anlik: false, aralik: 30, timer: null, sonTik: 0, sonDetay: 0, sinir: false, hata: "", calisiyor: false,
  ilk: null, onceki: null, views: {}, gorulen: null, feed: [] };
try { CL.anlik = localStorage.getItem("iganlik") === "1"; const a = +localStorage.getItem("igaralik"); if ([10, 20, 30, 60].includes(a)) CL.aralik = a; } catch {}
const canliAnlikAcik = () => CL.anlik;
const clGerek = () => (CL.panel || CL.anlik) && !document.hidden;
const clGecikme = () => (CL.sinir || CL.hata ? 60 : Math.max(10, CL.aralik)) * 1000;

function clPlanla() {
  clearTimeout(CL.timer); CL.timer = null;
  if (!clGerek()) return;
  const kalan = Math.max(0, clGecikme() - (Date.now() - CL.sonTik));
  CL.timer = setTimeout(clTik, kalan);
}
async function clTik() {
  CL.timer = null; if (!clGerek() || CL.calisiyor) return;
  CL.calisiyor = true; CL.sonTik = Date.now();
  const detay = Date.now() - CL.sonDetay >= 60000;
  try {
    const r = await api("ig_live", { detay: detay ? 1 : 0 });
    if (detay) CL.sonDetay = Date.now();
    CL.sinir = false; CL.hata = ""; clIsle(r);
  } catch (e) {
    const m = String(e.message || e); const kod = +(m.match(/\[kod (\d+)\]/)?.[1] || 0);
    if ([4, 17, 32, 613].includes(kod)) { CL.sinir = true; CL.hata = ""; } else CL.hata = m;
  } finally { CL.calisiyor = false; clDurum(); clPlanla(); }
}

function clIsle(r) {
  for (const m of r.medya || []) if (m.views != null) CL.views[m.id] = m.views; else m.views = CL.views[m.id] ?? null;
  const son = (r.medya || [])[0] || {};
  const d = { takipci: r.followers_count ?? null, izlenme: son.views ?? null, begeni: son.like_count ?? null, yorum: son.comments_count ?? null, vid: son.id, medya: r.medya || [] };
  const zaman = r.zaman || new Date().toISOString(), yeni = [];
  if (!CL.ilk) CL.ilk = { ...d };
  const o = CL.onceki;
  if (o) {
    if (d.takipci != null && o.takipci != null && d.takipci !== o.takipci) yeni.push({ t: `${d.takipci > o.takipci ? "+" : ""}${sayi(d.takipci - o.takipci)} takipçi`, ic: "👤" });
    for (const m of d.medya) {
      const p = o.medya.find((x) => x.id === m.id); if (!p) continue; const ad = m.baslik || "video";
      if (m.views != null && p.views != null && m.views > p.views) yeni.push({ t: `+${sayi(m.views - p.views)} izlenme · ${ad}`, ic: "▶" });
      if (m.like_count != null && p.like_count != null && m.like_count > p.like_count) yeni.push({ t: `+${sayi(m.like_count - p.like_count)} beğeni · ${ad}`, ic: "❤" });
    }
  }
  if (r.yorumlar) {
    if (!CL.gorulen) CL.gorulen = new Set(r.yorumlar.map((y) => y.id));
    else for (const y of [...r.yorumlar].reverse()) if (!CL.gorulen.has(y.id)) { CL.gorulen.add(y.id); yeni.push({ t: `@${y.kullanici} yorum yaptı: ${String(y.metin || "").slice(0, 90)}`, ic: "💬" }); }
  }
  for (const x of yeni) CL.feed.unshift({ ...x, zaman }); CL.feed = CL.feed.slice(0, 60);
  clPanelGuncelle(d, o); clYerinde(d, o);
  CL.onceki = d;
}

// ── sayı animasyonu + "+N" parlaması
function clSay(el, to) {
  if (!el || to == null) return; const from = +(el.dataset.v ?? to); el.dataset.v = to;
  if (from === to) { el.textContent = sayi(to); return; }
  const t0 = performance.now(), dur = 900;
  const ad = (t) => { const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3); el.textContent = sayi(Math.round(from + (to - from) * e)); if (k < 1) requestAnimationFrame(ad); };
  requestAnimationFrame(ad);
}
function clFlas(el, n) {
  if (!el || !n || n <= 0) return; const s = document.createElement("span"); s.className = "clflas"; s.textContent = "+" + sayi(n);
  el.append(s); setTimeout(() => s.remove(), 1800);
}

// ── Genel görünümde yerinde güncelleme (anahtar açıkken)
function clYerinde(d, o) {
  if (!CL.anlik) return; const ig = O.instagram;
  if (d.takipci != null) { if (ig?.hesap) ig.hesap.takipci = d.takipci; const k = document.querySelector('[data-lk="takipci"]');
    if (k) { const b = k.querySelector("b"); if (b.dataset.v == null) b.dataset.v = o?.takipci ?? d.takipci; clSay(b, d.takipci); if (o) clFlas(k, d.takipci - o.takipci); } }
  for (const m of d.medya) {
    const v = (ig?.medya || []).find((x) => x.id === m.id); const p = o?.medya.find((x) => x.id === m.id);
    const alan = { begeni: m.like_count, yorum: m.comments_count, izlenme: m.views };
    const tr = document.querySelector(`tr[data-igid="${CSS.escape(m.id)}"]`);
    for (const [k, val] of Object.entries(alan)) {
      if (val == null) continue; if (v) v[k] = val; if (!tr) continue;
      const el = tr.querySelector(`[data-lv="${k}"]`); if (!el) continue;
      if (el.dataset.v == null) el.dataset.v = val; clSay(el, val);
      const pv = p ? { begeni: p.like_count, yorum: p.comments_count, izlenme: p.views }[k] : null; if (pv != null) clFlas(el, val - pv);
    }
  }
}

// ── panel
function clRozet(n) { return n > 0 ? `<em class="clrz">+${sayi(n)}</em>` : ""; }
function clPanelGuncelle(d, o) {
  const p = $("#canlip"); if (!p || !CL.panel) return;
  for (const k of ["takipci", "izlenme", "begeni", "yorum"]) {
    const kut = p.querySelector(`[data-ck="${k}"]`); if (!kut) continue; const b = kut.querySelector("b");
    if (d[k] == null) { b.textContent = "—"; continue; }
    if (b.dataset.v == null) b.dataset.v = d[k]; clSay(b, d[k]);
    const ayni = o && o.vid === d.vid, ilkAyni = k === "takipci" || CL.ilk.vid === d.vid;
    kut.querySelector(".clr1").innerHTML = ilkAyni && CL.ilk[k] != null ? clRozet(d[k] - CL.ilk[k]) : "";
    kut.querySelector(".clr2").innerHTML = (k === "takipci" || ayni) && o?.[k] != null ? clRozet(d[k] - o[k]) : "";
  }
  const vb = p.querySelector(".clvid"); const son = d.medya[0]; if (vb) vb.textContent = son ? `Son video: ${son.baslik || "(açıklamasız)"}` : "";
  const f = p.querySelector(".clfeed");
  f.innerHTML = CL.feed.length ? CL.feed.map((x) => `<div class="clit"><span>${x.ic}</span><div>${esc(x.t)}<small>${clOnce(x.zaman)}</small></div></div>`).join("") : '<div class="mut">Henüz hareket yok. Yeni izlenme, beğeni, takipçi ve yorumlar burada akacak.</div>';
}
const clOnce = (iso) => { const s = Math.max(0, Math.round((Date.now() - new Date(iso)) / 1000)); return s < 60 ? `${s} sn önce` : s < 3600 ? `${Math.floor(s / 60)} dk önce` : `${Math.floor(s / 3600)} saat önce`; };
function clDurum() {
  const p = $("#canlip"); if (!p) return; const u = p.querySelector(".cluyari");
  u.textContent = CL.sinir ? "Instagram sınırına yaklaşıldı, 60 sn'ye düşürüldü" : CL.hata ? `Hata: ${CL.hata} · 60 sn sonra tekrar denenecek` : "";
  u.hidden = !u.textContent;
}
function clSaat() {
  const p = $("#canlip"); if (!p || !CL.panel) return;
  p.querySelector(".clson").textContent = CL.sonTik ? `son güncelleme ${clOnce(CL.sonTik)}` : "bağlanıyor…";
  p.querySelectorAll(".clit small").forEach((s, i) => { const x = CL.feed[i]; if (x) s.textContent = clOnce(x.zaman); });
}
setInterval(clSaat, 1000);

function clPanelAc(ac) {
  CL.panel = ac; let p = $("#canlip");
  if (ac && !p) {
    p = document.createElement("aside"); p.id = "canlip"; p.setAttribute("aria-label", "Canlı panel");
    const kut = (k, l) => `<div class="clk" data-ck="${k}"><b>—</b><span>${l}</span><div><i class="clr1" title="Panel açıldığından beri"></i><i class="clr2" title="Son güncellemeden beri"></i></div></div>`;
    p.innerHTML = `<div class="clbas"><b><i class="clnab"></i> Canlı</b><span class="clson mut">bağlanıyor…</span><button class="ghost clkapat" aria-label="Kapat">✕</button></div>
      <div class="segm clara" role="group" aria-label="Yenileme aralığı">${[10, 20, 30, 60].map((s) => `<button data-clara="${s}" class="${s === CL.aralik ? "on" : ""}">${s} sn</button>`).join("")}</div>
      <div class="cluyari" hidden></div>
      <div class="clgrid">${kut("takipci", "Takipçi")}${kut("izlenme", "İzlenme")}${kut("begeni", "Beğeni")}${kut("yorum", "Yorum")}</div>
      <div class="clvid mut"></div><div class="mut" style="font-size:11px;margin:2px 0 8px">Rozetler: ilk = panel açıldığından beri, ikinci = son güncellemeden beri</div>
      <h3>Hareketler</h3><div class="clfeed"></div>
      <div class="clnot">ℹ️ Instagram kimin beğendiğini/takip ettiğini paylaşmıyor; sayılar ve yorumlar canlı.<br>⏱ İzlenme sayısını Instagram birkaç dakikada bir günceller.</div>`;
    document.body.append(p);
    p.querySelector(".clkapat").onclick = () => clPanelAc(false);
    p.querySelectorAll("[data-clara]").forEach((b) => (b.onclick = () => {
      CL.aralik = +b.dataset.clara; try { localStorage.setItem("igaralik", CL.aralik); } catch {}
      p.querySelectorAll("[data-clara]").forEach((x) => x.classList.toggle("on", x === b)); clPlanla();
    }));
  }
  if (p) p.hidden = !ac; document.body.classList.toggle("clacik", ac);
  if (ac) { CL.ilk = null; CL.feed = []; CL.onceki = null; CL.gorulen = null; CL.sonDetay = 0; clDurum(); clPanelGuncelle({ medya: [] }, null); CL.sonTik = 0; }
  clFab(); clPlanla();
}
function clFab() {
  let f = $("#canlifab"); const igAcik = !!document.querySelector('[data-bolum="ig"]:not([hidden])');
  if (!f) { f = document.createElement("button"); f.id = "canlifab"; f.innerHTML = '<i class="clnab"></i> Canlı'; f.onclick = () => clPanelAc(!CL.panel); document.body.append(f); }
  f.hidden = !igAcik || CL.panel;
  if (!igAcik && CL.panel) clPanelAc(false);
}
// app.js render() sonrası çağrılır (baglaInstagram içinden)
function canliBagla() {
  const t = $("#iganlik"); if (t) { t.checked = CL.anlik; t.onchange = () => { CL.anlik = t.checked; try { localStorage.setItem("iganlik", CL.anlik ? "1" : "0"); } catch {} if (CL.anlik) CL.onceki = null; clPlanla(); }; }
  clFab(); clPlanla();
}
document.addEventListener("click", (e) => { if (e.target.closest("[data-sekme]")) setTimeout(clFab, 0); });
document.addEventListener("visibilitychange", () => (document.hidden ? (clearTimeout(CL.timer), (CL.timer = null)) : clPlanla()));
