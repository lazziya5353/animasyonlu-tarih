// Animasyonlu Tarih kontrol paneli API'si (Netlify Function).
// Ortam değişkenleri: GITHUB_TOKEN (repo + workflow yetkili), GITHUB_REPO (sahip/repo), PANEL_SIFRE, AYLIK_BUTCE_USD (isteğe bağlı)
// IG hızlı yenileme: IG token Netlify Blobs (ig/tok) içinde AES-256-GCM ile şifreli; anahtar PANEL_SIFRE’den türetilir (PANEL_SIFRE değişirse token yeniden kaydedilmeli). İsteğe bağlı IG_USER_ID.
import crypto from "node:crypto";
import { getStore } from "@netlify/blobs";
import * as wpMod from "web-push";
const webpush = wpMod.default || wpMod;

const REPO = process.env.GITHUB_REPO || "lazziya5353/animasyonlu-tarih";
const GH = "https://api.github.com";
const WORKFLOWS = {
  sil: "sil.yml",
  arastirmaci: "weekly-report.yml",
  senarist: "write-script.yml",
  gorsel: "generate-assets.yml",
  kurgucu: "render.yml",
  kontrol: "kontrol.yml",
  yayinci: "yayinci.yml",
  analist: "analist.yml",
  instagram: "instagram_analiz.yml",
  yorumcu: "yorumcu.yml",
  yonetici: "yonetici.yml",
  quiz: "quiz.yml",
  "harf-bul": "harf_bul.yml",
  "quiz-studyo": "quiz_studyo.yml",
  "quiz-taslak": "quiz_taslak.yml",
  haftalik: "weekly_rapor.yml",
};
const ASAMALAR = ["senaryo", "ses", "gorsel", "kurgu", "hepsi"];
const b64 = (o) => Buffer.from(JSON.stringify(o, null, 1)).toString("base64");
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
const token = () => crypto.createHmac("sha256", (process.env.PANEL_SIFRE || "").trim()).update("animasyonlu-tarih-panel").digest("hex");
const same = (a, b) => { const x = Buffer.from(String(a)), y = Buffer.from(String(b)); return x.length === y.length && crypto.timingSafeEqual(x, y); };

async function gh(path, opts = {}) {
  const r = await fetch(GH + path, {
    ...opts,
    headers: { authorization: `Bearer ${process.env.GITHUB_TOKEN}`, accept: opts.accept || "application/vnd.github+json", "x-github-api-version": "2022-11-28", ...(opts.headers || {}) },
  });
  return r;
}
async function ghJson(path, opts) { const r = await gh(path, opts); if (!r.ok) throw new Error(`GitHub ${r.status}: ${(await r.text()).slice(0, 200)}`); return r.status === 204 ? {} : r.json(); }
async function readJson(path) {
  const r = await gh(`/repos/${REPO}/contents/${path}`, { accept: "application/vnd.github.raw" });
  return r.ok ? r.json() : null;
}
async function writeFile(path, contentB64, message) {
  const cur = await gh(`/repos/${REPO}/contents/${path}`);
  const sha = cur.ok ? (await cur.json()).sha : undefined;
  return ghJson(`/repos/${REPO}/contents/${path}`, { method: "PUT", body: JSON.stringify({ message, content: contentB64, sha }) });
}
const dispatch = (wf, inputs = {}) => ghJson(`/repos/${REPO}/actions/workflows/${WORKFLOWS[wf]}/dispatches`, { method: "POST", body: JSON.stringify({ ref: "main", inputs }) });
const validSlug = (s) => /^[a-z0-9-]{1,60}$/.test(s || "");

// Quiz Stüdyo: format şemaları (panel, bu fonksiyon ve scripts/quiz_taslak.py aynı dosyayı kullanır)
import QSEMA from "../../quiz/semalar.json" with { type: "json" };
const QFORMAT = Object.keys(QSEMA).filter((k) => !QSEMA[k].eski), QTUM = Object.keys(QSEMA);
const quizAyirIstem = (fmt, metin, yerel, tema) => `Kullanıcı Türkçe bir ${tema === "spor" ? "spor tarihi" : "tarih"} quizi için soruları serbest biçimde yapıştırdı. Bunları '${QSEMA[fmt].ad}' formatının şemasına dönüştür.
KURALLAR: Kullanıcının verdiği soru sayısını AYNEN koru (soru ekleme/çıkarma yok). Kullanıcının soru ve cevap metinlerini değiştirme; sadece bölüp alanlara yerleştir. Eksik alanları sen taslakla: 4 seçenekli formatlarda seçenek yoksa doğru cevaba yakın, makul 3 çeldirici yaz; alt_bilgi/düzeltme/söyleyen yoksa kısa ve kesin doğru bir bilgi yaz; koordinat gerekiyorsa gerçek koordinatı yaz. Zorluk verilmemişse 'orta'. Format kuralları: ${QSEMA[fmt].kurallar}
Her taslakladığın alan için notlar'a "soru N: <alan> Gemini taslağı — <kısa doğruluk notu / kaynak>" yaz; kullanıcının bilgisinde şüpheli bir hata görürsen değiştirme, notlarda belirt.
Sadece JSON döndür: {"sorular":[...],"notlar":[...]}. Tek soru şeması: ${JSON.stringify(QSEMA[fmt].ornek)}
Yerel ayrıştırıcının kısmi sonucu (yardımcı olabilir): ${JSON.stringify(yerel || []).slice(0, 6000)}
METİN:
${metin}`;
const TR_ABC = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUVYZ";
function quizIstem(fmt, konu, adet, kar, tema) {
  const s = QSEMA[fmt]; const alan = tema === "spor" ? "spor tarihi" : "tarih (ağırlıklı Türk ve dünya tarihi)";
  return `Türkçe bir Instagram ${alan} quiz videosu için '${s.ad}' formatında ${adet} soru hazırla. Konu: ${konu}.\nZorluk dağılımı: ${kar.kolay} kolay, ${kar.orta} orta, ${kar.zor} zor; zorları başa/ortaya/sona dağıt.\nKurallar: ${s.kurallar} Her bilgi kesin doğru ve iki kaynakla doğrulanabilir olmalı; tartışmalı ya da rivayet bilgileri kullanma. Sorular kısa (en çok 14 kelime), alt_bilgi en çok 6 kelime. Türkçe karakterleri doğru yaz.\nSadece JSON döndür: {"sorular": [ ... ]}. Tek bir sorunun şeması (örnek): ${JSON.stringify(s.ornek)}`;
}
const quizKontrolIstem = (fmt, sorular) => "Aşağıdaki quiz sorularını tek tek doğruluk açısından denetle (Google araması kullan). Yanlış yıl, yanlış kişi, uydurma söz, birden fazla doğru cevabı olan soru, cevabı soruda ele veren ipucu ya da hatalı koordinat varsa DÜZELT; düzeltemiyorsan soruyu çıkar. Aynı şemayı koru. Sadece JSON döndür: {\"sorular\": [...], \"notlar\": [\"soru N: ne değişti ve neden (kaynak)\"]}.\n" + JSON.stringify({ format: fmt, sorular });
async function gemini(text, { arama = false, ms = 9000 } = {}) {
  const key = process.env.GEMINI_API_KEY; if (!key) throw new Error("anahtar yok");
  const body = { contents: [{ parts: [{ text }] }], generationConfig: arama ? { temperature: 0.2 } : { temperature: 0.6, responseMimeType: "application/json" } };
  if (arama) body.tools = [{ google_search: {} }];
  const r = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent", { method: "POST", signal: AbortSignal.timeout(ms), headers: { "content-type": "application/json", "x-goog-api-key": key }, body: JSON.stringify(body) });
  if (!r.ok) { let d = ""; try { d = (await r.json()).error?.message || ""; } catch {} throw new Error(`Gemini ${r.status}${d ? ": " + d.slice(0, 120) : ""}`); }
  const t = ((await r.json()).candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("").replace(/^```(json)?|```$/gm, "");
  return JSON.parse(t.slice(t.indexOf("{"), t.lastIndexOf("}") + 1));
}
async function quizSiradaki(fmt) { // projects/<format>-<n>: ilk boş n
  const r = await gh(`/repos/${REPO}/contents/projects`); const ad = r.ok ? (await r.json()).map((x) => x.name) : [];
  let n = 1; while (ad.includes(`${fmt}-${n}`)) n++; return `${fmt}-${n}`;
}

async function quizEskiScript(fmt, slug, tema, Q, baslik, n, girisOzel) {
  const t = (x) => String(x ?? "").trim(), up = (x) => t(x).toLocaleUpperCase("tr");
  const stil = "Bir quiz sunucususun. İlk cümleyi enerjik, gülümseyen ve meydan okuyan bir tonla söyle. Soruları net ve akıcı, cevapları kısa ve kendinden emin oku. Son cümleyi samimi bir çağrı gibi söyle. Uzun sessizlik bırakma, her cümleden sonra kısa bir durak ver:\n";
  if (fmt === "harf-bul") return { baslik: t(baslik) || `Harflerden Bul ${n}`, hook: "HARFLERDEN BUL", slug, format: "harf-bul", tema, ...(girisOzel ? { giris: girisOzel } : {}), konu: "Harflerden Bul quiz", tarih: "", durum: "onaylandi", kaynak: "panel", ses_stil: stil, sade: true,
    sorular: Q.map((q) => ({ zorluk: ["kolay", "orta", "zor"].includes(q.zorluk) ? q.zorluk : "orta", soru: t(q.soru), cevap: up(q.cevap), acik_harfler: t(q.acik_harfler), alt_bilgi: t(q.alt_bilgi), ...(q.cevap_okunus ? { cevap_okunus: t(q.cevap_okunus) } : {}) })) };
  const S = Q.map((q) => ({ ...q, harf: up(q.harf || t(q.cevap)[0]) })).sort((a, b) => TR_ABC.indexOf(a.harf) - TR_ABC.indexOf(b.harf));
  if (new Set(S.map((q) => q.harf)).size !== S.length) return { hata: "Her harf bir kez kullanılmalı" };
  const giris = girisOzel || (tema === "spor" ? "Her harfe bir spor sorusu! Bakalım kaçını bileceksin?" : "Her harfe bir tarih sorusu! Bakalım kaçını bileceksin?");
  const sahne = (l, z) => ({ lines: [l], big: "", sub: "", label: "QUIZ", fx: [], image: "images/bg.jpg", prompt: "quiz", ...(z ? { zorluk: z } : {}) });
  const sah = [sahne(giris)]; for (const q of S) { sah.push(sahne(`${q.harf} harfi. ${t(q.soru)}`, q.zorluk)); sah.push(sahne(`${t(q.cevap).replace(/[.]+$/, "")}.`)); }
  sah.push(sahne("Kaçını bildin? Yorumlara yaz."));
  return { baslik: t(baslik) || `Her Harfe Bir ${tema === "spor" ? "Spor" : "Tarih"} Sorusu ${n}`, hook: `HER HARFE BİR ${tema === "spor" ? "SPOR" : "TARİH"} SORUSU`, slug, tema, map_region: "anadolu", sahneler: sah, finale: "", maps: [], cards: [],
    eras: [{ name: "QUIZ", from: 0, to: 45 }], outro: { title: "KAÇINI BİLDİN?", line: "Yorumlara yaz" }, konu: "Harf quiz", tarih: "", durum: "onaylandi", kaynak: "panel", sade: true, ses_stil: stil,
    seslendirme_metni: sah.map((x) => x.lines[0]).join("\n"), alt_bilgi: Object.fromEntries(S.map((q) => [q.harf, t(q.alt_bilgi)])), aciklama: "", hashtagler: [], kaynaklar: [], kontrol_notlari: [] };
}

let failed = []; // basit kaba kuvvet koruması (sıcak fonksiyon örneği başına)
const gecerliGh = new Map(); // doğrulanmış GitHub Actions anahtarları (10 dk)

// Canlı olaylar (Kurgu Stüdyosu): Netlify Blobs'ta proje başına son 800 olay
const AJANLAR = ["arastirmaci", "senarist", "ses", "gorsel", "kurgucu", "efekt", "kontrol", "yayinci", "sen"];
const TURLER = ["yazi", "gorsel", "efekt", "harita", "ses", "muzik", "kontrol", "bilgi", "ilerleme", "asama"];
// ───────── proje adları: klasör adı yerine metindeki başlık (önbellekli) ─────────
async function basliklar(sluglar) {
  const st = getStore({ name: "ayar", consistency: "strong" }); const B = (await st.get("basliklar", { type: "json" })) || {};
  const eksik = sluglar.filter((s) => !B[s]);
  if (eksik.length) {
    await Promise.all(eksik.map(async (s) => { const sc = await readJson(`projects/${s}/script.json`); if (sc?.baslik) B[s] = String(sc.baslik).slice(0, 90); }));
    await st.setJSON("basliklar", B);
  }
  return Object.fromEntries(sluglar.filter((s) => B[s]).map((s) => [s, B[s]]));
}
async function baslikYaz(slug, baslik) { const st = getStore({ name: "ayar", consistency: "strong" }); const B = (await st.get("basliklar", { type: "json" })) || {}; B[slug] = String(baslik).slice(0, 90); await st.setJSON("basliklar", B); }

// ───────── telefona bildirim (Web Push). Anahtarlar ilk kullanımda üretilip Netlify'da saklanır ─────────
async function vapid() {
  const st = getStore({ name: "ayar", consistency: "strong" }); let v = await st.get("vapid", { type: "json" });
  if (!v) { v = webpush.generateVAPIDKeys(); await st.setJSON("vapid", v); }
  webpush.setVapidDetails("https://animasyonlu-tarih.netlify.app", v.publicKey, v.privateKey); return v;
}
async function bildirimGonder(baslik, metin, url = "/") {
  await vapid(); const st = getStore({ name: "ayar", consistency: "strong" }); const A = (await st.get("abonelikler", { type: "json" })) || [];
  const kalan = []; let n = 0;
  await Promise.all(A.map(async (a) => {
    try { await webpush.sendNotification(a, JSON.stringify({ baslik: String(baslik).slice(0, 80), metin: String(metin).slice(0, 180), url }), { TTL: 86400 }); kalan.push(a); n++; }
    catch (e) { if (![404, 410].includes(e.statusCode)) kalan.push(a); } // süresi dolan abonelikleri sil
  }));
  if (kalan.length !== A.length) await st.setJSON("abonelikler", kalan);
  return n;
}

async function olayEkle(slug, liste) {
  const st = getStore("olaylar"); const key = validSlug(slug) ? slug : "_genel";
  const cur = (await st.get(key, { type: "json" })) || { n: 0, liste: [] };
  for (const o of liste.slice(0, 60)) {
    if (!AJANLAR.includes(o.ajan) || !TURLER.includes(o.tur)) continue;
    const temiz = { i: ++cur.n, ajan: o.ajan, tur: o.tur, mesaj: String(o.mesaj || "").slice(0, 200), z: Number(o.z) || Date.now() / 1000 };
    for (const k of ["t0", "t1", "yuzde", "sahne", "adim", "toplam"]) if (Number.isFinite(Number(o[k])) && o[k] !== null && o[k] !== undefined) temiz[k] = Number(o[k]);
    for (const k of ["seviye", "asama", "durum"]) if (typeof o[k] === "string") temiz[k] = o[k].slice(0, 20);
    if (typeof o.onizleme === "string" && o.onizleme.length < 300000 && temiz.sahne) { // canlı görsel önizlemesi (küçük jpeg)
      await getStore("onizleme").set(`${key}/${temiz.sahne}`, o.onizleme); temiz.onz = 1;
    }
    cur.liste.push(temiz);
  }
  cur.liste = cur.liste.slice(-800);
  await st.setJSON(key, cur);
  return cur.n;
}

// --- Instagram hızlı yenileme: token Blobs'ta AES-256-GCM ile şifreli durur (anahtar PANEL_SIFRE'den türetilir); asla loglanmaz/döndürülmez
const igKey = () => crypto.createHash("sha256").update("ig-token-v1|" + (process.env.PANEL_SIFRE || "").trim()).digest();
function igSifrele(t) { const iv = crypto.randomBytes(12), c = crypto.createCipheriv("aes-256-gcm", igKey(), iv); const e = Buffer.concat([c.update(t, "utf8"), c.final()]); return [iv, c.getAuthTag(), e].map((x) => x.toString("base64")).join("."); }
function igCoz(s) { const [iv, tag, e] = s.split(".").map((x) => Buffer.from(x, "base64")); const d = crypto.createDecipheriv("aes-256-gcm", igKey(), iv); d.setAuthTag(tag); return Buffer.concat([d.update(e), d.final()]).toString("utf8"); }
const igStore = () => getStore({ name: "ig", consistency: "strong" });
const IG_GUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];
const IG_MEDYA = ["views", "reach", "saved", "shares", "total_interactions", "likes", "comments"], IG_REELS = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time"];
async function igRefresh(tok, eski) {
  const V = "v25.0"; let host = "graph.instagram.com";
  const get = async (yol, p = {}) => { const r = await fetch(`https://${host}/${V}/${yol}?${new URLSearchParams(p)}`, { headers: { Authorization: `Bearer ${tok}` } });
    const j = await r.json().catch(() => ({})); if (!r.ok) { const e = new Error(`Instagram ${r.status}: ${j.error?.message || ""}`.slice(0, 300)); e.kod = j.error?.code; throw e; } return j; };
  const deger = (x) => (x.total_value ? x.total_value.value : x.values?.[0]?.value);
  const F = "id,username,name,profile_picture_url,followers_count,follows_count,media_count";
  let h, uid = process.env.IG_USER_ID || "17841480918392807", son;
  for (const hh of ["graph.instagram.com", "graph.facebook.com"]) { host = hh;
    try { if (!uid && hh === "graph.instagram.com") uid = (await get("me", { fields: "user_id" })).user_id; if (!uid) throw new Error("IG_USER_ID yok"); h = await get(uid, { fields: F }); break; } catch (e) { son = e; } }
  const simdi = new Date(), out = { zaman: simdi.toISOString().slice(0, 19) + "Z", gecmis: eski?.gecmis || [], kaynak: "panel" };
  if (!h) { for (const k of ["hesap", "ozet30", "gunluk", "medya"]) if (eski?.[k]) out[k] = eski[k];
    out.hata = son?.kod === 190 ? "Instagram anahtarı geçersiz/süresi dolmuş" : `Instagram'a bağlanılamadı: ${son?.message || ""}`; return out; }
  out.host = host; out.hesap = { kullanici: h.username, ad: h.name, foto: h.profile_picture_url, takipci: h.followers_count || 0, takip: h.follows_count, gonderi: h.media_count || 0 };
  const until = Math.floor(simdi / 1000), since = until - 30 * 86400 + 60, yok = new Set(), ozet = {}, gunluk = {};
  await Promise.all([
    ...["reach", "views", "profile_views", "accounts_engaged", "total_interactions", "follows_and_unfollows"].map((m) => get(`${uid}/insights`, { metric: m, period: "day", metric_type: "total_value", since, until })
      .then((r) => (r.data || []).forEach((x) => (ozet[x.name] = deger(x)))).catch(() => yok.add(m))),
    ...["follower_count", "reach"].map((m) => get(`${uid}/insights`, { metric: m, period: "day", since, until })
      .then((r) => (r.data || []).forEach((x) => (gunluk[x.name] = (x.values || []).map((v) => ({ tarih: (v.end_time || "").slice(0, 10), deger: v.value })))))
      .catch(() => m === "follower_count" && yok.add("follower_count (günlük)"))),
  ]);
  out.ozet30 = ozet; out.gunluk = gunluk;
  // trafik kaynağı: Graph API hesap düzeyinde yalnız follow_type (takipçi / takipçi olmayan) ve media_product_type (Reels/gönderi/hikaye) kırılımlarını verir;
  // Keşfet / Reels sekmesi / profil gibi "yüzey" kırılımı API'de yok (denenip desteklenmeyenler kaynak30.yok'a yazılır)
  const kir = (r) => Object.fromEntries((r.data?.[0]?.total_value?.breakdowns?.[0]?.results || []).map((x) => [x.dimension_values.join("/"), x.value]));
  const k30 = { yok: [] };
  await Promise.all(["views", "reach"].flatMap((m) => ["follow_type", "media_product_type", "surface_type"].map((bd) =>
    get(`${uid}/insights`, { metric: m, period: "day", metric_type: "total_value", breakdown: bd, since, until })
      .then((r) => { const o = kir(r); if (Object.keys(o).length) (k30[m] ||= {})[bd] = o; else k30.yok.push(`${m}:${bd}`); })
      .catch(() => k30.yok.push(`${m}:${bd}`)))));
  out.kaynak30 = k30;
  const bugun = out.zaman.slice(0, 10);
  out.gecmis = [...out.gecmis.filter((g) => g.tarih !== bugun).slice(-365), { tarih: bugun, takipci: out.hesap.takipci }];
  const medya = ((await get(`${uid}/media`, { fields: "id,caption,media_type,media_product_type,permalink,thumbnail_url,media_url,timestamp,like_count,comments_count", limit: 50 })).data || []).slice(0, 50);
  const ist = async (id, met) => { try { const r = await get(`${id}/insights`, { metric: met.join(",") }); return Object.fromEntries((r.data || []).map((x) => [x.name, deger(x)])); } catch {}
    const o = {}; await Promise.all(met.map((m) => get(`${id}/insights`, { metric: m }).then((r) => (r.data || []).forEach((x) => (o[x.name] = deger(x)))).catch(() => yok.add(m)))); return o; };
  const liste = await Promise.all(medya.map(async (p) => { const [st, ek] = await Promise.all([ist(p.id, p.media_product_type === "REELS" ? [...IG_MEDYA, ...IG_REELS] : IG_MEDYA),
      get(`${p.id}/insights`, { metric: "follows,profile_visits" }).then((r) => Object.fromEntries((r.data || []).map((x) => [x.name, deger(x)]))).catch(() => ({}))]), ort = st.ig_reels_avg_watch_time;
    let kaynak = null; if (!yok.has("medya:follow_type")) kaynak = await get(`${p.id}/insights`, { metric: "reach", breakdown: "follow_type", metric_type: "total_value" }).then((r) => { const o = kir(r); return Object.keys(o).length ? o : null; }).catch(() => (yok.add("medya:follow_type"), null));
    return { id: p.id, baslik: (p.caption || "").trim().split("\n")[0].slice(0, 90), zaman: p.timestamp, tur: p.media_product_type || p.media_type, medya_turu: p.media_type, url: p.permalink,
      kapak: p.thumbnail_url || (p.media_type === "IMAGE" ? p.media_url : null), begeni: p.like_count ?? st.likes, yorum: p.comments_count ?? st.comments,
      izlenme: st.views, erisim: st.reach, kaydetme: st.saved, paylasim: st.shares, etkilesim: st.total_interactions, ort_izleme_sn: typeof ort === "number" ? Math.round(ort / 100) / 10 : null, kaynak, takip: ek.follows ?? null, profil_ziyaret: ek.profile_visits ?? null }; }));
  if (!liste.some((v) => v.takip != null)) yok.add("follows (gönderi başına)");
  liste.sort((a, b) => (b.izlenme || 0) - (a.izlenme || 0)); out.medya = liste;
  const ort = (a) => a.reduce((s, x) => s + x, 0) / a.length, saat = {}, gun = {};
  for (const v of liste) { if (!v.zaman || !v.izlenme) continue; const t = new Date(Date.parse(v.zaman.slice(0, 19) + "Z") + 3 * 3600e3);
    (saat[t.getUTCHours()] ||= []).push(v.izlenme); (gun[(t.getUTCDay() + 6) % 7] ||= []).push(v.izlenme); }
  out.en_iyi_saatler = Object.entries(saat).sort((a, b) => ort(b[1]) - ort(a[1])).slice(0, 3).map(([s, v]) => ({ saat: +s, ort_izlenme: Math.round(ort(v)), adet: v.length }));
  const gs = Object.entries(gun).sort((a, b) => ort(b[1]) - ort(a[1])); if (gs.length) out.en_iyi_gun = IG_GUN[+gs[0][0]];
  out.desteklenmeyen = [...yok].sort(); return out;
}

// ───────── Instagram canlı işlemler (yorumlar, cevap, gizle) ─────────
const IG_UID = () => process.env.IG_USER_ID || "17841480918392807";
async function igTok() { const enc = await igStore().get("tok").catch(() => null); if (!enc) return null; try { return igCoz(enc); } catch { return null; } }
let IG_HOST = null;
async function igHost(tok) { // token türüne göre çalışan adres (Instagram ile Giriş / Facebook ile Giriş)
  if (IG_HOST) return IG_HOST;
  for (const h of ["graph.instagram.com", "graph.facebook.com"]) {
    const r = await fetch(`https://${h}/v25.0/${IG_UID()}?fields=id,username`, { headers: { Authorization: `Bearer ${tok}` } });
    if (r.ok) { IG_HOST = h; return h; }
  }
  throw new Error("Instagram anahtarı geçersiz/süresi dolmuş");
}
async function igCagir(tok, method, yol, p = {}) {
  const h = await igHost(tok), get = method === "GET";
  const r = await fetch(`https://${h}/v25.0/${yol}${get ? "?" + new URLSearchParams(p) : ""}`, { method, headers: { Authorization: `Bearer ${tok}`, ...(get ? {} : { "content-type": "application/x-www-form-urlencoded" }) }, body: get ? undefined : new URLSearchParams(p) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`Instagram ${r.status}: ${j.error?.message || ""}`.slice(0, 280) + (j.error?.code != null ? ` [kod ${j.error.code}]` : ""));
  return j;
}
const FORMATLAR = ["Quiz", "Harflerden Bul", "Padişah serisi", "Harita/Gezi/Yer", "Diğer"];
// kural tabanlı, kısa ve doğal cevap önerisi (ücretsiz)
function kuralOneri(metin, id = "") {
  const t = String(metin || "").toLocaleLowerCase("tr").trim(), sec = (a) => a[[...String(id)].reduce((s, c) => s + c.charCodeAt(0), 0) % a.length];
  const skor = t.match(/(\d{1,2})\s*(?:\/|de|da|'de|'da|’de|’da)\s*(\d{1,2})\b/);
  if (skor && +skor[1] > 0 && +skor[2] > 0) { const o = Math.min(+skor[1], +skor[2]) / Math.max(+skor[1], +skor[2]);
    return o >= 0.8 ? sec(["helal olsun 👏", "efsane skor 🔥 helal", "bu ne bilgi böyle 👏"]) : o >= 0.5 ? sec(["fena değil 👏 bir dahakine full yaparsın", "güzel skor 💪"]) : sec(["bir dahaki sefere daha iyi olur 💪", "olsun, bir sonrakinde açarsın 💪"]); }
  if (/(\d+)\s*(doğru|dogru|bildim|puan|tane)/.test(t)) return sec(["helal olsun 👏", "güzel 👏 devamı geliyor", "iyi iş 💪"]);
  if (/(yanlış|yanlis|hata|öyle değil|degil)/.test(t)) return sec(["uyardığın için sağ ol 🙏 bakıyoruz", "haklı olabilirsin, kontrol edip düzelteceğiz 🙏"]);
  if (t.includes("?")) return sec(["güzel soru 🙏 bununla ilgili de bir video gelebilir", "not aldık, yakında 👀"]);
  if (/(harika|süper|mükemmel|muhteşem|eline sağlık|emeğine|güzel|bayıldım|efsane|helal)/.test(t)) return sec(["çok teşekkürler 🙏", "sağ ol 😊 daha nicesi gelecek", "teşekkürler, iyi ki varsın 🙌"]);
  if (/(yap|gelsin|bekliyoruz|anlat|konu)/.test(t)) return sec(["not aldık 👀 sıradakilere ekliyoruz", "güzel fikir, listeye ekledik 🙌"]);
  if (!/[a-zçğıöşü0-9]/i.test(t)) return sec(["❤️", "🙌", "🙏"]);
  return sec(["teşekkürler 🙌", "sağ ol 🙏", "yorumun için teşekkürler 😊"]);
}
async function geminiOneri(liste) { // isteğe bağlı: GEMINI_API_KEY varsa tek seferde toplu öneri
  const key = process.env.GEMINI_API_KEY; if (!key || !liste.length) return 0;
  const istem = "Bir Türk tarih Instagram sayfası (@animasyon.tarih) adına yorumlara cevap yaz. Çok kısa (en fazla 10 kelime), samimi, gündelik, yapay zekâ gibi durmayan, gerekirse 1 emoji. Örnek tarz: \"helal olsun 👏\", \"bir dahaki sefere daha iyi olur 💪\". JSON dizi döndür: [{\"id\":\"...\",\"cevap\":\"...\"}].\n" + JSON.stringify(liste.map((y) => ({ id: y.id, yorum: String(y.metin || "").slice(0, 300), video: y.medya?.baslik })));
  const r = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent", { method: "POST", signal: AbortSignal.timeout(7000),
    headers: { "content-type": "application/json", "x-goog-api-key": key }, body: JSON.stringify({ contents: [{ parts: [{ text: istem }] }], generationConfig: { temperature: 0.7, responseMimeType: "application/json" } }) });
  if (!r.ok) return 0;
  const j = await r.json(); let a = []; try { a = JSON.parse((j.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("")); } catch { return 0; }
  let n = 0; for (const x of Array.isArray(a) ? a : []) { const y = liste.find((z) => z.id === String(x.id)); if (y && x.cevap) { y.oneri = String(x.cevap).slice(0, 200); y.ai = true; n++; } }
  return n;
}

// Tüm quizler: projects/ altındaki quiz klasörleri + release + son koşu (20 sn önbellek)
const QUIZ_ON = ["her-harfe-", "harflerden-bul-", ...QFORMAT.map((k) => k + "-")];
const QWF = { quiz: "quiz.yml", "harf-bul": "harf_bul.yml", "quiz-studyo": "quiz_studyo.yml" };
const qWfKey = (fmt) => QSEMA[fmt]?.workflow || "quiz-studyo";
const qFmtSlug = (slug) => slug.startsWith("her-harfe-") ? "her-harfe" : slug.startsWith("harflerden-bul-") ? "harf-bul" : QFORMAT.find((k) => slug.startsWith(k + "-")) || "";
let qListeOnbellek = { t: 0, v: null };
function qHataTr(l) {
  if (/429|RESOURCE_EXHAUSTED|quota/i.test(l)) return "Gemini günlük ses hakkı doldu (11:00'de yenilenir)";
  return l.replace(/cevap sizmasi[^"]*/gi, "soru okunurken cevap duyuldu").replace(/ses yok/gi, "sessiz parça").trim().slice(0, 160);
}
function qHataOzet(log) {
  const sat = log.split("\n").map((x) => x.replace(/^\S+Z\s/, "").trim());
  if (sat.some((x) => /429|RESOURCE_EXHAUSTED/.test(x))) return ["Gemini günlük ses hakkı doldu (11:00'de yenilenir)"];
  const i = sat.findIndex((x) => /"hatalar"\s*:/.test(x));
  if (i >= 0) { const h = []; for (let k = i + 1; k < sat.length && h.length < 3; k++) { if (/^\]/.test(sat[k])) break; const m = sat[k].match(/^"(.+)",?$/); if (m) h.push(qHataTr(m[1])); } if (h.length) return h; }
  const e = sat.filter((x) => /HATA:|Error|error:/.test(x) && !/^##\[error\]Process completed/.test(x));
  return [...new Set(e.slice(-3).map(qHataTr))];
}
async function quizListe() {
  if (qListeOnbellek.v && Date.now() - qListeOnbellek.t < 20000) return qListeOnbellek.v;
  const [dir, rels, ...runl] = await Promise.all([ghJson(`/repos/${REPO}/contents/projects`), ghJson(`/repos/${REPO}/releases?per_page=100`).catch(() => []),
    ...Object.values(QWF).map((w) => ghJson(`/repos/${REPO}/actions/workflows/${w}/runs?per_page=60`).then((r) => r.workflow_runs || []).catch(() => []))]);
  const runs = runl.flat();
  const sluglar = dir.filter((d) => d.type === "dir" && QUIZ_ON.some((o) => d.name.startsWith(o))).map((d) => d.name);
  const liste = await Promise.all(sluglar.map(async (slug) => {
    const sc = (await readJson(`projects/${slug}/script.json`).catch(() => null)) || {};
    const format = QTUM.includes(sc.format) ? sc.format : qFmtSlug(slug);
    const soru = Array.isArray(sc.sorular) && sc.sorular.length ? sc.sorular.length : Math.max(0, (sc.alt_bilgi && typeof sc.alt_bilgi === "object" ? Object.keys(sc.alt_bilgi).length : 0) || (sc.sahneler || []).filter((x) => / harfi\. /.test((x.lines || [])[0] || "")).length);
    const R = rels.find((r) => r.tag_name === `video-${slug}`), a = (n) => R?.assets?.find((x) => x.name === n);
    const run = runs.filter((r) => (r.display_title || "").endsWith(`· ${slug}`) || r.display_title === slug).sort((x, y) => new Date(y.created_at) - new Date(x.created_at))[0];
    const o = { slug, format, format_ad: QSEMA[format]?.ad || format, baslik: sc.baslik || slug, soru, tema: sc.tema === "spor" || /-spor(-|$)/.test(slug) ? "spor" : "tarih",
      workflow: qWfKey(format), release: !!R, mp4: a("video.mp4")?.browser_download_url || null, kapak: a("kapak.jpg")?.browser_download_url || null, zaman: R?.published_at || null, run: null,
      aciklama: sc.aciklama || "", hashtagler: sc.hashtagler || "", sabit_yorum: sc.sabit_yorum || "" };
    if (run) {
      o.run = { id: run.id, status: run.status, conclusion: run.conclusion, started: run.run_started_at || run.created_at, updated: run.updated_at, url: run.html_url };
      const yeni = !R || new Date(run.created_at) > new Date(R.published_at);
      if (yeni && (run.status !== "completed" || run.conclusion === "failure")) {
        const jobs = (await ghJson(`/repos/${REPO}/actions/runs/${run.id}/jobs`).catch(() => ({}))).jobs || [], j = jobs[0];
        if (j) {
          const st = j.steps || [], cur = st.findIndex((x) => x.status === "in_progress");
          o.run.adim = cur >= 0 ? st[cur].name : null; o.run.adim_no = cur >= 0 ? cur + 1 : st.filter((x) => x.status === "completed").length; o.run.adim_top = st.length;
          if (run.conclusion === "failure") {
            o.run.hata_adim = st.find((x) => x.conclusion === "failure")?.name || null;
            const lg = await gh(`/repos/${REPO}/actions/jobs/${j.id}/logs`).catch(() => null);
            o.run.hata = lg?.ok ? qHataOzet((await lg.text()).slice(-200000)) : [];
          }
        }
      }
    }
    return o;
  }));
  const t = (x) => new Date(x.run?.updated || x.zaman || 0).getTime();
  liste.sort((x, y) => t(y) - t(x));
  qListeOnbellek = { t: Date.now(), v: liste }; return liste;
}
export default async (req) => {
  if (req.method !== "POST") return json({ hata: "POST gerekli" }, 405);
  let b = {};
  try { b = await req.json(); } catch {}
  if (b.action === "login") {
    const now = Date.now(); failed = failed.filter((t) => now - t < 15 * 60e3);
    if (failed.length >= 10) return json({ hata: "Çok fazla yanlış deneme. 15 dakika sonra tekrar dene." }, 429);
    if (!process.env.PANEL_SIFRE) return json({ hata: "PANEL_SIFRE Netlify'da tanımlı değil ya da yayın yenilenmedi" }, 500);
    if (!same(String(b.sifre || "").trim(), process.env.PANEL_SIFRE.trim())) { failed.push(now); return json({ hata: "Şifre yanlış" }, 401); }
    return json({ token: token() });
  }
  if ((b.action === "olay" || b.action === "bildirim") && req.headers.get("x-gh-token")) { // ajanlardan canlı olay: GitHub Actions anahtarı bu repoya erişebiliyor mu?
    const t = req.headers.get("x-gh-token"); const k = crypto.createHash("sha256").update(t).digest("hex");
    if (!(gecerliGh.get(k) > Date.now())) {
      const r = await fetch(`${GH}/repos/${REPO}`, { headers: { authorization: `Bearer ${t}`, accept: "application/vnd.github+json" } });
      if (!r.ok) return json({ hata: "Yetkisiz" }, 401);
      gecerliGh.set(k, Date.now() + 10 * 60e3);
    }
    if (b.bildirim) { // ajan: "video hazır" gibi telefona bildirim
      const sl = validSlug(b.slug) ? b.slug : null; const ad = sl ? (await basliklar([sl]))[sl] || sl : "";
      try { return json({ ok: true, n: await bildirimGonder(b.bildirim.baslik || "Animasyon Tarih", (b.bildirim.metin || "").replace("{ad}", ad), sl ? `/#p=${encodeURIComponent(sl)}` : "/") }); }
      catch (e) { return json({ hata: String(e.message || e) }, 500); }
    }
    if (!Array.isArray(b.olaylar)) return json({ hata: "Olay yok" }, 400);
    try { return json({ ok: true, n: await olayEkle(b.slug, b.olaylar) }); } catch (e) { return json({ hata: String(e.message || e) }, 500); }
  }
  if (!same(req.headers.get("x-panel-token") || "", token())) return json({ hata: "Giriş gerekli" }, 401);
  if (!process.env.GITHUB_TOKEN) return json({ hata: "GITHUB_TOKEN tanımlı değil (Netlify > Site settings > Environment variables)" }, 500);

  try {
    switch (b.action) {
      case "overview": {
        const [status, usage, report, list, analiz, yorumlar, instagram] = await Promise.all([
          readJson("data/status.json"), readJson("data/usage.json"), readJson("reports/latest.json"),
          gh(`/repos/${REPO}/contents/projects`).then((r) => (r.ok ? r.json() : [])),
          readJson("data/analiz.json"), readJson("data/yorumlar.json"), readJson("data/instagram.json"),
        ]);
        const igMeta = await igStore().get("meta", { type: "json" }).catch(() => null);
        const [igFormat, formatKurallari, haftalik, kuyruk, igGecmis] = await Promise.all([igStore().get("format", { type: "json" }).catch(() => null),
          readJson("data/format_kurallari.json"), readJson("data/haftalik_rapor.json"), readJson("data/yayin_kuyrugu.json"), readJson("data/ig_media_gecmis.json")]);
        const runs = {};
        await Promise.all(Object.entries(WORKFLOWS).map(async ([k, f]) => {
          const r = await gh(`/repos/${REPO}/actions/workflows/${f}/runs?per_page=1`);
          const run = r.ok ? (await r.json()).workflow_runs?.[0] : null;
          runs[k] = run ? { durum: run.status, sonuc: run.conclusion, zaman: run.updated_at, url: run.html_url } : null;
        }));
        const ay = new Date().toISOString().slice(0, 7);
        const kayit = usage?.kayitlar || [];
        const aylik = kayit.filter((x) => x.zaman.startsWith(ay)).reduce((s, x) => s + x.usd, 0);
        const servis = {};
        kayit.filter((x) => x.zaman.startsWith(ay)).forEach((x) => (servis[x.servis] = (servis[x.servis] || 0) + x.usd));
        const projeler = (list || []).filter((x) => x.type === "dir").map((x) => x.name);
        return json({ status: status || {}, runs, report, projeler, basliklar: await basliklar(projeler).catch(() => ({})), instagram, igToken: igMeta ? { kayitli: true, zaman: igMeta.zaman, son4: igMeta.son4 } : null, igFormat: igFormat || {}, igGecmis, formatKurallari, haftalik,
          kuyruk: (kuyruk?.isler || []).slice(-60), arsiv: ((await getStore({ name: "ayar", consistency: "strong" }).get("arsiv", { type: "json" })) || []).filter((x) => projeler.includes(x)), analiz,
          yorumlar: { bekleyen: (yorumlar?.yorumlar || []).filter((y) => y.durum === "yeni").slice(0, 40), fikirler: (yorumlar?.fikirler || []).slice(-8).reverse() },
          harcama: { aylik, servis, butce: Number(process.env.AYLIK_BUTCE_USD || 15), son: kayit.slice(-8).reverse() } });
      }
      case "project": {
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        const [script, project, imgs, files, rel, yayinlar, kuyruk, timed, ...kontrol] = await Promise.all([
          readJson(`projects/${b.slug}/script.json`), readJson(`projects/${b.slug}/project.json`),
          gh(`/repos/${REPO}/contents/projects/${b.slug}/images`).then((r) => (r.ok ? r.json() : [])),
          gh(`/repos/${REPO}/contents/projects/${b.slug}`).then((r) => (r.ok ? r.json() : [])),
          gh(`/repos/${REPO}/releases/tags/video-${b.slug}`).then((r) => (r.ok ? r.json() : null)),
          readJson("data/yayinlar.json"), readJson("data/yayin_kuyrugu.json"),
          b.studyo ? readJson(`projects/${b.slug}/project.timed.json`) : null,
          ...["senaryo", "ses", "gorsel", "kurgu"].map((k) => readJson(`projects/${b.slug}/kontrol/${k}.json`)),
        ]);
        const asset = rel?.assets?.find((a) => a.name.endsWith(".mp4"));
        return json({ script, project, gorseller: (imgs || []).map((x) => x.name), dosyalar: (files || []).map((x) => x.name),
          video: asset ? { id: asset.id, boyut: asset.size, zaman: asset.updated_at } : null,
          kontrol: Object.fromEntries(["senaryo", "ses", "gorsel", "kurgu"].map((k, i) => [k, kontrol[i]])),
          timed, yayin: yayinlar?.[b.slug] || {}, plan: (kuyruk?.isler || []).filter((x) => x.slug === b.slug).slice(-5) });
      }
      case "file": { // görsel / ses önizleme (en fazla ~4 MB)
        if (!/^projects\/[a-z0-9-]+\/[\w./-]+\.(jpg|jpeg|png|wav|mp3)$/.test(b.path || "") || b.path.includes("..")) return json({ hata: "Geçersiz dosya" }, 400);
        const r = await gh(`/repos/${REPO}/contents/${b.path}`, { accept: "application/vnd.github.raw" });
        if (!r.ok) return json({ hata: "Dosya yok" }, 404);
        const ext = b.path.split(".").pop();
        const type = { jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", wav: "audio/wav", mp3: "audio/mpeg" }[ext];
        return new Response(await r.arrayBuffer(), { headers: { "content-type": type, "cache-control": "private, max-age=300" } });
      }
      case "video_url": { // GitHub'ın kısa süreli imzalı indirme adresini döndürür
        const r = await gh(`/repos/${REPO}/releases/assets/${Number(b.id)}`, { accept: "application/octet-stream", redirect: "manual" });
        const loc = r.headers.get("location");
        return loc ? json({ url: loc }) : json({ hata: "Video adresi alınamadı" }, 500);
      }
      case "ig_token": { // Instagram token'ını GitHub Actions secret'ı (IG_TOKEN) olarak kaydet; token asla loglanmaz/geri döndürülmez
        const tok = String(b.token || "").trim();
        if (tok.length < 20 || tok.length > 1000 || /\s/.test(tok)) return json({ hata: "Geçersiz token" }, 400);
        const izinYok = () => json({ hata: "GitHub anahtarına 'Secrets: Read and write' izni eklenmeli", izin: true }, 403);
        const kr = await gh(`/repos/${REPO}/actions/secrets/public-key`);
        if (kr.status === 403 || kr.status === 404) return izinYok();
        if (!kr.ok) return json({ hata: `GitHub ${kr.status}` }, 502);
        const { key, key_id } = await kr.json();
        const sodium = (await import("tweetsodium")).default;
        const enc = Buffer.from(sodium.seal(Buffer.from(tok), Buffer.from(key, "base64"))).toString("base64");
        const pr = await gh(`/repos/${REPO}/actions/secrets/IG_TOKEN`, { method: "PUT", body: JSON.stringify({ encrypted_value: enc, key_id }) });
        if (pr.status === 403 || pr.status === 404) return izinYok();
        if (!pr.ok) return json({ hata: `GitHub ${pr.status}` }, 502);
        await igStore().set("tok", igSifrele(tok)); await igStore().setJSON("meta", { zaman: new Date().toISOString(), son4: tok.slice(-4) });
        await dispatch("instagram");
        return json({ ok: true, igToken: { kayitli: true, zaman: new Date().toISOString(), son4: tok.slice(-4) } });
      }
      case "ig_refresh": { // hızlı yenileme: Blobs'taki token ile doğrudan Graph API; token yoksa GitHub workflow'u tetiklenir
        const enc = await igStore().get("tok").catch(() => null); let tok = null;
        if (enc) try { tok = igCoz(enc); } catch { tok = null; }
        if (!tok) { await dispatch("instagram"); return json({ ok: true, yedek: true }); }
        return json({ ok: true, instagram: await igRefresh(tok, await readJson("data/instagram.json")) });
      }
      case "ig_live": { // canlı panel: her tikte 2 çağrı (takipçi + son 5 medya); detay=1 iken (istemci en fazla 60 sn'de bir) son 5'in izlenmesi + son ~10 yorum
        const tok = await igTok(); if (!tok) return json({ hata: "Kayıtlı Instagram token'ı yok; önce token'ı kaydet" }, 400);
        try {
          const [hes, md] = await Promise.all([igCagir(tok, "GET", IG_UID(), { fields: "followers_count,username" }),
            igCagir(tok, "GET", `${IG_UID()}/media`, { fields: "id,caption,timestamp,thumbnail_url,media_url,like_count,comments_count", limit: 5 })]);
          const medya = (md.data || []).slice(0, 5); let yorumlar = null;
          if (b.detay) { yorumlar = [];
            await Promise.all(medya.map(async (m) => {
              try { const r = await igCagir(tok, "GET", `${m.id}/insights`, { metric: "views" }); m.views = r.data?.[0]?.values?.[0]?.value ?? r.data?.[0]?.total_value?.value ?? null; } catch {}
              if (m.comments_count > 0) try { const c = await igCagir(tok, "GET", `${m.id}/comments`, { fields: "id,text,username,timestamp", limit: 10 });
                for (const y of c.data || []) if (y.username !== hes.username) yorumlar.push({ id: y.id, kullanici: y.username, metin: y.text, zaman: y.timestamp, medya_id: m.id }); } catch {}
            }));
            yorumlar.sort((x, y) => String(y.zaman).localeCompare(String(x.zaman))); yorumlar = yorumlar.slice(0, 10); }
          return json({ ok: true, zaman: new Date().toISOString(), followers_count: hes.followers_count,
            medya: medya.map((m) => ({ id: m.id, baslik: (m.caption || "").trim().split("\n")[0].slice(0, 60), zaman: m.timestamp, kapak: m.thumbnail_url || m.media_url || null, like_count: m.like_count ?? null, comments_count: m.comments_count ?? null, views: m.views ?? null })),
            yorumlar });
        } catch (e) { const kod = +(String(e.message).match(/\[kod (\d+)\]/)?.[1] || 0); return json({ hata: String(e.message || e), kod, sinir: [4, 17, 32, 613].includes(kod) }, [4, 17, 32, 613].includes(kod) ? 429 : 502); }
      }
      case "run": { // ajanı çalıştır
        if (!WORKFLOWS[b.agent]) return json({ hata: "Bilinmeyen ajan" }, 400);
        const inputs = {};
        for (const [k, v] of Object.entries(b.inputs || {})) inputs[k] = String(v).slice(0, 300);
        if (inputs.slug && !validSlug(inputs.slug)) return json({ hata: "Geçersiz proje" }, 400);
        if (b.agent === "kontrol" && (!inputs.slug || !ASAMALAR.includes(inputs.asama || "hepsi"))) return json({ hata: "Geçersiz kontrol isteği" }, 400);
        if (b.agent === "yorumcu" && inputs.mod && !["topla", "gonder"].includes(inputs.mod)) return json({ hata: "Geçersiz mod" }, 400);
        await dispatch(b.agent, inputs);
        return json({ ok: true });
      }
      case "komut": { // "Ajana yaz": serbest mesaj → yönetici ajan
        const mesaj = String(b.mesaj || "").trim().slice(0, 1500);
        if (mesaj.length < 2) return json({ hata: "Mesaj boş" }, 400);
        if (b.slug && !validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        await dispatch("yonetici", { mesaj, slug: b.slug || "" });
        return json({ ok: true });
      }
      case "duzelt": { // kontrolcünün / ajanın bulduğu hatayı yönetici ajana düzelttir
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        const M = (Array.isArray(b.maddeler) ? b.maddeler : []).slice(0, 12)
          .map((m) => `- [${String(m.asama || "genel").slice(0, 12)}]${Number(m.sahne) ? ` sahne ${Number(m.sahne)}:` : ""} ${String(m.mesaj || "").slice(0, 300)}`);
        if (!M.length) return json({ hata: "Düzeltilecek madde yok" }, 400);
        await dispatch("yonetici", { mesaj: `[DÜZELT] Kontrolcülerin bulduğu şu sorunları düzelt, sonra gerekiyorsa yeniden üret ve kontrol ettir:\n${M.join("\n")}`.slice(0, 1500), slug: b.slug });
        return json({ ok: true });
      }
      case "ajan_detay": { // ajanın son çalışmaları + açık/devre dışı durumu
        const wf = WORKFLOWS[b.k]; if (!wf || b.k === "sil") return json({ hata: "Bilinmeyen ajan" }, 400);
        const [w, r] = await Promise.all([ghJson(`/repos/${REPO}/actions/workflows/${wf}`), ghJson(`/repos/${REPO}/actions/workflows/${wf}/runs?per_page=15`)]);
        return json({ aktif: w.state === "active", calismalar: (r.workflow_runs || []).map((x) => ({ id: x.id, durum: x.status, sonuc: x.conclusion, zaman: x.created_at, sure: Math.max(0, Math.round((new Date(x.updated_at) - new Date(x.run_started_at || x.created_at)) / 1000)), url: x.html_url })) });
      }
      case "ajan_durdur": { // çalışan ya da sırada bekleyen işlerini iptal et
        const wf = WORKFLOWS[b.k]; if (!wf) return json({ hata: "Bilinmeyen ajan" }, 400);
        const r = await ghJson(`/repos/${REPO}/actions/workflows/${wf}/runs?per_page=20`);
        const canli = (r.workflow_runs || []).filter((x) => x.status !== "completed");
        await Promise.all(canli.map((x) => gh(`/repos/${REPO}/actions/runs/${x.id}/cancel`, { method: "POST" })));
        return json({ ok: true, n: canli.length });
      }
      case "ajan_mod": { // devre dışı bırak / yeniden aç (zamanlanmış çalışmalar da durur)
        const wf = WORKFLOWS[b.k]; if (!wf || b.k === "sil") return json({ hata: "Bilinmeyen ajan" }, 400);
        const r = await gh(`/repos/${REPO}/actions/workflows/${wf}/${b.aktif ? "enable" : "disable"}`, { method: "PUT" });
        if (!r.ok) return json({ hata: `GitHub ${r.status}: anahtarın 'Actions: write' yetkisi olmalı` }, 400);
        return json({ ok: true, aktif: !!b.aktif });
      }
      case "ajan_kayit_sil": { // çalışma kaydını sil: id varsa tek kayıt, yoksa bitmiş kayıtların hepsi (proje dosyalarına dokunmaz)
        const wf = WORKFLOWS[b.k]; if (!wf) return json({ hata: "Bilinmeyen ajan" }, 400);
        const r = await ghJson(`/repos/${REPO}/actions/workflows/${wf}/runs?per_page=30`);
        const hedef = (r.workflow_runs || []).filter((x) => x.status === "completed" && (!b.id || String(x.id) === String(b.id)));
        const s = await Promise.all(hedef.map((x) => gh(`/repos/${REPO}/actions/runs/${x.id}`, { method: "DELETE" })));
        return json({ ok: true, n: s.filter((x) => x.ok).length });
      }
      case "ayar": { // proje ayarı: film filtresi (sade = filtre kapalı)
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        for (const f of ["script.json", "project.json"]) {
          const j = await readJson(`projects/${b.slug}/${f}`); if (!j) continue;
          if (b.sade) j.sade = true; else delete j.sade;
          await writeFile(`projects/${b.slug}/${f}`, b64(j), `Film filtresi ${b.sade ? "kapatıldı" : "açıldı"}: ${b.slug}`);
        }
        return json({ ok: true, sade: !!b.sade });
      }
      case "sil": { // panelden silme: video = sadece hazır video, hepsi = projeyi tamamen
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        if (!["video", "hepsi"].includes(b.tur)) return json({ hata: "Geçersiz silme türü" }, 400);
        if (b.onay !== b.slug) return json({ hata: "Onay tutmadı" }, 400);
        await dispatch("sil", { slug: b.slug, tur: b.tur });
        return json({ ok: true });
      }
      case "arsiv": { // bitmiş videoyu arşive at / arşivden çıkar (hiçbir dosya silinmez)
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        const st = getStore({ name: "ayar", consistency: "strong" }); let A = (await st.get("arsiv", { type: "json" })) || [];
        if (Array.isArray(b.liste)) A = [...new Set([...b.liste.filter(validSlug), ...A])]; // panelin bildiği tam liste (hızlı art arda basınca kaybolmasın)
        A = A.filter((x) => x !== b.slug); if (!b.cikar) A.unshift(b.slug);
        await st.setJSON("arsiv", A); return json({ ok: true, arsiv: A });
      }
      case "push_anahtar": return json({ anahtar: (await vapid()).publicKey });
      case "push_abone": { // bu cihazı bildirim listesine ekle / çıkar
        const a = b.abonelik; if (!a?.endpoint || !/^https:\/\//.test(a.endpoint) || !a.keys?.p256dh || !a.keys?.auth) return json({ hata: "Geçersiz abonelik" }, 400);
        const st = getStore({ name: "ayar", consistency: "strong" }); let A = (await st.get("abonelikler", { type: "json" })) || [];
        A = A.filter((x) => x.endpoint !== a.endpoint); if (!b.cik) A.push({ endpoint: a.endpoint, keys: { p256dh: a.keys.p256dh, auth: a.keys.auth } });
        await st.setJSON("abonelikler", A.slice(-10));
        if (!b.cik) await bildirimGonder("🔔 Bildirimler açık", "Video bitince, hata çıkınca buraya haber gelecek.");
        return json({ ok: true });
      }
      case "komut_gecmis": {
        const g = (await readJson("data/yonetici.json")) || { mesajlar: [] };
        return json({ mesajlar: (g.mesajlar || []).slice(-20), durum: (await readJson("data/status.json"))?.yonetici || null });
      }
      case "save_text": { // onaydan önce paneldeki metin düzenlemelerini kaydet
        if (!validSlug(b.slug) || !Array.isArray(b.sahneler)) return json({ hata: "Geçersiz istek" }, 400);
        const sc = await readJson(`projects/${b.slug}/script.json`);
        if (!sc || sc.durum === "onaylandi") return json({ hata: "Onaylanmış metin düzenlenemez" }, 400);
        if (b.sahneler.length !== sc.sahneler.length) return json({ hata: "Sahne sayısı değişemez" }, 400);
        const clean = b.sahneler.map((l) => (Array.isArray(l) ? l : []).map((x) => String(x).trim().slice(0, 400)).filter(Boolean).slice(0, 6));
        if (clean.some((l) => !l.length)) return json({ hata: "Her sahnede en az bir cümle olmalı" }, 400);
        clean.forEach((l, i) => (sc.sahneler[i].lines = l));
        sc.seslendirme_metni = clean.flat().join("\n");
        const pj = await readJson(`projects/${b.slug}/project.json`);
        if (pj?.scenes) clean.forEach((l, i) => { if (pj.scenes[i]) { pj.scenes[i].lines = l; pj.scenes[i].start = null; pj.scenes[i].end = null; } });
        await writeFile(`projects/${b.slug}/script.json`, Buffer.from(JSON.stringify(sc, null, 1)).toString("base64"), `Metin düzenlendi: ${b.slug}`);
        if (sc.baslik) await baslikYaz(b.slug, sc.baslik).catch(() => {});
        if (pj) await writeFile(`projects/${b.slug}/project.json`, Buffer.from(JSON.stringify(pj, null, 1)).toString("base64"), `Sahne metinleri: ${b.slug}`);
        await dispatch("kontrol", { slug: b.slug, asama: "senaryo" }).catch(() => {});
        return json({ ok: true });
      }
      case "approve": { // metni onayla → görsel/ses üretimini başlat
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        const sc = await readJson(`projects/${b.slug}/script.json`);
        sc.durum = "onaylandi";
        await writeFile(`projects/${b.slug}/script.json`, Buffer.from(JSON.stringify(sc, null, 1)).toString("base64"), `Metin onaylandı: ${b.slug}`);
        if (b.uret !== false) await dispatch("gorsel", { slug: b.slug });
        return json({ ok: true });
      }
      case "upload": { // Gemini bağlı değilken görsel/ses elle yükleme
        if (!validSlug(b.slug) || !/^(images\/s\d{2}\.jpg|ses\.wav)$/.test(b.name || "")) return json({ hata: "Geçersiz dosya adı" }, 400);
        await writeFile(`projects/${b.slug}/${b.name}`, b.base64, `Yükleme: ${b.slug}/${b.name}`);
        return json({ ok: true });
      }
      case "decide": { // haftalık rapordaki konuya Yap / Geç
        const rep = await readJson("reports/latest.json");
        let hedef = null;
        for (const g of rep.gunler || []) for (const o of g.olaylar || []) if (o.baslik === b.baslik) { o.durum = b.karar; hedef = { ...o, tarih: g.tarih }; }
        if (rep.savas_onerisi?.baslik === b.baslik) { rep.savas_onerisi.durum = b.karar; hedef = rep.savas_onerisi; }
        await writeFile("reports/latest.json", Buffer.from(JSON.stringify(rep, null, 1)).toString("base64"), `Karar: ${b.karar} · ${b.baslik}`);
        if (b.karar === "yap" && hedef && b.api) await dispatch("senarist", { konu: `${hedef.baslik} (${hedef.yil || ""})`, tarih: hedef.tarih || "", notlar: hedef.ozet || "" });
        return json({ ok: true });
      }
      case "quiz_taslak": { // Quiz Stüdyo 'Ajan hazırlasın': Netlify'da anahtar varsa doğrudan Gemini, yoksa quiz_taslak.yml
        if (!QTUM.includes(b.format)) return json({ hata: "Format seçilmedi" }, 400);
        const konu = String(b.konu || "").trim().slice(0, 200); if (konu.length < 3) return json({ hata: "Konu yaz" }, 400);
        const adet = Math.max(6, Math.min(b.format === "her-harfe" ? 29 : 15, Number(b.adet) || 10)); const k = b.karisim || {};
        let kar = { kolay: Number(k.kolay) || 0, orta: Number(k.orta) || 0, zor: Number(k.zor) || 0 };
        if (kar.kolay + kar.orta + kar.zor !== adet) kar = { kolay: Math.round(adet * 0.4), zor: Math.round(adet * 0.2) }, kar.orta = adet - kar.kolay - kar.zor;
        const tema = b.tema === "spor" ? "spor" : "tarih";
        if (process.env.GEMINI_API_KEY && !b.yedek) {
          try { const j = await gemini(quizIstem(b.format, konu, adet, kar, tema)); return json({ ok: true, durum: "hazir", sorular: j.sorular || [], dogrulama_gerekli: true }); }
          catch (e) { /* zaman aşımı ya da kota: GitHub yedeğine düş */ }
        }
        const id = `${Date.now().toString(36)}-${crypto.randomBytes(3).toString("hex")}`;
        await dispatch("quiz-taslak", { id, format: b.format, konu, adet: String(adet), kolay: String(kar.kolay), orta: String(kar.orta), zor: String(kar.zor), tema });
        return json({ ok: true, durum: "bekliyor", id });
      }
      case "quiz_dogrula": { // taslağın ikinci geçişi: Google aramalı doğruluk kontrolü (Netlify'dan)
        if (!QTUM.includes(b.format) || !Array.isArray(b.sorular)) return json({ hata: "Geçersiz taslak" }, 400);
        try { const j = await gemini(quizKontrolIstem(b.format, b.sorular.slice(0, 29)), { arama: true, ms: 9500 }); return json({ ok: true, sorular: j.sorular || b.sorular, notlar: j.notlar || [] }); }
        catch (e) { return json({ ok: false, sorular: b.sorular, notlar: [`Doğruluk kontrolü yapılamadı (${e.message}); soruları elle kontrol et`] }); }
      }
      case "quiz_ayir": { // "Toplu soru ekle": yerel ayrıştırıcı emin olamazsa metni Gemini formatın şemasına çevirir, eksik alanları taslaklar
        if (!QTUM.includes(b.format)) return json({ hata: "Format seçilmedi" }, 400);
        const metin = String(b.metin || "").trim().slice(0, 12000); if (metin.length < 5) return json({ hata: "Metin boş" }, 400);
        try { const j = await gemini(quizAyirIstem(b.format, metin, b.yerel, b.tema), { ms: 9500 }); return json({ ok: true, sorular: j.sorular || [], notlar: j.notlar || [] }); }
        catch (e) { return json({ ok: false, hata: `Gemini ile ayrılamadı (${e.message})` }); }
      }
      case "quiz_taslak_durum": {
        if (!/^[a-z0-9-]{4,40}$/.test(b.id || "")) return json({ hata: "Geçersiz id" }, 400);
        const j = await readJson(`projects/_taslak/${b.id}.json`); return json(j || { durum: "bekliyor" });
      }
      case "quiz_uret": { // onaylanan sorular -> projects/<format>-<n>/script.json (+ görseller) -> quiz_studyo.yml
        const fmt = b.format; if (!QTUM.includes(fmt)) return json({ hata: "Format seçilmedi" }, 400);
        const Q = Array.isArray(b.sorular) ? b.sorular : [], ust = fmt === "her-harfe" ? 29 : 15; if (Q.length < 6 || Q.length > ust) return json({ hata: `6-${ust} soru olmalı` }, 400);
        const tema = b.tema === "spor" ? "spor" : "tarih";
        const giris = String(b.giris ?? "").replace(/\s+/g, " ").trim(); if (b.giris !== undefined && (!giris || giris.length > 180)) return json({ hata: "Giriş cümlesi boş olamaz / en fazla 180 karakter" }, 400);
        if (QSEMA[fmt].eski) { // Her Harfe -> quiz.yml, Harflerden Bul -> harf_bul.yml (mevcut script.json şemaları)
          const slug = await quizSiradaki(fmt === "her-harfe" ? `her-harfe-${tema}` : tema === "spor" ? "harflerden-bul-spor" : "harflerden-bul");
          const n = slug.split("-").pop(), sc = await quizEskiScript(fmt, slug, tema, Q, b.baslik, n, giris);
          if (sc.hata) return json({ hata: sc.hata }, 400);
          await writeFile(`projects/${slug}/script.json`, b64(sc), `Quiz Stüdyo: ${slug} (panelden onaylandı)`);
          await baslikYaz(slug, sc.baslik).catch(() => {});
          if (b.ses_harici) return json({ ok: true, slug, ses_bekliyor: true }); // dis ses: workflow, ses yüklenince quiz_ses_yukle'den başlar
          await dispatch(QSEMA[fmt].workflow, { slug }); // "quiz" -> quiz.yml, "harf-bul" -> harf_bul.yml
          return json({ ok: true, slug });
        }
        const slug = await quizSiradaki(fmt);
        const hex = (x) => (/^#[0-9a-fA-F]{6}$/.test(x || "") ? x : undefined);
        const sc = { slug, format: fmt, tema, baslik: String(b.baslik || QSEMA[fmt].ad).slice(0, 80), sorular: Q, durum: "uretiliyor", kaynak: "panel", ...(giris ? { giris } : {}) };
        if (tema === "spor" && (hex(b.takim?.ana) || hex(b.takim?.ikinci))) sc.takim = { ana: hex(b.takim?.ana), ikinci: hex(b.takim?.ikinci) };
        const resim = async (ad, b64) => { if (!b64 || b64.length > 4.5e6) return null; await writeFile(`projects/${slug}/images/${ad}`, b64, `Quiz Stüdyo görsel: ${slug}/${ad}`); return `images/${ad}`; };
        if (b.logo) sc.logo = await resim("logo.png", b.logo);
        if (b.arkaplan_mod === "yukle" && b.arka) sc.arkaplan = await resim("arka.jpg", b.arka);
        if (b.arkaplan_mod === "gemini") sc.arkaplan_uret = String(b.arkaplan_prompt || `${QSEMA[fmt].ad} quiz background, ${tema === "spor" ? "stadium at night" : "historical scene"}`).slice(0, 300);
        for (const [i, g] of Object.entries(b.gorseller || {})) { // soru görselleri: bu-kim portre, hangisi-once kart resmi
          const q = Q[+i]; if (!q) continue;
          if (fmt === "bu-kim") q.gorsel = await resim(`s${+i + 1}.jpg`, g);
          if (fmt === "hangisi-once") for (const L of ["a", "b"]) if (g[L]) q[L].gorsel = await resim(`s${+i + 1}${L}.jpg`, g[L]);
        }
        await writeFile(`projects/${slug}/script.json`, b64(sc), `Quiz Stüdyo: ${slug} (panelden onaylandı)`);
        await baslikYaz(slug, sc.baslik).catch(() => {});
        if (b.ses_harici) return json({ ok: true, slug, ses_bekliyor: true });
        await dispatch("quiz-studyo", { slug });
        return json({ ok: true, slug });
      }
      case "quiz_ses_yukle": { // dis ses (ElevenLabs vb.): <=4 MB parçalar halinde projects/<slug>/ses_harici.<ext>[.partNN]; son parçada workflow başlar
        const ext = String(b.ext || "").toLowerCase(), i = Number(b.i), n = Number(b.n);
        if (!validSlug(b.slug) || !["mp3", "wav", "m4a"].includes(ext) || !(n >= 1 && n <= 8) || !(i >= 0 && i < n) || !b.base64 || b.base64.length > 4.5e6) return json({ hata: "Geçersiz ses parçası" }, 400);
        const ad = n === 1 ? `ses_harici.${ext}` : `ses_harici.${ext}.part${String(i).padStart(2, "0")}`;
        await writeFile(`projects/${b.slug}/${ad}`, b.base64, `Dış ses: ${b.slug}/${ad} (${i + 1}/${n})`);
        if (i < n - 1) return json({ ok: true, devam: true });
        const wf = /^her-harfe-/.test(b.slug) ? "quiz" : /^harflerden-bul/.test(b.slug) ? "harf-bul" : "quiz-studyo";
        await dispatch(wf, { slug: b.slug });
        return json({ ok: true, slug: b.slug });
      }
      case "quiz_liste": return json({ quizler: await quizListe() });
      case "quiz_tekrar": { // hatalı quizi yeniden başlat (ses=1 yok: mevcut ses kullanılır)
        if (!validSlug(b.slug) || !QUIZ_ON.some((o) => b.slug.startsWith(o))) return json({ hata: "Geçersiz proje" }, 400);
        const sc = (await readJson(`projects/${b.slug}/script.json`)) || {}, fmt = QTUM.includes(sc.format) ? sc.format : qFmtSlug(b.slug);
        await dispatch(qWfKey(fmt), { slug: b.slug }); qListeOnbellek.v = null; return json({ ok: true });
      }
      case "quiz_aciklama_kaydet": { // video detay: Instagram açıklama / hashtag / sabit yorum
        if (!validSlug(b.slug) || !QUIZ_ON.some((o) => b.slug.startsWith(o))) return json({ hata: "Geçersiz proje" }, 400);
        const sc = (await readJson(`projects/${b.slug}/script.json`)) || {};
        for (const k of ["aciklama", "hashtagler", "sabit_yorum"]) if (typeof b[k] === "string") sc[k] = b[k].slice(0, 2200);
        await writeFile(`projects/${b.slug}/script.json`, Buffer.from(JSON.stringify(sc, null, 1)).toString("base64"), `Açıklama düzenlendi: ${b.slug}`);
        qListeOnbellek.v = null; return json({ ok: true });
      }
      case "quiz_aciklama_gemini": {
        const n = Math.max(1, Math.min(99, +b.soru || 10)), spor = b.tema === "spor";
        try { const j = await gemini(`Türkçe bir Instagram ${spor ? "spor" : "tarih"} quiz Reels'i (${String(b.format_ad || "quiz").slice(0, 60)}, ${n} soru) için açıklama yaz. Ton: samimi, esprili, takipçiyle konuşur gibi; yapay zeka gibi durmasın; videonun içeriğini/sorularını ÖZETLEME. Kısa paragraflar, birkaç emoji, sonunda puanı yorumlara yazmaya çağır. Örnek stil: "Geçen quiz çok kolay dediniz, bu sefer zorlaştırdık 😏\n\n22 harf, 22 tarih sorusu. Bakalım bu sefer kaç tane bileceksin? 🤔\nVideoyu durdurmak yok, puanını yorumlara yaz 👇\n\n22'de 22 yapan gerçek tarih kurdu 🏆". Hashtag'leri açıklamaya koyma. Sadece JSON: {"aciklama":"...","hashtagler":"#.. #..","sabit_yorum":"..."}`);
          return json({ ok: true, aciklama: String(j.aciklama || ""), hashtagler: String(j.hashtagler || ""), sabit_yorum: String(j.sabit_yorum || "") }); }
        catch (e) { return json({ hata: String(e.message || e) }, 500); }
      }
      case "quiz_durum": { // release varsa video + kapak, yoksa son quiz_studyo koşusu
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        const rel = await gh(`/repos/${REPO}/releases/tags/video-${b.slug}`);
        if (rel.ok) { const R = await rel.json(); const a = (n) => R.assets.find((x) => x.name === n); if (a("video.mp4")) return json({ durum: "hazir", video_id: a("video.mp4").id, kapak: a("kapak.jpg")?.browser_download_url }); }
        const runs = await ghJson(`/repos/${REPO}/actions/workflows/quiz_studyo.yml/runs?per_page=10`);
        const r = (runs.workflow_runs || []).find((x) => (x.display_title || "").includes(b.slug)) || (runs.workflow_runs || [])[0];
        return json({ durum: r ? (r.status === "completed" ? (r.conclusion === "success" ? "bitti" : "hata") : "calisiyor") : "bekliyor", url: r?.html_url });
      }
      case "olay": { // panelden (senin) olayların: ör. toplu görsel yükleme
        if (b.bildirim) { // ajan: "video hazır" gibi telefona bildirim
      const sl = validSlug(b.slug) ? b.slug : null; const ad = sl ? (await basliklar([sl]))[sl] || sl : "";
      try { return json({ ok: true, n: await bildirimGonder(b.bildirim.baslik || "Animasyon Tarih", (b.bildirim.metin || "").replace("{ad}", ad), sl ? `/#p=${encodeURIComponent(sl)}` : "/") }); }
      catch (e) { return json({ hata: String(e.message || e) }, 500); }
    }
    if (!Array.isArray(b.olaylar)) return json({ hata: "Olay yok" }, 400);
        return json({ ok: true, n: await olayEkle(b.slug, b.olaylar.map((o) => ({ ...o, ajan: "sen" }))) });
      }
      case "onizleme": { // canlı stüdyo: ajanın az önce çizdiği görselin küçük hali
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        const d = await getStore("onizleme").get(`${b.slug}/${Number(b.sahne)}`);
        if (!d) return json({ hata: "Önizleme yok" }, 404);
        return new Response(Buffer.from(d, "base64"), { headers: { "content-type": "image/jpeg", "cache-control": "no-store" } });
      }
      case "olaylar": { // Kurgu Stüdyosu: belli bir sıradan sonraki olaylar
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        const cur = (await getStore("olaylar").get(b.slug, { type: "json" })) || { n: 0, liste: [] };
        const den = Number(b.den) || 0;
        return json({ n: cur.n, olaylar: cur.liste.filter((o) => o.i > den) });
      }
      case "save_caption": { // paylaşım açıklamasını düzenle
        if (!validSlug(b.slug) || typeof b.metin !== "string") return json({ hata: "Geçersiz istek" }, 400);
        const sc = await readJson(`projects/${b.slug}/script.json`);
        if (!sc) return json({ hata: "Metin yok" }, 404);
        sc.paylasim = b.metin.slice(0, 2200);
        await writeFile(`projects/${b.slug}/script.json`, b64(sc), `Paylaşım metni: ${b.slug}`);
        return json({ ok: true });
      }
      case "planla": { // Instagram paylaşımını ileri bir saate planla / düzenle (zamanlayıcı fonksiyon 10 dk'da bir bakar; yalnız buradan planlananlar paylaşılır)
        const url = String(b.url || "").trim(), kapakUrl = String(b.kapak_url || "").trim();
        if (!validSlug(b.slug) && !url) return json({ hata: "Video seç ya da adres gir" }, 400);
        if (url && !/^https:\/\/\S{8,800}$/.test(url)) return json({ hata: "Geçersiz video adresi (https ile başlamalı)" }, 400);
        if (kapakUrl && !/^https:\/\/\S{8,800}$/.test(kapakUrl)) return json({ hata: "Geçersiz kapak adresi" }, 400);
        const t = new Date(b.zaman); const now = Date.now();
        if (isNaN(t) || t < now - 60e3 || t > now + 60 * 864e5) return json({ hata: "Geçersiz zaman (en fazla 60 gün sonrası)" }, 400);
        const q = (await readJson("data/yayin_kuyrugu.json")) || { isler: [] };
        const ayni24 = q.isler.filter((x) => x.id !== b.id && ["bekliyor", "gonderildi", "tamam"].includes(x.durum) && Math.abs(new Date(x.zaman) - t) < 864e5).length;
        if (ayni24 >= 25) return json({ hata: "Instagram 24 saatte en fazla 25 paylaşıma izin veriyor; başka bir saat seç" }, 400);
        const alan = { zaman: t.toISOString(), slug: validSlug(b.slug) ? b.slug : undefined, url: url || undefined, kapak_url: kapakUrl || undefined,
          kapak_ms: Number.isFinite(Number(b.kapak_ms)) && b.kapak_ms !== "" && b.kapak_ms !== null ? Math.max(0, Math.min(90000, Math.round(Number(b.kapak_ms)))) : undefined,
          caption: typeof b.caption === "string" ? b.caption.slice(0, 2200) : undefined, hashtag: typeof b.hashtag === "string" ? b.hashtag.slice(0, 600) : undefined,
          akis: b.akis === undefined ? undefined : b.akis !== false, ad: typeof b.ad === "string" ? b.ad.slice(0, 90) : undefined };
        if (b.id) { // düzenle: yalnız bekleyen iş
          const it = q.isler.find((x) => x.id === b.id && x.durum === "bekliyor"); if (!it) return json({ hata: "Plan bulunamadı ya da artık düzenlenemez" }, 404);
          for (const [k, v] of Object.entries(alan)) if (v === undefined) delete it[k]; else it[k] = v;
          it.mesaj = "Düzenlendi"; it.guncelleme = new Date().toISOString();
          await writeFile("data/yayin_kuyrugu.json", b64(q), `Plan düzenlendi → ${t.toISOString()}`); return json({ ok: true, id: b.id });
        }
        if (!url && q.isler.some((x) => x.slug === b.slug && !x.url && x.durum === "bekliyor")) return json({ hata: "Bu video için zaten bekleyen bir plan var" }, 400);
        const id = `${Date.now().toString(36)}-${crypto.randomBytes(3).toString("hex")}`;
        q.isler.push(JSON.parse(JSON.stringify({ id, platform: "instagram", ...alan, durum: "bekliyor", kaynak: "panel", olusturma: new Date().toISOString() })));
        q.isler = q.isler.slice(-100);
        await writeFile("data/yayin_kuyrugu.json", b64(q), `Plan: ${alan.slug || "video"} → ${t.toISOString()}`);
        return json({ ok: true, id });
      }
      case "ig_videolar": { // yayınlanabilir videolar: GitHub sürümleri video-*
        const r = await ghJson(`/repos/${REPO}/releases?per_page=100`);
        const v = (r || []).filter((x) => x.tag_name?.startsWith("video-")).map((x) => { const a = (x.assets || []).find((y) => y.name.endsWith(".mp4"));
          return a ? { slug: x.tag_name.slice(6), url: a.browser_download_url, boyut: a.size, zaman: a.updated_at } : null; }).filter(Boolean);
        const ad = await basliklar(v.map((x) => x.slug).filter(validSlug)).catch(() => ({}));
        v.forEach((x) => (x.ad = ad[x.slug] || x.slug)); return json({ videolar: v });
      }
      case "ig_format": { // video formatını elle değiştir ("" = otomatik)
        if (!/^\d{5,30}$/.test(String(b.id || ""))) return json({ hata: "Geçersiz video" }, 400);
        if (b.format && !FORMATLAR.includes(b.format)) return json({ hata: "Geçersiz format" }, 400);
        const F = (await igStore().get("format", { type: "json" }).catch(() => null)) || {};
        if (b.format) F[b.id] = b.format; else delete F[b.id];
        await igStore().setJSON("format", F); return json({ ok: true, igFormat: F });
      }
      case "ig_yorumlar": { // son ~20 gönderinin yorumları (canlı), cevaplanmamışları işaretle + cevap önerisi
        const tok = await igTok(); if (!tok) return json({ hata: "Kayıtlı Instagram token'ı yok; önce token'ı kaydet" }, 400);
        const ben = (await igCagir(tok, "GET", IG_UID(), { fields: "username" })).username;
        const medya = (await igCagir(tok, "GET", `${IG_UID()}/media`, { fields: "id,caption,thumbnail_url,media_url,media_type,permalink,comments_count", limit: 20 })).data || [];
        const liste = []; let hatali = 0;
        await Promise.all(medya.filter((m) => m.comments_count > 0).map(async (m) => {
          try { const c = await igCagir(tok, "GET", `${m.id}/comments`, { fields: "id,text,username,timestamp,like_count,hidden,replies{id,username,text,timestamp}", limit: 50 });
            for (const y of c.data || []) { if (y.username === ben) continue; const cev = (y.replies?.data || []).filter((r) => r.username === ben);
              liste.push({ id: y.id, metin: y.text, kullanici: y.username, zaman: y.timestamp, begeni: y.like_count, gizli: !!y.hidden, cevaplandi: cev.length > 0, cevap: cev[0]?.text || "",
                medya: { id: m.id, baslik: (m.caption || "").trim().split("\n")[0].slice(0, 80), kapak: m.thumbnail_url || (m.media_type === "IMAGE" ? m.media_url : null), url: m.permalink } }); }
          } catch { hatali++; } }));
        liste.sort((a, b2) => String(b2.zaman).localeCompare(String(a.zaman)));
        for (const y of liste) y.oneri = kuralOneri(y.metin, y.id);
        const ai = await geminiOneri(liste.filter((y) => !y.cevaplandi && !y.gizli).slice(0, 25)).catch(() => 0);
        return json({ ok: true, ben, yorumlar: liste.slice(0, 200), ai, hatali });
      }
      case "ig_medya_yorum": { // video detayı: tek videonun yorumları (beğeni sayısı + cevaplanmış mı); en fazla ~200
        if (!/^\d{5,30}$/.test(String(b.id || ""))) return json({ hata: "Geçersiz video" }, 400);
        const tok = await igTok(); if (!tok) return json({ hata: "Kayıtlı Instagram token'ı yok" }, 400);
        const ben = (await igCagir(tok, "GET", IG_UID(), { fields: "username" })).username, L = [];
        let yol = `${b.id}/comments`, p = { fields: "id,text,username,timestamp,like_count,replies{username}", limit: 50 };
        for (let i = 0; i < 4 && yol; i++) { const c = await igCagir(tok, "GET", yol, p);
          for (const y of c.data || []) if (y.username !== ben) L.push({ id: y.id, metin: String(y.text || "").slice(0, 300), kullanici: y.username, begeni: y.like_count ?? null, cevaplandi: (y.replies?.data || []).some((r) => r.username === ben) });
          const s = c.paging?.cursors?.after; if (!c.paging?.next || !s) break; p = { ...p, after: s }; }
        return json({ ok: true, yorumlar: L });
      }
      case "ig_degerlendir": { // "Gemini ile yorumla": metrik özetinden kısa değerlendirme; medya başına 1 gün Blobs önbelleği
        if (!/^\d{5,30}$/.test(String(b.id || ""))) return json({ hata: "Geçersiz video" }, 400);
        const st = igStore(), k = `deg-${b.id}`, c = await st.get(k, { type: "json" }).catch(() => null);
        if (c && Date.now() - c.t < 864e5 && !b.yenile) return json({ ok: true, metin: c.metin, zaman: c.t, onbellek: true });
        const istem = "Bir Türk tarih Instagram sayfasının (@animasyon.tarih) tek bir Reels videosunun verileri aşağıda. Sade, samimi, gündelik Türkçeyle (yapay zekâ gibi durmayan) 2-3 cümlelik değerlendirme ve 1-2 somut öneri yaz. Abartma, rakamlara dayan. Sadece JSON: {\"metin\": \"...\"}\n" + JSON.stringify(b.ozet || {}).slice(0, 3000);
        try { const j = await gemini(istem); const metin = String(j.metin || "").slice(0, 1200); if (!metin) throw new Error("boş cevap");
          await st.setJSON(k, { t: Date.now(), metin }); return json({ ok: true, metin, zaman: Date.now() }); }
        catch (e) { return json({ hata: e.message === "anahtar yok" ? "GEMINI_API_KEY tanımlı değil" : `Gemini yanıt vermedi (${e.message})` }, 502); }
      }
      case "ig_yanitla": case "ig_gizle": {
        if (!/^\d{5,30}$/.test(String(b.id || ""))) return json({ hata: "Geçersiz yorum" }, 400);
        const tok = await igTok(); if (!tok) return json({ hata: "Kayıtlı Instagram token'ı yok" }, 400);
        if (b.action === "ig_gizle") { await igCagir(tok, "POST", String(b.id), { hide: b.goster ? "false" : "true" }); return json({ ok: true }); }
        const m = String(b.mesaj || "").trim(); if (!m || m.length > 1000) return json({ hata: "Cevap boş ya da çok uzun" }, 400);
        const r = await igCagir(tok, "POST", `${b.id}/replies`, { message: m }); return json({ ok: true, id: r.id });
      }
      case "plan_iptal": {
        const q = (await readJson("data/yayin_kuyrugu.json")) || { isler: [] };
        const it = q.isler.find((x) => x.id === b.id && x.durum === "bekliyor");
        if (!it) return json({ hata: "Plan bulunamadı" }, 404);
        it.durum = "iptal"; it.guncelleme = new Date().toISOString();
        await writeFile("data/yayin_kuyrugu.json", b64(q), `Plan iptal: ${it.slug || "video"}`);
        return json({ ok: true });
      }
      case "yorum_karar": { // [{id, durum: onaylandi|gizle|gecildi, taslak}]
        if (!Array.isArray(b.kararlar) || !b.kararlar.length) return json({ hata: "Karar yok" }, 400);
        const db = (await readJson("data/yorumlar.json")) || { yorumlar: [] };
        let gonderilecek = 0;
        for (const k of b.kararlar.slice(0, 60)) {
          const y = db.yorumlar.find((x) => x.id === String(k.id));
          if (!y || !["onaylandi", "gizle", "gecildi"].includes(k.durum)) continue;
          y.durum = k.durum; if (typeof k.taslak === "string") y.taslak = k.taslak.slice(0, 1000);
          if (k.durum !== "gecildi") gonderilecek++;
        }
        await writeFile("data/yorumlar.json", b64(db), "Yorum kararları");
        if (gonderilecek) await dispatch("yorumcu", { mod: "gonder" });
        return json({ ok: true, gonderilecek });
      }
      default:
        return json({ hata: "Bilinmeyen işlem" }, 400);
    }
  } catch (e) {
    return json({ hata: String(e.message || e) }, 500);
  }
};

export const config = { path: "/api" };
