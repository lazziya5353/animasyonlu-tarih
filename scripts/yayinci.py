"""Yayıncı ajanı: bitmiş videoyu Instagram'a Reels olarak paylaşır (resmi API, ücretsiz).
  python scripts/yayinci.py --test                       # anahtar çalışıyor mu? (hesap adını yazar)
  python scripts/yayinci.py --slug X [--kuyruk ID]       # paylaş
Paylaşmadan önce kurgu kontrolcüsünün sonucuna bakar; hata varsa paylaşmaz (--zorla ile geçilir).
YouTube: Google, denetimden geçmemiş uygulamaların yüklediği videoları kalıcı olarak gizli bırakıyor; bu yüzden YouTube'a
yükleme elle yapılır, başlık/açıklama/etiket paketi panelde hazırlanır."""
import os, sys, json, argparse, datetime, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, set_status
import instagram as IG

MARKA = json.load(open(os.path.join(ROOT, "engine", "assets", "marka.json")))
KUYRUK = os.path.join(ROOT, "data", "yayin_kuyrugu.json")
YAYINLAR = os.path.join(ROOT, "data", "yayinlar.json")
simdi = lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def oku(p, bos):
    try: return json.load(open(p))
    except Exception: return bos


def yaz(p, v):
    os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(v, open(p, "w"), ensure_ascii=False, indent=1)


def aciklama_metni(sc):
    if (sc.get("paylasim") or "").strip(): return sc["paylasim"].strip()
    hs = " ".join(h if h.startswith("#") else "#" + h for h in (sc.get("hashtagler") or []))
    return f"{(sc.get('aciklama') or '').strip()}\n\n🔔 Tarihin unutulmaz anları için takip et: {MARKA.get('handle', '')}\n\n{hs}".strip()


class _YonlendirmeYok(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None


def video_adresi(slug):
    """Gizli repodaki videonun birkaç dakika geçerli imzalı indirme adresi (Instagram bu adresten çeker)."""
    repo, tok = os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]
    h = {"authorization": f"Bearer {tok}", "accept": "application/vnd.github+json"}
    rel = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/tags/video-{slug}", headers=h)))
    asset = next(a for a in rel["assets"] if a["name"].endswith(".mp4"))
    op = urllib.request.build_opener(_YonlendirmeYok)
    try:
        op.open(urllib.request.Request(asset["url"], headers={**h, "accept": "application/octet-stream"}))
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307) and e.headers.get("location"): return e.headers["location"], asset["size"]
        raise
    raise SystemExit("Video adresi alınamadı")


def kuyruk_guncelle(kid, durum, mesaj=""):
    if not kid: return
    q = oku(KUYRUK, {"isler": []})
    for it in q["isler"]:
        if it.get("id") == kid: it.update(durum=durum, mesaj=mesaj, guncelleme=simdi())
    yaz(KUYRUK, q)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug"); ap.add_argument("--kuyruk", default="")
    ap.add_argument("--test", action="store_true"); ap.add_argument("--zorla", action="store_true"); ap.add_argument("--tekrar", action="store_true")
    a = ap.parse_args()
    if not IG.hazir():
        set_status("yayinci", "bekliyor", "Instagram bağlı değil: docs/YAYIN_KURULUM.md adımlarını tamamla")
        kuyruk_guncelle(a.kuyruk, "hata", "Instagram bağlı değil"); print("IG_TOKEN / IG_USER_ID yok; atlandı"); return
    if a.test:
        h = IG.hesap(); set_status("yayinci", "tamam", f"Instagram bağlı: @{h.get('username')} · {h.get('followers_count', 0)} takipçi")
        print("Bağlantı tamam:", h.get("username")); return
    slug = a.slug or ""
    d = os.path.join(ROOT, "projects", slug)
    if not slug or not os.path.isdir(d): raise SystemExit("Proje bulunamadı")
    yay = oku(YAYINLAR, {})
    if yay.get(slug, {}).get("instagram") and not a.tekrar:
        m = f"{slug} zaten paylaşılmış: {yay[slug]['instagram'].get('permalink')}"
        kuyruk_guncelle(a.kuyruk, "tamam", m); set_status("yayinci", "tamam", m); print(m); return
    k = oku(os.path.join(d, "kontrol", "kurgu.json"), {})
    if k.get("durum") == "hata" and not a.zorla:
        m = f"{slug}: kurgu kontrolünde hata var, paylaşılmadı ({k.get('ozet', '')})"
        kuyruk_guncelle(a.kuyruk, "hata", m); set_status("yayinci", "hata", m); raise SystemExit(m)
    sc = oku(os.path.join(d, "script.json"), {})
    metin = aciklama_metni(sc)
    set_status("yayinci", "calisiyor", f"{slug} Instagram'a yükleniyor")
    try:
        url, boyut = video_adresi(slug)
        print(f"Video: {boyut / 1e6:.1f} MB")
        sonuc = IG.reels_yayinla(url, metin, kapak_ms=1500)
    except IG.IGHata as e:
        m = ("Instagram anahtarının süresi dolmuş, yenilenmeli (docs/YAYIN_KURULUM.md)" if IG.anahtar_hatasi(e) else str(e))
        kuyruk_guncelle(a.kuyruk, "hata", m); set_status("yayinci", "hata", f"{slug}: {m}"); raise SystemExit(m)
    yay.setdefault(slug, {})["instagram"] = sonuc; yaz(YAYINLAR, yay)
    m = f"{slug} Instagram'da yayında: {sonuc.get('permalink')}"
    kuyruk_guncelle(a.kuyruk, "tamam", m); set_status("yayinci", "tamam", m, sonuc.get("permalink")); print(m)


if __name__ == "__main__":
    main()
