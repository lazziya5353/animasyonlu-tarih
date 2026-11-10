"""Kontrolcü ajanlar: her ajanın işini arkasından denetler. Claude kredisi harcamaz.
  python scripts/kontrol.py senaryo --slug X   # kural tabanlı metin kontrolü
  python scripts/kontrol.py ses --slug X       # süre, sessizlik, patlama + Gemini (ücretsiz) ile metin-ses karşılaştırması
  python scripts/kontrol.py gorsel --slug X    # teknik kontrol + Gemini (ücretsiz) ile görsel inceleme
  python scripts/kontrol.py kurgu --slug X     # bitmiş videoda kare, ses seviyesi, senkron + Gemini ile kare incelemesi
Sonuç: projects/X/kontrol/<asama>.json  (durum: tamam | uyari | hata). Çıkış kodu her zaman 0; --sert verilirse hata durumunda 2."""
import os, sys, re, json, math, argparse, datetime, difflib, subprocess, hashlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, set_status
import gemini

ENGINE = os.path.join(ROOT, "engine")
TR_KARAKTER_SN = 11.3          # işlenmiş seslendirmede ölçülen hız (karakter / sn)
REELS_MAX = 90                 # Instagram API ile Reels üst sınırı (sn)


# ───────── ortak ─────────
class Rapor:
    def __init__(self, asama):
        self.asama = asama; self.maddeler = []; self.ek = {}

    def ekle(self, seviye, mesaj, sahne=None):
        self.maddeler.append({"seviye": seviye, "mesaj": mesaj, **({"sahne": sahne} if sahne else {})})

    hata = lambda self, m, s=None: self.ekle("hata", m, s)
    uyari = lambda self, m, s=None: self.ekle("uyari", m, s)
    bilgi = lambda self, m, s=None: self.ekle("bilgi", m, s)

    @property
    def durum(self):
        sv = {m["seviye"] for m in self.maddeler}
        return "hata" if "hata" in sv else "uyari" if "uyari" in sv else "tamam"

    def kaydet(self, slug, ozet):
        d = os.path.join(ROOT, "projects", slug, "kontrol"); os.makedirs(d, exist_ok=True)
        out = {"asama": self.asama, "durum": self.durum, "ozet": ozet, "maddeler": self.maddeler, **self.ek,
               "zaman": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        json.dump(out, open(os.path.join(d, f"{self.asama}.json"), "w"), ensure_ascii=False, indent=1)
        ikon = {"tamam": "✓", "uyari": "!", "hata": "✗"}[self.durum]
        print(f"[{self.asama}] {ikon} {ozet}")
        for m in self.maddeler: print(f"   - {m['seviye']}: {('sahne ' + str(m['sahne']) + ': ') if m.get('sahne') else ''}{m['mesaj']}")
        return out


def yukle(slug):
    d = os.path.join(ROOT, "projects", slug)
    sc = json.load(open(os.path.join(d, "script.json"))) if os.path.exists(os.path.join(d, "script.json")) else None
    pj = json.load(open(os.path.join(d, "project.json"))) if os.path.exists(os.path.join(d, "project.json")) else None
    return d, sc, pj


def sahneler(sc, pj):
    if sc and sc.get("sahneler"): return sc["sahneler"]
    return (pj or {}).get("scenes", [])


def ff_sure(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0


# Türkçe sayı → yazı (yıllar ve küçük sayılar için; ses karşılaştırmasında rakam/yazı farkını yok sayar)
_BIR = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_ON = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
def sayi_yazi(n):
    n = int(n)
    if n == 0: return "sıfır"
    if n >= 1_000_000: return str(n)
    p = []
    if n >= 1000: b = n // 1000; p += ([] if b == 1 else sayi_yazi(b).split()) + ["bin"]; n %= 1000
    if n >= 100: y = n // 100; p += ([] if y == 1 else [_BIR[y]]) + ["yüz"]; n %= 100
    if n >= 10: p.append(_ON[n // 10]); n %= 10
    if n: p.append(_BIR[n])
    return " ".join(p)


def kelimeler(t):
    t = t.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"(\d+)[.:](\d+)", lambda m: f"{m.group(1)} {m.group(2)}", t)
    t = re.sub(r"\d+", lambda m: " " + sayi_yazi(m.group()) + " ", t)
    t = t.replace("â", "a").replace("î", "i").replace("û", "u").replace("’", "'")
    t = re.sub(r"'\w*", "", t)                     # ek ayrımı: Samsun'a → samsun
    return re.findall(r"[a-zçğıöşü]+", t)


# ───────── 1. SENARYO ─────────
def senaryo(slug):
    d, sc, pj = yukle(slug); R = Rapor("senaryo")
    if not sc and not pj:
        R.hata("script.json ya da project.json yok"); return R.kaydet(slug, "Proje bulunamadı")
    S = sahneler(sc, pj); n = len(S)
    if not 6 <= n <= 16: R.uyari(f"{n} sahne var; 60 sn için 8–14 arası ideal")
    sys.path.insert(0, ENGINE)
    from core import caption_img, text as ctext, W
    gorulen = {}
    for i, s in enumerate(S, 1):
        lines = s.get("lines") or []
        if not lines: R.hata("altyazı/cümle yok", i)
        for l in lines:
            h = caption_img(l).height; satir = round((h - 40) / 70)
            if satir >= 3: R.uyari(f"altyazı {satir} satıra taşıyor, kısaltılabilir: “{l[:60]}…”", i)
            if re.search(r"\bbin (dokuz|sekiz|yedi|altı|beş|dört|üç|iki)? ?yüz\b", l.lower()): R.uyari(f"yıl yazıyla yazılmış, ekranda rakam olmalı: “{l[:50]}”", i)
            k = l.strip().lower()
            if k in gorulen: R.uyari(f"aynı cümle {gorulen[k]}. sahnede de var", i)
            gorulen[k] = i
        big = s.get("big") or ""
        if big and ctext(big, "serif", 118, (255, 255, 255)).width > W - 90: R.bilgi(f"başlık “{big}” uzun, otomatik küçültülecek", i)
        if sc:
            pr = s.get("prompt_tam") or s.get("prompt") or ""
            if not pr: R.hata("görsel promptu yok", i)
            elif "no text" not in pr.lower(): R.uyari("promptta “no text” yok, görselde yazı çıkabilir", i)
            if re.search(r"(atat[uü]rk|mustafa kemal)", pr, re.I) and re.search(r"(face|portrait|close-?up of (him|atat))", pr, re.I):
                R.hata("promptta Atatürk'ün yüzü isteniyor; yapay zekayla yüz çizdirmiyoruz", i)
        if not s.get("image"): R.hata("görsel dosya adı yok", i)
    # süre tahmini
    konusma = (sc or {}).get("seslendirme_metni") or " ".join(l for s in S for l in s.get("lines", []))
    tahmin = len(konusma) / TR_KARAKTER_SN
    if tahmin > 85: R.hata(f"metin çok uzun: tahmini {tahmin:.0f} sn (Reels için ≤ 85 sn olmalı)")
    elif tahmin > 75: R.uyari(f"metin biraz uzun: tahmini {tahmin:.0f} sn")
    elif tahmin < 35: R.uyari(f"metin kısa: tahmini {tahmin:.0f} sn")
    if sc:
        cumle = [x for x in konusma.split("\n") if x.strip()]; satir = sum(len(s.get("lines", [])) for s in S)
        if cumle and len(cumle) != satir: R.uyari(f"seslendirme {len(cumle)} satır, altyazılar {satir} cümle; hizalama şaşabilir")
        if not (sc.get("aciklama") or "").strip(): R.uyari("paylaşım açıklaması boş")
        hs = sc.get("hashtagler") or []
        if not 3 <= len(hs) <= 15: R.uyari(f"{len(hs)} hashtag var; 3–15 arası olmalı")
        if any(" " in h.strip() for h in hs): R.uyari("boşluk içeren hashtag var")
        if not sc.get("kaynaklar"): R.uyari("kaynak listesi boş; bilgiler doğrulanamıyor")
    # haritalar ve planlar
    cities = json.load(open(os.path.join(ENGINE, "map", "cities.json")))
    regions = json.load(open(os.path.join(ENGINE, "map", "regions.json")))
    cfg = pj or {}; ekstra = cfg.get("cities") or {}
    for m in cfg.get("maps_plan") or cfg.get("maps") or (sc or {}).get("maps") or []:
        for c in (m.get("cities") or []) + (m.get("route") or []):
            if c not in cities and c not in ekstra: R.hata(f"haritada bilinmeyen şehir: “{c}” (engine/map/cities.json'a eklenmeli)", (m.get("scene") or 0) + 1 if m.get("scene") is not None else None)
        if (m.get("scene") or 0) >= n: R.hata(f"harita {m.get('scene')}. sahneye bağlı ama o sahne yok")
    if cfg.get("map_region") and cfg["map_region"] not in regions: R.hata(f"bilinmeyen harita bölgesi: {cfg['map_region']}")
    for e in cfg.get("eras") or []:
        if e.get("to", 0) >= n or e.get("from", 0) > e.get("to", 0): R.uyari(f"çizelge dönemi “{e.get('name')}” sahne aralığı hatalı")
    for k in cfg.get("cards_plan") or []:
        if k.get("scene", 0) >= n: R.hata("sayaç kartı olmayan bir sahneye bağlı")
    R.ek["tahmini_sure"] = round(tahmin, 1)
    return R.kaydet(slug, f"{n} sahne, tahmini {tahmin:.0f} sn · {len([m for m in R.maddeler if m['seviye'] != 'bilgi'])} not")


# ───────── 2. SES ─────────
def sessizlikler(path, esik=-35, sure=0.3):
    log = subprocess.run(["ffmpeg", "-i", path, "-af", f"silencedetect=n={esik}dB:d={sure}", "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(st, en))


def ses(slug):
    d, sc, pj = yukle(slug); R = Rapor("ses")
    voice = os.path.join(d, (pj or {}).get("voice", "ses.wav"))
    if not os.path.exists(voice): R.hata("ses dosyası yok"); return R.kaydet(slug, "Ses yok")
    dur = ff_sure(voice); R.ek["sure"] = round(dur, 1)
    if dur > REELS_MAX - 5: R.hata(f"ses {dur:.0f} sn; video Reels sınırını ({REELS_MAX} sn) aşar")
    elif dur > 80: R.uyari(f"ses {dur:.0f} sn, biraz uzun")
    elif dur < 25: R.uyari(f"ses {dur:.0f} sn, çok kısa")
    sil = sessizlikler(voice)
    uzun = [(a, b) for a, b in sil if b - a > 1.2 and a > 0.2 and b < dur - 0.2]
    if uzun: R.uyari(f"{len(uzun)} yerde 1,2 sn'den uzun sessizlik var (ilki {uzun[0][0]:.1f}. sn)")
    if sil and sil[0][0] < 0.05 and sil[0][1] > 1.0: R.uyari(f"başta {sil[0][1]:.1f} sn sessizlik var")
    vol = subprocess.run(["ffmpeg", "-i", voice, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mx = re.search(r"max_volume: ([-\d.]+)", vol)
    if mx and float(mx.group(1)) > -0.3: R.uyari("seste patlama (clipping) olabilir")
    hedef = (sc or {}).get("seslendirme_metni") or " ".join(l for s in sahneler(sc, pj) for l in s.get("lines", []))
    benzerlik = None
    try:
        txt = gemini.sor([gemini.ses_parca(voice), "Bu Türkçe ses kaydını kelimesi kelimesine, hiçbir şey eklemeden ve düzeltmeden yazıya dök. Sayıları duyduğun gibi yazıyla yaz. Sadece metni döndür."], json_cevap=False, sicaklik=0, sure=200)
        a, b = kelimeler(hedef), kelimeler(txt)
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False); benzerlik = sm.ratio()
        R.ek["benzerlik"] = round(benzerlik, 3); R.ek["dokum"] = txt.strip()[:4000]
        eksik = [" ".join(a[i1:i2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("delete", "replace") and i2 - i1 >= 2]
        fazla = [" ".join(b[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("insert", "replace") and j2 - j1 >= 3]
        if benzerlik < 0.85: R.hata(f"ses metinle %{benzerlik * 100:.0f} uyuşuyor; okuma hatalı olabilir")
        elif benzerlik < 0.93: R.uyari(f"ses metinle %{benzerlik * 100:.0f} uyuşuyor")
        for e in eksik[:4]: R.uyari(f"okunmamış/yanlış okunmuş olabilir: “{e}”")
        for e in fazla[:2]: R.uyari(f"metinde olmayan bir şey okunmuş olabilir: “{e}”")
    except gemini.GeminiYok as e:
        R.bilgi(f"metin-ses karşılaştırması atlandı: {e}")
    oz = f"{dur:.0f} sn" + (f", metinle %{benzerlik * 100:.0f} uyumlu" if benzerlik is not None else "")
    return R.kaydet(slug, oz)


# ───────── 3. GÖRSEL ─────────
GORSEL_KURAL = """Sen bir tarih belgeseli için görsel denetçisisin. Bu görsel dikey bir videonun {i}. sahnesinde kullanılacak.
Sahne: yıl {yil}, başlık “{big}”, alt başlık “{sub}”. Anlatılan: “{cumle}”.
Görselden istenen: {prompt}
Proje notları: {notlar}
Kontrol et:
1) Görsel sahneye ve döneme uyuyor mu? Dönemine aykırı (anakronik) bir şey var mı (modern araç, modern bina, plastik, telefon vb.)?
2) Görselde okunabilir yazı, harf, logo, filigran ya da imza var mı?
3) Bozuk el/yüz/beden, saçma birleşmiş nesne gibi yapay zeka hatası var mı?
4) Türk bayrağı varsa doğru mu (kırmızı zemin, beyaz ay ve yıldız, yıldız ayın açık tarafında)? Başka bayraklar döneme uygun mu?
5) Gerçek bir tarihi kişinin yüzü net şekilde tanınır biçimde çizilmiş mi? (Proje notları yasaklıyorsa ciddi sorun.)
6) Şiddet/kan gibi platform kurallarına takılacak bir şey var mı?
Sadece şu JSON'u döndür: {{"uygun": true/false, "puan": 1-10, "sorunlar": [{{"ciddiyet": "hata" veya "uyari", "aciklama": "kısa Türkçe açıklama"}}]}}"""


def gorsel(slug):
    d, sc, pj = yukle(slug); R = Rapor("gorsel"); S = sahneler(sc, pj)
    from PIL import Image, ImageStat
    eksik, hashler, puanlar, ai_atla = [], {}, [], None
    notlar = ((sc or {}).get("kontrol_notlari") or "")
    if isinstance(notlar, list): notlar = " ".join(map(str, notlar))
    notlar = (notlar + " Atatürk ve gerçek kişilerin yüzleri yapay zekayla çizilmez; yalnızca arkadan/uzaktan siluet olabilir.")[:600]
    for i, s in enumerate(S, 1):
        p = os.path.join(d, s.get("image", f"images/s{i:02d}.jpg"))
        if not os.path.exists(p): eksik.append(i); continue
        try: im = Image.open(p); im.load()
        except Exception: R.hata("görsel açılamıyor (bozuk dosya)", i); continue
        w, h = im.size
        if w / h > 0.75: R.uyari(f"görsel dikey değil ({w}×{h}); kenarları kırpılacak", i)
        if h < 1000 and w < 1000: R.uyari(f"çözünürlük düşük ({w}×{h}), videoda bulanık görünebilir", i)
        g = im.convert("L").resize((16, 16)); ort = ImageStat.Stat(g).mean[0]
        if ort < 14: R.uyari("görsel neredeyse tamamen karanlık", i)
        hb = "".join("1" if v > ort else "0" for v in g.tobytes())
        for j, hb2 in hashler.items():
            if sum(a != b for a, b in zip(hb, hb2)) < 18: R.uyari(f"{j}. sahnedeki görselle neredeyse aynı", i)
        hashler[i] = hb
        if ai_atla is None or ai_atla is False:
            try:
                cev = gemini.sor([gemini.resim_parca(p), GORSEL_KURAL.format(i=i, yil=s.get("year", ""), big=s.get("big", ""), sub=s.get("sub", ""),
                                  cumle=" ".join(s.get("lines", []))[:300], prompt=(s.get("prompt") or "")[:500], notlar=notlar)])
                ai_atla = False; puanlar.append(cev.get("puan") or 0)
                for so in (cev.get("sorunlar") or [])[:3]:
                    (R.hata if so.get("ciddiyet") == "hata" else R.uyari)(so.get("aciklama", "sorun"), i)
                time.sleep(4)   # ücretsiz kota: dakikada ~15 istek
            except gemini.GeminiYok as e:
                ai_atla = True; R.bilgi(f"yapay zeka incelemesi atlandı: {e}")
    if eksik: R.hata(f"eksik görsel: sahne {', '.join(map(str, eksik))}")
    R.ek["eksik"] = eksik
    if puanlar: R.ek["ortalama_puan"] = round(sum(puanlar) / len(puanlar), 1)
    oz = f"{len(S) - len(eksik)}/{len(S)} görsel" + (f", ortalama puan {R.ek['ortalama_puan']}/10" if puanlar else "")
    return R.kaydet(slug, oz)


# ───────── 4. KURGU ─────────
KURGU_KURAL = """Bu, dikey bir tarih videosundan her sahnenin ortasından alınmış {n} karelik bir kontrol tablosu (soldan sağa, yukarıdan aşağı numaralı).
Videoda olması GEREKENLER: altın renkli büyük başlık (üstte), altyazı (ortanın altında), altta zaman çizelgesi, sol altta küçük soluk logo, bazen haritalar.
Sadece GERÇEK kurgu hatalarını bul: kenardan taşan/kesilen yazı, üst üste binen okunmaz yazılar, arka plana karışıp okunmayan altyazı,
bozuk/siyah/donuk kare, görselin önemli kısmını kapatan yazı, harita etiketlerinin kadraj dışında kalması.
Sadece şu JSON'u döndür: {{"sorunlar": [{{"kare": numara, "ciddiyet": "hata" veya "uyari", "aciklama": "kısa Türkçe açıklama"}}]}}"""


def kurgu(slug, video=None):
    d, sc, pj = yukle(slug); R = Rapor("kurgu")
    video = video or os.path.join(d, "out", "video.mp4")
    if not os.path.exists(video): R.hata("video dosyası yok"); return R.kaydet(slug, "Video yok")
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", video], capture_output=True, text=True).stdout)
    vs = next((s for s in pr["streams"] if s["codec_type"] == "video"), {}); aud = any(s["codec_type"] == "audio" for s in pr["streams"])
    dur = float(pr["format"]["duration"]); R.ek["sure"] = round(dur, 1)
    if (vs.get("width"), vs.get("height")) != (1080, 1920): R.hata(f"çözünürlük {vs.get('width')}×{vs.get('height')}, 1080×1920 olmalı")
    if not aud: R.hata("videoda ses yok")
    if dur > REELS_MAX: R.hata(f"video {dur:.0f} sn; Instagram'a otomatik yükleme sınırı {REELS_MAX} sn")
    elif dur < 15: R.uyari(f"video {dur:.0f} sn, çok kısa")
    lu = subprocess.run(["ffmpeg", "-i", video, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+([-\d.]+) LUFS", lu)
    if m:
        L = float(m[-1]); R.ek["lufs"] = L
        if abs(L + 14) > 2.5: R.uyari(f"ses seviyesi {L:.1f} LUFS; −14 civarı olmalı")
    bl = subprocess.run(["ffmpeg", "-i", video, "-vf", "blackdetect=d=0.4:pix_th=0.08", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bl):
        a, b = float(a), float(b)
        if a > 0.8 and b < dur - 2.6: R.uyari(f"{a:.1f}–{b:.1f}. saniyeler arası siyah ekran")
    fz = subprocess.run(["ffmpeg", "-i", video, "-vf", "freezedetect=n=0.0008:d=2.5", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    for a in re.findall(r"freeze_start: ([\d.]+)", fz)[:2]:
        if float(a) < dur - 3: R.uyari(f"{float(a):.1f}. saniyede görüntü donuyor")
    # altyazı ↔ ses senkronu: her altyazı penceresinde konuşma olmalı
    tf = os.path.join(d, "project.timed.json"); voice = os.path.join(d, (pj or {}).get("voice", "ses.wav"))
    if os.path.exists(tf) and os.path.exists(voice):
        T = json.load(open(tf)); off = T.get("voice_offset", 0.3); sil = sessizlikler(voice, -38, 0.25)
        kotu = 0
        for c in T.get("captions", []):
            a, b = c["start"], c["end"]; L = max(0.01, b - a)
            sessiz = sum(max(0, min(b, y) - max(a, x)) for x, y in sil)
            if sessiz / L > 0.6: kotu += 1; R.uyari(f"altyazı sesle örtüşmüyor olabilir: “{c['text'][:40]}”")
        R.ek["senkron"] = f"{len(T.get('captions', [])) - kotu}/{len(T.get('captions', []))}"
    uy = os.path.join(d, "out", "uyarilar.json")
    if os.path.exists(uy):
        for t in json.load(open(uy))[:5]: R.bilgi(f"sığmadığı için küçültüldü: “{t}”")
    # kontrol tablosu: her sahnenin ortasından kare
    kareler = []
    if os.path.exists(tf):
        T = json.load(open(tf)); off = T.get("voice_offset", 0.3)
        kareler = [min(dur - 0.2, off + (s["start"] + s["end"]) / 2) for s in T["scenes"]]
    else:
        kareler = [dur * (k + .5) / 12 for k in range(12)]
    from PIL import Image, ImageDraw
    sys.path.insert(0, ENGINE); from core import F
    tw, th, cols = 270, 480, 6; rows = math.ceil(len(kareler) / cols)
    tablo = Image.new("RGB", (cols * tw, rows * th), (10, 10, 12))
    for k, t in enumerate(kareler):
        tmp = f"/tmp/kk_{k}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", f"scale={tw}:{th}", "-y", tmp], check=True)
        tablo.paste(Image.open(tmp), ((k % cols) * tw, (k // cols) * th))
        dr = ImageDraw.Draw(tablo); x, y = (k % cols) * tw, (k // cols) * th
        dr.rectangle([x, y, x + 40, y + 34], fill=(232, 196, 120)); dr.text((x + 20, y + 17), str(k + 1), font=F("sans9", 22), fill=(20, 15, 5), anchor="mm")
    yol = os.path.join(d, "kontrol", "kareler.jpg"); os.makedirs(os.path.dirname(yol), exist_ok=True); tablo.save(yol, quality=82)
    try:
        cev = gemini.sor([gemini.resim_parca(yol, max_h=1600), KURGU_KURAL.format(n=len(kareler))])
        for so in (cev.get("sorunlar") or [])[:6]:
            (R.hata if so.get("ciddiyet") == "hata" else R.uyari)(so.get("aciklama", "sorun"), so.get("kare"))
    except gemini.GeminiYok as e:
        R.bilgi(f"yapay zeka kare incelemesi atlandı: {e}")
    return R.kaydet(slug, f"{dur:.0f} sn" + (f", {R.ek['lufs']:.0f} LUFS" if "lufs" in R.ek else "") + (f", senkron {R.ek['senkron']}" if "senkron" in R.ek else ""))


def ses_onarli(slug, deneme=2):
    """Ses metinle uyuşmuyorsa (Gemini yanlış okuduysa) sesi ücretsiz kotayla en fazla `deneme` kez yeniden ürettirir."""
    out = ses(slug)
    for k in range(deneme):
        if out.get("benzerlik") is None or out["benzerlik"] >= 0.85: break
        print(f"Ses metinle uyuşmuyor (%{out['benzerlik'] * 100:.0f}); yeniden üretiliyor ({k + 1}/{deneme})")
        import generate_assets as GA
        d, sc, pj = yukle(slug)
        try: GA.voice(sc["seslendirme_metni"], os.path.join(d, "ses.wav"))
        except Exception as e: print("Yeniden üretilemedi:", e); break
        out = ses(slug)
    return out


ASAMALAR = {"senaryo": senaryo, "ses": ses, "gorsel": gorsel, "kurgu": kurgu}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("asama", choices=list(ASAMALAR) + ["hepsi"]); ap.add_argument("--slug", required=True)
    ap.add_argument("--sert", action="store_true"); ap.add_argument("--onar", action="store_true", help="ses hatalıysa yeniden ürettir"); a = ap.parse_args()
    if a.onar: ASAMALAR["ses"] = ses_onarli
    if not re.fullmatch(r"[a-z0-9-]{1,60}", a.slug): sys.exit("Geçersiz proje adı")
    sonuc = []
    for k in (ASAMALAR if a.asama == "hepsi" else [a.asama]):
        try: sonuc.append(ASAMALAR[k](a.slug))
        except Exception as e:  # kontrolcü çökerse işi durdurmasın, panelde görünsün
            R = Rapor(k); R.hata(f"kontrolcü çalışırken hata: {e}"); sonuc.append(R.kaydet(a.slug, "Kontrol tamamlanamadı"))
    kotu = [s for s in sonuc if s["durum"] == "hata"]
    set_status("kontrol", "hata" if kotu else "tamam", f"{a.slug}: " + ", ".join(f"{s['asama']} {'✓' if s['durum'] == 'tamam' else '!' if s['durum'] == 'uyari' else '✗'}" for s in sonuc), f"projects/{a.slug}/kontrol")
    if a.sert and kotu: sys.exit(2)
