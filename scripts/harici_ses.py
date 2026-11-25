"""Panelden yuklenen dis ses (ElevenLabs vb.) icin yardimci.
  harici_ses.py hazirla <slug>   -> projects/<slug>/ses_harici.* varsa (parcaliysa birlestirir) ffmpeg ile ses.wav yapar
                                    (mono, 24000 Hz, loudnorm). Cikis kodu 0 = dis ses kullanildi, 3 = dis ses yok.
  harici_ses.py hata <kontrol.log> -> kontrol bekcisi dustuyse Turkce hata satirini basar.
"""
import glob, os, re, subprocess, sys

ORNEK = 24000  # quiz_studyo_ses.py / generate_assets.py ile ayni ornekleme hizi
TR_ABC = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUVYZ"

def bul(d):
    for ext in ("mp3", "wav", "m4a"):
        p = os.path.join(d, f"ses_harici.{ext}")
        parc = sorted(glob.glob(p + ".part*"))
        if parc:  # buyuk dosya parca parca yuklendi: birlestir
            with open(p, "wb") as o:
                for x in parc: o.write(open(x, "rb").read())
        if os.path.exists(p) and os.path.getsize(p) > 0: return p
    return None

def hazirla(slug):
    d = os.path.join("projects", slug); src = bul(d)
    if not src: print("dis ses yok, Gemini TTS kullanilacak"); return 3
    out = os.path.join(d, "ses.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(ORNEK), "-ac", "1", out], check=True)
    print(f"dis ses kullanildi: {src} -> {out}"); return 0

def hata(log):
    t = open(log, encoding="utf-8", errors="ignore").read()
    satir = [l for l in t.splitlines() if re.search(r"eslesm|uyusm|ses yok|ic durak|kayma", l, re.I)]
    x = 0
    for l in satir:
        m = re.search(r"soru (\d+)", l) or re.search(r"bekci (\d+)\.", l)
        if m: x = int(m.group(1)); break
        m = re.search(r'"([A-ZÇĞİÖŞÜ]) (soru|cevap)', l)
        if m and m.group(1) in TR_ABC: x = TR_ABC.index(m.group(1)) + 1; break
        if "giris" in l: x = 0; break
    print(f"::error::Yüklenen ses metinle eşleşmiyor: {x}. sorudan sonra kayma var")
    print(f"Yüklenen ses metinle eşleşmiyor: {x}. sorudan sonra kayma var")

if __name__ == "__main__":
    if sys.argv[1] == "hazirla": sys.exit(hazirla(sys.argv[2]))
    if sys.argv[1] == "hata": hata(sys.argv[2])
