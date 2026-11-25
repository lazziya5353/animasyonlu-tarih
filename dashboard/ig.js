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
// trafik kaynağı: API'nin verdiği kırılımlar (takipçi/takipçi olmayan, içerik türü) % çubuk olarak
const KAYNAK_AD = { FOLLOWER: "Takipçiler", NON_FOLLOWER: "Takipçi olmayanlar", UNKNOWN: "Bilinmiyor", REELS: "Reels", POST: "Gönderi", FEED: "Gönderi", CAROUSEL_CONTAINER: "Karusel", STORY: "Hikaye", AD: "Reklam", IGTV: "Video", LIVE: "Canlı" };
const KAYNAK_NOT = `<div class="uyari" style="margin-top:10px">ℹ️ Instagram bu kaynak dağılımını (Keşfet/Reels) API ile paylaşmıyor; uygulamadaki istatistiklerde görünür. En yakın gösterge: <b>Takipçi olmayanlara ulaşma oranı</b> — bu oran yüksekse izlenmenin çoğu Keşfet / Reels akışından gelir.</div>`;
function igBar(o) {
  const L = Object.entries(o || {}).filter(([, x]) => x > 0), top = L.reduce((t, [, x]) => t + x, 0); if (!top) return "";
  return L.sort((a, b) => b[1] - a[1]).map(([k, x]) => { const y = (x * 100) / top;
    return `<div class="igbar"><span>${esc(KAYNAK_AD[k] || k)}</span><i><em style="width:${y.toFixed(1)}%"></em></i><b>%${virgul(y)}</b><small>${sayi(x)}</small></div>`; }).join("");
}
const disOran = (o) => { const t = (o?.FOLLOWER || 0) + (o?.NON_FOLLOWER || 0); return t ? ((o.NON_FOLLOWER || 0) * 100) / t : null; };
function igKaynakHtml(g) {
  const k = g?.kaynak30; if (!k) return `<h2>Trafik kaynakları</h2><div class="card"><div class="mut">Kaynak verisi henüz yok; "Şimdi güncelle" ile çek.</div>${KAYNAK_NOT}</div>`;
  const blok = (m, ad) => { const f = k[m]?.follow_type, t = k[m]?.media_product_type, s = k[m]?.surface_type, d = disOran(f); if (!f && !t && !s) return "";
    return `<div style="margin-top:10px"><b style="font-size:14px">${ad} (30 gün)</b>${d != null ? `<div class="mut" style="margin:4px 0">Takipçi olmayanlara ulaşma oranı: <b style="color:var(--gold)">%${virgul(d)}</b></div>` : ""}
      ${f ? `<div class="mut" style="margin-top:6px">Takipçi / takipçi olmayan</div>${igBar(f)}` : ""}${t ? `<div class="mut" style="margin-top:6px">İçerik türüne göre</div>${igBar(t)}` : ""}${s ? `<div class="mut" style="margin-top:6px">Kaynak (yüzey)</div>${igBar(s)}` : ""}</div>`; };
  const ic = blok("views", "İzlenme") + blok("reach", "Erişim");
  return `<h2>Trafik kaynakları</h2><div class="card">${ic || '<div class="mut">Bu token ile kırılım verisi gelmedi.</div>'}${k.views?.surface_type || k.reach?.surface_type ? "" : KAYNAK_NOT}</div>`;
}

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
    <div style="margin-top:12px"><b style="font-size:14px">Erişim kaynağı</b>${v.kaynak ? `<div class="mut" style="margin:4px 0">Takipçi olmayanlara ulaşma oranı: <b style="color:var(--gold)">%${virgul(disOran(v.kaynak) ?? 0)}</b></div>${igBar(v.kaynak)}`
      : `<div class="mut" style="margin-top:4px">Bu video için takipçi/takipçi olmayan kırılımı API'den gelmedi.${v.erisim && O.instagram?.hesap?.takipci ? ` Kaba gösterge: erişim takipçi sayısının ${virgul(v.erisim / O.instagram.hesap.takipci)} katı.` : ""}</div>`}
      <div class="mut" style="font-size:11.5px;margin-top:6px">Instagram bu kaynak dağılımını (Keşfet/Reels) API ile paylaşmıyor; uygulamadaki istatistiklerde görünür.</div></div>
    ${igZamanHtml(v)}${igBuyumeHtml(v)}${igTakipEtkisiHtml(v)}${igKaliteHtml(v)}${igYorumAnalizHtml(v)}${igDegerlendirmeHtml(v)}
    <div class="flex">${v.url ? `<a class="btn gold" href="${esc(v.url)}" target="_blank" rel="noopener">Instagram'da aç</a>` : ""}<button id="igkapat">Kapat</button></div></div>`;
  document.body.append(d);
  d.onclick = (e) => { if (e.target === d) d.remove(); }; d.querySelector("#igkapat").onclick = () => d.remove();
  igDetayEkBagla(d, v);
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

// ───────── Video detay: zaman · büyüme · takipçi etkisi · kalite · yorumlar · değerlendirme ─────────
const SAAT_MS = 36e5, GUN_AD = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"];
IGS.oturum = IGS.oturum || {}; IGS.myorum = IGS.myorum || {}; IGS.deg = IGS.deg || {};
function igOturumEkle(medya, zaman) { // ig_live tikleri: oturum içi ek noktalar (kalıcı kayıt workflow'da)
  const t = zaman || new Date().toISOString();
  for (const m of medya || []) if (m.id && m.views != null) { const a = (IGS.oturum[m.id] ||= []); if (!a.length || a.at(-1).views !== m.views) a.push({ t, views: m.views }); }
}
function igNoktalar(v) { // [{h: paylaşımdan bu yana saat, y: izlenme}], başta (0,0)
  if (!v.zaman) return [];
  const t0 = new Date(v.zaman).getTime(), H = [...(O.igGecmis?.medya?.[v.id] || []), ...(IGS.oturum[v.id] || [])];
  const P = H.filter((x) => x.views != null).map((x) => ({ h: (new Date(x.t) - t0) / SAAT_MS, y: x.views })).filter((p) => p.h > 0).sort((a, b) => a.h - b.h);
  return [{ h: 0, y: 0 }, ...P];
}
function igAra(P, h) { // h saatteki değer: yakın nokta varsa kesin, yoksa doğrusal ara değer (yaklaşık)
  if (P.length < 2 || P.at(-1).h < h) return null;
  const yak = P.find((p) => p.h > 0 && Math.abs(p.h - h) <= Math.max(0.15, h * 0.04)); if (yak) return { y: yak.y, yaklasik: false };
  const i = P.findIndex((p) => p.h >= h), a = P[i - 1], b = P[i]; if (!a) return null;
  return { y: Math.round(a.y + ((b.y - a.y) * (h - a.h)) / (b.h - a.h || 1)), yaklasik: true };
}
function igGunlukHiz(v) { // liste kartı: "+X izlenme/gün" (son 24 saat noktaları varsa onlardan, yoksa ortalama)
  if (!v.zaman || v.izlenme == null) return null;
  const P = igNoktalar(v), son = P.at(-1), gun = Math.max((Date.now() - new Date(v.zaman)) / 864e5, 1 / 24);
  if (P.length >= 3 && son.h > 24) { const ref = [...P].reverse().find((p) => son.h - p.h >= 20); if (ref) return ((son.y - ref.y) * 24) / (son.h - ref.h); }
  return v.izlenme / gun;
}
function igListeOzet(v) { const h = igGunlukHiz(v); return h == null ? "" : ` · <b style="color:var(--ok)">+${sayi(Math.round(h))} izlenme/gün</b>`; }

function igZamanHtml(v) {
  if (!v.zaman) return "";
  const ms = Date.now() - new Date(v.zaman), g = Math.floor(ms / 864e5), s = Math.floor((ms % 864e5) / SAAT_MS);
  const ist = new Date(new Date(v.zaman).getTime() + 3 * SAAT_MS), saat = ist.getUTCHours(), gun = GUN_AD[ist.getUTCDay()];
  const iyi = (O.instagram?.en_iyi_saatler || []).map((x) => x.saat), sira = iyi.indexOf(saat);
  const ne = g ? `${g} gün${s ? ` ${s} saat` : ""} önce` : s ? `${s} saat önce` : "az önce";
  return `<div class="igsec"><b>🕒 Zaman</b><div>${ne} paylaşıldı · ${istTarih(v.zaman, { day: "numeric", month: "long", year: "numeric" })}, ${gun}, saat ${String(saat).padStart(2, "0")}.${String(ist.getUTCMinutes()).padStart(2, "0")}</div>
    <div class="mut">${!iyi.length ? "En iyi saat verisi henüz yok." : sira >= 0 ? `<span style="color:var(--ok)">✓ En iyi saatlerden birinde (${sira + 1}. sırada)</span>` : `En iyi saatler dışında (en iyiler: ${iyi.map((h) => String(h).padStart(2, "0") + ".00").join(", ")})`}${O.instagram?.en_iyi_gun ? ` · en iyi gün: ${esc(O.instagram.en_iyi_gun)}${O.instagram.en_iyi_gun === gun ? " ✓" : ""}` : ""}</div></div>`;
}
function igBuyumeHtml(v) {
  const P = igNoktalar(v), gercek = P.length - 1;
  const d1 = igAra(P, 1), d24 = igAra(P, 24);
  const deg = (l, d) => d ? `<div class="igm"><span>${l}</span><b>${sayi(d.y)}</b>${d.yaklasik ? '<span class="mut">yaklaşık</span>' : ""}</div>` : "";
  let g = "";
  if (gercek >= 3) {
    const W = 340, H = 150, Pd = 28, mx = P.at(-1).h || 1, my = Math.max(...P.map((p) => p.y), 1);
    const X = (h) => Pd + ((W - Pd - 8) * h) / mx, Y = (y) => H - 22 - ((H - 34) * y) / my;
    const yol = P.map((p, i) => `${i ? "L" : "M"}${X(p.h).toFixed(1)},${Y(p.y).toFixed(1)}`).join("");
    const etk = (h) => (h >= 48 ? `${Math.round(h / 24)} g` : `${Math.round(h)} sa`);
    g = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;margin-top:6px" role="img" aria-label="İzlenme büyümesi">
      <line x1="${Pd}" y1="${H - 22}" x2="${W - 8}" y2="${H - 22}" stroke="var(--line)"/>
      <path d="${yol}L${X(mx)},${H - 22}L${Pd},${H - 22}Z" fill="rgba(232,196,120,.12)"/><path d="${yol}" fill="none" stroke="var(--gold)" stroke-width="2" stroke-linejoin="round"/>
      ${P.slice(1).map((p) => `<circle cx="${X(p.h).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="2.2" fill="var(--gold)"><title>${etk(p.h)}: ${sayi(p.y)}</title></circle>`).join("")}
      ${[24, 48, 72].filter((h) => h < mx).map((h) => `<line x1="${X(h)}" y1="${H - 22}" x2="${X(h)}" y2="10" stroke="var(--line)" stroke-dasharray="3 3"/><text x="${X(h)}" y="${H - 8}" fill="var(--mut)" font-size="10" text-anchor="middle">${h / 24}. gün</text>`).join("")}
      <text x="${Pd}" y="${H - 8}" fill="var(--mut)" font-size="10">paylaşım</text><text x="${W - 8}" y="${Y(P.at(-1).y) - 6}" fill="var(--gold)" font-size="11" font-weight="700" text-anchor="end">${sayi(P.at(-1).y)}</text>
      <text x="${Pd}" y="12" fill="var(--mut)" font-size="10">▶ izlenme</text></svg>`;
  } else g = `<div class="mut" style="margin-top:6px">Grafik veri birikince dolacak (her 3 saatte bir kaydediliyor)</div>`;
  return `<div class="igsec"><b>📈 Büyüme grafiği</b>${g}${d1 || d24 ? `<div class="igmet">${deg("İlk 1 saat", d1)}${deg("İlk 24 saat", d24)}</div>` : ""}</div>`;
}

// hesap takipçi serisi (birikimli, ms → takipçi): önce Instagram günlük follower_count, yoksa kendi anlık görüntülerimiz
function igTakipciSerileri() {
  const g = O.instagram || {}, S = [];
  const fc = g.gunluk?.follower_count;
  if (fc?.length) { let t = (g.hesap?.takipci || 0) - fc.reduce((s, x) => s + (x.deger || 0), 0); const a = [];
    for (const x of fc) { t += x.deger || 0; a.push({ t: new Date(x.tarih + "T00:00:00Z").getTime(), n: t }); } S.push({ ad: "Instagram günlük takipçi verisi", a }); }
  const a = [...(O.igGecmis?.takipci || []).map((x) => ({ t: new Date(x.t).getTime(), n: x.n })), ...(g.gecmis || []).map((x) => ({ t: new Date(x.tarih + "T04:40:00Z").getTime(), n: x.takipci }))]
    .filter((x) => x.n != null).sort((p, q) => p.t - q.t);
  if (a.length >= 2) S.push({ ad: "kendi takipçi kayıtlarımız", a });
  return S;
}
const igSeriDeger = (a, t) => { if (!a.length || t < a[0].t || t > a.at(-1).t) return null; const i = a.findIndex((p) => p.t >= t); if (a[i].t === t || i === 0) return a[i].n; const p = a[i - 1], q = a[i]; return p.n + ((q.n - p.n) * (t - p.t)) / (q.t - p.t); };
function igTakipEtkisiHtml(v) {
  const bas = `<div class="igsec"><b>➕ Tahmini takipçi etkisi</b> <span class="mut">(tahmini — Instagram Reels için kesin veri vermiyor)</span>`;
  if (!v.zaman) return bas + "</div>";
  const t0 = new Date(v.zaman).getTime(), sat = [];
  let kaynak = null, baz = null, k24 = null, k48 = null;
  for (const s of igTakipciSerileri()) {
    const n0 = igSeriDeger(s.a, t0), nb = igSeriDeger(s.a, t0 - 7 * 864e5), n24 = igSeriDeger(s.a, t0 + 864e5), n48 = igSeriDeger(s.a, t0 + 2 * 864e5);
    if (n0 == null || n24 == null) continue;
    kaynak = s.ad; baz = nb != null ? (n0 - nb) / 7 : null; k24 = n24 - n0 - (baz || 0); k48 = n48 != null ? n48 - n0 - 2 * (baz || 0) : null; break;
  }
  if (kaynak == null) return bas + `<div class="mut">Paylaşımdan sonraki 24 saati kapsayan takipçi verisi yok${Date.now() - t0 < 864e5 ? " (henüz 24 saat dolmadı)" : ""}.</div></div>`;
  // aynı pencerede başka video varsa artışı izlenmeye göre böl
  const ort = (O.instagram?.medya || []).filter((x) => x.id !== v.id && x.zaman && Math.abs(new Date(x.zaman) - t0) < 2 * 864e5);
  const top = (v.izlenme || 0) + ort.reduce((s, x) => s + (x.izlenme || 0), 0), pay = ort.length && top ? (v.izlenme || 0) / top : 1;
  const f = (x) => x == null ? "—" : `<b style="color:${x >= 0 ? "var(--ok)" : "var(--err)"}">${x >= 0 ? "+" : ""}${sayi(Math.round(x * pay))}</b>`;
  sat.push(`<div class="igmet"><div class="igm"><span>İlk 24 saat</span>${f(k24)}</div><div class="igm"><span>İlk 48 saat</span>${f(k48)}</div><div class="igm"><span>Önceki 7 gün ort.</span><b>${baz == null ? "—" : (baz >= 0 ? "+" : "") + virgul(baz)}/gün</b></div></div>`);
  sat.push(`<div class="mut" style="font-size:11.5px">Paylaşım sonrası artıştan önceki 7 günün günlük ortalaması çıkarıldı · kaynak: ${esc(kaynak)}${baz == null ? " · 7 günlük taban hesaplanamadı, ham artış" : ""}.${ort.length ? ` Aynı 48 saatte ${ort.length} video daha var; artış izlenmeye göre bölündü (bu videonun payı %${Math.round(pay * 100)}).` : ""}</div>`);
  return bas + sat.join("") + "</div>";
}

// kalite göstergeleri
const igTamamlama = (v) => (v.ort_izleme_sn && v.sure_sn ? Math.min(v.ort_izleme_sn / v.sure_sn, 1.5) : null);
const igBin = (k) => (v) => (v.izlenme ? ((v[k] || 0) * 1000) / v.izlenme : null);
const IG_KALITE = [["tam", "🎯 İzlenme oranı (ort. izleme / süre)", igTamamlama, (x) => "%" + Math.round(x * 100)],
  ["kay", "🔖 1000 izlenmede kayıt", igBin("kaydetme"), (x) => virgul(x)], ["pay", "↗ 1000 izlenmede paylaşım", igBin("paylasim"), (x) => virgul(x)],
  ["dis", "🌍 Takipçi olmayan erişim", (v) => disOran(v.kaynak), (x) => "%" + virgul(x)]];
function igKaliteDeger(v) { const M = O.instagram?.medya || [], o = {};
  for (const [k, , fn] of IG_KALITE) { const x = fn(v); if (x == null || !isFinite(x)) continue; const ort = ortalama(M, fn); o[k] = { x, ort, oran: ort ? x / ort : null }; } return o; }
function igKaliteHtml(v) {
  const D = igKaliteDeger(v);
  const s = IG_KALITE.filter(([k]) => D[k]).map(([k, l, , f]) => { const d = D[k];
    return `<div class="igm"><span>${l}</span><b>${f(d.x)}</b>${d.oran != null ? `<span style="color:${d.oran >= 1 ? "var(--ok)" : "var(--err)"}">ortalamanın ${virgul(d.oran)} katı</span>` : ""}</div>`; }).join("");
  return `<div class="igsec"><b>⭐ Kalite göstergeleri</b>${s ? `<div class="igmet">${s}</div>` : '<div class="mut">Yeterli veri yok.</div>'}${!v.sure_sn && v.ort_izleme_sn ? '<div class="mut" style="font-size:11.5px">Video süresi bulunamadı (yayın kuyruğunda eşleşmedi), izlenme oranı gösterilmiyor.</div>' : ""}</div>`;
}

// yorum analizi
const igQuizMi = (v) => /quiz|harf/i.test(igFormat(v)) || /quiz|kaçını bil|harflerden/i.test(String(v.baslik || "").toLocaleLowerCase("tr"));
function igSkor(t) {
  t = String(t || "").toLocaleLowerCase("tr");
  let m = t.match(/(\d{1,2})\s*(?:\/|'?\s*[dt][ae]\b|’\s*[dt][ae]\b|üzerinden|uzerinden)\s*(\d{1,2})\b/);
  if (m && +m[2] > 0 && +m[1] <= +m[2]) return { s: +m[1], n: +m[2] };
  m = t.match(/^\D{0,25}?(\d{1,2})\s*(?:doğru|dogru|tane|puan|bildim)?\D{0,25}$/);
  return m && t.length <= 60 ? { s: +m[1], n: null } : null;
}
function igYorumAnalizHtml(v) {
  const Y = IGS.myorum[v.id], bas = `<div class="igsec" id="igyorumanaliz"><b>💬 Yorum analizi</b>`;
  if (!v.yorum) return bas + '<div class="mut">Henüz yorum yok.</div></div>';
  if (Y === undefined) return bas + `<div class="mut">${sayi(v.yorum)} yorum · yükleniyor…</div></div>`;
  if (Y?.hata) return bas + `<div class="mut">${sayi(v.yorum)} yorum · ayrıntı alınamadı: ${esc(Y.hata)}</div></div>`;
  const L = Y.yorumlar, cevapsiz = L.filter((y) => !y.cevaplandi).length;
  let s = `<div class="igmet"><div class="igm"><span>Yorum</span><b>${sayi(Math.max(v.yorum || 0, L.length))}</b></div><div class="igm"><span>Cevaplanmamış</span><b style="color:${cevapsiz ? "var(--err)" : "var(--ok)"}">${sayi(cevapsiz)}</b></div></div>`;
  const ust = L.filter((y) => y.begeni > 0).sort((a, b) => b.begeni - a.begeni).slice(0, 3);
  if (ust.length) s += `<div class="mut" style="margin-top:6px">En çok beğenilenler</div>${ust.map((y) => `<div class="igyor"><b>@${esc(y.kullanici)}</b> ${esc(y.metin)} <span class="tag">❤ ${sayi(y.begeni)}</span></div>`).join("")}`;
  if (igQuizMi(v)) {
    const S = L.map((y) => igSkor(y.metin)).filter(Boolean), pay = {};
    for (const x of S) if (x.n) pay[x.n] = (pay[x.n] || 0) + 1;
    const N = +Object.entries(pay).sort((a, b) => b[1] - a[1])[0]?.[0] || null, G = S.filter((x) => (x.n ? x.n === N : !N || x.s <= N));
    if (G.length) { const ort = G.reduce((t, x) => t + x.s, 0) / G.length, D = {}; for (const x of G) D[x.s] = (D[x.s] || 0) + 1; const mx = Math.max(...Object.values(D));
      s += `<div style="margin-top:8px"><span class="mut">Quiz skorları (${G.length} yorumdan)</span> · ortalama <b style="color:var(--gold)">${virgul(ort)}${N ? ` / ${N}` : ""}</b></div>
        <div class="igdag">${Object.keys(D).map(Number).sort((a, b) => a - b).map((k) => `<div><i style="height:${Math.max(6, (D[k] * 60) / mx)}px"></i><small>${k}</small><em>${D[k]}</em></div>`).join("")}</div>`;
    } else s += '<div class="mut" style="margin-top:6px">Yorumlarda skor bulunamadı.</div>';
  }
  return bas + s + "</div>";
}

// otomatik değerlendirme (kural tabanlı, her zaman çalışır)
function igOzet(v) {
  const M = O.instagram?.medya || [], D = igKaliteDeger(v), oi = ortalama(M, "izlenme"), P = igNoktalar(v);
  return { baslik: v.baslik, format: igFormat(v), izlenme: v.izlenme, kanal_ort_izlenme: oi && Math.round(oi), izlenme_orani_ortalamaya: oi && v.izlenme != null ? +(v.izlenme / oi).toFixed(2) : null,
    gun: v.zaman ? +((Date.now() - new Date(v.zaman)) / 864e5).toFixed(1) : null, ilk24: igAra(P, 24)?.y ?? null, gunluk_hiz: Math.round(igGunlukHiz(v) || 0), ort_izleme_sn: v.ort_izleme_sn, sure_sn: v.sure_sn || null,
    kalite: Object.fromEntries(Object.entries(D).map(([k, d]) => [k, { deger: +d.x.toFixed(3), ortalamaya: d.oran && +d.oran.toFixed(2) }])), yorum: v.yorum, begeni: v.begeni };
}
function igDegerlendirme(v) {
  const o = igOzet(v), D = igKaliteDeger(v), c = [], on = [];
  const r = o.izlenme_orani_ortalamaya;
  if (r == null) c.push("Bu videonun izlenme verisi henüz gelmedi, biraz bekleyip tekrar bakmak lazım.");
  else if (r >= 1.5) c.push(`Bu video iyi gitti: kanal ortalamasının ${virgul(r)} katı izlenmiş.`);
  else if (r >= 0.9) c.push("İzlenme kanal ortalaması civarında, ne kötü ne parlak.");
  else c.push(`İzlenme kanal ortalamasının altında kalmış (${virgul(r)} katı)${o.gun != null && o.gun < 2 ? ", ama video daha yeni, toparlayabilir" : ""}.`);
  if (D.tam) c.push(D.tam.oran >= 1 ? `İzleyenler videoyu ortalamadan daha uzun izlemiş (%${Math.round(D.tam.x * 100)}), giriş tutmuş.` : `İzleyenler videoyu erken bırakıyor (izlenme oranı %${Math.round(D.tam.x * 100)}, ortalamanın altında).`);
  const kp = [D.kay, D.pay].filter(Boolean);
  if (kp.length) { const iyi = kp.every((d) => (d.oran || 0) >= 1), kotu = kp.every((d) => (d.oran || 0) < 0.8);
    c.push(iyi ? "Kaydetme ve paylaşım ortalamanın üstünde, yani içerik değerli bulunmuş." : kotu ? "Kaydetme ve paylaşım ortalamanın altında kalmış." : "Kaydetme/paylaşım tarafı karışık, biri iyi biri zayıf."); }
  if (D.tam && D.tam.oran < 1) on.push("İlk 2 saniyeyi daha sert yap: soruyu ya da en çarpıcı bilgiyi direkt başa koy.");
  if (D.kay && (D.kay.oran || 0) < 0.8) on.push("Sona \"kaydet, sonra tekrar dene\" gibi kısa bir çağrı ekle; quiz ve liste videolarında kaydetmeyi artırır.");
  if (D.pay && (D.pay.oran || 0) < 0.8) on.push("Açıklamaya \"bunu bilemeyecek bir arkadaşını etiketle\" tarzı bir satır ekle.");
  if (D.dis && (D.dis.oran || 0) < 0.8) on.push("Daha çok takipçi dışı kişiye ulaşmak için ilk karede merak uyandıran büyük bir yazı dene.");
  if (r != null && r >= 1.5) on.push(`Bu formatın (${o.format}) benzerini birkaç gün içinde tekrar dene, tutan şeyi tekrarlamak işe yarar.`);
  if (!on.length) on.push("Paylaşım saatini en iyi saatlerden birine denk getirip aynı formatta devam et.");
  return c.slice(0, 3).join(" ") + `<ul style="margin:6px 0 0 18px;padding:0">${on.slice(0, 2).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
}
function igDegerlendirmeHtml(v) {
  const g = IGS.deg[v.id];
  return `<div class="igsec"><b>🧭 Değerlendirme</b><div style="margin-top:4px">${igDegerlendirme(v)}</div>
    <div id="iggem" style="margin-top:8px">${g?.metin ? `<div class="card" style="padding:10px"><span class="mut">Gemini:</span> ${esc(g.metin)}</div>` : g?.hata ? `<div class="mut">${esc(g.hata)}</div>` : ""}
    <button id="iggembtn" class="ghost" style="margin-top:6px">${g?.yuk ? "Gemini düşünüyor…" : "Gemini ile yorumla"}</button></div></div>`;
}
function igDetayEkBagla(d, v) {
  const yen = (sel, html) => { const el = d.querySelector(sel); if (el) el.outerHTML = html; };
  if (v.yorum && IGS.myorum[v.id] === undefined) api("ig_medya_yorum", { id: v.id }).then((r) => (IGS.myorum[v.id] = r)).catch((e) => (IGS.myorum[v.id] = { hata: e.message || "hata" }))
    .finally(() => yen("#igyorumanaliz", igYorumAnalizHtml(v)));
  const b = d.querySelector("#iggembtn"); if (!b) return;
  b.onclick = async () => { if (IGS.deg[v.id]?.yuk) return; IGS.deg[v.id] = { yuk: true }; b.textContent = "Gemini düşünüyor…"; b.disabled = true;
    try { const r = await api("ig_degerlendir", { id: v.id, ozet: igOzet(v) }); IGS.deg[v.id] = { metin: r.metin }; } catch (e) { IGS.deg[v.id] = { hata: e.message || "Gemini yanıt vermedi" }; }
    const g = d.querySelector("#iggem"); if (g) { g.parentElement.outerHTML = igDegerlendirmeHtml(v); igDetayEkBagla(d, v); } };
}
