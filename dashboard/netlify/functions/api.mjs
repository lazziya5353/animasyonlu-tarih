// Animasyonlu Tarih kontrol paneli API'si (Netlify Function).
// Ortam değişkenleri: GITHUB_TOKEN (repo + workflow yetkili), GITHUB_REPO (sahip/repo), PANEL_SIFRE, AYLIK_BUTCE_USD (isteğe bağlı)
import crypto from "node:crypto";
import { getStore } from "@netlify/blobs";

const REPO = process.env.GITHUB_REPO || "lazziya5353/animasyonlu-tarih";
const GH = "https://api.github.com";
const WORKFLOWS = {
  arastirmaci: "weekly-report.yml",
  senarist: "write-script.yml",
  gorsel: "generate-assets.yml",
  kurgucu: "render.yml",
  kontrol: "kontrol.yml",
  yayinci: "yayinci.yml",
  analist: "analist.yml",
  yorumcu: "yorumcu.yml",
  yonetici: "yonetici.yml",
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
const AJANLAR = ["arastirmaci", "senarist", "ses", "kurgucu", "efekt", "kontrol", "yayinci", "sen"];
const TURLER = ["yazi", "gorsel", "efekt", "harita", "ses", "muzik", "kontrol", "bilgi", "ilerleme"];
async function olayEkle(slug, liste) {
  const st = getStore("olaylar"); const key = validSlug(slug) ? slug : "_genel";
  const cur = (await st.get(key, { type: "json" })) || { n: 0, liste: [] };
  for (const o of liste.slice(0, 60)) {
    if (!AJANLAR.includes(o.ajan) || !TURLER.includes(o.tur)) continue;
    const temiz = { i: ++cur.n, ajan: o.ajan, tur: o.tur, mesaj: String(o.mesaj || "").slice(0, 200), z: Number(o.z) || Date.now() / 1000 };
    for (const k of ["t0", "t1", "yuzde", "sahne"]) if (Number.isFinite(Number(o[k])) && o[k] !== null && o[k] !== undefined) temiz[k] = Number(o[k]);
    for (const k of ["seviye", "asama", "durum"]) if (typeof o[k] === "string") temiz[k] = o[k].slice(0, 20);
    cur.liste.push(temiz);
  }
  cur.liste = cur.liste.slice(-800);
  await st.setJSON(key, cur);
  return cur.n;
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
  if (b.action === "olay" && req.headers.get("x-gh-token")) { // ajanlardan canlı olay: GitHub Actions anahtarı bu repoya erişebiliyor mu?
    const t = req.headers.get("x-gh-token"); const k = crypto.createHash("sha256").update(t).digest("hex");
    if (!(gecerliGh.get(k) > Date.now())) {
      const r = await fetch(`${GH}/repos/${REPO}`, { headers: { authorization: `Bearer ${t}`, accept: "application/vnd.github+json" } });
      if (!r.ok) return json({ hata: "Yetkisiz" }, 401);
      gecerliGh.set(k, Date.now() + 10 * 60e3);
    }
    if (!Array.isArray(b.olaylar)) return json({ hata: "Olay yok" }, 400);
    try { return json({ ok: true, n: await olayEkle(b.slug, b.olaylar) }); } catch (e) { return json({ hata: String(e.message || e) }, 500); }
  }
  if (!same(req.headers.get("x-panel-token") || "", token())) return json({ hata: "Giriş gerekli" }, 401);
  if (!process.env.GITHUB_TOKEN) return json({ hata: "GITHUB_TOKEN tanımlı değil (Netlify > Site settings > Environment variables)" }, 500);

  try {
    switch (b.action) {
      case "overview": {
        const [status, usage, report, list, analiz, yorumlar] = await Promise.all([
          readJson("data/status.json"), readJson("data/usage.json"), readJson("reports/latest.json"),
          gh(`/repos/${REPO}/contents/projects`).then((r) => (r.ok ? r.json() : [])),
          readJson("data/analiz.json"), readJson("data/yorumlar.json"),
        ]);
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
        return json({ status: status || {}, runs, report, projeler: (list || []).filter((x) => x.type === "dir").map((x) => x.name), analiz,
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
        if (!Array.isArray(b.olaylar)) return json({ hata: "Olay yok" }, 400);
        return json({ ok: true, n: await olayEkle(b.slug, b.olaylar.map((o) => ({ ...o, ajan: "sen" }))) });
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
