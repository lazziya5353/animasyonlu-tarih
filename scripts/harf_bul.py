#!/usr/bin/env python3
""""Harflerden Bul" Reel renderer (soru + sabit maskeli harf kutulari -> 3 sn yay (zor +1 sn) -> tum kutular birden dolar, cevap yesil).
Kullanim:
  harf_bul.py --hazirla script.json            # sorular[] -> sahneler + seslendirme_metni (maskeleri dogrular)
  harf_bul.py script.json ses.wav cikti.mp4    # video (+ cikti.mp4.times.json, cikti.mp4.kutular.json)
  harf_bul.py --kapak script.json kapak.jpg [--bolum N]
script.json: "format": "harf-bul", "sorular": [{soru, cevap, acik_harfler, zorluk, alt_bilgi[, cevap_okunus]}].
Ayrintilar: docs/HARF_BUL_REHBERI.md
"""
import json, math, subprocess, sys, os, argparse, random
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harf_quiz import F, W, H, FPS, GOLD, WHITE, BG, ZOR_RENK, up

CX = 540
KREM = (225, 210, 190)
YESIL, YESIL_K = (40, 120, 70), (80, 190, 120)
SAFE_X0, SAFE_X1 = 70, 1010           # yatay guvenli alan
Y_SAYAC, Y_ZOR, Y_SORU = 640, 560, 690
Y_KUTU = 1080                          # kutu blogunun dikey merkezi
TIMER = (540, 1530, 78)                # yay merkezi + yaricap
GIRIS = "Harflerden bul! Boşlukları doldur, bakalım kaçını çözebileceksin?"
CIKIS = "Kaçını bildin? Yorumlara yaz!"
ORAN_MAX = 0.30                        # maskede acik harf orani ust siniri (hedef kolay ~%25, orta ~%20)
ZOR_MAX = 2                            # zor soruda en fazla acik harf

# ---------- maske ----------
def maske_coz(q):
    """acik_harfler -> cevapla ayni uzunlukta maske dizisi ('_' = kapali). Tutarsizlikta ValueError."""
    c = up(q["cevap"]); m = q.get("acik_harfler", "")
    if isinstance(m, list):
        m = "".join(ch if (i in m or not ch.isalpha()) else "_" for i, ch in enumerate(c))
    m = up(m)
    if len(m) != len(c): raise ValueError(f"maske uzunlugu {len(m)} != cevap {len(c)}: {m!r} / {c!r}")
    for i, (a, b) in enumerate(zip(m, c)):
        if b.isalpha():
            if a != "_" and a != b: raise ValueError(f"{c}: {i}. harf maskede {a!r}, cevapta {b!r}")
        elif a != b: raise ValueError(f"{c}: {i}. konumda bosluk/tire uyusmuyor ({a!r} / {b!r})")
    harf = [i for i, b in enumerate(c) if b.isalpha()]; acik = [i for i in harf if m[i] != "_"]
    if len(acik) == len(harf): raise ValueError(f"{c}: maske cevabin tamamini aciyor")
    if len(acik) > ORAN_MAX*len(harf): raise ValueError(f"{c}: cok harf acik ({len(acik)}/{len(harf)} > %{int(ORAN_MAX*100)})")
    if q.get("zorluk") == "zor" and len(acik) > ZOR_MAX: raise ValueError(f"{c}: zor soruda en fazla {ZOR_MAX} harf acik olabilir ({len(acik)})")
    kel = c.split(" ")
    if len(kel) > 1:
        bas = 0
        for w in kel:
            if not any(m[bas + j] != "_" for j, ch in enumerate(w) if ch.isalpha()): raise ValueError(f"{c}: '{w}' kelimesinde hic acik harf yok")
            bas += len(w) + 1
        bas = [0] + [i + 1 for i, ch in enumerate(c) if ch == " "]
        if all(m[i] != "_" for i in bas): raise ValueError(f"{c}: her kelimenin ilk harfi acik (cok kolay)")
    return m

def okunus(cevap):
    w = []
    for p in cevap.split(" "):
        p = "-".join((s[:1] + s[1:].replace("I", "ı").replace("İ", "i").lower()) for s in p.split("-"))
        w.append(p)
    return " ".join(w)

def hazirla(path):
    S = json.load(open(path)); Q = S["sorular"]
    for k, q in enumerate(Q): maske_coz(q)   # hata varsa dur
    sah = [dict(lines=[S.get("giris", GIRIS)])]
    for q in Q:
        sah.append(dict(lines=[q["soru"]], zorluk=q.get("zorluk", "kolay")))
        sah.append(dict(lines=[(q.get("cevap_okunus") or okunus(up(q["cevap"]))).rstrip(".") + "."]))
    sah.append(dict(lines=[S.get("cikis", CIKIS)]))
    for s in sah: s.update(big="", sub="", label="QUIZ", fx=[], image="images/bg.jpg", prompt="quiz")
    S["sahneler"] = sah; S["format"] = "harf-bul"; S["sade"] = True
    S["alt_bilgi"] = {str(k + 1): q.get("alt_bilgi", "") for k, q in enumerate(Q)}
    from sayi_yazi import metni_yaziya
    S["seslendirme_metni"] = metni_yaziya("\n".join(s["lines"][0] for s in sah))
    json.dump(S, open(path, "w"), ensure_ascii=False, indent=1)
    print(f"hazirla: {len(Q)} soru, maskeler tutarli")

# ---------- cizim ----------
def base():
    im = Image.new("RGB", (W, H), BG)
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse((CX-620, 1080-620, CX+620, 1080+620), fill=255)
    im = Image.composite(Image.new("RGB", (W, H), (70, 45, 22)), im, g.filter(ImageFilter.GaussianBlur(260)))
    d = ImageDraw.Draw(im)
    d.text((CX, 330), "HARFLERDEN BUL", font=F("Cinzel-700", 96), fill=GOLD, anchor="ms")
    d.text((CX, 400), "kaçını çözebileceksin?", font=F("Montserrat-700", 38), fill=KREM, anchor="ms")
    d.text((CX, 1820), "@animasyon.tarih", font=F("Montserrat-700", 34), fill=WHITE, anchor="ms")
    return im

def satirlara_bol(c):
    """Cevabi 1 ya da 2 satira bol; kutu boyu en buyuk olan duzeni sec."""
    ws = c.split(" "); sec = [[c]] + [[" ".join(ws[:i]), " ".join(ws[i:])] for i in range(1, len(ws))]
    best = None
    for rows in sec:
        s = min(118, min(boyut(r) for r in rows), int(300 / len(rows) / 1.18))
        if len(rows) == 1 and s >= 82: return rows, s
        if best is None or s > best[1]: best = (rows, s)
    return best

def genislik(r, s): return sum(s if ch.isalpha() else (s*0.55 if ch == " " else s*0.42) for ch in r) + s*0.12*(len(r) - 1)
def boyut(r):
    s = 118
    while s > 30 and genislik(r, s) > SAFE_X1 - SAFE_X0: s -= 2
    return s

def kutu_yerlesim(c):
    """Her karakter icin (i, ch, x0, y0, x1, y1) listesi; bosluklar atlanir, tire kutusuz."""
    rows, s = satirlara_bol(c); out = []; i = 0; rh = s*1.18
    y0 = Y_KUTU - rh*len(rows)/2 + (rh - s)/2
    for r in rows:
        x = CX - genislik(r, s)/2
        for ch in r:
            w = s if ch.isalpha() else (s*0.55 if ch == " " else s*0.42)
            if ch != " ": out.append((i, ch, int(x), int(y0), int(x + w), int(y0 + s)))
            x += w + s*0.12; i += 1
        i += 1; y0 += rh   # satir sonundaki bosluk
    return out, s

def kutular_ciz(d, c, acik, yeni, yesil, pop=1.0):
    lay, s = kutu_yerlesim(c); f = F("Montserrat-900", int(s*0.62)); boxes = []
    for i, ch, x0, y0, x1, y1 in lay:
        if not ch.isalpha():
            d.text(((x0+x1)/2, (y0+y1)/2), ch, font=f, fill=WHITE, anchor="mm"); continue
        if yesil: d.rounded_rectangle((x0, y0, x1, y1), int(s*0.14), fill=YESIL, outline=YESIL_K, width=4)
        else: d.rounded_rectangle((x0, y0, x1, y1), int(s*0.14), fill=(22, 15, 9), outline=GOLD, width=3)
        if yesil or i in acik:
            renk = WHITE if (yesil or i not in yeni) else GOLD
            if i in yeni and not yesil and pop < 1: f2 = F("Montserrat-900", max(8, int(s*0.62*(0.6 + 0.4*pop)))); d.text(((x0+x1)/2, (y0+y1)/2 + 2), ch, font=f2, fill=renk, anchor="mm")
            else: d.text(((x0+x1)/2, (y0+y1)/2 + 2), ch, font=f, fill=renk, anchor="mm")
        else:
            d.line((x0 + s*0.25, y1 - s*0.2, x1 - s*0.25, y1 - s*0.2), fill=(120, 95, 60), width=3)
        boxes.append([x0, y0, x1, y1])
    return boxes

def wrap(d, t, f, mw):
    out, cur = [], ""
    for w in t.split():
        s = (cur + " " + w).strip()
        if d.textlength(s, font=f) <= mw or not cur: cur = s
        else: out.append(cur); cur = w
    return out + [cur]

def soru_ciz(d, k, n, q):
    """Sayac + soru metni (en cok 3 satir); kutu blogunun ustunde kalacak sekilde kuculur."""
    bx = []; d.text((CX, Y_SAYAC), f"{k} / {n}", font=F("Montserrat-900", 40), fill=GOLD, anchor="ms")
    bx.append(list(d.textbbox((CX, Y_SAYAC), f"{k} / {n}", font=F("Montserrat-900", 40), anchor="ms")))
    lay, s = kutu_yerlesim(up(q["cevap"])); ust = min(b[3] for b in lay) - 50
    for sz in range(54, 33, -2):
        f = F("Montserrat-700", sz); ls = wrap(d, q["soru"], f, SAFE_X1 - SAFE_X0)
        if len(ls) <= 3 and Y_SORU + len(ls)*int(sz*1.3) <= ust: break
    y = Y_SORU
    for l in ls:
        d.text((CX, y), l, font=f, fill=WHITE, anchor="mt"); bx.append(list(d.textbbox((CX, y), l, font=f, anchor="mt"))); y += int(f.size*1.3)
    return bx

def alt_bilgi_ciz(d, c, t, al=1.0):
    lay, s = kutu_yerlesim(c); y = max(b[5] for b in lay) + 44; bx = []
    ht = f"•  {up(t)}  •"
    for sz in range(36, 21, -2):
        hf = F("Montserrat-900", sz)
        if d.textlength(ht, font=hf) <= SAFE_X1 - SAFE_X0: break
    col = tuple(int(BG[i] + (KREM[i] - BG[i])*al) for i in range(3))
    d.text((CX, y), ht, font=hf, fill=col, anchor="mt"); bx.append(list(d.textbbox((CX, y), ht, font=hf, anchor="mt")))
    return bx

def timer_ciz(d, p, kalan):
    x, y, r = TIMER
    d.ellipse((x-r, y-r, x+r, y+r), outline=(60, 42, 25), width=8)
    d.arc((x-r, y-r, x+r, y+r), -90, -90 + 360*p, fill=(200, 60, 50), width=8)
    d.text((x, y + 2), str(kalan), font=F("Montserrat-900", 60), fill=WHITE, anchor="mm")
    return [x-r, y-r, x+r, y+r]

def zor_flas(im, fa):
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(fl)
    ff = F("Montserrat-900", 40); w = fd.textlength("ZOR SORU", font=ff) + 50
    fd.rounded_rectangle((CX - w/2, Y_ZOR - 30, CX + w/2, Y_ZOR + 30), 30, fill=ZOR_RENK + (int(235*fa),), outline=GOLD + (int(255*fa),), width=3)
    fd.text((CX, Y_ZOR + 2), "ZOR SORU", font=ff, fill=(255, 240, 215, int(255*fa)), anchor="mm")
    im = im.convert("RGBA"); im.alpha_composite(fl); return im.convert("RGB"), [int(CX - w/2), Y_ZOR - 30, int(CX + w/2), Y_ZOR + 30]

def zor_etiket(d):
    f = F("Montserrat-900", 22); w = d.textlength("ZOR", font=f) + 24
    d.rounded_rectangle((CX + 150 - w/2, Y_SAYAC - 33, CX + 150 + w/2, Y_SAYAC - 5), 14, fill=ZOR_RENK, outline=GOLD, width=1)
    d.text((CX + 150, Y_SAYAC - 19), "ZOR", font=f, fill=(250, 235, 210), anchor="mm")
    return [int(CX + 150 - w/2), Y_SAYAC - 33, int(CX + 150 + w/2), Y_SAYAC - 5]

def kapak(script, out, bolum=None):
    S = json.load(open(script)); Q = S["sorular"]; n = len(Q); nz = sum(q.get("zorluk") == "zor" for q in Q)
    im = base(); d = ImageDraw.Draw(im)
    g = Image.new("L", im.size, 0); ImageDraw.Draw(g).ellipse((CX-380, 1080-380, CX+380, 1080+380), fill=110)
    im = Image.composite(Image.new("RGB", im.size, (150, 110, 60)), im, g.filter(ImageFilter.GaussianBlur(120))); d = ImageDraw.Draw(im)
    if bolum: d.text((CX, 560), f"{bolum}. BÖLÜM", font=F("Montserrat-900", 30), fill=KREM, anchor="ms")
    d.text((CX, 700), f"{n} SORU", font=F("Montserrat-900", 44), fill=WHITE, anchor="ms")
    q = Q[0]; c = up(q["cevap"]); kutular_ciz(d, c, {i for i, ch in enumerate(maske_coz(q)) if ch != "_"}, set(), False)
    d.text((CX, 1340), "KAÇINI", font=F("Cinzel-700", 100), fill=GOLD, anchor="ms")
    d.text((CX, 1450), "ÇÖZEBİLECEKSİN?", font=F("Cinzel-700", 80), fill=GOLD, anchor="ms")
    if nz:
        zf = F("Montserrat-900", 30); t = f"{nz} ZOR SORU"; w = d.textlength(t, font=zf) + 40
        d.rounded_rectangle((CX - w/2, 1510, CX + w/2, 1560), 25, fill=ZOR_RENK, outline=GOLD, width=2)
        d.text((CX, 1536), t, font=zf, fill=(255, 240, 215), anchor="mm")
    im.save(out, quality=93); print("kapak", out)

# ---------- ses ----------
def bol(au, SR, S, n):
    """Sesi metin uzunluguna gore DP ile 2n+2 parcaya boler (harf_quiz ile ayni yontem)."""
    import numpy as np
    tot = len(au)/SR
    fr = np.sqrt((au[:len(au)//480*480].reshape(-1, 480)**2).mean(1))
    def sess(th, mn):
        q = fr < 10**(th/20); out = []; j = 0
        while j < len(q):
            if q[j]:
                k = j
                while k < len(q) and q[k]: k += 1
                if k - j >= mn: out.append((j*0.01, k*0.01))
                j = k
            else: j += 1
        return out
    sil = [x for x in sess(-42, 8) if x[0] > 0.05 and x[1] < tot - 0.05]; sil35 = sess(-35, 41)
    ch = [len(x) for x in S]; rate = tot/sum(ch); m = len(sil); K = 2*n + 1
    if m < K: sys.exit(f"HATA: sessizlik sayisi yetmiyor ({m} < {K})")
    mid = lambda j: (sil[j][0]+sil[j][1])/2
    cost = lambda t0, t1, c: math.log(max(t1 - t0, 0.05)/(rate*c))**2
    pen = lambda k, i, j: 3.0*sum(1 for g in sil[i+1:j] if g[1] - g[0] > 0.2) if k % 2 == 0 else 0
    INF = float("inf"); D = [[INF]*m for _ in range(K)]; P = [[-1]*m for _ in range(K)]
    for j in range(m): D[0][j] = cost(0, mid(j), ch[0])
    for k in range(1, K):
        for j in range(k, m):
            for i in range(k-1, j):
                v = D[k-1][i] + cost(mid(i), mid(j), ch[k]) - 1.5*(sil[j][1]-sil[j][0]) + pen(k, i, j)
                if v < D[k][j]: D[k][j] = v; P[k][j] = i
    j = min(range(m), key=lambda j: D[K-1][j] + cost(mid(j), tot, ch[-1])); idx = []
    for k in range(K-1, -1, -1): idx.append(j); j = P[k][j]
    gaps = [sil[j] for j in reversed(idx)]; edges = [(0.0, None)] + gaps + [(None, tot)]; segs = []
    for k in range(2*n + 2):
        s0 = edges[k][1] - 0.06 if edges[k][1] is not None else 0.0
        s1 = edges[k+1][0] + 0.08 if edges[k+1][0] is not None else tot
        sg = au[int(max(0, s0)*SR):int(s1*SR)].copy()
        for g in reversed([g for g in sil35 if g[0] > s0 + 0.05 and g[1] < s1 - 0.05 and g[1] - g[0] > 0.4]):
            c0 = int((g[0] - s0 + 0.125)*SR); c1 = int((g[1] - s0 - 0.125)*SR); sg = np.concatenate([sg[:c0], sg[c1:]])
        f = min(240, len(sg)//2); r = np.linspace(0, 1, f, dtype=np.float32); sg[:f] *= r; sg[len(sg)-f:] *= r[::-1]
        segs.append(sg)
    return segs

def render(a):
    import numpy as np, wave
    SJ = json.load(open(a.script)); Q = SJ["sorular"]; n = len(Q)
    S = [" ".join(x["lines"]) for x in SJ["sahneler"]]
    assert len(S) == 2*n + 2, "sahneler sorularla uyusmuyor: once --hazirla"
    M = [maske_coz(q) for q in Q]; C = [up(q["cevap"]) for q in Q]; P = [a.pause + (1.0 if q.get("zorluk") == "zor" else 0) for q in Q]
    ZOR = {k for k, q in enumerate(Q) if q.get("zorluk") == "zor"}
    SR = 48000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.wav, "-af", f"atempo={a.tempo}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    segs = bol(np.frombuffer(raw, np.float32), SR, S, n)
    z = lambda t: np.zeros(int(t*SR), np.float32)
    parts, t = [segs[0], z(0.25)], len(segs[0])/SR + 0.25; ev = []
    for k in range(n):
        qa, aa = segs[1+2*k], segs[2+2*k]
        qs = t; qe = qs + len(qa)/SR; as_ = qe + P[k]; ae = as_ + len(aa)/SR; gone = max(ae, as_ + 0.8) + a.hold + 0.25
        parts += [qa, z(P[k]), aa, z(gone - ae)]; ev.append((qs, qe, as_, ae, gone)); t = gone
    outro = t; parts += [segs[-1], z(1.0)]
    A = np.concatenate(parts); dur = len(A)/SR; tmpa = a.out + ".a.wav"
    with wave.open(tmpa, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(A, -1, 1)*32767).astype("<i2").tobytes())
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", tmpa, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    WMf = F("Montserrat-900", 44); wb = WMf.getbbox("@animasyon.tarih")
    WM = Image.new("RGBA", (wb[2]+8, wb[3]+8), (0, 0, 0, 0)); ImageDraw.Draw(WM).text((4, 4), "@animasyon.tarih", font=WMf, fill=(255, 255, 255, 43))
    B = base(); kayit = {}; HF = SJ.get("alt_bilgi", {})
    for fi in range(int(dur*FPS)):
        t = fi/FPS; im = B.copy(); d = ImageDraw.Draw(im); faz = None
        if t >= outro:
            al = min(1, (t - outro)/0.3); col = tuple(int(BG[i] + (GOLD[i]-BG[i])*al) for i in range(3))
            d.text((CX, 1040), "KAÇINI", font=F("Cinzel-700", 110), fill=col, anchor="ms")
            d.text((CX, 1160), "BİLDİN?", font=F("Cinzel-700", 110), fill=col, anchor="ms")
            d.text((CX, 1250), "YORUMLARA YAZ", font=F("Montserrat-900", 40), fill=tuple(int(BG[i] + (WHITE[i]-BG[i])*al) for i in range(3)), anchor="ms")
        elif t < ev[0][0]:
            al = min(1, t/0.4); col = tuple(int(BG[i] + (GOLD[i]-BG[i])*al) for i in range(3))
            d.text((CX, 1040), f"{n} SORU", font=F("Cinzel-700", 110), fill=col, anchor="ms")
            d.text((CX, 1130), "BOŞLUKLARI DOLDUR", font=F("Montserrat-900", 40), fill=tuple(int(BG[i] + (WHITE[i]-BG[i])*al) for i in range(3)), anchor="ms")
        else:
            k = max(i for i, e in enumerate(ev) if t >= e[0]); qs, qe, as_, ae, gone = ev[k]; q = Q[k]
            bg = im.copy(); bx = soru_ciz(d, k+1, n, q)
            if k in ZOR: bx.append(zor_etiket(d))
            acik = {i for i, ch in enumerate(M[k]) if ch != "_"}
            yesil = t >= as_; yeni = set(); pop = 1.0
            if qe <= t < as_:
                el = t - qe   # maske sabit: yay sirasinda harf acilmaz
                bx.append(timer_ciz(d, min(1, el/P[k]), max(1, math.ceil(P[k] - el)))); faz = "yay"
            elif not yesil: faz = "soru"
            else: faz = "cevap"
            bx += kutular_ciz(d, C[k], acik | yeni, yeni, yesil, pop)
            if yesil: bx += alt_bilgi_ciz(d, C[k], HF.get(str(k+1), q.get("alt_bilgi", "")), min(1, (t - as_)/0.3))
            if k in ZOR and qs <= t < qs + 1.2:
                im, zb = zor_flas(im, min(1, (t - qs)/0.15, (qs + 1.2 - t)/0.3)); bx.append(zb)
            al = min(1, (t - qs)/0.25, max(0, (gone - t)/0.25))
            if al < 1: im = Image.blend(bg, im, al)
            anah = {"soru": f"{k}s", "yay": f"{k}y", "cevap": f"{k}c"}[faz]
            esik = {"soru": qs + 0.4, "yay": as_ - 0.15, "cevap": as_ + 0.4}[faz]
            if t >= esik and anah not in kayit and al >= 1: kayit[anah] = bx
        wx = int(CX - WM.width/2 + 230*math.sin(t*0.21)); wy = int(1080 - WM.height/2 + 330*math.sin(t*0.13 + 1.1))
        im = im.convert("RGBA"); im.alpha_composite(WM, (wx, wy)); im = im.convert("RGB")
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait(); os.remove(tmpa)
    json.dump([dict(no=k+1, cevap=C[k], soru_t=round(e[0], 2), soru_bit=round(e[1], 2), cevap_t=round(e[2], 2), cevap_bit=round(e[3], 2), gone=round(e[4], 2)) for k, e in enumerate(ev)],
              open(a.out + ".times.json", "w"), ensure_ascii=False)
    json.dump(dict(guvenli=[SAFE_X0, SAFE_X1], kareler=kayit), open(a.out + ".kutular.json", "w"))
    print("sure", round(dur, 1))

def main():
    if sys.argv[1:2] == ["--hazirla"]: return hazirla(sys.argv[2])
    if sys.argv[1:2] == ["--kapak"]:
        ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("out"); ap.add_argument("--bolum"); a = ap.parse_args(sys.argv[2:])
        return kapak(a.script, a.out, a.bolum)
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("wav"); ap.add_argument("out")
    ap.add_argument("--pause", type=float, default=3.0); ap.add_argument("--hold", type=float, default=0.6); ap.add_argument("--tempo", type=float, default=1.08)
    render(ap.parse_args())

if __name__ == "__main__": main()
