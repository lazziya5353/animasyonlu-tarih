// Zamanlayıcı (Netlify zamanlanmış fonksiyon, ücretsiz): 10 dakikada bir planlanan Instagram paylaşımlarına bakar,
// zamanı gelenler için Yayıncı ajanını GitHub'da başlatır. GitHub Actions dakikası harcamadan bekler.
const REPO = process.env.GITHUB_REPO || "lazziya5353/animasyonlu-tarih";
const GH = "https://api.github.com";
const PATH = "data/yayin_kuyrugu.json";

const gh = (path, opts = {}) => fetch(GH + path, {
  ...opts,
  headers: { authorization: `Bearer ${process.env.GITHUB_TOKEN}`, accept: "application/vnd.github+json", "x-github-api-version": "2022-11-28", ...(opts.headers || {}) },
});

export default async () => {
  if (!process.env.GITHUB_TOKEN) return new Response("GITHUB_TOKEN yok");
  const r = await gh(`/repos/${REPO}/contents/${PATH}`);
  if (!r.ok) return new Response("kuyruk yok");
  const meta = await r.json();
  const q = JSON.parse(Buffer.from(meta.content, "base64").toString("utf8"));
  const now = Date.now(); let n = 0;
  for (const it of q.isler || []) {
    if (it.durum !== "bekliyor" || new Date(it.zaman).getTime() > now) continue;
    const d = await gh(`/repos/${REPO}/actions/workflows/yayinci.yml/dispatches`, { method: "POST", body: JSON.stringify({ ref: "main", inputs: { slug: it.slug, kuyruk: it.id } }) });
    it.durum = d.ok ? "gonderildi" : "hata"; it.mesaj = d.ok ? "Yayıncı başlatıldı" : `Başlatılamadı (${d.status})`; it.guncelleme = new Date().toISOString(); n++;
  }
  if (n) {
    await gh(`/repos/${REPO}/contents/${PATH}`, { method: "PUT", body: JSON.stringify({ message: `Zamanlayıcı: ${n} paylaşım başlatıldı`, content: Buffer.from(JSON.stringify(q, null, 1)).toString("base64"), sha: meta.sha }) });
  }
  return new Response(`${n} iş başlatıldı`);
};

export const config = { schedule: "*/10 * * * *" };
