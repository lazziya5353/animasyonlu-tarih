#!/usr/bin/env python3
"""Quiz Studyo: 7 yeni quiz formatinin ortak renderer'i (rehber: docs/QUIZ_STUDYO_REHBERI.md).
  quiz_studyo.py hazirla script.json           -> semayi dogrular, sahneler + seslendirme_metni uretir
  quiz_studyo.py video script.json ses.wav out.mp4
  quiz_studyo.py kapak script.json kapak.jpg
Formatlar: hangisi-once, dogru-yanlis, bu-kim, haritada-bul, yili-tahmin, emoji-tarih, kelime-eksik.
Akis (her soru): soru sesi (satir satir) -> 3 sn yay sayaci (ZOR: 4 sn) -> cevap + alt bilgi.
Ses tek parca TTS; satir sinirlari Whisper kelime zamanlariyla bulunur, en sessiz noktadan kesilir."""
import json, math, os, re, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
FD = os.path.join(ROOT, "engine", "fonts") + "/"
W, H, FPS, SR = 1080, 1920, 30, 48000
CX = 540
DOGRU = (46, 170, 92); YANLIS = (200, 52, 46); ZOR_RENK = (196, 48, 40)
EMOJI_FONT = [p for p in ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", os.path.join(FD, "NotoColorEmoji.ttf")) if os.path.exists(p)]
FORMATLAR = {
    "hangisi-once": "HANGİSİ ÖNCE?", "dogru-yanlis": "DOĞRU MU YANLIŞ MI?", "bu-kim": "BU KİM?", "haritada-bul": "HARİTADA BUL",
    "yili-tahmin": "YILI TAHMİN ET", "emoji-tarih": "EMOJİ İLE TARİH", "kelime-eksik": "BİR KELİME EKSİK"}
HARF = "ABCD"
TR = str.maketrans("iı", "İI")
def up(t): return t.translate(TR).upper()
def hexrgb(h, d):
    try: h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception: return d

# ---------------------------------------------------------------- tema
class Tema:
    def __init__(self, SJ):
        cfg = json.load(open(os.path.join(ROOT, "config", "quiz_tema.json")))
        self.ad = SJ.get("tema", "tarih") if SJ.get("tema") in ("tarih", "spor") else "tarih"; c = cfg[self.ad]
        self.handle = c["handle"]; self.ses_stil = c["ses_stil"]
        if self.ad == "tarih":
            self.bg, self.glow, self.acc, self.acc2 = (14, 10, 7), (70, 45, 22), (232, 196, 120), (232, 196, 120)
            self.txt, self.mut, self.kart = (255, 255, 255), (225, 210, 190), (20, 14, 9)
            self.f_bas, self.f_kalin, self.f_metin = "Cinzel-700", "Montserrat-900", "Montserrat-700"
        else:
            tk = SJ.get("takim") or {}
            self.acc = hexrgb(tk.get("ana", ""), hexrgb(c["ana"], (31, 209, 122)))
            self.acc2 = hexrgb(tk.get("ikinci", ""), hexrgb(c["ikinci"], (255, 200, 61)))
            self.bg, self.glow = (6, 13, 28), (8, 62, 44)
            self.txt, self.mut, self.kart = (255, 255, 255), (196, 214, 230), (10, 22, 40)
            self.f_bas, self.f_kalin, self.f_metin = "BebasNeue-Regular", "BarlowCondensed-ExtraBold", "BarlowCondensed-Bold"
    def F(self, rol, s):
        n = {"bas": self.f_bas, "kalin": self.f_kalin, "metin": self.f_metin}.get(rol, rol)
        return ImageFont.truetype(FD + n + ".ttf", s)

def arkaplan_hazirla(yol):
    """Yuklenen / uretilen arka plan: kapla-kirp, bulanik, %38 parlaklik."""
    im = ImageOps.fit(Image.open(yol).convert("RGB"), (W, H), Image.LANCZOS)
    return ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(7))).enhance(0.38)

def zemin(T, bgsrc=None):
    if bgsrc is not None: return bgsrc.copy()
    im = Image.new("RGB", (W, H), T.bg)
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse((CX-640, 1060-640, CX+640, 1060+640), fill=255)
    im = Image.composite(Image.new("RGB", (W, H), T.glow), im, g.filter(ImageFilter.GaussianBlur(260)))
    if T.ad == "spor":  # stadyum: sik cim seritleri, saha cizgileri, iki projektor isigi
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for i in range(0, H, 160): d.rectangle((0, i, W, i + 80), fill=(255, 255, 255, 7))
        d.line((0, 1060, W, 1060), fill=(255, 255, 255, 22), width=4); d.ellipse((CX-230, 830, CX+230, 1290), outline=(255, 255, 255, 22), width=4)
        d.rectangle((CX-300, 1600, CX+300, H+10), outline=(255, 255, 255, 18), width=4)
        for x in (60, W-60):
            gl = Image.new("L", (W, H), 0); ImageDraw.Draw(gl).ellipse((x-260, -260, x+260, 260), fill=120)
            lay.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (W, H), v) for v in (230, 240, 255)], gl.filter(ImageFilter.GaussianBlur(120)))))
        im = im.convert("RGBA"); im.alpha_composite(lay); im = im.convert("RGB")
    return im

# ---------------------------------------------------------------- metin yardimcilari
KAYIT = []  # (ad, kutu, kap) : kontrol icin metin kutulari
def wrap(d, t, f, mw):
    out, cur = [], ""
    for w in t.split():
        s = (cur + " " + w).strip()
        if d.textlength(s, font=f) <= mw or not cur: cur = s
        else: out.append(cur); cur = w
    return out + [cur]

def sigdir(d, t, T, rol, size, mw, maxl, minsize=26):
    while True:
        f = T.F(rol, size); ls = wrap(d, t, f, mw)
        if (len(ls) <= maxl and all(d.textlength(l, font=f) <= mw for l in ls)) or size <= minsize: return f, ls
        size -= 2

def blok(d, T, t, rol, size, kutu, maxl, renk, ad, minsize=26, ls_k=1.22, valign="m"):
    """Metni kutuya (x0,y0,x1,y1) sigdirip ortalar; satir kutularini KAYIT'a yazar."""
    x0, y0, x1, y1 = kutu; mw = x1 - x0
    while True:
        f, ls = sigdir(d, t, T, rol, size, mw, maxl, minsize); lh = int(f.size*ls_k); th = lh*len(ls)
        if th <= y1 - y0 or f.size <= minsize: break
        size = f.size - 2
    y = y0 + ((y1 - y0 - th)//2 if valign == "m" else 0); cx = (x0 + x1)//2
    for l in ls:
        d.text((cx, y + lh//2), l, font=f, fill=renk, anchor="mm"); b = d.textbbox((cx, y + lh//2), l, font=f, anchor="mm")
        KAYIT.append((ad, list(b), list(kutu))); y += lh
    return f.size

def hap(d, T, x, y, t, fill, size=30, txt=(255, 245, 230)):
    f = T.F("kalin", size); w = d.textlength(t, font=f) + 2*size*0.8; h = size*1.6
    d.rounded_rectangle((x - w/2, y - h/2, x + w/2, y + h/2), h/2, fill=fill, outline=T.acc2, width=2)
    d.text((x, y + 1), t, font=f, fill=txt, anchor="mm"); KAYIT.append(("hap", list(d.textbbox((x, y+1), t, font=f, anchor="mm")), None))

def baslik(im, T, fmt, logo=None):
    d = ImageDraw.Draw(im); y0 = 0
    if logo is not None:
        lg = logo.copy(); lg.thumbnail((120, 120)); im.paste(lg, (CX - lg.width//2, 70 + (120 - lg.height)//2), lg); y0 = 30
    ad = FORMATLAR[fmt]
    ust = "ANİMASYONLU TARİH QUIZ" if T.ad == "tarih" else "SPOR TARİHİ QUIZ"
    f = T.F("kalin", 40); s = 8; ws = [d.textlength(ch, font=f) for ch in ust]; x = CX - (sum(ws) + s*(len(ust)-1))/2
    for ch, w in zip(ust, ws): d.text((x, 225 + y0), ch, font=f, fill=T.txt, anchor="ls"); x += w + s
    blok(d, T, ad, "bas", 92 if T.ad == "tarih" else 120, (60, 245 + y0, 1020, 350 + y0), 1, T.acc, "baslik", 50)
    if T.ad == "spor": d.rectangle((CX - 90, 362 + y0, CX + 90, 368 + y0), fill=T.acc2)
    d.text((CX, 1830), T.handle, font=T.F("kalin", 36), fill=T.txt, anchor="ms")

# ---------------------------------------------------------------- sema
def satirlar(fmt, q):
    """Bir sorunun seslendirilen satirlari: (soru satirlari listesi, cevap satiri)."""
    if fmt == "hangisi-once":
        return ["Hangisi daha önce oldu?", f"A: {q['a']['metin']}.", f"B: {q['b']['metin']}."], f"Cevap {q['dogru']}: {q[q['dogru'].lower()]['metin']}."
    if fmt == "dogru-yanlis":
        return [q["ifade"]], ("Doğru! " if q["dogru"] else "Yanlış! ") + q["duzeltme"]
    if fmt == "bu-kim":
        return ["Bu kim?"] + [x for x in q["ipuclari"]], q["cevap"] + "."
    if fmt == "haritada-bul":
        d = q["secenekler"][q["dogru"]]; return [q["soru"]], f"Cevap {HARF[q['dogru']]}: {d['ad']}."
    if fmt == "yili-tahmin":
        return [q["soru"]], f"Cevap {q['secenekler'][q['dogru']]}."
    if fmt == "emoji-tarih":
        return [q.get("soru") or "Bu emojiler hangi olayı anlatıyor?"], q["cevap"] + "."
    if fmt == "kelime-eksik":
        return ["Eksik kelime ne?", q["soz"].replace("___", "...")], q["soz"].replace("___", q["secenekler"][q["dogru"]])
    raise ValueError(fmt)

def alt_bilgi(fmt, q):
    if fmt == "hangisi-once": return f"A · {q['a']['yil']}   ·   B · {q['b']['yil']}"
    if fmt == "kelime-eksik": return "— " + q["soyleyen"]
    if fmt == "dogru-yanlis": return q.get("alt_bilgi") or q.get("duzeltme", "")
    return q.get("alt_bilgi", "")

def dogrula(SJ):
    """Panel ve workflow ayni kurallari kullanir. Hata listesi dondurur."""
    h = []; fmt = SJ.get("format")
    if fmt not in FORMATLAR: return [f"format bilinmiyor: {fmt}"]
    Q = SJ.get("sorular") or []
    if not 6 <= len(Q) <= 15: h.append(f"soru sayisi {len(Q)} (6-15 olmali; video icin 8-15 onerilir)")
    for i, q in enumerate(Q, 1):
        e = lambda m: h.append(f"soru {i}: {m}")
        if q.get("zorluk", "orta") not in ("kolay", "orta", "zor"): e("zorluk kolay/orta/zor olmali")
        try: satirlar(fmt, q)
        except Exception as x: e(f"eksik alan {x}"); continue
        if not alt_bilgi(fmt, q).strip(): e("alt_bilgi bos")
        if fmt == "hangisi-once":
            if q["dogru"] not in ("A", "B"): e("dogru A ya da B")
            ya, yb = q["a"]["yil"], q["b"]["yil"]
            if not (isinstance(ya, int) and isinstance(yb, int)) or ya == yb: e("yillar tam sayi ve farkli olmali")
            elif (ya < yb) != (q["dogru"] == "A"): e("dogru secenek yillarla uyusmuyor")
        if fmt == "dogru-yanlis" and not isinstance(q.get("dogru"), bool): e("dogru true/false olmali")
        if fmt == "bu-kim" and len(q["ipuclari"]) != 3: e("tam 3 ipucu olmali")
        if fmt in ("haritada-bul", "yili-tahmin", "kelime-eksik"):
            if len(q["secenekler"]) != 4 or q["dogru"] not in range(4): e("4 secenek ve dogru 0-3 olmali")
        if fmt == "haritada-bul":
            for s in q["secenekler"]:
                if not (-180 <= s.get("lon", 999) <= 180 and -70 <= s.get("lat", 999) <= 75): e(f"koordinat hatali: {s}")
        if fmt == "yili-tahmin" and len(set(q["secenekler"])) != 4: e("yillar farkli olmali")
        if fmt == "kelime-eksik" and q["soz"].count("___") != 1: e("sozde tam bir ___ olmali")
        if fmt == "emoji-tarih":
            if not 2 <= len(q["emoji"]) <= 6: e("2-6 emoji olmali")
            if EMOJI_FONT:
                from fontTools.ttLib import TTFont
                cm = TTFont(EMOJI_FONT[0]).getBestCmap()
                for em in q["emoji"]:
                    eks = [hex(ord(c)) for c in em if ord(c) not in cm and ord(c) not in (0x200D, 0xFE0F)]
                    if eks: e(f"emoji fontta yok (tofu olur): {em} {eks}")
        ql, al = satirlar(fmt, q)
        sz = [q["cevap"]] if fmt in ("bu-kim", "emoji-tarih") else [q["secenekler"][q["dogru"]]] if fmt == "kelime-eksik" else []
        for w in sz:
            k = norm(w).split()
            if k and any(re.search(r"\b" + re.escape(k[0][:max(4, len(k[0]) - 2)]), norm(x)) for x in ql): e(f"soru metni cevabi ele veriyor ({w})")
    return h

def norm(t): return re.sub(r"[^a-zçğıöşü0-9 ]", " ", t.replace("İ", "i").replace("I", "ı").lower().translate(str.maketrans("âîûÂÎÛ", "aiuaiu"))).strip()

def hazirla(path):
    from sayi_yazi import metni_yaziya
    SJ = json.load(open(path)); h = dogrula(SJ)
    if h: print("\n".join(h)); sys.exit("HATA: script.json gecersiz")
    T = Tema(SJ); fmt = SJ["format"]; n = len(SJ["sorular"])
    sah = [dict(lines=[SJ.get("giris") or f"{FORMATLAR[fmt].title()}! {n} soru, bakalım kaçını bileceksin?"], tip="giris")]
    for i, q in enumerate(SJ["sorular"]):
        ql, al = satirlar(fmt, q)
        for l in ql: sah.append(dict(lines=[l], tip="soru", soru=i))
        sah.append(dict(lines=[al], tip="cevap", soru=i, zorluk=q.get("zorluk", "orta")))
    sah.append(dict(lines=[SJ.get("kapanis") or "Kaçını bildin? Yorumlara yaz!"], tip="kapanis"))
    for s in sah: s.update(big="", sub="", label="QUIZ", fx=[], image="images/bg.jpg", prompt="quiz")
    SJ["sahneler"] = sah; SJ["seslendirme_metni"] = "\n".join(metni_yaziya(s["lines"][0]) for s in sah)
    SJ.setdefault("ses_stil", T.ses_stil); SJ.setdefault("baslik", FORMATLAR[fmt].title())
    json.dump(SJ, open(path, "w"), ensure_ascii=False, indent=1); print(f"hazir: {fmt}, {n} soru, {len(sah)} ses satiri")

# ---------------------------------------------------------------- ses hizalama
def rms_kare(au):
    return np.sqrt((au[:len(au)//480*480].reshape(-1, 480)**2).mean(1))  # 10 ms

def hizala(au, satir):
    """Whisper kelime zamanlari ile satir sinirlari (sn). Kesim, sinir penceresindeki en sessiz noktadan."""
    from faster_whisper import WhisperModel
    from sayi_yazi import metni_yaziya
    import difflib
    m = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), compute_type="int8")
    a16 = au[::3].astype(np.float32)  # 48k -> 16k
    segs, _ = m.transcribe(a16, language="tr", word_timestamps=True, vad_filter=False, beam_size=5)
    ww = []
    for s in segs:
        for w in s.words:
            for t in norm(metni_yaziya(w.word)).split(): ww.append((w.start, w.end, t))
    sw = [(k, t) for k, s in enumerate(satir) for t in norm(metni_yaziya(s)).split()]
    sm = difflib.SequenceMatcher(None, [t for _, t in sw], [t for _, _, t in ww], autojunk=False)
    M = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for o in range(i2 - i1): M[i1 + o] = j1 + o
    oran = len(M)/max(1, len(sw)); print(f"hizalama: {len(M)}/{len(sw)} kelime eslesti ({oran:.0%})")
    if oran < 0.6: sys.exit("HATA: ses metinle uyusmuyor (baska projenin sesi / eksik okuma?)")
    ilk, son = {}, {}
    for i, (k, _) in enumerate(sw):
        if i in M: ilk.setdefault(k, ww[M[i]][0]); son[k] = ww[M[i]][1]
    tot = len(au)/SR; fr = rms_kare(au); K = len(satir)
    for k in range(K):  # eslesmeyen satir: komsulardan karakter oraniyla tahmin
        if k not in ilk:
            p = max([j for j in range(k) if j in son], default=None); nx = min([j for j in range(k+1, K) if j in ilk], default=None)
            t0 = son[p] if p is not None else 0.0; t1 = ilk[nx] if nx is not None else tot
            ilk[k], son[k] = t0 + 0.05, max(t0 + 0.1, t1 - 0.05); print(f"uyari: satir {k} eslesmedi, tahmin")
    sinir = [0.0]
    for k in range(K - 1):
        a, b = son[k] - 0.12, ilk[k+1] + 0.12
        a, b = max(a, sinir[-1] + 0.05), max(b, a + 0.02)
        i0, i1 = int(a*100), max(int(b*100), int(a*100) + 1); w = fr[i0:i1]
        if len(w) == 0: sinir.append((a + b)/2); continue
        q = w < 10**(-40/20); best = (0, int(np.argmin(w)), int(np.argmin(w)) + 1); j = 0
        while j < len(q):
            if q[j]:
                e = j
                while e < len(q) and q[e]: e += 1
                if e - j > best[0]: best = (e - j, j, e)
                j = e
            else: j += 1
        sinir.append((i0 + (best[1] + best[2])/2)/100)
    sinir.append(tot); return sinir

def parca(au, t0, t1):
    sg = au[int(t0*SR):int(t1*SR)].copy(); fr = rms_kare(sg); on = np.where(fr > 10**(-42/20))[0]
    if len(on) == 0: return sg[:0]
    sg = sg[max(0, on[0]*480 - int(0.05*SR)):min(len(sg), (on[-1] + 1)*480 + int(0.08*SR))]
    fr = rms_kare(sg); q = fr < 10**(-38/20); j = 0; kes = []
    while j < len(q):  # 0.4 sn'den uzun ic sessizlik -> 0.25 sn
        if q[j]:
            e = j
            while e < len(q) and q[e]: e += 1
            if e - j > 40: kes.append((j*480 + int(0.125*SR), e*480 - int(0.125*SR)))
            j = e
        else: j += 1
    for c0, c1 in reversed(kes): sg = np.concatenate([sg[:c0], sg[c1:]])
    f = min(240, len(sg)//2); r = np.linspace(0, 1, f, dtype=np.float32); sg[:f] *= r; sg[len(sg)-f:] *= r[::-1]
    return sg

# ---------------------------------------------------------------- format cizimleri
GOVDE = (60, 740, 1020, 1450)   # format govdesi
SORU = (70, 505, 1010, 715)     # soru metni
CEVAP = (60, 1470, 1020, 1730)  # cevap kutusu / sayac alani

def resim(SJd, yol, kutu, daire=False):
    if not yol: return None
    p = os.path.join(SJd, yol)
    if not os.path.exists(p): sys.exit(f"HATA: gorsel yok: {p}")
    im = ImageOps.fit(Image.open(p).convert("RGB"), kutu, Image.LANCZOS)
    if daire:
        m = Image.new("L", kutu, 0); ImageDraw.Draw(m).ellipse((0, 0, kutu[0]-1, kutu[1]-1), fill=255); im.putalpha(m)
    else: im.putalpha(255)
    return im

def kart(d, T, b, durum=None, r=26):
    fill = {None: T.kart, "dogru": DOGRU, "yanlis": YANLIS, "soluk": tuple(int(c*0.6) for c in T.kart)}[durum]
    ol = {None: T.acc, "dogru": (150, 240, 180), "yanlis": (255, 150, 140), "soluk": tuple(int(c*0.45) for c in T.acc)}[durum]
    d.rounded_rectangle(b, r, fill=fill, outline=ol, width=4)

def rozet(d, T, x, y, L, durum=None):
    d.ellipse((x-34, y-34, x+34, y+34), fill=T.acc if durum != "soluk" else tuple(int(c*0.5) for c in T.acc))
    d.text((x, y + 2), L, font=T.F("kalin", 40), fill=T.bg, anchor="mm")

class Format:
    def __init__(self, SJ, T, SJd):
        self.SJ, self.T, self.d0, self.fmt = SJ, T, SJd, SJ["format"]; self.cache = {}
    def soru_metni(self, q):
        f = self.fmt
        if f == "hangisi-once": return "Hangisi daha önce oldu?"
        if f == "dogru-yanlis": return "Doğru mu, yanlış mı?"
        if f == "bu-kim": return "BU KİM?"
        if f == "emoji-tarih": return q.get("soru") or "Bu emojiler hangi olayı anlatıyor?"
        if f == "kelime-eksik": return "Eksik kelime hangisi?"
        return q["soru"]
    def ipucu_sayisi(self): return 3 if self.fmt == "bu-kim" else 0

    def ciz(self, im, qi, ac, acik):
        """ac: acilan ipucu sayisi (bu-kim), acik: cevap gorunur mu"""
        T, q, f = self.T, self.SJ["sorular"][qi], self.fmt; d = ImageDraw.Draw(im); x0, y0, x1, y1 = GOVDE
        dg = q.get("dogru")
        if f == "hangisi-once":
            for j, L in enumerate("AB"):
                b = (x0, y0 + j*365, x1, y0 + j*365 + 330); o = q[L.lower()]
                du = None if not acik else ("dogru" if L == dg else "soluk"); kart(d, T, b, du)
                img = resim(self.d0, o.get("gorsel"), (250, 250)); tx = b[0] + 110
                if img is not None: im.paste(img, (b[0] + 110, b[1] + 40), img); tx = b[0] + 380
                rozet(d, T, b[0] + 58, b[1] + 165, L, du)
                blok(d, T, o["metin"], "metin", 50, (tx, b[1] + 30, b[2] - 30, b[3] - (95 if acik else 30)), 3, T.txt, f"kart{L}", 30)
                if acik: blok(d, T, str(o["yil"]), "bas", 64, (tx, b[3] - 92, b[2] - 30, b[3] - 18), 1, (255, 255, 255) if L == dg else T.mut, f"yil{L}")
        elif f == "dogru-yanlis":
            b = (x0, y0 + 40, x1, y1 - 40); kart(d, T, b, None if not acik else ("dogru" if dg else "yanlis"))
            d.text((CX, b[1] + 70), "“", font=T.F("bas", 140), fill=T.acc, anchor="mm")
            blok(d, T, q["ifade"], "metin", 60, (b[0] + 60, b[1] + 120, b[2] - 60, b[3] - 50), 6, T.txt, "ifade", 34)
        elif f == "bu-kim":
            pk = (300, 300); px, py = CX - 150, y0
            img = resim(self.d0, q.get("gorsel"), pk, True)
            d.ellipse((px - 8, py - 8, px + 308, py + 308), outline=DOGRU if acik else T.acc, width=6)
            if img is not None:
                if acik: im.paste(img, (px, py), img)
                elif q.get("siluet", True):
                    bl = img.filter(ImageFilter.GaussianBlur(22)); bl = ImageEnhance.Brightness(bl).enhance(0.35)
                    im.paste(bl, (px, py), bl)
                    d.text((CX, py + 150), "?", font=T.F("bas", 200), fill=T.acc, anchor="mm")
            else:
                sl = Image.new("RGBA", pk, T.kart + (255,)); sd = ImageDraw.Draw(sl); sc = tuple(int(c*0.5) for c in T.acc)
                sd.ellipse((90, 45, 210, 165), fill=sc); sd.ellipse((30, 185, 270, 425), fill=sc)
                m = Image.new("L", pk, 0); ImageDraw.Draw(m).ellipse((0, 0, 299, 299), fill=255); sl.putalpha(m); im.paste(sl, (px, py), sl)
                if not acik: d.text((CX, py + 110), "?", font=T.F("bas", 120), fill=T.acc, anchor="mm")
            for j, ip in enumerate(q["ipuclari"]):
                b = (x0, py + 330 + j*128, x1, py + 330 + j*128 + 112)
                if j < ac:
                    kart(d, T, b, None, 20); rozet(d, T, b[0] + 52, (b[1] + b[3])//2, str(j + 1))
                    blok(d, T, ip, "metin", 40, (b[0] + 100, b[1] + 8, b[2] - 24, b[3] - 8), 2, T.txt, f"ipucu{j}", 26)
                else:
                    d.rounded_rectangle(b, 20, outline=tuple(int(c*0.5) for c in T.acc), width=3)
                    d.text((CX, (b[1] + b[3])//2), f"İPUCU {j + 1}", font=T.F("kalin", 34), fill=tuple(int(c*0.55) for c in T.acc), anchor="mm")
        elif f == "haritada-bul":
            pan, pins = self.harita(qi); b = (x0, y0, x1, y1)
            im.paste(pan, (x0, y0), pan)
            d.rounded_rectangle(b, 26, outline=T.acc, width=4)
            for j, (px, py) in enumerate(pins):
                du = None if not acik else ("dogru" if j == dg else "soluk")
                col = DOGRU if du == "dogru" else (T.acc if du is None else (90, 90, 90))
                d.ellipse((px - 30, py - 30, px + 30, py + 30), fill=col, outline=(255, 255, 255), width=4)
                d.text((px, py + 2), HARF[j], font=T.F("kalin", 34), fill=(255, 255, 255) if du == "dogru" else T.bg, anchor="mm")
                KAYIT.append((f"pin{j}", [px - 30, py - 30, px + 30, py + 30], [x0, y0, x1, y1]))
                if acik and j == dg:
                    nm = q["secenekler"][j]["ad"]; fnt = T.F("kalin", 38); tw = d.textlength(up(nm), font=fnt)
                    lx = min(max(px, x0 + tw/2 + 30), x1 - tw/2 - 30); ly = py - 62 if py - 62 > y0 + 40 else py + 62
                    d.rounded_rectangle((lx - tw/2 - 16, ly - 26, lx + tw/2 + 16, ly + 26), 14, fill=(0, 0, 0))
                    d.text((lx, ly + 1), up(nm), font=fnt, fill=(255, 255, 255), anchor="mm")
                    KAYIT.append(("pinad", list(d.textbbox((lx, ly + 1), up(nm), font=fnt, anchor="mm")), [x0, y0, x1, y1]))
        elif f in ("yili-tahmin", "kelime-eksik"):
            if f == "kelime-eksik":
                b = (x0, y0, x1, y0 + 400); kart(d, T, b)
                d.text((b[0] + 50, b[1] + 60), "“", font=T.F("bas", 140), fill=T.acc, anchor="mm")
                kel = q["secenekler"][dg]; s = q["soz"].replace("___", up(kel) if acik else "______")
                blok(d, T, s, "metin", 54, (b[0] + 60, b[1] + 60, b[2] - 60, b[3] - 40), 5, T.txt, "soz", 30)
                gy0, gh = y0 + 440, 120
            else: gy0, gh = y0 + 30, 300
            for j, v in enumerate(q["secenekler"]):
                cx0 = x0 + (j % 2)*490; cy0 = gy0 + (j // 2)*(gh + 26); b = (cx0, cy0, cx0 + 470, cy0 + gh)
                du = None if not acik else ("dogru" if j == dg else "soluk"); kart(d, T, b, du, 22)
                rozet(d, T, b[0] + 50, (b[1] + b[3])//2, HARF[j], du)
                blok(d, T, str(v), "bas" if f == "yili-tahmin" else "kalin", 96 if f == "yili-tahmin" else 46, (b[0] + 96, b[1] + 10, b[2] - 20, b[3] - 10), 1 if f == "yili-tahmin" else 2,
                     (255, 255, 255) if du != "soluk" else (150, 150, 150), f"secenek{j}", 26)
        elif f == "emoji-tarih":
            E = q["emoji"]; n = len(E); per = n if n <= 3 else math.ceil(n/2); rows = [E[:per], E[per:]] if n > 3 else [E]
            sz = 220 if per <= 3 else 180
            b = (x0, y0 + 20, x1, y0 + 120 + len(rows)*(sz + 50)); kart(d, T, b)
            for r, row in enumerate(rows):
                for j, em in enumerate(row):
                    ex = CX + (j - (len(row) - 1)/2)*(sz + 40); ey = b[1] + 60 + r*(sz + 50) + sz/2
                    g = self.emoji(em, sz); im.paste(g, (int(ex - sz/2), int(ey - sz/2)), g)
                    KAYIT.append(("emoji", [int(ex - sz/2), int(ey - sz/2), int(ex + sz/2), int(ey + sz/2)], list(b)))
            if q.get("ipucu"): hap(d, T, CX, b[3] + 60, up(q["ipucu"]), tuple(int(c*0.35) for c in T.acc), 32)

    def emoji(self, em, sz):
        k = (em, sz)
        if k not in self.cache:
            if not EMOJI_FONT: sys.exit("HATA: Noto Color Emoji fontu yok (fonts-noto-color-emoji kur)")
            f = ImageFont.truetype(EMOJI_FONT[0], 109); c = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
            ImageDraw.Draw(c).text((10, 100), em, font=f, embedded_color=True, anchor="lm")
            bb = c.getbbox()
            if not bb: sys.exit(f"HATA: emoji cizilemedi: {em}")
            g = c.crop(bb); a = np.asarray(g).astype(int)
            renkli = ((a[..., 3] > 128) & (np.ptp(a[..., :3], axis=2) > 40)).sum()
            if renkli < 300 or g.width > 1.6*g.height: sys.exit(f"HATA: emoji tofu/kutu ya da birlesik degil: {em} (renkli {renkli}, {g.size})")
            sc = sz/max(g.size); g = g.resize((max(1, int(g.width*sc)), max(1, int(g.height*sc))), Image.LANCZOS)
            o = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); o.paste(g, ((sz - g.width)//2, (sz - g.height)//2)); self.cache[k] = o
        return self.cache[k]

    def harita(self, qi):
        if ("h", qi) in self.cache: return self.cache[("h", qi)]
        sys.path.insert(0, os.path.join(ROOT, "engine")); from deprem import Harita
        q = self.SJ["sorular"][qi]; S = q["secenekler"]; x0, y0, x1, y1 = GOVDE; pw, ph = x1 - x0, y1 - y0
        lo = [s["lon"] for s in S]; la = [s["lat"] for s in S]; C = math.cos(math.radians(sum(la)/4))
        clon, clat = (min(lo) + max(lo))/2, (min(la) + max(la))/2
        span_x = (max(lo) - min(lo))*1.5; span_y = (max(la) - min(la))*1.5
        wdeg = max(span_x*W/pw, span_y/C*W/ph, q.get("min_genislik", 2.5))
        hm = Harita("uydu"); ox, oy = (W - pw)//2, (H - ph)//2
        for _ in range(6):  # altlik kenarinda kamera kayarsa pin disarida kalabilir: biraz uzaklas
            fr, to, _s = hm.kare((clon, clat, wdeg))
            pins = [(to(s["lon"], s["lat"])[0] - ox + x0, to(s["lon"], s["lat"])[1] - oy + y0) for s in S]
            if all(x0 + 45 <= px <= x1 - 45 and y0 + 45 <= py <= y1 - 45 for px, py in pins): break
            wdeg *= 1.25
        else: sys.exit(f"HATA: soru {qi+1} pin panel disinda {[(round(a), round(b)) for a, b in pins]}")
        pan = fr.crop((ox, oy, ox + pw, oy + ph)).convert("RGBA")
        m = Image.new("L", (pw, ph), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, pw - 1, ph - 1), 26, fill=255); pan.putalpha(m)
        for a in range(4):
            for b2 in range(a):
                if math.dist(pins[a], pins[b2]) < 70: sys.exit(f"HATA: soru {qi+1} pinler cakisiyor ({HARF[a]}/{HARF[b2]}); secenekleri uzaklastir ya da min_genislik kucult")
        self.cache[("h", qi)] = (pan, pins); return pan, pins

# ---------------------------------------------------------------- ekran durumlari
def cevap_kutusu(im, T, fmt, q, al):
    d = ImageDraw.Draw(im); x0, y0, x1, y1 = CEVAP
    renk = YANLIS if fmt == "dogru-yanlis" and not q["dogru"] else DOGRU
    d.rounded_rectangle(CEVAP, 30, fill=tuple(int(c*0.22) for c in renk), outline=renk, width=6)
    if fmt == "dogru-yanlis": metin = "DOĞRU" if q["dogru"] else "YANLIŞ"
    elif fmt in ("hangisi-once",): metin = f"{q['dogru']} DAHA ÖNCE"
    elif fmt == "haritada-bul": metin = f"{HARF[q['dogru']]} · {up(q['secenekler'][q['dogru']]['ad'])}"
    elif fmt == "yili-tahmin": metin = str(q["secenekler"][q["dogru"]])
    elif fmt == "kelime-eksik": metin = up(q["secenekler"][q["dogru"]])
    else: metin = up(q["cevap"])
    blok(d, T, metin, "bas", 78, (x0 + 40, y0 + 22, x1 - 40, y0 + 150), 2, (255, 255, 255) if fmt != "dogru-yanlis" else (renk[0] + 40 if renk[0] < 215 else 255, min(255, renk[1] + 60), min(255, renk[2] + 40)), "cevap", 40)
    blok(d, T, alt_bilgi(fmt, q), "kalin", 38, (x0 + 40, y0 + 158, x1 - 40, y1 - 18), 2, T.mut, "alt", 24)

def sayac(im, T, p, kalan):
    d = ImageDraw.Draw(im); cy = (CEVAP[1] + CEVAP[3])//2; r = 95
    d.ellipse((CX - r, cy - r, CX + r, cy + r), fill=T.kart, outline=tuple(int(c*0.4) for c in T.acc), width=10)
    d.arc((CX - r, cy - r, CX + r, cy + r), -90, -90 + 360*p, fill=T.acc, width=10)
    d.text((CX, cy + 4), str(kalan), font=T.F("bas", 96), fill=T.txt, anchor="mm")

def ust(im, T, k, n, zor, soru):
    d = ImageDraw.Draw(im)
    d.text((CX, 470), f"{k} / {n}", font=T.F("kalin", 40), fill=T.acc, anchor="ms")
    if zor: hap(d, T, CX + 150, 456, "ZOR", ZOR_RENK, 22)
    blok(d, T, soru, "metin", 54, SORU, 3, T.txt, "soru", 34)

# ---------------------------------------------------------------- video
def video(spath, wav, out):
    SJ = json.load(open(spath)); h = dogrula(SJ)
    if h: print("\n".join(h)); sys.exit("HATA: script.json gecersiz")
    T = Tema(SJ); fmt = SJ["format"]; Q = SJ["sorular"]; n = len(Q); d0 = os.path.dirname(os.path.abspath(spath))
    sah = SJ["sahneler"]; satir = [s["lines"][0] for s in sah]
    bgsrc = arkaplan_hazirla(os.path.join(d0, SJ["arkaplan"])) if SJ.get("arkaplan") and os.path.exists(os.path.join(d0, SJ["arkaplan"])) else None
    if SJ.get("arkaplan") and bgsrc is None: print("uyari: arkaplan dosyasi yok, tema zemini kullanildi")
    logo = None
    if SJ.get("logo") and os.path.exists(os.path.join(d0, SJ["logo"])): logo = Image.open(os.path.join(d0, SJ["logo"])).convert("RGBA")
    B = zemin(T, bgsrc); baslik(B, T, fmt, logo); KAYIT.clear()
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    au = np.frombuffer(raw, np.float32).copy()
    sn = json.load(open(os.environ["QS_SINIR"])) if os.environ.get("QS_SINIR") else hizala(au, satir)  # QS_SINIR: yerel deneme
    P = [parca(au, sn[k], sn[k+1]) for k in range(len(satir))]
    for k, p in enumerate(P):
        if len(p) < SR*0.25: sys.exit(f"HATA: satir {k} sesi bos/kisa: {satir[k]!r}")
    z = lambda t: np.zeros(int(t*SR), np.float32); parts = []; t = 0.0
    def ekle(x):
        nonlocal t; parts.append(x); t += len(x)/SR
    ekle(P[0]); ekle(z(0.35)); ev = []; si = 1
    for i, q in enumerate(Q):
        zor = q.get("zorluk") == "zor"; e = dict(i=i, bas=t, satir=[]); ekle(z(0.3))
        while sah[si]["tip"] == "soru":
            t0 = t; ekle(P[si]); e["satir"].append((round(t0, 3), round(t, 3), satir[si])); ekle(z(0.3)); si += 1
        e["bekle"] = t - 0.3; ekle(z((4.0 if zor else 3.0) - 0.3))
        e["cevap"] = t; ekle(P[si]); e["cevap_bit"] = t; e["cevap_satir"] = satir[si]; si += 1
        ekle(z(1.3)); e["bit"] = t; ev.append(e)
    outro = t; ekle(P[si]); ekle(z(1.2))
    A = np.concatenate(parts); dur = len(A)/SR; t = sum(len(x) for x in parts)/SR
    assert abs(t - dur) < 0.01
    tmpa = out + ".a.wav"
    with wave.open(tmpa, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(A, -1, 1)*32767).astype("<i2").tobytes())
    FMT = Format(SJ, T, d0)
    # durum goruntuleri (onbellek): soru i, acilan ipucu c, cevap acik mi
    durum = {}; kutular = {}
    def goruntu(i, c, acik, sayac_p=None):
        k = (i, c, acik)
        if k not in durum:
            KAYIT.clear(); im = B.copy(); q = Q[i]
            ust(im, T, i + 1, n, q.get("zorluk") == "zor", FMT.soru_metni(q)); FMT.ciz(im, i, c, acik)
            if acik: cevap_kutusu(im, T, fmt, q, None); kutular[i] = [list(x) for x in KAYIT]
            durum.clear() if len(durum) > 12 else None; durum[k] = im
        return durum[k]
    giris = B.copy(); dg = ImageDraw.Draw(giris); KAYIT.clear()
    blok(dg, T, FORMATLAR[fmt], "bas", 130, (60, 760, 1020, 1060), 2, T.acc, "g1", 60)
    blok(dg, T, f"{n} SORU", "kalin", 60, (60, 1080, 1020, 1160), 1, T.txt, "g2")
    blok(dg, T, "KAÇINI BİLECEKSİN?", "kalin", 46, (60, 1170, 1020, 1240), 1, T.mut, "g3")
    nz = sum(q.get("zorluk") == "zor" for q in Q)
    if nz: hap(dg, T, CX, 1310, f"{nz} ZOR SORU", ZOR_RENK, 30)
    son = B.copy(); ds = ImageDraw.Draw(son)
    blok(ds, T, "KAÇINI BİLDİN?", "bas", 130, (60, 800, 1020, 1060), 2, T.acc, "s1", 60)
    blok(ds, T, "YORUMLARA YAZ", "kalin", 56, (60, 1080, 1020, 1160), 1, T.txt, "s2")
    blok(ds, T, f"TAKİP ET · {T.handle}", "kalin", 40, (60, 1180, 1020, 1240), 1, T.mut, "s3")
    WMf = T.F("kalin", 46); wb = WMf.getbbox(T.handle)
    WM = Image.new("RGBA", (wb[2] + 8, wb[3] + 8), (0, 0, 0, 0)); ImageDraw.Draw(WM).text((4, 4), T.handle, font=WMf, fill=(255, 255, 255, 43))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", tmpa,
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(dur*FPS)):
        t = fi/FPS
        if t < ev[0]["bas"]: im = Image.blend(B, giris, min(1, t/0.4))
        elif t >= outro: im = Image.blend(B, son, min(1, (t - outro)/0.35))
        else:
            e = max((x for x in ev if t >= x["bas"]), key=lambda x: x["bas"]); i = e["i"]; q = Q[i]
            c = sum(1 for (s0, _, _) in e["satir"][1:] if t >= s0) if fmt == "bu-kim" else 0
            if t >= e["cevap"]:
                k = min(1, (t - e["cevap"])/0.3); im = Image.blend(goruntu(i, 3 if fmt == "bu-kim" else 0, False), goruntu(i, c, True), k) if k < 1 else goruntu(i, c, True).copy()
                if fmt == "haritada-bul":  # dogru pin nabiz atar
                    _, pins = FMT.harita(i); px, py = pins[q["dogru"]]; r = 34 + 22*((t - e["cevap"])*1.6 % 1)
                    ImageDraw.Draw(im).ellipse((px - r, py - r, px + r, py + r), outline=DOGRU, width=5)
            else:
                im = goruntu(i, c, False).copy()
                if t >= e["bekle"]:
                    L = e["cevap"] - e["bekle"]; sayac(im, T, min(1, (t - e["bekle"])/L), max(1, math.ceil(L - (t - e["bekle"]))))
            if q.get("zorluk") == "zor" and e["bas"] <= t < e["bas"] + 1.2:
                fa = min(1, (t - e["bas"])/0.15, (e["bas"] + 1.2 - t)/0.3)
                fl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(fl); ff = T.F("kalin", 40); ww = fd.textlength("ZOR SORU", font=ff) + 50
                fd.rounded_rectangle((CX - ww/2, 382, CX + ww/2, 432), 25, fill=ZOR_RENK + (int(235*fa),), outline=T.acc2 + (int(255*fa),), width=3)
                fd.text((CX, 408), "ZOR SORU", font=ff, fill=(255, 240, 215, int(255*fa)), anchor="mm")
                im = im.convert("RGBA"); im.alpha_composite(fl); im = im.convert("RGB")
            a = min(1, (t - e["bas"])/0.25, max(0, (e["bit"] - t)/0.25))
            if a < 1: im = Image.blend(B, im, a)
        im = im.convert("RGBA"); wx = int(CX - WM.width/2 + 230*math.sin(t*0.21)); wy = int(1060 - WM.height/2 + 380*math.sin(t*0.13 + 1.1))
        im.alpha_composite(WM, (wx, wy)); p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close(); p.wait(); os.remove(tmpa)
    json.dump(dict(format=fmt, tema=T.ad, mut=T.mut, sure=dur, outro=outro, sorular=ev, kutular=kutular), open(out + ".times.json", "w"), ensure_ascii=False)
    print("sure", round(dur, 1))

def kapak(spath, out):
    SJ = json.load(open(spath)); T = Tema(SJ); fmt = SJ["format"]; Q = SJ["sorular"]; d0 = os.path.dirname(os.path.abspath(spath))
    bg = arkaplan_hazirla(os.path.join(d0, SJ["arkaplan"])) if SJ.get("arkaplan") and os.path.exists(os.path.join(d0, SJ["arkaplan"])) else None
    logo = Image.open(os.path.join(d0, SJ["logo"])).convert("RGBA") if SJ.get("logo") and os.path.exists(os.path.join(d0, SJ["logo"])) else None
    im = zemin(T, bg); baslik(im, T, fmt, logo); FMT = Format(SJ, T, d0)
    ornek = zemin(T, bg); FMT.ciz(ornek, 0, 3, False)
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rectangle((GOVDE[0], GOVDE[1], GOVDE[2], GOVDE[3] + 60), fill=150); im = Image.composite(ornek, im, m.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im); KAYIT.clear()
    d.rounded_rectangle((60, 470, 1020, 720), 30, fill=T.kart, outline=T.acc, width=4)
    blok(d, T, "KAÇINI BİLECEKSİN?", "bas", 100, (90, 490, 990, 630), 1, T.acc, "k1", 50)
    nz = sum(q.get("zorluk") == "zor" for q in Q)
    blok(d, T, f"{len(Q)} SORU" + (f" · {nz} ZOR" if nz else ""), "kalin", 50, (90, 630, 990, 700), 1, T.txt, "k2")
    if SJ.get("bolum"): hap(d, T, CX, 1560, f"{SJ['bolum']}. BÖLÜM", ZOR_RENK, 32)
    im.save(out, quality=93)

def onizle(spath, out, genislik=1200, sorular=None):
    """Sessiz hizli onizleme: her soru icin (soru+sayac, cevap) karesi yan yana; panel kucuk resmi ve yerlesim kontrolu icin."""
    SJ = json.load(open(spath)); T = Tema(SJ); fmt = SJ["format"]; Q = SJ["sorular"]; d0 = os.path.dirname(os.path.abspath(spath))
    bg = arkaplan_hazirla(os.path.join(d0, SJ["arkaplan"])) if SJ.get("arkaplan") and os.path.exists(os.path.join(d0, SJ["arkaplan"])) else None
    B = zemin(T, bg); baslik(B, T, fmt); FMT = Format(SJ, T, d0); ims = []
    for i in (sorular if sorular is not None else range(len(Q))):
        a = B.copy(); ust(a, T, i + 1, len(Q), Q[i].get("zorluk") == "zor", FMT.soru_metni(Q[i])); FMT.ciz(a, i, 3, False); sayac(a, T, 0.4, 2)
        b = B.copy(); ust(b, T, i + 1, len(Q), Q[i].get("zorluk") == "zor", FMT.soru_metni(Q[i])); FMT.ciz(b, i, 3, True); cevap_kutusu(b, T, fmt, Q[i], None)
        ims += [a, b]
    k = min(len(ims), 8); tw = genislik//k; th = int(tw*H/W); rows = math.ceil(len(ims)/k)
    sheet = Image.new("RGB", (tw*k, th*rows), (0, 0, 0))
    for j, im in enumerate(ims): sheet.paste(im.resize((tw, th), Image.LANCZOS), ((j % k)*tw, (j//k)*th))
    sheet.save(out, quality=85)

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "hazirla": hazirla(sys.argv[2])
    elif c == "video": video(*sys.argv[2:5])
    elif c == "kapak": kapak(*sys.argv[2:4])
    elif c == "onizle": onizle(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1200)
    elif c == "dogrula":
        h = dogrula(json.load(open(sys.argv[2]))); print("\n".join(h) or "gecerli"); sys.exit(1 if h else 0)
