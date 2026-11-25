// ───────── İNSTAGRAM ANALİZ: alt sekmeler (Genel · Formatlar · Yorumlar · Rapor · Takvim) ─────────
// app.js'teki $, esc, api, guvenli, toast, sayi, ago, O, render, renderInstagram, renderTokenKart kullanılır.
const IG_ALT = [["genel", "Genel"], ["format", "Formatlar"], ["yorum", "Yorumlar"], ["rapor", "Rapor"], ["takvim", "Takvim"]];
const FORMATLAR = ["Quiz", "Harflerden Bul", "Padişah serisi", "Harita/Gezi/Yer", "Diğer"];
const IGS = { yorumlar: null, yukleniyor: false, videolar: null };
const virgul = (x, d = 1) => Number(x).toFixed(d).replace(".", ",");
const istTarih = (iso, o = { dateStyle: "medium", timeStyle: "short" }) => new Date(iso).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul", ...o });

function igFormat(v) {
  const el = O.igFormat?.[v.id]; if (el) return el;
  const t = String(v.baslik || "").toLocaleLowerCase("tr");
  for (const k of O.formatKurallari?.sira || []) {
    if ((k.kelimeler || []).some((w) => t.includes(w))) return k.ad;
    if ((k.desenler || []).some((d) => { try { return new RegExp(d).test(t); } catch { return false; } })) return k.ad;
  }
  return "Diğer";
}
const etkOran = (v) => { const e = v.etkilesim ?? ((v.begeni || 0) + (v.yorum || 0) + (v.kaydetme || 0) + (v.paylasim || 0)); return v.izlenme ? (e * 100) / v.izlenme : null; };
const ortalama = (L, k) => { const a = L.map((v) => (typeof k === "function" ? k(v) : v[k])).filter((x) => typeof x === "number" && isFinite(x)); return a.length ? a.reduce((s, x) => s + x, 0) / a.length : null; };

function igSekmeHtml() {
  let alt = "genel"; try { const k = localStorage.getItem("igalt"); if (IG_ALT.some((x) => x[0] === k)) alt = k; } catch {}
  const bol = { genel: renderTokenKart() + (renderInstagram() || '<div class="card mut" style="margin-top:12px">Henüz Instagram verisi yok.</div>') + igTakipKazandiran(),
    format: igFormatHtml(), yorum: igYorumHtml(), rapor: igRaporHtml(), takvim: igTakvimHtml() };
  return `<nav class="altsek">${IG_ALT.map(([k, l]) => `<button class="${k === alt ? "on" : ""}" data-igalt="${k}">${l}</button>`).join("")}</nav>` +
    IG_ALT.map(([k]) => `<div data-igbol="${k}"${k === alt ? "" : " hidden"}>${bol[k]}</div>`).join("");
}

// ── 6. Takipçi kazandıran videolar
function igTakipKazandiran() {
  const M = (O.instagram?.medya || []).filter((v) => v.takip != null || v.profil_ziyaret != null);
  if (!M.length) return `<h2>Takipçi kazandıran videolar</h2><div class="card mut">Instagram bu veriyi Reels için vermiyor (gönderi başına "follows" / "profile_visits" metriği gelmedi). Hesap geneli takipçi değişimi yukarıdaki grafikte.</div>`;
  M.sort((a, b) => (b.takip || 0) - (a.takip || 0) || (b.profil_ziyaret || 0) - (a.profil_ziyaret || 0));
  return `<h2>Takipçi kazandıran videolar</h2><div class="card">${M.slice(0, 10).map((v, i) => `<div class="igsat" data-igid="${esc(v.id)}"><b>${i + 1}</b>${igKapak(v, 36)}<div style="flex:1;min-width:0">${esc(v.baslik || "(açıklamasız)")}</div><span class="tag yap">+${sayi(v.takip)} takip</span><span class="tag">${sayi(v.profil_ziyaret)} profil</span></div>`).join("")}</div>`;
}
const igKapak = (v, w = 56) => v?.kapak ? `<img class="igkp" style="width:${w}px;height:${Math.round(w * 16 / 9)}px" src="${esc(v.kapak)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.visibility='hidden'">` : `<span class="igph" style="width:${w}px;height:${Math.round(w * 16 / 9)}px">🎬</span>`;

// ── 1. Video detay
function igDetay(id) {
  const M = O.instagram?.medya || [], v = M.find((x) => x.id === id); if (!v) return;
  const met = [["izlenme", "▶ İzlenme"], ["erisim", "👥 Erişim"], ["begeni", "❤ Beğeni"], ["yorum", "💬 Yorum"], ["kaydetme", "🔖 Kayıt"], ["paylasim", "↗ Paylaşım"], ["etkilesim", "✦ Toplam etkileşim"], ["ort_izleme_sn", "⏱ Ort. izleme (sn)"], ["takip", "➕ Takip"], ["profil_ziyaret", "👤 Profil ziyareti"]];
  const satir = met.filter(([k]) => v[k] != null).map(([k, l]) => { const o = ortalama(M, k); let kar = "";
    if (o) { const r = v[k] / o; kar = `<span style="color:${r >= 1 ? "var(--ok)" : "var(--err)"}">ortalamanın ${virgul(r)} katı</span>`; }
    return `<div class="igm"><span>${l}</span><b>${k === "ort_izleme_sn" ? virgul(v[k]) : sayi(v[k])}</b>${kar}</div>`; }).join("");
  const f = igFormat(v), el = !!O.igFormat?.[v.id];
  const d = document.createElement("div"); d.className = "modal";
  d.innerHTML = `<div class="kutu"><div style="display:flex;gap:12px">${igKapak(v, 84)}<div style="flex:1;min-width:0"><b>${esc(v.baslik || "(açıklamasız)")}</b>
    <div class="mut" style="margin-top:4px">${v.zaman ? istTarih(v.zaman) : ""} · ${esc(v.tur || "")}</div>
    <label class="mut" style="display:block;margin-top:8px">Format <select id="igfsel">${["", ...FORMATLAR].map((x) => `<option value="${esc(x)}"${(el ? f : "") === x ? " selected" : ""}>${x ? esc(x) : `Otomatik (${esc(el ? "kural" : f)})`}</option>`).join("")}</select></label></div></div>
    <div class="igmet">${satir || '<div class="mut">Metrik yok</div>'}</div>
    <div class="flex">${v.url ? `<a class="btn gold" href="${esc(v.url)}" target="_blank" rel="noopener">Instagram'da aç</a>` : ""}<button id="igkapat">Kapat</button></div></div>`;
  document.body.append(d);
  d.onclick = (e) => { if (e.target === d) d.remove(); }; d.querySelector("#igkapat").onclick = () => d.remove();
  d.querySelector("#igfsel").onchange = async (e) => {
    try { const r = await api("ig_format", { id: v.id, format: e.target.value }); O.igFormat = r.igFormat; toast("Format kaydedildi"); d.remove(); render(); } catch (er) { toast(er.message || "Hata"); }
  };
}

// ── 2. Format karşılaştırması
function igFormatHtml() {
  const M = O.instagram?.medya || []; if (!M.length) return `<div class="card mut" style="margin-top:12px">Henüz Instagram verisi yok.</div>`;
  const G = {}; for (const v of M) (G[igFormat(v)] ||= []).push(v);
  const S = Object.entries(G).map(([ad, L]) => ({ ad, n: L.length, izl: ortalama(L, "izlenme"), kay: ortalama(L, "kaydetme"), pay: ortalama(L, "paylasim"), izs: ortalama(L, "ort_izleme_sn"), etk: ortalama(L, etkOran) })).sort((a, b) => (b.izl || 0) - (a.izl || 0));
  const mx = Math.max(...S.map((x) => x.izl || 0), 1), W = 600, sh = 34, H = S.length * sh + 8;
  const bar = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="Formata göre ortalama izlenme">${S.map((x, i) => { const w = Math.max(2, ((x.izl || 0) / mx) * (W - 250));
    return `<text x="0" y="${i * sh + 22}" fill="var(--txt)" font-size="13">${esc(x.ad)}</text><rect x="150" y="${i * sh + 8}" width="${w}" height="20" rx="5" fill="${i ? "rgba(232,196,120,.55)" : "var(--gold)"}"/><text x="${156 + w}" y="${i * sh + 22}" fill="var(--mut)" font-size="12">${sayi(Math.round(x.izl || 0))}</text>`; }).join("")}</svg>`;
  return `<h2>Format karşılaştırması</h2><div class="card"><div class="mut" style="margin-bottom:8px">Ortalama izlenme (son ${M.length} gönderi). Formatı video detayından elle değiştirebilirsin.</div>${bar}
    <div style="overflow-x:auto;margin-top:12px"><table class="igtab fmt"><thead><tr><th>Format</th><th>Adet</th><th>Ort. izlenme</th><th>Ort. kayıt</th><th>Ort. paylaşım</th><th>Ort. izleme</th><th>Etkileşim</th></tr></thead><tbody>
    ${S.map((x) => `<tr><td class="igb"><b>${esc(x.ad)}</b></td><td data-l="Adet">${x.n}</td><td data-l="Ort. izlenme">${sayi(x.izl == null ? null : Math.round(x.izl))}</td><td data-l="Ort. kayıt">${sayi(x.kay == null ? null : Math.round(x.kay))}</td><td data-l="Ort. paylaşım">${sayi(x.pay == null ? null : Math.round(x.pay))}</td><td data-l="Ort. izleme">${x.izs == null ? "—" : virgul(x.izs) + " sn"}</td><td data-l="Etkileşim">${x.etk == null ? "—" : "%" + virgul(x.etk)}</td></tr>`).join("")}
    </tbody></table></div></div>`;
}

// ── 3. Yorumlar
function igYorumHtml() {
  const Y = IGS.yorumlar;
  let s = `<h2>Yorumlar</h2><div class="card"><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span class="mut" style="flex:1">Son 20 gönderinin yorumları, en yeni üstte.${Y ? ` ${Y.filter((y) => !y.cevaplandi).length} cevapsız.` : ""}</span><button id="igyorumgetir">${IGS.yukleniyor ? "Yükleniyor…" : Y ? "Yenile" : "Yorumları getir"}</button></div>`;
  if (!Y) return s + `</div>`;
  if (!Y.length) return s + `<div class="mut" style="margin-top:10px">Yorum yok.</div></div>`;
  s += Y.map((y) => `<div class="igy${y.cevaplandi ? " cev" : ""}" data-yid="${esc(y.id)}">${igKapak(y.medya, 40)}<div style="flex:1;min-width:0">
    <div class="mut" style="font-size:11.5px">${esc(y.medya?.baslik || "")} · ${y.zaman ? ago(y.zaman) : ""}</div>
    <div><b>@${esc(y.kullanici || "")}</b> ${esc(y.metin || "")}</div>
    ${y.gizli ? `<span class="tag gec">Gizli</span> ` : ""}${y.cevaplandi ? `<div class="mut" style="margin-top:4px">✓ Cevaplandı: ${esc(y.cevap)}</div>` : `<span class="tag" style="color:var(--wait)">Cevapsız</span>
    <textarea rows="2" class="igcev">${esc(y.oneri || "")}</textarea><div class="acts"><button class="gold" data-ygonder>Gönder</button><button data-ygizle>${y.gizli ? "Göster" : "Gizle"}</button>${y.ai ? `<span class="mut" style="font-size:11px">öneri: Gemini</span>` : ""}</div>`}
    </div></div>`).join("");
  return s + `</div>`;
}
async function igYorumGetir() {
  IGS.yukleniyor = true; igYenidenCiz("yorum");
  try { const r = await api("ig_yorumlar"); IGS.yorumlar = r.yorumlar || []; if (r.hatali) toast(`${r.hatali} gönderinin yorumları alınamadı`); }
  catch (e) { toast(e.message || "Hata"); } finally { IGS.yukleniyor = false; igYenidenCiz("yorum"); }
}

// ── 4. Haftalık rapor
function igRaporBlok(r) {
  return `<div class="mut">${esc(r.hafta)} · ${r.kaynak === "gemini" ? "Gemini" : "şablon"}</div><p style="line-height:1.55">${esc(r.ozet)}</p>
    <div class="kpi"><div><b>${sayi(r.bu_hafta?.izlenme)}</b><span>Bu hafta izlenme</span></div><div><b>${r.takipci_artisi == null ? "—" : (r.takipci_artisi >= 0 ? "+" : "") + sayi(r.takipci_artisi)}</b><span>Takipçi değişimi</span></div><div><b style="font-size:14px">${esc(r.en_iyi_format || "—")}</b><span>En iyi format</span></div></div>
    <b style="font-size:13px">Gelecek hafta için 3 öneri</b><ol style="margin:6px 0 10px;padding-left:20px;line-height:1.5;font-size:13.5px">${(r.oneriler || []).map((o) => `<li>${esc(o)}</li>`).join("")}</ol>
    ${(r.en_iyi_3 || []).length ? `<b style="font-size:13px">En iyi 3 video</b>${r.en_iyi_3.map((v, i) => `<div class="igsat"><b>${i + 1}</b>${igKapak(v, 30)}<div style="flex:1;min-width:0">${v.url ? `<a href="${esc(v.url)}" target="_blank" rel="noopener">${esc(v.baslik || "video")}</a>` : esc(v.baslik || "video")}</div><span class="tag">${sayi(v.izlenme)} izl.</span></div>`).join("")}` : ""}
    ${(r.en_iyi_saatler || []).length ? `<div class="mut" style="margin-top:8px">⏰ En iyi saatler: ${r.en_iyi_saatler.map(esc).join(", ")}${r.en_iyi_gun ? ` · ${esc(r.en_iyi_gun)}` : ""}</div>` : ""}`;
}
function igRaporHtml() {
  const H = O.haftalik, r = H?.son;
  let s = `<h2>Haftalık rapor</h2><div class="card">${r ? igRaporBlok(r) : `<div class="mut">Henüz rapor yok. Her pazartesi 09:10'da otomatik yazılır.</div>`}<div class="flex"><button id="igraporyap">Şimdi oluştur</button></div></div>`;
  const A = (H?.arsiv || []).slice(1);
  if (A.length) s += `<h2>Arşiv</h2>${A.map((x) => `<details class="card" style="margin-bottom:8px"><summary style="cursor:pointer"><b>${esc(x.hafta)}</b> <span class="mut">· ${sayi(x.bu_hafta?.izlenme)} izlenme</span></summary><div style="margin-top:8px">${igRaporBlok(x)}</div></details>`).join("")}`;
  return s;
}

// ── 5. Paylaşım takvimi
const DURUM = { bekliyor: ["wait", "Bekliyor"], gonderildi: ["run", "Yayınlanıyor"], tamam: ["ok", "Yayınlandı"], hata: ["err", "Hata"], iptal: ["", "İptal"] };
function oneriSlotlar() {
  const g = O.instagram || {}, saat = (g.en_iyi_saatler || []).map((x) => x.saat), GUN = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"];
  if (!saat.length) return [];
  const hedefGun = GUN.indexOf(g.en_iyi_gun || ""), simdi = Date.now(), out = [];
  for (const h of saat.slice(0, 3)) { // İstanbul = UTC+3 (yaz saati yok)
    for (let d = 0; d < 8; d++) { const t = new Date(simdi + d * 864e5), ist = new Date(t.getTime() + 3 * 3600e3);
      const c = new Date(Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate(), h - 3, 0));
      if (c.getTime() < simdi + 20 * 60e3) continue; if (hedefGun >= 0 && d < 7 && new Date(c.getTime() + 3 * 3600e3).getUTCDay() !== hedefGun) continue;
      out.push(c); break; }
  }
  return out.sort((a, b) => a - b);
}
const yerelIst = (d) => new Date(d.getTime() + 3 * 3600e3).toISOString().slice(0, 16);
function igTakvimHtml() {
  const Q = [...(O.kuyruk || [])].sort((a, b) => new Date(b.zaman) - new Date(a.zaman));
  const aktif = Q.filter((x) => ["bekliyor", "gonderildi"].includes(x.durum)).reverse(), gecmis = Q.filter((x) => !["bekliyor", "gonderildi"].includes(x.durum)).slice(0, 15);
  const satir = (x) => { const [c, l] = DURUM[x.durum] || ["", x.durum];
    return `<div class="igplan"><div style="flex:1;min-width:0"><b>${istTarih(x.zaman, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</b> <span class="st ${c}">${l}</span>
      <div class="mut" style="overflow-wrap:anywhere">${esc(x.ad || (x.slug ? projeAdi(x.slug) : "Video adresi"))}${x.caption ? " · " + esc(x.caption.slice(0, 60)) : ""}</div>
      ${x.mesaj ? `<div class="mut" style="font-size:11.5px;${x.durum === "hata" ? "color:var(--err)" : ""}">${esc(adlandir(x.mesaj))}</div>` : ""}${x.permalink ? `<a href="${esc(x.permalink)}" target="_blank" rel="noopener" style="font-size:12px">Gönderiyi aç</a>` : ""}</div>
      ${x.durum === "bekliyor" ? `<div class="acts"><button data-pduz="${esc(x.id)}">Düzenle</button><button class="silb" data-piptal="${esc(x.id)}">İptal</button></div>` : ""}</div>`; };
  const sl = oneriSlotlar();
  return `<h2>Paylaşım takvimi</h2><div class="card"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap"><span class="mut">Yalnız buradan planladığın videolar paylaşılır. Zamanlayıcı 10 dakikada bir bakar.</span><button class="gold" id="ignplan">Yeni paylaşım planla</button></div>
    ${sl.length ? `<div class="mut" style="margin-top:8px">Önerilen: ${sl.map((d) => `<b style="color:var(--gold)">${istTarih(d.toISOString(), { weekday: "long", hour: "2-digit", minute: "2-digit" })}</b>`).join(" · ")}</div>` : ""}
    <div style="margin-top:10px">${aktif.map(satir).join("") || `<div class="mut">Planlanmış paylaşım yok.</div>`}</div></div>
    ${gecmis.length ? `<h2>Geçmiş</h2><div class="card">${gecmis.map(satir).join("")}</div>` : ""}`;
}
async function igPlanForm(id) {
  const it = id ? (O.kuyruk || []).find((x) => x.id === id) : null, sl = oneriSlotlar();
  const d = document.createElement("div"); d.className = "modal";
  d.innerHTML = `<div class="kutu igform"><b style="font-size:15px">${it ? "Paylaşımı düzenle" : "Yeni paylaşım planla"}</b>
    <label>Video<select id="pv"><option value="">Yükleniyor…</option></select></label>
    <label>ya da herkese açık video adresi (mp4)<input id="pu" type="url" placeholder="https://..." value="${esc(it?.url && !it?.slug ? it.url : "")}"></label>
    <label>Açıklama<textarea id="pc" rows="4" placeholder="Boş bırakırsan projenin hazır açıklaması kullanılır">${esc(it?.caption || "")}</textarea></label>
    <label>Hashtagler<input id="ph" placeholder="#tarih #osmanlı" value="${esc(it?.hashtag || "")}"></label>
    <div class="flex" style="margin-top:4px"><label style="flex:1">Kapak karesi (sn)<input id="pk" type="number" min="0" max="90" step="0.5" value="${it?.kapak_ms != null ? it.kapak_ms / 1000 : 1.5}"></label><label style="flex:2">ya da kapak görseli adresi<input id="pku" type="url" placeholder="https://...jpg" value="${esc(it?.kapak_url || "")}"></label></div>
    <label>Tarih / saat (İstanbul)<input id="pz" type="datetime-local" value="${it ? yerelIst(new Date(it.zaman)) : sl[0] ? yerelIst(sl[0]) : ""}"></label>
    ${sl.length ? `<div class="chips" style="margin-top:6px">${sl.map((x) => `<button type="button" class="ghost" data-slot="${yerelIst(x)}">Önerilen: ${istTarih(x.toISOString(), { weekday: "long", hour: "2-digit", minute: "2-digit" })}</button>`).join("")}</div>` : ""}
    <label class="chk"><input id="pf" type="checkbox"${it?.akis === false ? "" : " checked"}> Akışta da göster (share to feed)</label>
    <div class="flex"><button class="gold" id="pkaydet">${it ? "Kaydet" : "Planla"}</button><button id="pkapat">Vazgeç</button></div></div>`;
  document.body.append(d);
  const kapat = () => d.remove(); d.querySelector("#pkapat").onclick = kapat; d.onclick = (e) => { if (e.target === d) kapat(); };
  d.querySelectorAll("[data-slot]").forEach((b) => (b.onclick = () => (d.querySelector("#pz").value = b.dataset.slot)));
  try { if (!IGS.videolar) IGS.videolar = (await api("ig_videolar")).videolar || [];
    d.querySelector("#pv").innerHTML = `<option value="">— Video seç —</option>` + IGS.videolar.map((v) => `<option value="${esc(v.slug)}"${it?.slug === v.slug ? " selected" : ""}>${esc(v.ad)} (${(v.boyut / 1e6).toFixed(0)} MB)</option>`).join(""); }
  catch (e) { d.querySelector("#pv").innerHTML = `<option value="">Videolar alınamadı</option>`; }
  d.querySelector("#pkaydet").onclick = async (e) => {
    const slug = d.querySelector("#pv").value, v = (IGS.videolar || []).find((x) => x.slug === slug), elle = d.querySelector("#pu").value.trim(), z = d.querySelector("#pz").value;
    if (!slug && !elle) return toast("Video seç ya da adres gir"); if (!z) return toast("Tarih/saat seç");
    const t = new Date(z + ":00+03:00"); if (isNaN(t) || t < Date.now()) return toast("Geçmiş bir saat seçilemez");
    const kms = d.querySelector("#pk").value;
    const body = { id: it?.id, slug: slug || undefined, url: elle || v?.url || undefined, ad: v?.ad || (elle ? "Video adresi" : undefined), caption: d.querySelector("#pc").value, hashtag: d.querySelector("#ph").value,
      kapak_ms: kms === "" ? null : Math.round(Number(kms) * 1000), kapak_url: d.querySelector("#pku").value.trim(), akis: d.querySelector("#pf").checked, zaman: t.toISOString() };
    if (!confirm(`${istTarih(t.toISOString())} saatinde Instagram'da paylaşılsın mı?`)) return;
    e.target.disabled = true;
    try { await guvenli(() => api("planla", body), it ? "Plan güncellendi" : "Planlandı"); kapat(); await load(); } catch { e.target.disabled = false; }
  };
}

// ── ortak
function igYenidenCiz(k) {
  const el = document.querySelector(`[data-igbol="${k}"]`); if (!el) return;
  el.innerHTML = { yorum: igYorumHtml, takvim: igTakvimHtml, format: igFormatHtml, rapor: igRaporHtml }[k]();
  baglaIgEk();
}
function baglaIgEk() {
  document.querySelectorAll("[data-igalt]").forEach((b) => (b.onclick = () => {
    const k = b.dataset.igalt; try { localStorage.setItem("igalt", k); } catch {}
    document.querySelectorAll("[data-igalt]").forEach((x) => x.classList.toggle("on", x === b));
    document.querySelectorAll("[data-igbol]").forEach((x) => (x.hidden = x.dataset.igbol !== k));
    if (k === "yorum" && !IGS.yorumlar && !IGS.yukleniyor) igYorumGetir();
  }));
  document.querySelectorAll("[data-igid]").forEach((r) => (r.onclick = () => igDetay(r.dataset.igid)));
  const yg = $("#igyorumgetir"); if (yg) yg.onclick = () => !IGS.yukleniyor && igYorumGetir();
  document.querySelectorAll("[data-ygonder]").forEach((b) => (b.onclick = async () => {
    const box = b.closest("[data-yid]"), y = IGS.yorumlar.find((x) => x.id === box.dataset.yid), m = box.querySelector("textarea").value.trim();
    if (!m) return toast("Önce cevabı yaz");
    if (!confirm(`@${y.kullanici} kullanıcısına şu cevap gönderilsin mi?\n\n"${m}"`)) return;
    b.disabled = true;
    try { await guvenli(() => api("ig_yanitla", { id: y.id, mesaj: m }), "Cevap gönderildi ✓"); y.cevaplandi = true; y.cevap = m; igYenidenCiz("yorum"); } catch { b.disabled = false; }
  }));
  document.querySelectorAll("[data-ygizle]").forEach((b) => (b.onclick = async () => {
    const box = b.closest("[data-yid]"), y = IGS.yorumlar.find((x) => x.id === box.dataset.yid);
    if (!confirm(y.gizli ? "Yorum tekrar gösterilsin mi?" : "Bu yorum gizlensin mi? (Silinmez, sadece herkese gizlenir)")) return;
    try { await guvenli(() => api("ig_gizle", { id: y.id, goster: y.gizli }), y.gizli ? "Yorum gösteriliyor" : "Yorum gizlendi"); y.gizli = !y.gizli; igYenidenCiz("yorum"); } catch {}
  }));
  const acik = document.querySelector("[data-igalt].on")?.dataset.igalt;
  if (acik === "yorum" && !IGS.yorumlar && !IGS.yukleniyor && !IGS.denendi) { IGS.denendi = true; igYorumGetir(); }
  const rp = $("#igraporyap"); if (rp) rp.onclick = async () => { rp.disabled = true; try { await guvenli(() => api("run", { agent: "haftalik" }), "Rapor hazırlanıyor (~1 dk), sonra ↻ ile yenile"); } catch { rp.disabled = false; } };
  const np = $("#ignplan"); if (np) np.onclick = () => igPlanForm();
  document.querySelectorAll("[data-pduz]").forEach((b) => (b.onclick = () => igPlanForm(b.dataset.pduz)));
  document.querySelectorAll("[data-piptal]").forEach((b) => (b.onclick = async () => {
    if (!confirm("Bu planlanmış paylaşım iptal edilsin mi?")) return;
    b.disabled = true; try { await guvenli(() => api("plan_iptal", { id: b.dataset.piptal }), "Plan iptal edildi"); await load(); } catch { b.disabled = false; }
  }));
}
