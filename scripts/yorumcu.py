"""Yorum ajanı (ücretsiz): Instagram yorumlarını toplar, Gemini'nin ücretsiz kotasıyla türünü belirler ve cevap taslağı yazar.
Hiçbir cevabı kendiliğinden göndermez: panelde sen onaylarsın, sonra gönderir.
  python scripts/yorumcu.py topla    # yeni yorumları topla + taslak yaz
  python scripts/yorumcu.py gonder   # panelde onaylanan cevapları gönder, gizlenecekleri gizle"""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, set_status
import instagram as IG, gemini

OUT = os.path.join(ROOT, "data", "yorumlar.json")
MARKA = json.load(open(os.path.join(ROOT, "engine", "assets", "marka.json")))
TASLAK = """Sen "{handle}" adlı Türkçe tarih sayfasının yorum asistanısın. Sayfa 60 saniyelik animasyonlu tarih videoları paylaşıyor.
Aşağıdaki yorumların her biri için:
- "tur": soru | ovgu | elestiri | oneri | spam | hakaret | diger
- "taslak": samimi, kısa (en fazla 2 cümle), saygılı bir Türkçe cevap. Tarihi bilgi veriyorsan sadece kesin bildiğin şeyi yaz; emin değilsen
  "araştırıp yeni bir videoda ele alabiliriz" gibi söz ver. Siyasi/dini tartışmaya girme, kimseyle kavga etme. spam ve hakarette taslak boş olsun.
- "fikir": yorum yeni bir video konusu öneriyorsa kısa konu adı, yoksa boş.
Yorumlar (JSON): {yorumlar}
Sadece şu JSON'u döndür: {{"sonuclar": [{{"id": "...", "tur": "...", "taslak": "...", "fikir": "..."}}]}}"""


def oku():
    try: return json.load(open(OUT))
    except Exception: return {"yorumlar": [], "fikirler": []}


def yaz(v):
    os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(v, open(OUT, "w"), ensure_ascii=False, indent=1)


def topla():
    db = oku(); bilinen = {y["id"] for y in db["yorumlar"]}; yeni = []
    kendi = (IG.hesap().get("username") or "").lower()
    for p in IG.son_gonderiler(12):
        for c in IG.yorumlar(p["id"]):
            if c["id"] in bilinen or (c.get("username") or "").lower() == kendi: continue
            yeni.append({"id": c["id"], "media_id": p["id"], "gonderi": (p.get("caption") or "").split("\n")[0][:60], "url": p.get("permalink"),
                         "kullanici": c.get("username"), "metin": c.get("text", ""), "zaman": c.get("timestamp"), "durum": "yeni", "tur": "diger", "taslak": ""})
    if yeni:
        try:
            r = gemini.sor([TASLAK.format(handle=MARKA.get("handle", ""), yorumlar=json.dumps([{"id": y["id"], "gonderi": y["gonderi"], "yorum": y["metin"][:500]} for y in yeni], ensure_ascii=False))], sicaklik=0.5)
            by = {x.get("id"): x for x in r.get("sonuclar", [])}
            for y in yeni:
                x = by.get(y["id"], {}); y["tur"] = x.get("tur", "diger"); y["taslak"] = (x.get("taslak") or "").strip()
                if x.get("fikir"): db.setdefault("fikirler", []).append({"konu": x["fikir"], "kaynak": f"@{y['kullanici']}", "zaman": y["zaman"]})
        except gemini.GeminiYok as e:
            print("Taslaklar yazılamadı:", e)
    db["yorumlar"] = (yeni + db["yorumlar"])[:300]; db["fikirler"] = db.get("fikirler", [])[-50:]
    yaz(db)
    bekleyen = sum(1 for y in db["yorumlar"] if y["durum"] == "yeni")
    set_status("yorumcu", "tamam", f"{len(yeni)} yeni yorum · {bekleyen} cevap bekliyor"); print(f"{len(yeni)} yeni yorum")


def gonder():
    db = oku(); n = 0
    for y in db["yorumlar"]:
        try:
            if y["durum"] == "onaylandi" and y.get("taslak"):
                IG.yanitla(y["id"], y["taslak"]); y["durum"] = "gonderildi"; n += 1
            elif y["durum"] == "gizle":
                IG.gizle(y["id"]); y["durum"] = "gizlendi"; n += 1
        except IG.IGHata as e:
            y["hata"] = str(e)[:200]
    yaz(db); set_status("yorumcu", "tamam", f"{n} işlem yapıldı"); print(f"{n} işlem")


if __name__ == "__main__":
    if not IG.hazir():
        set_status("yorumcu", "bekliyor", "Instagram bağlı değil: docs/YAYIN_KURULUM.md"); print("IG anahtarı yok; atlandı"); sys.exit(0)
    try:
        {"topla": topla, "gonder": gonder}[sys.argv[1] if len(sys.argv) > 1 else "topla"]()
    except IG.IGHata as e:
        set_status("yorumcu", "hata", "Instagram anahtarının süresi dolmuş, yenilenmeli" if IG.anahtar_hatasi(e) else str(e)[:200]); raise SystemExit(str(e))
