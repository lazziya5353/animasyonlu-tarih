// Quiz Stüdyo paneli: "ANİMASYON TARİH VİDEO" ve "SPOR TARİHİ VİDEO" sekmelerindeki QUIZ bölümü.
// Format seç -> soruları elle yaz ya da "Ajan hazırlasın" (Gemini taslak + doğruluk kontrolü) -> düzenle/onayla -> Üret.
// Onaydan önce video üretilmez. Kurallar: docs/QUIZ_STUDYO_REHBERI.md
let QS = null; // semalar.json
const QST = { tarih: { format: "", sorular: [], gorseller: {} }, spor: { format: "", sorular: [], gorseller: {} } };
const QYOL = { // her alan: [yol, etiket, tür]
  "hangisi-once": [["a.metin", "A olayı", "t"], ["a.yil", "A yılı", "n"], ["b.metin", "B olayı", "t"], ["b.yil", "B yılı", "n"]],
  "dogru-yanlis": [["ifade", "İddia", "t"], ["dogru", "Cevap", "dy"], ["duzeltme", "Tek satır düzeltme / kanıt", "t"]],
  "bu-kim": [["ipuclari.0", "1. ipucu (en zor)", "t"], ["ipuclari.1", "2. ipucu", "t"], ["ipuclari.2", "3. ipucu (en kolay)", "t"], ["cevap", "Cevap (kişi)", "t"], ["alt_bilgi", "Alt bilgi", "t"]],
  "haritada-bul": [["soru", "Soru", "t"], ...[0, 1, 2, 3].flatMap((i) => [[`secenekler.${i}.ad`, `${"ABCD"[i]} yer adı`, "t"], [`secenekler.${i}.lat`, `${"ABCD"[i]} enlem`, "f"], [`secenekler.${i}.lon`, `${"ABCD"[i]} boylam`, "f"]]), ["dogru", "Doğru iğne", "abcd"], ["alt_bilgi", "Alt bilgi", "t"]],
  "yili-tahmin": [["soru", "Soru", "t"], ...[0, 1, 2, 3].map((i) => [`secenekler.${i}`, `${"ABCD"[i]} yılı`, "n"]), ["dogru", "Doğru seçenek", "abcd"], ["alt_bilgi", "Alt bilgi", "t"]],
  "emoji-tarih": [["emoji", "Emojiler (boşlukla ayır)", "e"], ["ipucu", "İpucu (cevabı söyleme)", "t"], ["cevap", "Cevap", "t"], ["alt_bilgi", "Alt bilgi", "t"]],
  "kelime-eksik": [["soz", "Söz (boşluk yerine ___)", "t"], ...[0, 1, 2, 3].map((i) => [`secenekler.${i}`, `${"ABCD"[i]} seçeneği`, "t"]), ["dogru", "Doğru seçenek", "abcd"], ["soyleyen", "Söyleyen · yer/yıl", "t"]],
};
const qget = (o, p) => p.split(".").reduce((x, k) => (x == null ? x : x[k]), o);
function qset(o, p, v) { const k = p.split("."); let x = o; k.slice(0, -1).forEach((a, i) => { if (x[a] == null) x[a] = /^\d+$/.test(k[i + 1]) ? [] : {}; x = x[a]; }); x[k.at(-1)] = v; }
function qbos(fmt) { const q = { zorluk: "orta" }; (QYOL[fmt] || []).forEach(([p, , t]) => qset(q, p, t === "dy" ? true : t === "abcd" ? 0 : t === "e" ? [] : "")); return q; }

function quizSekmeHtml(tema) {
  return `<h2>🧩 QUIZ</h2><div class="card qs" data-qs="${tema}"><div class="mut">Format seç, soruları yaz ya da ajana hazırlat, onayla, üret. Ücretsiz: GitHub Actions + Gemini ücretsiz kota.</div>
  <div class="qs-formatlar" data-qf></div><div data-qgovde></div><div data-qisler></div></div>`;
}
const qcss = `.qs-formatlar{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin:10px 0}
.qs-f{background:#0002;border:1px solid #fff2;border-radius:12px;padding:6px;text-align:left;color:inherit;font:inherit;cursor:pointer}
.qs-f.on{border-color:var(--gold);box-shadow:0 0 0 1px var(--gold)}.qs-f img{width:100%;aspect-ratio:9/8;object-fit:cover;object-position:top;border-radius:8px;display:block}
.qs-f b{display:block;font-size:13px;margin-top:4px}.qs-f small{display:block;opacity:.7;font-size:11px;line-height:1.3}
.qs-row{border:1px solid #fff2;border-radius:12px;padding:8px;margin:8px 0}.qs-row label{display:block;font-size:11px;opacity:.75;margin-top:6px}
.qs-row input,.qs-row select,.qs textarea,.qs input[type=text],.qs input[type=number]{width:100%;box-sizing:border-box}.qs-2{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.qs-err{color:var(--err);font-size:12px}.qs-not{font-size:12px;opacity:.85;margin:3px 0}.qs-tab{display:flex;gap:6px;margin:8px 0}.qs-tab button.on{outline:2px solid var(--gold)}
.qs-is{display:flex;gap:8px;align-items:center;padding:6px 0;border-top:1px solid #fff1}.qs-is img{width:54px;border-radius:6px}
.qs input,.qs select,.qs textarea{background:#0005;color:inherit;border:1px solid #fff3;border-radius:8px;padding:8px;font:inherit}.qs input[type=color]{padding:2px;height:38px}.qs input[type=checkbox]{width:auto}`;

async function baglaQuiz() {
  if (!document.getElementById("qs-css")) { const s = document.createElement("style"); s.id = "qs-css"; s.textContent = qcss; document.head.append(s); }
  if (!QS) { try { QS = await (await fetch("quiz/semalar.json?v=1")).json(); } catch { return; } }
  document.querySelectorAll("[data-qs]").forEach((kok) => {
    const tema = kok.dataset.qs;
    kok.querySelector("[data-qf]").innerHTML = Object.entries(QS).map(([k, f]) => `<button class="qs-f${QST[tema].format === k ? " on" : ""}" data-fmt="${k}"><img loading="lazy" src="quiz/onizleme-${k}.jpg" alt=""><b>${esc(f.ad)}</b><small>${esc(f.aciklama)}</small></button>`).join("");
    kok.querySelectorAll("[data-fmt]").forEach((b) => (b.onclick = () => { QST[tema] = { format: b.dataset.fmt, sorular: [], gorseller: {} }; baglaQuiz(); }));
    qGovde(kok, tema); qIsler(kok);
  });
}

function qGovde(kok, tema) {
  const S = QST[tema], fmt = S.format, g = kok.querySelector("[data-qgovde]"); if (!fmt) { g.innerHTML = ""; return; }
  const F = QS[fmt];
  if (F.eski) { // mevcut iki format: ajan, kendi rehberiyle hazırlar
    g.innerHTML = `<div class="mut" style="margin:8px 0">${esc(F.ad)} kendi rehberiyle (QUIZ_REHBERI / HARF_BUL_REHBERI) ajan tarafından hazırlanır.</div>
      <input type="text" data-qkonu placeholder="Konu / not (örn. Osmanlı padişahları)"><button class="gold" data-qeski style="width:100%;margin-top:8px">🤖 Ajana hazırlat</button>`;
    g.querySelector("[data-qeski]").onclick = () => guvenli(() => api("komut", { mesaj: `Yeni bir "${F.ad}" quizi hazırla (${tema === "spor" ? "spor teması" : "tarih teması"}). Konu: ${g.querySelector("[data-qkonu]").value || "serbest"}. Rehbere uy, metni onaya sun.` }), "Ajan hazırlıyor; cevabı 'Ajana yaz' kutusunda");
    return;
  }
  const kar = S.kar || { kolay: 4, orta: 4, zor: 2 };
  g.innerHTML = `<div class="qs-tab"><button class="ghost" data-qmod="elle">✍️ Elle yaz</button><button class="ghost" data-qmod="ajan">🤖 Ajan hazırlasın</button></div>
   <div data-qajan hidden><input type="text" data-qkonu placeholder="Konu (örn. Kurtuluş Savaşı, Galatasaray tarihi)" value="${esc(S.konu || "")}">
     <div class="qs-2" style="margin-top:6px"><label>Kolay <input type="number" min="0" max="15" data-k="kolay" value="${kar.kolay}"></label><label>Orta <input type="number" min="0" max="15" data-k="orta" value="${kar.orta}"></label><label>Zor <input type="number" min="0" max="15" data-k="zor" value="${kar.zor}"></label></div>
     <button class="gold" data-qtaslak style="width:100%;margin-top:8px">Taslak hazırla</button><div data-qnot></div></div>
   <div data-qsorular></div><button class="ghost" data-qekle style="width:100%">＋ Soru ekle</button>
   <h3 style="margin:14px 0 4px">Görünüm</h3>
   ${tema === "spor" ? `<div class="qs-2"><label>Takım ana rengi <input type="color" data-qana value="${S.ana || "#1fd17a"}"></label><label>İkinci renk <input type="color" data-qikinci value="${S.ikinci || "#ffc83d"}"></label></div>
     <label class="mut" style="font-size:12px"><input type="checkbox" data-qrenk ${S.renk ? "checked" : ""}> Takım renklerini kullan</label>
     <label>Logo (isteğe bağlı, PNG) <input type="file" accept="image/*" data-qlogo></label>` : ""}
   <label>Arka plan <select data-qarka><option value="tema">Tema varsayılanı</option><option value="yukle">Resim yükle (karartılır, bulanık)</option><option value="gemini">Gemini çizsin</option></select></label>
   <input type="file" accept="image/*" data-qarkadosya hidden><input type="text" data-qarkaprompt placeholder="Sahne tarifi (örn. gece Osmanlı kalyonları)" hidden>
   <div data-qhata class="qs-err"></div><button class="gold" data-quret style="width:100%;margin-top:10px">🎬 Onayla ve Üret</button>`;
  const ciz = () => qSorular(g, fmt, S); ciz();
  g.querySelectorAll("[data-qmod]").forEach((b) => (b.onclick = () => { g.querySelector("[data-qajan]").hidden = b.dataset.qmod !== "ajan"; g.querySelectorAll("[data-qmod]").forEach((x) => x.classList.toggle("on", x === b)); if (b.dataset.qmod === "elle" && !S.sorular.length) { for (let i = 0; i < 8; i++) S.sorular.push(qbos(fmt)); ciz(); } }));
  g.querySelector("[data-qekle]").onclick = () => { if (S.sorular.length < 15) { S.sorular.push(qbos(fmt)); ciz(); } };
  const arka = g.querySelector("[data-qarka]"); arka.value = S.arka_mod || "tema";
  const arkaGoster = () => { S.arka_mod = arka.value; g.querySelector("[data-qarkadosya]").hidden = arka.value !== "yukle"; g.querySelector("[data-qarkaprompt]").hidden = arka.value !== "gemini"; }; arka.onchange = arkaGoster; arkaGoster();
  g.querySelector("[data-qarkadosya]").onchange = async (e) => (S.arka = await qResim(e.target.files[0], 1080, "image/jpeg"));
  const lg = g.querySelector("[data-qlogo]"); if (lg) lg.onchange = async (e) => (S.logo = await qResim(e.target.files[0], 400, "image/png"));
  g.querySelector("[data-qtaslak]").onclick = (e) => qTaslak(g, fmt, S, tema, e.target, ciz);
  g.querySelector("[data-quret]").onclick = (e) => qUret(g, fmt, S, tema, e.target);
}

function qSorular(g, fmt, S) {
  const kap = g.querySelector("[data-qsorular]");
  kap.innerHTML = S.sorular.map((q, i) => `<div class="qs-row" data-qi="${i}"><div style="display:flex;justify-content:space-between;align-items:center"><b>${i + 1}. soru</b>
    <span><select data-qz>${["kolay", "orta", "zor"].map((z) => `<option ${q.zorluk === z ? "selected" : ""}>${z}</option>`).join("")}</select> <button class="ghost" data-qsil>✕</button></span></div>
    ${QYOL[fmt].map(([p, l, t]) => { const v = qget(q, p); const id = `data-p="${p}" data-t="${t}"`;
      if (t === "dy") return `<label>${l}<select ${id}><option value="1" ${v ? "selected" : ""}>DOĞRU</option><option value="0" ${!v ? "selected" : ""}>YANLIŞ</option></select></label>`;
      if (t === "abcd") return `<label>${l}<select ${id}>${"ABCD".split("").map((L, j) => `<option value="${j}" ${v === j ? "selected" : ""}>${L}</option>`).join("")}</select></label>`;
      return `<label>${l}<input ${id} ${t === "n" ? 'inputmode="numeric"' : t === "f" ? 'inputmode="decimal"' : ""} value="${esc(t === "e" ? (v || []).join(" ") : v ?? "")}"></label>`; }).join("")}
    ${fmt === "bu-kim" ? `<label>Portre (isteğe bağlı) <input type="file" accept="image/*" data-qg="p"></label>` : fmt === "hangisi-once" ? `<label>A resmi (isteğe bağlı) <input type="file" accept="image/*" data-qg="a"></label><label>B resmi <input type="file" accept="image/*" data-qg="b"></label>` : ""}
    <div class="qs-err" data-qerr></div></div>`).join("");
  kap.querySelectorAll("[data-qi]").forEach((r) => {
    const i = +r.dataset.qi, q = S.sorular[i];
    r.querySelector("[data-qz]").onchange = (e) => (q.zorluk = e.target.value);
    r.querySelector("[data-qsil]").onclick = () => { S.sorular.splice(i, 1); qSorular(g, fmt, S); };
    r.querySelectorAll("[data-p]").forEach((el) => (el.onchange = () => {
      const t = el.dataset.t, v = el.value.trim();
      qset(q, el.dataset.p, t === "n" ? parseInt(v, 10) : t === "f" ? parseFloat(v.replace(",", ".")) : t === "dy" ? v === "1" : t === "abcd" ? +v : t === "e" ? [...v.split(/\s+/).filter(Boolean)] : v);
      if (fmt === "hangisi-once" && q.a?.yil && q.b?.yil) q.dogru = q.a.yil < q.b.yil ? "A" : "B";
    }));
    r.querySelectorAll("[data-qg]").forEach((el) => (el.onchange = async () => { const d = await qResim(el.files[0], 600, "image/jpeg"); S.gorseller[i] = S.gorseller[i] || {}; if (el.dataset.qg === "p") S.gorseller[i] = d; else S.gorseller[i][el.dataset.qg] = d; }));
  });
}

function qDogrula(fmt, Q) { // scripts/quiz_studyo.py dogrula() ile aynı temel kurallar
  const h = []; if (Q.length < 6 || Q.length > 15) h.push(`Soru sayısı ${Q.length} (6–15 olmalı, 8–15 önerilir)`);
  const bos = (x) => x == null || x === "" || Number.isNaN(x);
  Q.forEach((q, i) => {
    const e = (m) => h.push(`${i + 1}. soru: ${m}`);
    QYOL[fmt].forEach(([p, l, t]) => { if (t !== "dy" && t !== "e" && bos(qget(q, p))) e(`${l} boş`); });
    if (fmt === "hangisi-once" && q.a?.yil === q.b?.yil) e("yıllar farklı olmalı");
    if (fmt === "yili-tahmin" && new Set(q.secenekler).size !== 4) e("yıllar farklı olmalı");
    if (fmt === "kelime-eksik" && (q.soz || "").split("___").length !== 2) e("sözde tam bir ___ olmalı");
    if (fmt === "emoji-tarih" && !((q.emoji || []).length >= 2 && q.emoji.length <= 6)) e("2–6 emoji olmalı");
    if (fmt === "haritada-bul") (q.secenekler || []).forEach((s, j) => { if (!(Math.abs(s?.lat) <= 75 && Math.abs(s?.lon) <= 180)) e(`${"ABCD"[j]} koordinatı hatalı`); });
    const cev = fmt === "bu-kim" || fmt === "emoji-tarih" ? q.cevap : fmt === "kelime-eksik" ? q.secenekler?.[q.dogru] : "";
    const kok = (cev || "").toLocaleLowerCase("tr").split(/\s+/)[0]?.slice(0, Math.max(4, (cev || "").split(/\s+/)[0].length - 2));
    const soruMetni = fmt === "bu-kim" ? (q.ipuclari || []).join(" ") : fmt === "kelime-eksik" ? q.soz : fmt === "emoji-tarih" ? q.ipucu : "";
    if (kok && kok.length >= 3 && (soruMetni || "").toLocaleLowerCase("tr").includes(kok)) e("ipucu/soru cevabı ele veriyor");
  });
  return h;
}

async function qTaslak(g, fmt, S, tema, btn, ciz) {
  const not = g.querySelector("[data-qnot]"); S.konu = g.querySelector("[data-qkonu]").value.trim();
  const kar = {}; g.querySelectorAll("[data-k]").forEach((x) => (kar[x.dataset.k] = +x.value || 0)); S.kar = kar;
  const adet = kar.kolay + kar.orta + kar.zor; if (adet < 6 || adet > 15) return toast("Toplam 6–15 soru olmalı");
  btn.disabled = true; btn.textContent = "Ajan yazıyor…"; not.innerHTML = "";
  try {
    let r = await api("quiz_taslak", { format: fmt, konu: S.konu, adet, karisim: kar, tema });
    if (r.durum === "bekliyor") { // GitHub yedeği: taslak dosyası gelene kadar bekle (~1–2 dk)
      btn.textContent = "Ajan yazıyor (GitHub)…";
      for (let k = 0; k < 40 && r.durum !== "hazir" && r.durum !== "hata"; k++) { await new Promise((s) => setTimeout(s, 8000)); r = { ...(await api("quiz_taslak_durum", { id: r.id })), id: r.id }; }
      if (r.durum !== "hazir") throw new Error(r.hata || "Taslak gelmedi, biraz sonra tekrar dene");
    } else if (r.dogrulama_gerekli) {
      btn.textContent = "Doğruluk kontrolü…"; const k = await api("quiz_dogrula", { format: fmt, sorular: r.sorular }); r.sorular = k.sorular; r.notlar = k.notlar;
    }
    S.sorular = (r.sorular || []).map((q) => ({ zorluk: "orta", ...q })); ciz();
    const h = qDogrula(fmt, S.sorular);
    not.innerHTML = [...(r.notlar || []), ...h.map((x) => "⚠️ " + x)].map((x) => `<div class="qs-not">${esc(typeof x === "string" ? x : JSON.stringify(x))}</div>`).join("") + `<div class="qs-not"><b>Taslak hazır. Kontrol et, düzelt, sonra "Onayla ve Üret".</b></div>`;
  } catch (e) { toast(e.message || "Hata"); }
  btn.disabled = false; btn.textContent = "Taslak hazırla";
}

async function qUret(g, fmt, S, tema, btn) {
  const err = g.querySelector("[data-qhata]"); const h = qDogrula(fmt, S.sorular); err.textContent = h.slice(0, 6).join(" · ");
  if (h.length) return;
  if (S.arka_mod === "yukle" && !S.arka) return (err.textContent = "Arka plan resmi seç ya da 'Tema varsayılanı' yap");
  if (!confirm(`${S.sorular.length} soruluk "${QS[fmt].ad}" videosu üretilsin mi? (~8–10 dk)`)) return;
  const renk = g.querySelector("[data-qrenk]")?.checked;
  const body = { format: fmt, tema, sorular: S.sorular, gorseller: S.gorseller, logo: S.logo, arkaplan_mod: S.arka_mod, arka: S.arka, arkaplan_prompt: g.querySelector("[data-qarkaprompt]").value,
    takim: renk ? { ana: g.querySelector("[data-qana]").value, ikinci: g.querySelector("[data-qikinci]").value } : undefined };
  btn.disabled = true; btn.textContent = "Gönderiliyor…";
  try {
    const r = await api("quiz_uret", body); toast(`Üretim başladı: ${r.slug}`);
    const L = JSON.parse(localStorage.getItem("quiz_isler") || "[]"); L.unshift(r.slug); localStorage.setItem("quiz_isler", JSON.stringify(L.slice(0, 12)));
    QST[tema] = { format: "", sorular: [], gorseller: {} }; baglaQuiz();
  } catch (e) { err.textContent = e.message || "Hata"; btn.disabled = false; btn.textContent = "🎬 Onayla ve Üret"; }
}

function qResim(file, max, tip) { // tarayıcıda küçült -> base64 (Netlify istek sınırı için)
  return new Promise((ok) => { if (!file) return ok(null); const im = new Image(); im.onload = () => { const s = Math.min(1, max / Math.max(im.width, im.height)); const c = document.createElement("canvas"); c.width = im.width * s; c.height = im.height * s; c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); ok(c.toDataURL(tip, 0.88).split(",")[1]); }; im.src = URL.createObjectURL(file); });
}

let qZaman = null;
async function qIsler(kok) {
  const L = JSON.parse(localStorage.getItem("quiz_isler") || "[]"), d = kok.querySelector("[data-qisler]"); if (!L.length) { d.innerHTML = ""; return; }
  d.innerHTML = `<h3 style="margin:14px 0 4px">Üretimler</h3>` + L.map((s) => `<div class="qs-is" data-qis="${esc(s)}"><span class="mut">⏳</span><b>${esc(s)}</b><span class="mut" data-qd>…</span></div>`).join("");
  let bekleyen = false;
  for (const el of d.querySelectorAll("[data-qis]")) {
    try {
      const r = await api("quiz_durum", { slug: el.dataset.qis }), sd = el.querySelector("[data-qd]");
      if (r.durum === "hazir") { el.firstElementChild.outerHTML = r.kapak ? `<img src="${esc(r.kapak)}" alt="">` : "✅"; sd.innerHTML = `<button class="ghost" data-qv="${r.video_id}">▶ Videoyu aç</button>`; }
      else { bekleyen ||= r.durum === "calisiyor" || r.durum === "bekliyor"; sd.innerHTML = `${{ calisiyor: "üretiliyor…", bekliyor: "sırada…", hata: "❌ hata", bitti: "yükleniyor…" }[r.durum] || r.durum}${r.url ? ` · <a href="${esc(r.url)}" target="_blank" rel="noopener">kayıt</a>` : ""}`; }
    } catch {}
  }
  d.querySelectorAll("[data-qv]").forEach((b) => (b.onclick = async () => { const r = await api("video_url", { id: b.dataset.qv }); window.open(r.url, "_blank"); }));
  clearTimeout(qZaman); if (bekleyen) qZaman = setTimeout(() => document.querySelectorAll("[data-qs]").forEach(qIsler), 45000);
}
