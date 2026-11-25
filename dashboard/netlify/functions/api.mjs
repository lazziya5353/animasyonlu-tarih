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
  const bugun = out.zaman.slice(0, 10);
  out.gecmis = [...out.gecmis.filter((g) => g.tarih !== bugun).slice(-365), { tarih: bugun, takipci: out.hesap.takipci }];
  const medya = ((await get(`${uid}/media`, { fields: "id,caption,media_type,media_product_type,permalink,thumbnail_url,media_url,timestamp,like_count,comments_count", limit: 50 })).data || []).slice(0, 50);
  const ist = async (id, met) => { try { const r = await get(`${id}/insights`, { metric: met.join(",") }); return Object.fromEntries((r.data || []).map((x) => [x.name, deger(x)])); } catch {}
    const o = {}; await Promise.all(met.map((m) => get(`${id}/insights`, { metric: m }).then((r) => (r.data || []).forEach((x) => (o[x.name] = deger(x)))).catch(() => yok.add(m)))); return o; };
  const liste = await Promise.all(medya.map(async (p) => { const st = await ist(p.id, p.media_product_type === "REELS" ? [...IG_MEDYA, ...IG_REELS] : IG_MEDYA), ort = st.ig_reels_avg_watch_time;
    return { id: p.id, baslik: (p.caption || "").trim().split("\n")[0].slice(0, 90), zaman: p.timestamp, tur: p.media_product_type || p.media_type, medya_turu: p.media_type, url: p.permalink,
      kapak: p.thumbnail_url || (p.media_type === "IMAGE" ? p.media_url : null), begeni: p.like_count ?? st.likes, yorum: p.comments_count ?? st.comments,
      izlenme: st.views, erisim: st.reach, kaydetme: st.saved, paylasim: st.shares, etkilesim: st.total_interactions, ort_izleme_sn: typeof ort === "number" ? Math.round(ort / 100) / 10 : null }; }));
  liste.sort((a, b) => (b.izlenme || 0) - (a.izlenme || 0)); out.medya = liste;
  const ort = (a) => a.reduce((s, x) => s + x, 0) / a.length, saat = {}, gun = {};
  for (const v of liste) { if (!v.zaman || !v.izlenme) continue; const t = new Date(Date.parse(v.zaman.slice(0, 19) + "Z") + 3 * 3600e3);
    (saat[t.getUTCHours()] ||= []).push(v.izlenme); (gun[(t.getUTCDay() + 6) % 7] ||= []).push(v.izlenme); }
  out.en_iyi_saatler = Object.entries(saat).sort((a, b) => ort(b[1]) - ort(a[1])).slice(0, 3).map(([s, v]) => ({ saat: +s, ort_izlenme: Math.round(ort(v)), adet: v.length }));
  const gs = Object.entries(gun).sort((a, b) => ort(b[1]) - ort(a[1])); if (gs.length) out.en_iyi_gun = IG_GUN[+gs[0][0]];
  out.desteklenmeyen = [...yok].sort(); return out;
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
        return json({ status: status || {}, runs, report, projeler, basliklar: await basliklar(projeler).catch(() => ({})), instagram, igToken: igMeta ? { kayitli: true, zaman: igMeta.zaman, son4: igMeta.son4 } : null, arsiv: ((await getStore({ name: "ayar", consistency: "strong" }).get("arsiv", { type: "json" })) || []).filter((x) => projeler.includes(x)), analiz,
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
      case "planla": { // Instagram paylaşımını ileri bir saate planla (zamanlayıcı fonksiyon 10 dk'da bir bakar)
        if (!validSlug(b.slug)) return json({ hata: "Geçersiz proje" }, 400);
        const t = new Date(b.zaman); const now = Date.now();
        if (isNaN(t) || t < now - 60e3 || t > now + 60 * 864e5) return json({ hata: "Geçersiz zaman (en fazla 60 gün sonrası)" }, 400);
        const q = (await readJson("data/yayin_kuyrugu.json")) || { isler: [] };
        if (q.isler.some((x) => x.slug === b.slug && x.durum === "bekliyor")) return json({ hata: "Bu video için zaten bekleyen bir plan var" }, 400);
        const id = `${Date.now().toString(36)}-${crypto.randomBytes(3).toString("hex")}`;
        q.isler.push({ id, slug: b.slug, platform: "instagram", zaman: t.toISOString(), durum: "bekliyor" });
        q.isler = q.isler.slice(-100);
        await writeFile("data/yayin_kuyrugu.json", b64(q), `Plan: ${b.slug} → ${t.toISOString()}`);
        return json({ ok: true, id });
      }
      case "plan_iptal": {
        const q = (await readJson("data/yayin_kuyrugu.json")) || { isler: [] };
        const it = q.isler.find((x) => x.id === b.id && x.durum === "bekliyor");
        if (!it) return json({ hata: "Plan bulunamadı" }, 404);
        it.durum = "iptal";
        await writeFile("data/yayin_kuyrugu.json", b64(q), `Plan iptal: ${it.slug}`);
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
