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


def kuyruk_guncelle(kid, durum, mesaj="", **ek):
    if not kid: return
    q = oku(KUYRUK, {"isler": []})
    for it in q["isler"]:
        if it.get("id") == kid: it.update(durum=durum, mesaj=mesaj, guncelleme=simdi(), **ek)
    yaz(KUYRUK, q)


def kuyruk_isi(kid):
    return next((x for x in oku(KUYRUK, {"isler": []})["isler"] if x.get("id") == kid), None) if kid else None


def dogrudan_adres(url):
    """github.com/.../releases/download/... gibi yönlendiren adresi son (doğrudan mp4) adrese çevirir."""
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, method="HEAD", headers={"user-agent": "tarih-yayinci"}), timeout=60)
        return r.geturl(), int(r.headers.get("content-length") or 0)
    except Exception:
        return url, 0


def ozel_metin(it):
    m = (it.get("caption") or "").strip(); hs = (it.get("hashtag") or "").strip()
    if hs: hs = " ".join(h if h.startswith("#") else "#" + h for h in hs.replace(",", " ").split())
    return (m + ("\n\n" + hs if hs else "")).strip()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug"); ap.add_argument("--kuyruk", default="")
    ap.add_argument("--test", action="store_true"); ap.add_argument("--zorla", action="store_true"); ap.add_argument("--tekrar", action="store_true")
    ap.add_argument("--deneme", action="store_true", help="Kap oluştur, işlenmesini bekle ama PAYLAŞMA")
    a = ap.parse_args()
    it = kuyruk_isi(a.kuyruk)
    if a.kuyruk and (not it or it.get("durum") not in ("bekliyor", "gonderildi")):
        print("Kuyruk işi yok ya da iptal/bitmiş; paylaşılmadı"); return   # sadece panelden planlanmış ve hâlâ geçerli işler paylaşılır
    if it and not a.slug: a.slug = it.get("slug") or ""
    if not IG.hazir():
        set_status("yayinci", "bekliyor", "Instagram bağlı değil: docs/YAYIN_KURULUM.md adımlarını tamamla")
        kuyruk_guncelle(a.kuyruk, "hata", "Instagram bağlı değil"); print("IG_TOKEN / IG_USER_ID yok; atlandı"); return
    if a.test:
        h = IG.hesap(); set_status("yayinci", "tamam", f"Instagram bağlı: @{h.get('username')} · {h.get('followers_count', 0)} takipçi")
        print("Bağlantı tamam:", h.get("username")); return
    try: IG.baglan_host()
    except IG.IGHata as e:
        m = "Instagram anahtarının süresi dolmuş, yenilenmeli" if IG.anahtar_hatasi(e) else str(e)
        kuyruk_guncelle(a.kuyruk, "hata", m); set_status("yayinci", "hata", m); raise SystemExit(m)
    kullanilan, limit = IG.yayin_kotasi()
    if kullanilan is not None and kullanilan >= limit and not a.deneme:
        sonra = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        m = f"Instagram günlük paylaşım limiti dolu ({kullanilan}/{limit}); 1 saat sonra tekrar denenecek"
        if it: kuyruk_guncelle(a.kuyruk, "bekliyor", m, zaman=sonra)
        set_status("yayinci", "bekliyor", m); print(m); return
    slug = a.slug or ""
    d = os.path.join(ROOT, "projects", slug)
    if it and it.get("url"):                                   # panelden doğrudan video adresiyle planlanmış iş
        metin = ozel_metin(it) or (aciklama_metni(oku(os.path.join(d, "script.json"), {})) if slug and os.path.isdir(d) else "")
        if not metin: kuyruk_guncelle(a.kuyruk, "hata", "Açıklama boş"); raise SystemExit("Açıklama boş")
        set_status("yayinci", "calisiyor", "Planlanan video Instagram'a yükleniyor")
        try:
            url, boyut = dogrudan_adres(it["url"]); print(f"Video: {boyut / 1e6:.1f} MB")
            sonuc = IG.reels_yayinla(url, metin, kapak_ms=it.get("kapak_ms"), akisa=it.get("akis", True) is not False, kapak_url=it.get("kapak_url"), deneme=a.deneme)
        except IG.IGHata as e:
            m = "Instagram anahtarının süresi dolmuş, yenilenmeli" if IG.anahtar_hatasi(e) else str(e)
            kuyruk_guncelle(a.kuyruk, "hata", m); set_status("yayinci", "hata", m); raise SystemExit(m)
        if a.deneme: print("Deneme: kap hazır, paylaşılmadı", sonuc.get("kap")); return
        m = f"Instagram'da yayında: {sonuc.get('permalink')}"
        kuyruk_guncelle(a.kuyruk, "tamam", m, permalink=sonuc.get("permalink")); set_status("yayinci", "tamam", m, sonuc.get("permalink")); print(m); return
    if not slug or not os.path.isdir(d):
        kuyruk_guncelle(a.kuyruk, "hata", "Proje bulunamadı"); raise SystemExit("Proje bulunamadı")
    yay = oku(YAYINLAR, {})
    if yay.get(slug, {}).get("instagram") and not a.tekrar and not a.deneme:
        m = f"{slug} zaten paylaşılmış: {yay[slug]['instagram'].get('permalink')}"
        kuyruk_guncelle(a.kuyruk, "tamam", m); set_status("yayinci", "tamam", m); print(m); return
    k = oku(os.path.join(d, "kontrol", "kurgu.json"), {})
    if k.get("durum") == "hata" and not a.zorla:
        m = f"{slug}: kurgu kontrolünde hata var, paylaşılmadı ({k.get('ozet', '')})"
        kuyruk_guncelle(a.kuyruk, "hata", m); set_status("yayinci", "hata", m); raise SystemExit(m)
    sc = oku(os.path.join(d, "script.json"), {})
    metin = (ozel_metin(it) if it else "") or aciklama_metni(sc)
    set_status("yayinci", "calisiyor", f"{slug} Instagram'a yükleniyor")
    try:
        url, boyut = video_adresi(slug)
        print(f"Video: {boyut / 1e6:.1f} MB")
        sonuc = IG.reels_yayinla(url, metin, kapak_ms=(it or {}).get("kapak_ms", 1500), akisa=(it or {}).get("akis", True) is not False,
                                 kapak_url=(it or {}).get("kapak_url"), deneme=a.deneme)
    except IG.IGHata as e:
        m = ("Instagram anahtarının süresi dolmuş, yenilenmeli (docs/YAYIN_KURULUM.md)" if IG.anahtar_hatasi(e) else str(e))
        kuyruk_guncelle(a.kuyruk, "hata", m); set_status("yayinci", "hata", f"{slug}: {m}"); raise SystemExit(m)
    if a.deneme: print("Deneme: kap hazır, paylaşılmadı", sonuc.get("kap")); return
    yay.setdefault(slug, {})["instagram"] = sonuc; yaz(YAYINLAR, yay)
    m = f"{slug} Instagram'da yayında: {sonuc.get('permalink')}"
    kuyruk_guncelle(a.kuyruk, "tamam", m, permalink=sonuc.get("permalink")); set_status("yayinci", "tamam", m, sonuc.get("permalink")); print(m)


if __name__ == "__main__":
    main()
