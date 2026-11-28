// Quiz Stüdyo paneli: "ANİMASYON TARİH VİDEO" ve "SPOR TARİHİ VİDEO" sekmelerindeki QUIZ bölümü.
// Format seç -> soruları elle yaz ya da "Ajan hazırlasın" (Gemini taslak + doğruluk kontrolü) -> düzenle/onayla -> Üret.
// Onaydan önce video üretilmez. Kurallar: docs/QUIZ_STUDYO_REHBERI.md
let QS = null; // semalar.json
const QST = { tarih: { format: "", sorular: [], gorseller: {} }, spor: { format: "", sorular: [], gorseller: {} } };
const QYOL = { // her alan: [yol, etiket, tür]
  "her-harfe": [["harf", "Harf", "t"], ["soru", "Soru", "t"], ["cevap", "Cevap (bu harfle başlar)", "t"], ["alt_bilgi", "Alt bilgi", "t"]],
  "harf-bul": [["soru", "Soru", "t"], ["cevap", "Cevap", "t"], ["acik_harfler", "Maske (_ kapalı harf; boşsa otomatik)", "t"], ["alt_bilgi", "Alt bilgi", "t"]],
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
  return `<h2>🧩 QUIZ</h2><div class="card qs" data-qs="${tema}"><a class="btn gold" style="display:block;text-align:center;margin-bottom:8px" href="hizli-studyo.html?tema=${tema === "spor" ? "spor" : "tarih"}">⚡ Hızlı Stüdyo · tarayıcıda anında MP4 (Her Harfe Bir)</a><div class="mut">Format seç, soruları yaz ya da ajana hazırlat, onayla, üret. Ücretsiz: GitHub Actions + Gemini ücretsiz kota.</div>
  <div class="qs-formatlar" data-qf></div><div data-qgovde></div><div data-qisler></div><div data-qtum></div></div>`;
}
const qcss = `.qt-kart{display:flex;gap:10px;padding:8px 0;border-top:1px solid #fff1}.qt-kart img,.qt-yok{width:64px;aspect-ratio:9/16;object-fit:cover;border-radius:8px;flex:none;background:#0004;display:grid;place-items:center}
.qt-govde{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}.qt-govde b{font-size:14px;overflow-wrap:anywhere}.qt-roz{align-self:flex-start;color:#000;font-size:11px;font-weight:700;border-radius:99px;padding:2px 8px}
.qt-bar{height:5px;background:#fff2;border-radius:3px;overflow:hidden}.qt-bar i{display:block;height:100%;background:var(--gold)}.qt-btn{display:flex;flex-wrap:wrap;gap:6px;margin-top:3px}.qt-btn .btn{text-decoration:none;font-size:13px;padding:6px 10px}
.qt-kart{cursor:pointer}.qt-modal{position:fixed;inset:0;background:#000d;z-index:999;overflow-y:auto;padding:12px;-webkit-overflow-scrolling:touch}.qt-modal>div{display:flex;flex-direction:column;gap:10px;max-width:520px;margin:0 auto}
.qt-modal video{max-height:70vh;width:100%;border-radius:10px;background:#000}.qt-ust{display:flex;justify-content:space-between;align-items:center;gap:8px}.qt-ust b{overflow-wrap:anywhere}
.qt-kutu{background:#0006;border:1px solid #fff2;border-radius:12px;padding:10px}.qt-kutu h4{margin:0 0 6px;font-size:13px;display:flex;justify-content:space-between;align-items:center;gap:6px}
.qt-kutu textarea{width:100%;box-sizing:border-box;background:#0005;color:inherit;border:1px solid #fff3;border-radius:8px;padding:8px;font:inherit;font-size:14px;resize:vertical}.qt-kutu pre{white-space:pre-wrap;margin:0;font:inherit;font-size:14px;overflow-wrap:anywhere}
.qt-kapak{display:flex;gap:10px;align-items:center}.qt-kapak img{width:72px;aspect-ratio:9/16;object-fit:cover;border-radius:8px}
.qs-formatlar{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin:10px 0}
.qs-f img{height:78px}@media(max-width:640px){.qs-f img{height:auto}}.qs-row.hata{border-color:var(--err);box-shadow:0 0 0 1px var(--err)}.qs-row input.hata{border-color:var(--err)}
.qs-blok{border:1px dashed #fff3;border-radius:12px;padding:10px;margin:12px 0}.qs-blok h3{margin:0 0 6px;font-size:14px}.qs textarea{min-height:170px;resize:vertical}
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
  if (!QS) { try { QS = await (await fetch("quiz/semalar.json?v=2")).json(); } catch { return; } }
  document.querySelectorAll("[data-qs]").forEach((kok) => {
    const tema = kok.dataset.qs;
    kok.querySelector("[data-qf]").innerHTML = Object.entries(QS).map(([k, f]) => `<button class="qs-f${QST[tema].format === k ? " on" : ""}" data-fmt="${k}"><img loading="lazy" src="quiz/onizleme-${k}.jpg" alt=""><b>${esc(f.ad)}</b><small>${esc(f.aciklama)}</small></button>`).join("");
    kok.querySelectorAll("[data-fmt]").forEach((b) => (b.onclick = () => { QST[tema] = { format: QST[tema].format === b.dataset.fmt ? "" : b.dataset.fmt, sorular: [], gorseller: {} }; baglaQuiz(); }));
    qGovde(kok, tema); qIsler(kok);
  });
  qTum();
}

function qGovde(kok, tema) {
  const S = QST[tema], fmt = S.format, g = kok.querySelector("[data-qgovde]"); if (!fmt) { g.innerHTML = `<div class="mut" style="font-size:12px;margin:4px 0 8px">👆 Bir format seç</div>`; return; }
  const F = QS[fmt], kar = S.kar || { kolay: 4, orta: 4, zor: 2 }, ust = fmt === "her-harfe" ? 29 : 15;
  if (!S.sorular.length) for (let i = 0; i < 6; i++) S.sorular.push(qbos(fmt));
  g.innerHTML = `<h3 style="margin:12px 0 4px">✍️ Sorular (elle)</h3><div class="mut" style="font-size:12px">${esc(F.kurallar || "")}</div>
   <div data-qsorular></div><button class="ghost" data-qekle style="width:100%">＋ Soru ekle</button>
   <div class="qs-blok"><h3>📋 Toplu soru ekle</h3><div class="mut" style="font-size:12px">Soruları istediğin biçimde yapıştır: "1. Soru? - Cevap", "Soru? Cevap: X", "A) … B) … Doğru: B"${fmt === "her-harfe" ? ', "A - Soru - Cevap"' : ""}. Eksik alanları (çeldirici, alt bilgi${fmt === "harf-bul" ? ", maske" : ""}) panel tamamlar.</div>
     <textarea data-qtoplu placeholder="1. Osmanlı'nın kurucusu kimdir? - Osman Bey&#10;2. İstanbul hangi yıl fethedildi? Cevap: 1453"></textarea>
     <label class="mut" style="font-size:12px"><input type="checkbox" data-qekle2> Mevcut soruların sonuna ekle</label>
     <button class="gold" data-qayir style="width:100%;margin-top:6px">✂️ Ayır</button><div data-qayirnot></div></div>
   <div class="qs-blok"><h3>🤖 Ajan hazırlasın</h3><input type="text" data-qkonu placeholder="Konu (örn. Kurtuluş Savaşı, Galatasaray tarihi)" value="${esc(S.konu || "")}">
     <div class="qs-2" style="margin-top:6px"><label>Kolay <input type="number" min="0" max="${ust}" data-k="kolay" value="${kar.kolay}"></label><label>Orta <input type="number" min="0" max="${ust}" data-k="orta" value="${kar.orta}"></label><label>Zor <input type="number" min="0" max="${ust}" data-k="zor" value="${kar.zor}"></label></div>
     <button class="gold" data-qtaslak style="width:100%;margin-top:8px">Taslak hazırla</button><div data-qnot></div></div>
   <h3 style="margin:14px 0 4px">Görünüm</h3>
   ${tema === "spor" ? `<div class="qs-2"><label>Takım ana rengi <input type="color" data-qana value="${S.ana || "#1fd17a"}"></label><label>İkinci renk <input type="color" data-qikinci value="${S.ikinci || "#ffc83d"}"></label></div>
     <label class="mut" style="font-size:12px"><input type="checkbox" data-qrenk ${S.renk ? "checked" : ""}> Takım renklerini kullan</label>
     <label>Logo (isteğe bağlı, PNG) <input type="file" accept="image/*" data-qlogo></label>` : ""}
   <label>Arka plan <select data-qarka><option value="tema">Tema varsayılanı</option><option value="yukle">Resim yükle (karartılır, bulanık)</option><option value="gemini">Gemini çizsin</option></select></label>
   <input type="file" accept="image/*" data-qarkadosya hidden><input type="text" data-qarkaprompt placeholder="Sahne tarifi (örn. gece Osmanlı kalyonları)" hidden>
   <h3 style="margin:14px 0 4px">Ses</h3>
   <label>Giriş cümlesi <a href="#" data-qgirisvars style="float:right;font-size:12px">Varsayılana dön</a><input type="text" maxlength="180" data-qgiris></label>
   <label>Ses kaynağı <select data-qses><option value="gemini">Gemini (otomatik)</option><option value="harici">Kendi ses dosyam (ElevenLabs vb.)</option></select></label>
   <div data-qsesharici hidden><button class="ghost" data-qmetin style="width:100%;margin-top:6px">📋 Seslendirme metnini kopyala</button>
     <textarea data-qmetinkutu readonly hidden style="min-height:140px;margin-top:6px"></textarea>
     <div class="mut" style="font-size:12px;margin:4px 0">ElevenLabs'e aynen yapıştır, mp3 indir, buraya yükle.</div>
     <label>Ses dosyası yükle (mp3/wav/m4a, en fazla 25 MB) <input type="file" accept=".mp3,.wav,.m4a,audio/mpeg,audio/wav,audio/mp4,audio/x-m4a" data-qsesdosya></label></div>
   <div data-qhata class="qs-err"></div><button class="gold" data-quret style="width:100%;margin-top:10px">🎬 Onayla ve Üret</button>`;
  const ciz = () => qSorular(g, fmt, S); ciz();
  g.querySelector("[data-qekle]").onclick = () => { if (S.sorular.length < ust) { S.sorular.push(qbos(fmt)); ciz(); } };
  g.querySelector("[data-qayir]").onclick = (e) => qAyir(g, fmt, S, tema, e.target, ciz);
  const arka = g.querySelector("[data-qarka]"); arka.value = S.arka_mod || "tema";
  const arkaGoster = () => { S.arka_mod = arka.value; g.querySelector("[data-qarkadosya]").hidden = arka.value !== "yukle"; g.querySelector("[data-qarkaprompt]").hidden = arka.value !== "gemini"; }; arka.onchange = arkaGoster; arkaGoster();
  g.querySelector("[data-qarkadosya]").onchange = async (e) => (S.arka = await qResim(e.target.files[0], 1080, "image/jpeg"));
  const lg = g.querySelector("[data-qlogo]"); if (lg) lg.onchange = async (e) => (S.logo = await qResim(e.target.files[0], 400, "image/png"));
  g.querySelector("[data-qtaslak]").onclick = (e) => qTaslak(g, fmt, S, tema, e.target, ciz);
  const gi = g.querySelector("[data-qgiris]"); gi.value = qGiris(fmt, tema, S.sorular.length);
  gi.oninput = () => { try { const v = gi.value.trim(); if (!v || v === qGirisVars(fmt, tema, S.sorular.length)) localStorage.removeItem(QGK + fmt); else localStorage.setItem(QGK + fmt, v); } catch {} };
  g.querySelector("[data-qgirisvars]").onclick = (e) => { e.preventDefault(); try { localStorage.removeItem(QGK + fmt); } catch {} gi.value = qGirisVars(fmt, tema, S.sorular.length); };
  const ses = g.querySelector("[data-qses]"); ses.value = S.ses_mod || "gemini";
  const sesGoster = () => { S.ses_mod = ses.value; g.querySelector("[data-qsesharici]").hidden = ses.value !== "harici"; }; ses.onchange = sesGoster; sesGoster();
  g.querySelector("[data-qmetin]").onclick = async () => {
    qTamamla(fmt, S.sorular); const k = g.querySelector("[data-qmetinkutu]"); const gh = qGirisHata(g); if (gh) return toast(gh); k.value = qSesMetni(fmt, tema, S.sorular, qGiris(fmt, tema, S.sorular.length)); k.hidden = false;
    try { await navigator.clipboard.writeText(k.value); toast("Seslendirme metni kopyalandı"); } catch { k.select(); toast("Metni kutudan kopyala"); }
  };
  g.querySelector("[data-qsesdosya]").onchange = (e) => { const f = e.target.files[0]; S.ses_dosya = null; if (!f) return;
    if (!/\.(mp3|wav|m4a)$/i.test(f.name)) { e.target.value = ""; return toast("Sadece mp3/wav/m4a"); }
    if (f.size > 25 * 1024 * 1024) { e.target.value = ""; return toast("Dosya 25 MB'tan büyük"); }
    S.ses_dosya = f; };
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
      qIsaretle(g, fmt, S);
    }));
    r.querySelectorAll("[data-qg]").forEach((el) => (el.onchange = async () => { const d = await qResim(el.files[0], 600, "image/jpeg"); S.gorseller[i] = S.gorseller[i] || {}; if (el.dataset.qg === "p") S.gorseller[i] = d; else S.gorseller[i][el.dataset.qg] = d; }));
  });
  if (S.sorular.some((q) => QYOL[fmt].some(([p]) => { const v = qget(q, p); return v != null && v !== "" && !(Array.isArray(v) && !v.length); }))) qIsaretle(g, fmt, S);
}

function qDogrula(fmt, Q) { // scripts/quiz_studyo.py dogrula() ile aynı temel kurallar (+ Her Harfe / Harflerden Bul)
  const ust = fmt === "her-harfe" ? 29 : 15, h = []; h.satir = {}; h.alan = {};
  if (Q.length < 6 || Q.length > ust) h.push(`Soru sayısı ${Q.length} (6–${ust} olmalı)`);
  const bos = (x) => x == null || x === "" || Number.isNaN(x);
  Q.forEach((q, i) => {
    const e = (m, p) => { h.push(`${i + 1}. soru: ${m}`); (h.satir[i] ||= []).push(m); if (p) (h.alan[i] ||= new Set()).add(p); };
    QYOL[fmt].forEach(([p, l, t]) => { if (t !== "dy" && t !== "e" && !(fmt === "harf-bul" && p === "acik_harfler") && bos(qget(q, p))) e(`${l} boş`, p); });
    if (fmt === "her-harfe") { const H = trUst(q.harf); if (q.cevap && trUst(q.cevap)[0] !== H) e("cevap bu harfle başlamıyor", "harf"); if (Q.findIndex((x) => trUst(x.harf) === H) !== i) e(`${H} harfi tekrar ediyor`, "harf"); }
    if (fmt === "harf-bul" && q.cevap && q.acik_harfler) { const m = qMaskeHata(trUst(q.cevap), q.acik_harfler, q.zorluk); if (m) e(m, "acik_harfler"); }
    if ((fmt === "her-harfe" || fmt === "harf-bul") && q.cevap && q.soru) { const k = trUst(q.cevap).split(/\s+/)[0]; if (k.length >= 4 && trUst(q.soru).includes(k.slice(0, Math.max(4, k.length - 2)))) e("soru cevabı ele veriyor", "soru"); }
    if (fmt === "hangisi-once" && q.a?.yil === q.b?.yil) e("yıllar farklı olmalı", "b.yil");
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
  const adet = kar.kolay + kar.orta + kar.zor, ust = fmt === "her-harfe" ? 29 : 15; if (adet < 6 || adet > ust) return toast(`Toplam 6–${ust} soru olmalı`);
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
    S.sorular = qTamamla(fmt, (r.sorular || []).map((q) => ({ zorluk: "orta", ...q }))); ciz();
    const h = qDogrula(fmt, S.sorular);
    not.innerHTML = [...(r.notlar || []), ...h.map((x) => "⚠️ " + x)].map((x) => `<div class="qs-not">${esc(typeof x === "string" ? x : JSON.stringify(x))}</div>`).join("") + `<div class="qs-not"><b>Taslak hazır. Kontrol et, düzelt, sonra "Onayla ve Üret".</b></div>`;
  } catch (e) { toast(e.message || "Hata"); }
  btn.disabled = false; btn.textContent = "Taslak hazırla";
}

async function qUret(g, fmt, S, tema, btn) {
  qTamamla(fmt, S.sorular); qSorular(g, fmt, S);
  const err = g.querySelector("[data-qhata]"); const h = qDogrula(fmt, S.sorular); err.textContent = h.slice(0, 6).join(" · ");
  if (h.length) return;
  if (S.arka_mod === "yukle" && !S.arka) return (err.textContent = "Arka plan resmi seç ya da 'Tema varsayılanı' yap");
  const gh = qGirisHata(g); if (gh) return (err.textContent = gh);
  if (S.ses_mod === "harici" && !S.ses_dosya) return (err.textContent = "Ses dosyası seç ya da 'Gemini (otomatik)' yap");
  if (!confirm(`${S.sorular.length} soruluk "${QS[fmt].ad}" videosu üretilsin mi? (~8–10 dk)`)) return;
  const renk = g.querySelector("[data-qrenk]")?.checked;
  const body = { format: fmt, tema, sorular: S.sorular, gorseller: S.gorseller, logo: S.logo, arkaplan_mod: S.arka_mod, arka: S.arka, arkaplan_prompt: g.querySelector("[data-qarkaprompt]").value, giris: qGiris(fmt, tema, S.sorular.length),
    takim: renk ? { ana: g.querySelector("[data-qana]").value, ikinci: g.querySelector("[data-qikinci]").value } : undefined };
  btn.disabled = true; btn.textContent = "Gönderiliyor…";
  try {
    if (S.ses_mod === "harici") body.ses_harici = true;
    const r = await api("quiz_uret", body);
    if (r.ses_bekliyor) { // dış ses: 3 MB'lık parçalar (Netlify istek sınırı), son parçada üretim başlar
      const f = S.ses_dosya, ext = f.name.split(".").pop().toLowerCase(), P = 3 * 1024 * 1024, n = Math.ceil(f.size / P);
      for (let i = 0; i < n; i++) {
        btn.textContent = `Ses yükleniyor ${i + 1}/${n}…`;
        const b64 = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(",")[1]); fr.readAsDataURL(f.slice(i * P, (i + 1) * P)); });
        await api("quiz_ses_yukle", { slug: r.slug, ext, i, n, base64: b64 });
      }
    }
    toast(`Üretim başladı: ${r.slug}`);
    const L = JSON.parse(localStorage.getItem("quiz_isler") || "[]"); L.unshift(r.slug); localStorage.setItem("quiz_isler", JSON.stringify(L.slice(0, 12)));
    QST[tema] = { format: "", sorular: [], gorseller: {} }; baglaQuiz();
  } catch (e) { err.textContent = e.message || "Hata"; btn.disabled = false; btn.textContent = "🎬 Onayla ve Üret"; }
}

function qResim(file, max, tip) { // tarayıcıda küçült -> base64 (Netlify istek sınırı için)
  return new Promise((ok) => { if (!file) return ok(null); const im = new Image(); im.onload = () => { const s = Math.min(1, max / Math.max(im.width, im.height)); const c = document.createElement("canvas"); c.width = im.width * s; c.height = im.height * s; c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); ok(c.toDataURL(tip, 0.88).split(",")[1]); }; im.src = URL.createObjectURL(file); });
}

let qZaman = null;
// ───────── Tüm quizler (cihazdan bağımsız, GitHub'dan) ─────────
let qTumZaman = 0, qTumYukleniyor = false, qTumCalisan = false;
const qGecen = (t) => { if (!t) return ""; const d = (Date.now() - new Date(t)) / 1000; return d < 60 ? "az önce" : d < 3600 ? `${Math.floor(d / 60)} dk önce` : d < 86400 ? `${Math.floor(d / 3600)} sa önce` : `${Math.floor(d / 86400)} gün önce`; };
function qTumDurum(q) {
  const r = q.run, yeni = r && (!q.zaman || new Date(r.started) > new Date(q.zaman));
  if (r && r.status !== "completed") return r.status === "in_progress" ? "uret" : "sira";
  if (yeni && r.conclusion === "failure") return "hata";
  if (q.release && q.mp4) return "hazir";
  if (r && r.conclusion === "failure") return "hata";
  return "taslak";
}
async function qTum() {
  if (qTumYukleniyor) return; qTumYukleniyor = true; clearTimeout(qTumZaman);
  const kutular = [...document.querySelectorAll("[data-qs] [data-qtum]")]; if (!kutular.length) { qTumYukleniyor = false; return; }
  let L; try { L = (await api("quiz_liste")).quizler || []; } catch (e) { kutular.forEach((k) => (k.innerHTML = `<h3 style="margin:14px 0 4px">Tüm quizler</h3><div class="qs-err">Liste alınamadı</div>`)); qTumYukleniyor = false; return; }
  qTumYukleniyor = false;
  const ROZ = { sira: ["Sırada", "#888"], uret: ["Üretiliyor", "var(--gold)"], hazir: ["Hazır ✓", "#1fd17a"], hata: ["Hata ✗", "var(--err)"], taslak: ["Taslak", "#666"] };
  let calisan = false;
  kutular.forEach((k) => {
    const tema = k.closest("[data-qs]").dataset.qs, Q = L.filter((q) => (q.tema === "spor") === (tema === "spor"));
    k.innerHTML = `<h3 style="margin:14px 0 4px">Tüm quizler <span class="mut">(${Q.length})</span></h3>` + (Q.length ? Q.map((q) => {
      const d = qTumDurum(q), r = q.run || {}; calisan ||= d === "sira" || d === "uret";
      const [ad, renk] = ROZ[d], ust = d === "uret" && r.adim ? `${ad} · ${esc(r.adim)}` : ad;
      const ilerleme = d === "uret" && r.adim_top ? `<div class="qt-bar"><i style="width:${Math.round((100 * (r.adim_no || 0)) / r.adim_top)}%"></i></div><small class="mut">Adım ${r.adim_no || 0} / ${r.adim_top}</small>` : "";
      const alt = d === "hazir" ? `<div class="qt-btn"><button class="ghost" data-qtizle="${esc(q.mp4)}">▶ İzle</button><a class="ghost btn" href="${esc(q.mp4)}" download>⬇ İndir (video)</a>${q.kapak ? `<a class="ghost btn" href="${esc(q.kapak)}" download>⬇ Kapak</a>` : ""}</div>`
        : d === "hata" ? `<div class="qs-err">${esc(r.hata_adim ? r.hata_adim + ": " : "")}${(r.hata || []).map(esc).join(" · ") || "bilinmeyen hata"}</div><div class="qt-btn">${r.url ? `<a class="ghost btn" href="${esc(r.url)}" target="_blank" rel="noopener">GitHub'da aç</a>` : ""}<button class="ghost" data-qttekrar="${esc(q.slug)}">↻ Tekrar dene</button></div>` : "";
      return `<div class="qt-kart" data-qtslug="${esc(q.slug)}">${q.kapak ? `<img loading="lazy" src="${esc(q.kapak)}" alt="">` : `<div class="qt-yok">🧩</div>`}<div class="qt-govde"><b>${esc(q.baslik)}</b>
        <small class="mut">${esc(q.format_ad)}${q.soru ? ` · ${q.soru} soru` : ""} · ${qGecen(r.updated || q.zaman)}</small>
        <span class="qt-roz" style="background:${renk}">${ust}</span>${ilerleme}${alt}</div></div>`;
    }).join("") : `<div class="mut" style="font-size:12px">Henüz quiz yok</div>`);
  });
  qTumListe = L;
  document.querySelectorAll("[data-qtslug]").forEach((k) => (k.onclick = (e) => { if (e.target.closest("a,button:not([data-qtizle])")) return; e.preventDefault(); const q = L.find((x) => x.slug === k.dataset.qtslug); if (q) qDetay(q); }));
  document.querySelectorAll("[data-qttekrar]").forEach((b) => (b.onclick = async () => {
    if (!confirm(`"${b.dataset.qttekrar}" yeniden üretilsin mi? Mevcut ses kullanılır.`)) return;
    b.disabled = true; try { await api("quiz_tekrar", { slug: b.dataset.qttekrar }); toast("Yeniden başlatıldı"); setTimeout(qTum, 4000); } catch (e) { toast("Başlatılamadı"); b.disabled = false; }
  }));
  qTumCalisan = calisan;
  if (calisan && !document.hidden) qTumZaman = setTimeout(qTum, 20000);
}
let qTumListe = [];
const QHT_TARIH = "#tarih #osmanlı #türktarihi #tarihsorusu #quiz #bilgiyarışması #osmanlıtarihi #atatürk #tarihbilgisi #animasyontarih #keşfet #reels";
const QHT_SPOR = "#spor #futbol #sportarihi #sporquiz #quiz #bilgiyarışması #futbolbilgisi #galatasaray #fenerbahçe #beşiktaş #keşfet #reels";
const QSABIT = "Kaçını bildin? 👇 Puanını yaz, en yüksek puanı sabitleyelim 🏆";
function qVarsayilan(q) { // kural tabanlı, ücretsiz: slug numarasına göre şablon değişir
  const n = q.soru || 22, spor = q.tema === "spor", konu = spor ? "spor" : "tarih", kurt = spor ? "gerçek spor kurdu" : "gerçek tarih kurdu";
  const no = +((q.slug.match(/(\d+)(?!.*\d)/) || [0, 0])[1]) || 0, f = q.format_ad || "quiz";
  const har = /harf/i.test(f + q.format), birim = har ? `${n} harf, ${n} ${konu} sorusu` : `${n} soru, ${f.toLowerCase()} usulü`;
  const G = ["Geçen quiz çok kolay dediniz, bu sefer zorlaştırdık 😏", "Bu sefer kimse kolay demesin 😏", "Yorumlarda \"daha zor\" diyenler, bu sizin için 😎", "Hızlı olan kazanır, hazır mısın? ⏱️", "Bunu arkadaşına da at, bakalım kim daha çok biliyor 😏", "Söz veriyoruz, bu sefer biraz kafa yakacak 🤯"];
  const O = [`Bakalım bu sefer kaç tane bileceksin? 🤔`, `Kaçta kaç yapacaksın, merak ediyoruz 🤔`, `İlk yarıyı herkes bilir, asıl iş sonda 👀`, `Dürüst ol, kopya yok 🤫`];
  const S = ["Videoyu durdurmak yok, puanını yorumlara yaz 👇", "Durdurmadan oyna, skorunu yorumlara bırak 👇", "Puanını yorumlara yaz, en yükseği sabitliyoruz 👇"];
  const K = [`${n}'de ${n} yapan ${kurt} 🏆`, `${n}/${n} yapan varsa efsanedir 🏆`, `Yarısını geçtiysen fena değil, ${n}'de ${n} ise saygılar 🫡`];
  return { aciklama: `${G[no % G.length]}\n\n${birim}. ${O[no % O.length]}\n${S[no % S.length]}\n\nBir sonraki quiz ne olsun? 👇`, hashtagler: spor ? "#spor #sporquiz #soru #keşfetteyiz #sorucevap #keşfet" : "#soru #keşfetteyiz #tarih #sorucevap #keşfet", sabit_yorum: QSABIT };
}
async function qKopyala(t) { try { await navigator.clipboard.writeText(t); } catch { const a = document.createElement("textarea"); a.value = t; document.body.append(a); a.select(); document.execCommand("copy"); a.remove(); } toast("Kopyalandı ✓"); }
function qDetay(q) {
  const v = qVarsayilan(q), D = { aciklama: q.aciklama || v.aciklama, hashtagler: q.hashtagler || v.hashtagler, sabit_yorum: q.sabit_yorum || v.sabit_yorum };
  const kutu = (k, b, sat) => `<div class="qt-kutu"><h4>${b}<button class="ghost" data-qkop="${k}">📋 Kopyala</button></h4><pre data-qgos="${k}"></pre><textarea data-qdz="${k}" rows="${sat}" hidden></textarea></div>`;
  const m = document.createElement("div"); m.className = "qt-modal";
  m.innerHTML = `<div><div class="qt-ust"><b>${esc(q.baslik)}</b><button class="ghost" data-kapat>✕ Kapat</button></div>
    ${q.mp4 ? `<video src="${esc(q.mp4)}" controls autoplay playsinline ${q.kapak ? `poster="${esc(q.kapak)}"` : ""}></video>` : `<div class="mut">Video henüz hazır değil</div>`}
    <div class="qt-kapak">${q.kapak ? `<img src="${esc(q.kapak)}" alt="Kapak">` : ""}<div class="qt-btn">${q.mp4 ? `<a class="ghost btn" href="${esc(q.mp4)}" download>⬇ Video</a>` : ""}${q.kapak ? `<a class="ghost btn" href="${esc(q.kapak)}" download>⬇ Kapak</a>` : ""}</div></div>
    ${!q.aciklama ? `<small class="mut">Hazır şablon öneri gösteriliyor — düzenleyip kaydedebilirsin.</small>` : ""}
    ${kutu("aciklama", "Açıklama", 9)}${kutu("hashtagler", "Hashtagler", 3)}${kutu("sabit_yorum", "Sabit yorum önerisi", 2)}
    <div class="qs-err" data-qderr></div>
    <div class="qt-btn"><button class="ghost" data-qduzenle>✏️ Düzenle</button><button data-qkaydet hidden>💾 Kaydet</button><button class="ghost" data-qgem>✨ Gemini ile yeni öneri</button></div></div>`;
  const $ = (s) => m.querySelector(s), ciz = () => Object.keys(D).forEach((k) => { $(`[data-qgos=${k}]`).textContent = D[k]; $(`[data-qdz=${k}]`).value = D[k]; });
  const duzen = (on) => { Object.keys(D).forEach((k) => { $(`[data-qgos=${k}]`).hidden = on; $(`[data-qdz=${k}]`).hidden = !on; }); $("[data-qkaydet]").hidden = !on; $("[data-qduzenle]").textContent = on ? "Vazgeç" : "✏️ Düzenle"; };
  const oku = () => { if (!$("[data-qkaydet]").hidden) Object.keys(D).forEach((k) => (D[k] = $(`[data-qdz=${k}]`).value)); };
  ciz();
  m.querySelectorAll("[data-qkop]").forEach((b) => (b.onclick = () => { oku(); qKopyala(D[b.dataset.qkop]); }));
  $("[data-qduzenle]").onclick = () => { const on = $("[data-qkaydet]").hidden; if (!on) ciz(); duzen(on); };
  $("[data-qkaydet]").onclick = async (e) => { const b = e.target; oku(); b.disabled = true; $("[data-qderr]").textContent = "";
    try { await api("quiz_aciklama_kaydet", { slug: q.slug, ...D }); Object.assign(q, D); ciz(); duzen(false); toast("Kaydedildi ✓"); } catch (er) { $("[data-qderr]").textContent = er.message || "Kaydedilemedi"; } b.disabled = false; };
  $("[data-qgem]").onclick = async (e) => { const b = e.target; b.disabled = true; b.textContent = "Gemini yazıyor…"; $("[data-qderr]").textContent = "";
    try { const r = await api("quiz_aciklama_gemini", { soru: q.soru, tema: q.tema, format_ad: q.format_ad }); ["aciklama", "hashtagler", "sabit_yorum"].forEach((k) => r[k] && (D[k] = r[k])); ciz(); duzen(true); toast("Öneri geldi — beğendiysen Kaydet"); }
    catch (er) { $("[data-qderr]").textContent = "Gemini: " + (er.message || "hata"); } b.disabled = false; b.textContent = "✨ Gemini ile yeni öneri"; };
  m.onclick = (e) => { if (e.target === m || e.target.dataset.kapat != null) m.remove(); }; document.body.append(m);
}
document.addEventListener("visibilitychange", () => { if (document.hidden) clearTimeout(qTumZaman); else if (qTumCalisan) qTum(); });

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

// ───────── Toplu soru ekle: yerel ayrıştırıcı -> (gerekirse) Gemini -> türetilen alanlar -> düzenlenebilir satırlar ─────────
const TR_ABC = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ";
const trUst = (x) => String(x ?? "").trim().toLocaleUpperCase("tr");
function qIsaretle(g, fmt, S) { // doğrulama hatalarını satırlarda kırmızı göster
  const h = qDogrula(fmt, S.sorular);
  g.querySelectorAll("[data-qi]").forEach((r) => { const i = +r.dataset.qi, m = h.satir[i] || [];
    r.classList.toggle("hata", m.length > 0); r.querySelector("[data-qerr]").textContent = m.join(" · ");
    r.querySelectorAll("[data-p]").forEach((el) => el.classList.toggle("hata", !!h.alan[i]?.has(el.dataset.p))); });
}
function qMaskeHata(cev, m, z) { // docs/HARF_BUL_REHBERI.md maske kuralı
  m = String(m); if (m.length !== cev.length) return "maske cevapla aynı uzunlukta olmalı";
  let acik = 0, harf = 0;
  for (let i = 0; i < cev.length; i++) { const c = cev[i], x = m[i];
    if (c === " " || c === "-") { if (x !== c) return "maskede boşluk/tire yeri hatalı"; continue; }
    harf++; if (x !== "_") { if (trUst(x) !== c) return "maskedeki açık harf cevapla uyuşmuyor"; acik++; } }
  if (acik >= harf) return "en az bir harf kapalı olmalı";
  if (acik / harf > 0.3) return "açık harf oranı %30'u aşıyor";
  if (z === "zor" && acik > 2) return "zor soruda en çok 2 açık harf";
  const W = qKelimeler(cev);
  if (W.length > 1 && z !== "zor") { if (W.some((w) => !w.some((i) => m[i] !== "_"))) return "her kelimede en az 1 açık harf olmalı"; if (W.every((w) => m[w[0]] !== "_")) return "tüm kelimelerin ilk harfi birden açık olmamalı"; }
  return "";
}
function qKelimeler(cev) { const W = []; let w = []; for (let i = 0; i <= cev.length; i++) { if (i === cev.length || cev[i] === " " || cev[i] === "-") { if (w.length) W.push(w); w = []; } else w.push(i); } return W; }
function qMaske(cev, z = "orta") { // kolay ~%25, orta ~%20, zor 1–2 harf; çok kelimede her kelimede ≥1 açık (ilk harf değil); %30'u aşmaz
  cev = trUst(cev); const W = qKelimeler(cev), n = W.flat().length; if (n < 2) return cev.replace(/[^ -]/g, "_");
  const tavan = Math.max(1, Math.floor(n * 0.3));
  let hedef = z === "zor" ? (n >= 8 ? 2 : 1) : Math.max(1, Math.round(n * (z === "kolay" ? 0.25 : 0.2)));
  if (z !== "zor" && W.length > 1) hedef = Math.max(hedef, W.length);
  hedef = Math.min(hedef, tavan, n - 1);
  const ac = new Set(), ic = (w) => w.slice(1).length ? w.slice(1) : w;
  if (z !== "zor" && W.length > 1) W.forEach((w) => { const a = ic(w); ac.add(a[Math.floor(a.length / 2)]); });
  const aday = W.flatMap(ic).filter((i) => !ac.has(i));
  for (let k = 0; ac.size < hedef && aday.length; k++) { const i = aday.splice(Math.floor(((k * 0.618) % 1) * aday.length), 1)[0]; if (![...ac].some((x) => Math.abs(x - i) < 2) || aday.length < hedef) ac.add(i); }
  return [...cev].map((c, i) => (c === " " || c === "-" ? c : ac.has(i) ? c : "_")).join("");
}
function qTamamla(fmt, Q) { // türetilen alanlar: Her Harfe harfi + sıralama, Harflerden Bul maskesi
  if (fmt === "her-harfe") { Q.forEach((q) => { q.cevap = String(q.cevap || "").trim(); if (!q.harf && q.cevap) q.harf = trUst(q.cevap)[0]; q.harf = trUst(q.harf).slice(0, 1); });
    Q.sort((a, b) => (TR_ABC.indexOf(a.harf) + 1 || 99) - (TR_ABC.indexOf(b.harf) + 1 || 99)); }
  if (fmt === "harf-bul") Q.forEach((q) => { if (!q.cevap) return; q.cevap = trUst(q.cevap); if (!q.acik_harfler || qMaskeHata(q.cevap, q.acik_harfler, q.zorluk)) q.acik_harfler = qMaske(q.cevap, q.zorluk); });
  if (fmt === "hangisi-once") Q.forEach((q) => { if (q.a?.yil && q.b?.yil) q.dogru = q.a.yil < q.b.yil ? "A" : "B"; });
  return Q;
}
function qAyirYerel(fmt, metin) { // kural tabanlı: blokları bul, soru/cevap/seçenek/doğru harfini çıkar
  metin = String(metin).replace(/\\n/g, "\n").replace(/^\s*["“”']+|["“”']+\s*$/g, "");
  const borulu = metin.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
  if (borulu.length && borulu.every((l) => l.split(/\s*[|\t]\s*/).length >= 2 && /[|\t]/.test(l))) { // "A | soru | cevap | alt" ya da "soru | cevap | alt"
    const sorular = borulu.map((l) => { const p = l.split(/\s*[|\t]\s*/).map((x) => x.trim()); const q = qbos(fmt);
      const harfli = p.length >= 3 && p[0].length <= 2, [h, so, ce, al] = harfli ? p : ["", ...p];
      if (fmt === "her-harfe") Object.assign(q, { harf: h, soru: so || "", cevap: ce || "" }); else if ("soru" in q) Object.assign(q, { soru: so || "", cevap: ce || "" });
      if ("alt_bilgi" in q && al) q.alt_bilgi = al; return q; });
    if (fmt === "her-harfe" || fmt === "harf-bul") return { sorular, belirsiz: false };
  }
  const sat = metin.replace(/\r/g, "").replace(/[ \t]+(?=\(?[B-Da-d]\)\s)/g, "\n").replace(/[ \t]+(?=(Doğru|Cevap)\s*:)/gi, "\n").split("\n").map((x) => x.trim()).filter(Boolean);
  const SEC = /^\(?([A-Da-d])[).:\-]\s*(.+)$/, DOG = /^(doğru(\s*cevap)?|cevap|yanıt|answer)\s*[:=\-]\s*(.+)$/i, NUM = /^(\d{1,2})\s*[.)\-:]\s*(.+)$/;
  const HH = /^([A-Za-zÇĞİÖŞÜçğıöşü])\s*[-–:)]\s*(.+?)\s+[-–]\s+(.+)$/;
  const blok = []; let cur = null; const yeni = (t) => { cur = { metin: t, sec: [], dogru: null }; blok.push(cur); };
  const numarali = sat.filter((x) => NUM.test(x)).length >= 2;
  for (const l of sat) {
    if (fmt === "her-harfe" && HH.test(l) && !NUM.test(l)) { const [, h, so, ce] = l.match(HH); blok.push({ metin: so, cevap: ce, harf: h, sec: [] }); cur = null; continue; }
    const n = l.match(NUM), sc = l.match(SEC), dg = l.match(DOG);
    if (n && (numarali || !cur)) { yeni(n[2]); continue; }
    if (cur && sc && cur.sec.length < 4 && "abcd".indexOf(sc[1].toLowerCase()) === cur.sec.length) { cur.sec.push(sc[2].replace(/\s*[(\[]?(doğru|✓|✔)[)\]]?\s*$/i, (m) => ((cur.dogru = "ABCD"[cur.sec.length]), ""))); continue; }
    if (cur && dg) { const v = dg[3].trim(); if (/^[A-Da-d]\)?$/.test(v) && cur.sec.length) cur.dogru = v[0].toUpperCase(); else cur.cevap = v; continue; }
    if (!cur || (!numarali && (cur.cevap || cur.sec.length || /[?]\s*$/.test(cur.metin)))) yeni(l); else cur.metin += " " + l;
  }
  // satır içi: "Soru? - Cevap", "Soru? Cevap: X", "Soru? Cevap"
  for (const b of blok) { if (b.cevap) continue; let m = b.metin.match(/^(.+?)\s*(?:cevap|yanıt|doğru)\s*[:=]\s*(.+)$/i) || b.metin.match(/^(.+?\?)\s*[-–—=>]+\s*(.+)$/) || b.metin.match(/^(.+?)\s+[-–—]\s+(.+)$/) || b.metin.match(/^(.+?\?)\s*(.+)$/);
    if (m) { b.metin = m[1].trim(); b.cevap = m[2].trim(); }
    if (fmt === "her-harfe" && !b.harf) { const h = b.metin.match(/^([A-ZÇĞİÖŞÜ])\s*[-–:)]\s*(.+)$/); if (h) { b.harf = h[1]; b.metin = h[2]; } } }
  // "Cevap - Alt bilgi": cevaptaki son boşluklu tireden sonrası alt bilgidir
  for (const b of blok) { if (b.cevap && /\s[-–—]\s/.test(b.cevap)) { const i = b.cevap.search(/\s[-–—]\s(?!.*\s[-–—]\s)/); b.alt = b.cevap.slice(i + 3).trim(); b.cevap = b.cevap.slice(0, i).trim(); } }
  const sonuc = [], ac = []; let belirsiz = false;
  const yil = (x) => { const m = String(x || "").match(/-?\d{3,4}/); return m ? +m[0] : NaN; };
  blok.forEach((b, i) => {
    const q = qbos(fmt); if (b.alt && "alt_bilgi" in q) q.alt_bilgi = b.alt; const di = b.dogru ? "ABCD".indexOf(b.dogru) : b.cevap && b.sec.length ? b.sec.findIndex((x) => trUst(x) === trUst(b.cevap)) : -1;
    if (fmt === "her-harfe") Object.assign(q, { harf: b.harf || "", soru: b.metin, cevap: b.cevap || "" });
    else if (fmt === "harf-bul") Object.assign(q, { soru: b.metin, cevap: b.cevap || "" });
    else if (fmt === "dogru-yanlis") { const t = trUst(b.cevap || ""); q.ifade = b.metin; q.dogru = !/^(Y|YANLIŞ|YANLIS|HAYIR|F|FALSE)/.test(t); if (!b.cevap) belirsiz = true; q.duzeltme = (b.cevap || "").replace(/^(doğru|yanlış|d|y)\b[\s.,:\-–]*/i, ""); }
    else if (fmt === "bu-kim") { const ip = b.metin.split(/(?<=[.;!?])\s+|\s*\|\s*/).filter(Boolean); q.ipuclari = [ip[0] || "", ip[1] || "", ip.slice(2).join(" ") || ""]; q.cevap = b.cevap || ""; }
    else if (fmt === "emoji-tarih") { const em = b.metin.match(/\p{Extended_Pictographic}(\uFE0F|\u200D\p{Extended_Pictographic})*/gu) || []; q.emoji = em; q.ipucu = b.metin.replace(/\p{Extended_Pictographic}|\uFE0F|\u200D/gu, "").trim(); q.cevap = b.cevap || ""; }
    else if (fmt === "hangisi-once") { const p = b.metin.split(/\s+(?:mı|mi|mu|mü|veya|ya da|vs\.?|\/)\s+|\s+[-–]\s+/i); const A = p[0] || "", B = p[1] || b.cevap || "";
      q.a = { metin: A.replace(/\(?-?\d{3,4}\)?/, "").trim(), yil: yil(A) }; q.b = { metin: B.replace(/\(?-?\d{3,4}\)?/, "").replace(/\?$/, "").trim(), yil: yil(B) }; }
    else if (fmt === "yili-tahmin") { q.soru = b.metin; const s = b.sec.length === 4 ? b.sec.map(yil) : []; if (s.length) { q.secenekler = s; q.dogru = Math.max(0, di); } else { q.secenekler = [yil(b.cevap), NaN, NaN, NaN]; q.dogru = 0; } }
    else if (fmt === "kelime-eksik") { q.soz = b.metin.replace(/_{2,}|…|\.{3}/, "___"); if (b.sec.length === 4) { q.secenekler = b.sec; q.dogru = Math.max(0, di); } else { q.secenekler = [b.cevap || "", "", "", ""]; q.dogru = 0; } }
    else if (fmt === "haritada-bul") { q.soru = b.metin; if (b.sec.length === 4) { q.secenekler = b.sec.map((ad) => ({ ad, lat: NaN, lon: NaN })); q.dogru = Math.max(0, di); } else q.secenekler[0] = { ad: b.cevap || "", lat: NaN, lon: NaN }; }
    if (b.sec.length && di < 0) belirsiz = true;
    sonuc.push(q); ac.push(i);
  });
  return { sorular: sonuc, belirsiz };
}
async function qAyir(g, fmt, S, tema, btn, ciz) {
  const metin = g.querySelector("[data-qtoplu]").value.trim(), not = g.querySelector("[data-qayirnot]"); if (!metin) return toast("Önce soruları yapıştır");
  const yerel = qAyirYerel(fmt, metin); qTamamla(fmt, yerel.sorular);
  const h = qDogrula(fmt, yerel.sorular), eksik = Object.keys(h.satir).length > 0 || !yerel.sorular.length;
  let sorular = yerel.sorular, notlar = [`Yerel ayrıştırıcı ${yerel.sorular.length} soru buldu.`];
  if (eksik || yerel.belirsiz) { // eksik alan / belirsizlik: Gemini şemaya döksün, çeldirici + alt bilgi taslaklasın
    btn.disabled = true; btn.textContent = "Gemini tamamlıyor…";
    try { const r = await api("quiz_ayir", { format: fmt, metin, yerel: yerel.sorular, tema });
      if (r.ok && r.sorular?.length) { sorular = r.sorular.map((q) => ({ zorluk: "orta", ...q })); notlar = [`Gemini ${sorular.length} soruya ayırdı; eksik alanları taslakladı.`, ...(r.notlar || [])];
        btn.textContent = "Doğruluk notu…"; const k = await api("quiz_dogrula", { format: fmt, sorular }).catch(() => null); if (k?.notlar?.length) notlar.push(...k.notlar.map((x) => "🔎 " + (typeof x === "string" ? x : JSON.stringify(x)))); }
      else notlar.push(`ℹ️ ${r.hata || "Gemini ayıramadı"}; yerel sonuç kullanıldı, boş alanları elle doldur.`);
    } catch (e) { notlar.push(`ℹ️ Gemini'ye ulaşılamadı (${e.message}); yerel sonuç kullanıldı.`); }
    btn.disabled = false; btn.textContent = "✂️ Ayır";
  }
  qTamamla(fmt, sorular);
  const ekle = g.querySelector("[data-qekle2]").checked, ust = fmt === "her-harfe" ? 29 : 15;
  S.sorular = (ekle ? [...S.sorular.filter((q) => QYOL[fmt].some(([p]) => { const v = qget(q, p); return v != null && v !== "" && !(Array.isArray(v) && !v.length); })), ...sorular] : sorular).slice(0, ust);
  qTamamla(fmt, S.sorular); ciz();
  const h2 = qDogrula(fmt, S.sorular);
  not.innerHTML = [...notlar, h2.length ? `⚠️ ${h2.length} sorun: ${h2.slice(0, 4).join(" · ")}${h2.length > 4 ? " …" : ""}` : "✓ Tüm satırlar geçerli. Kontrol et, sonra \"Onayla ve Üret\"."].map((x) => `<div class="qs-not">${esc(x)}</div>`).join("");
}

// ---- Dış ses: workflow'un seslendirme_metni ile birebir aynı metin (quiz_studyo.py hazirla / harf_bul.py hazirla / api quizEskiScript)
const QGIRIS = { "hangisi-once": "Hangisi önce", "dogru-yanlis": "Doğru mu yanlış mı", "bu-kim": "Bu kim", "haritada-bul": "Haritada bul",
  "yili-tahmin": "Yılı tahmin et", "emoji-tarih": "Emoji ile tarih", "kelime-eksik": "Bir kelime eksik" };
const QTR_ABC = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ";
function qSayiYaz(n) { // sayi_yazi.yaz
  const B = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"], O = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"];
  if (n === 0) return "sıfır"; const p = [];
  for (const [d, ad] of [[1e9, "milyar"], [1e6, "milyon"], [1000, "bin"]]) if (n >= d) { const k = Math.floor(n / d); n %= d; p.push((d === 1000 && k === 1 ? "" : qSayiYaz(k) + " ") + ad); }
  if (n >= 100) { const k = Math.floor(n / 100); n %= 100; p.push((k === 1 ? "" : B[k] + " ") + "yüz"); }
  if (n >= 10) { p.push(O[Math.floor(n / 10)]); n %= 10; }
  if (n) p.push(B[n]); return p.join(" ");
}
function qYaziya(t) { // sayi_yazi.metni_yaziya (Python \b ile aynı: Türkçe harfler kelime karakteri)
  const SIRA = { bir: "birinci", iki: "ikinci", "üç": "üçüncü", "dört": "dördüncü", "beş": "beşinci", "altı": "altıncı", yedi: "yedinci", sekiz: "sekizinci", dokuz: "dokuzuncu", on: "onuncu", yirmi: "yirminci", otuz: "otuzuncu", "kırk": "kırkıncı", elli: "ellinci", "altmış": "altmışıncı", "yetmiş": "yetmişinci", seksen: "sekseninci", doksan: "doksanıncı", "yüz": "yüzüncü", bin: "bininci" };
  const sira = (n) => { const w = qSayiYaz(n).split(" "); w[w.length - 1] = SIRA[w.at(-1)] || w.at(-1); return w.join(" "); };
  const W = "[\\p{L}\\p{N}_]", b = `(?<!${W})`;
  t = t.replace(new RegExp(`${b}(\\d+)\\. (?=[a-zçğıöşü])`, "gu"), (m, d) => sira(+d) + " ");
  t = t.replace(new RegExp(`${b}II\\. `, "gu"), "İkinci ").replace(new RegExp(`${b}III\\. `, "gu"), "Üçüncü ").replace(new RegExp(`${b}IV\\. `, "gu"), "Dördüncü ");
  t = t.replace(new RegExp(`${b}MÖ `, "gu"), "Milattan önce ").replace(new RegExp(`${b}MS `, "gu"), "Milattan sonra ");
  return t.replace(/(\d{1,3}(?:\.\d{3})+|\d+)('[a-zçğıöşü]+)?/gu, (m, d, ek) => qSayiYaz(+d.replace(/\./g, "")) + (ek || "").replace(/'/g, ""));
}
function qSatirlar(fmt, q) { // quiz_studyo.satirlar
  const H = "ABCD";
  if (fmt === "hangisi-once") return [["Hangisi daha önce oldu?", `A: ${q.a.metin}.`, `B: ${q.b.metin}.`], `Cevap ${q.dogru}: ${q[q.dogru.toLowerCase()].metin}.`];
  if (fmt === "dogru-yanlis") return [[q.ifade], (q.dogru ? "Doğru! " : "Yanlış! ") + q.duzeltme];
  if (fmt === "bu-kim") return [["Bu kim?", ...q.ipuclari], q.cevap + "."];
  if (fmt === "haritada-bul") return [[q.soru], `Cevap ${H[q.dogru]}: ${q.secenekler[q.dogru].ad}.`];
  if (fmt === "yili-tahmin") return [[q.soru], `Cevap ${q.secenekler[q.dogru]}.`];
  if (fmt === "emoji-tarih") return [[q.soru || "Bu emojiler hangi olayı anlatıyor?"], q.cevap + "."];
  if (fmt === "kelime-eksik") return [["Eksik kelime ne?", q.soz.replace("___", "...")], q.soz.replace("___", q.secenekler[q.dogru])];
  return [[], ""];
}
// Giriş cümlesi: format başına localStorage; kayıt yoksa varsayılan (soru sayısı o anki sayıdan)
const QGK = "quiz_giris_";
function qGirisVars(fmt, tema, n) {
  if (fmt === "her-harfe") return tema === "spor" ? "Her harfe bir spor sorusu! Bakalım kaçını bileceksin?" : "Her harfe bir tarih sorusu! Bakalım kaçını bileceksin?";
  if (fmt === "harf-bul") return "Harflerden bul! Boşlukları doldur, bakalım kaçını çözebileceksin?";
  return `${QGIRIS[fmt]}! ${n} soru, bakalım kaçını bileceksin?`;
}
function qGiris(fmt, tema, n) { let v = null; try { v = localStorage.getItem(QGK + fmt); } catch {} return (v || "").replace(/\s+/g, " ").trim() || qGirisVars(fmt, tema, n); }
function qGirisHata(g) { const v = g.querySelector("[data-qgiris]")?.value.trim() ?? "x"; return !v ? "Giriş cümlesi boş olamaz" : v.length > 180 ? "Giriş cümlesi en fazla 180 karakter" : ""; }
function qSesMetni(fmt, tema, Q, giris) {
  giris = String(giris || "").trim() || qGirisVars(fmt, tema, Q.length);
  const t = (x) => String(x ?? "").trim(), up = (x) => t(x).toLocaleUpperCase("tr");
  if (fmt === "her-harfe") { // api quizEskiScript: harfe göre sıralı, sayı çevirisi yok
    const S = Q.map((q) => ({ ...q, harf: up(q.harf || t(q.cevap)[0]) })).sort((a, b) => QTR_ABC.indexOf(a.harf) - QTR_ABC.indexOf(b.harf));
    const L = [giris];
    for (const q of S) L.push(`${q.harf} harfi. ${t(q.soru)}`, `${t(q.cevap).replace(/[.]+$/, "")}.`);
    L.push("Kaçını bildin? Yorumlara yaz."); return L.join("\n");
  }
  if (fmt === "harf-bul") { // harf_bul.py hazirla: okunus + metni_yaziya
    const okunus = (c) => c.split(" ").map((p) => p.split("-").map((s) => s.slice(0, 1) + s.slice(1).replace(/I/g, "ı").replace(/İ/g, "i").toLowerCase()).join("-")).join(" ");
    const L = [giris];
    for (const q of Q) L.push(t(q.soru), (t(q.cevap_okunus) || okunus(up(q.cevap))).replace(/[.]+$/, "") + ".");
    L.push("Kaçını bildin? Yorumlara yaz!"); return qYaziya(L.join("\n"));
  }
  const L = [giris];
  for (const q of Q) { const [ql, al] = qSatirlar(fmt, q); L.push(...ql, al); }
  L.push("Kaçını bildin? Yorumlara yaz!"); return L.map(qYaziya).join("\n");
}
