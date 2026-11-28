#!/usr/bin/env python3
"""Harf quiz Reel renderer (soru -> 3 sn yay -> cevap akisi).
Kullanim: harf_quiz.py script.json ses.wav cikti.mp4 [--timed project.timed.json] [--kapak kapak.jpg]
script.json sahneleri: 0=intro, her harf icin (soru "X harfi. ...", cevap), son=outro.
Ses, sessizliklere (silencedetect) gore kesilip yeniden dizilir: soru sesi, 2.5 sn sessiz yay,
cevap sesi, 0.7 sn bekleme, 0.25 sn kararma; ses atempo ile hizlanir. timed.json verilirse sinirlar en yakin sessizlige oturtulur,
verilmezse sessizlikler sirayla kullanilir.
"""
import json, math, subprocess, sys, os, argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
R = os.path.dirname(os.path.abspath(__file__)) + "/../engine/fonts/"
W, H, FPS = 1080, 1920, 30
GOLD = (232, 196, 120); WHITE = (255, 255, 255); BG = (14, 10, 7)
F = lambda n, s: ImageFont.truetype(R + n + ".ttf", s)
CX, CY, RAD, RR = 540, 1060, 440, 36

def arkaplan_hazirla(yol):
    """Tematik arka plan (quiz 3+): kapla-kirp, hafif bulanik, %38 parlaklik. Metin okunur kalsin diye karartilir."""
    from PIL import ImageEnhance, ImageOps
    im = ImageOps.fit(Image.open(yol).convert("RGB"), (int(W*1.08), int(H*1.08)), Image.LANCZOS)
    return ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(6))).enhance(0.38)

def arkaplan_kare(src, t, dur, kb):
    """Cok yavas Ken Burns: sure boyunca %0 -> %8 yakinlasma (kb kapaliysa sabit orta kirpim)."""
    z = 1.0 + (0.08*min(1, t/max(dur, 1)) if kb else 0.04)
    w, h = int(src.width/z), int(src.height/z); x, y = (src.width - w)//2, (src.height - h)//2
    return src.crop((x, y, x+w, y+h)).resize((W, H), Image.BILINEAR)

def base(bg=None):
    if bg is not None: im = bg.copy()
    else:
        im = Image.new("RGB", (W, H), BG)
        g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse((CX-620, CY-620, CX+620, CY+620), fill=255)
        g = g.filter(ImageFilter.GaussianBlur(260))
        im = Image.composite(Image.new("RGB", (W, H), (70, 45, 22)), im, g)
    d = ImageDraw.Draw(im)
    def ct(y, t, f, c, sp=0):
        if sp:
            ws = [d.textlength(ch, font=f) for ch in t]; x = CX - (sum(ws) + sp*(len(t)-1))/2
            for ch, w in zip(t, ws): d.text((x, y), ch, font=f, fill=c, anchor="ls"); x += w + sp
        else: d.text((CX, y), t, font=f, fill=c, anchor="ms")
    ct(235, "HER HARFE BİR", F("Montserrat-900", 44), WHITE, 9)
    ct(340, "TARİH SORUSU", F("Cinzel-700", 92), GOLD)
    ct(408, "kaçını bileceksin?", F("Montserrat-700", 38), (225, 210, 190))
    d.text((CX, 1820), "@animasyon.tarih", font=F("Montserrat-700", 34), fill=WHITE, anchor="ms")
    return im

def pos(i, n):
    st = 360 / n; a = math.radians(90 + st/2 + i*st)
    return CX + RAD*math.cos(a), CY + RAD*math.sin(a)

def wrap(d, t, f, mw):
    out, cur = [], ""
    for w in t.split():
        s = (cur + " " + w).strip()
        if d.textlength(s, font=f) <= mw or not cur: cur = s
        else: out.append(cur); cur = w
    return out + [cur]

def fitlines(d, t, name, size, mw, maxl, minsize=40):
    while True:
        f = F(name, size); ls = wrap(d, t, f, mw)
        if (len(ls) <= maxl and all(d.textlength(l, font=f) <= mw for l in ls)) or size <= minsize: return f, ls
        size -= 4

ZOR_RENK = (196, 48, 40)
def zor_etiket(d, x, y):
    """Balonun altinda kucuk kirmizi 'ZOR' etiketi (kendi stilimiz: koyu kirmizi hap, krem yazi)."""
    f = F("Montserrat-900", 17); w = d.textlength("ZOR", font=f) + 16
    d.rounded_rectangle((x - w/2, y + RR + 15, x + w/2, y + RR + 37), 11, fill=ZOR_RENK, outline=GOLD, width=1)
    d.text((x, y + RR + 26), "ZOR", font=f, fill=(250, 235, 210), anchor="mm")

def ring(d, letters, done, cur, pulse=0, prog=None, zor=()):
    lf = F("Montserrat-900", 34); n = len(letters)
    for i, L in enumerate(letters):
        x, y = pos(i, n)
        if i in zor: zor_etiket(d, x, y)
        if i in done: d.ellipse((x-RR, y-RR, x+RR, y+RR), fill=(40, 120, 70), outline=(80, 190, 120), width=4)
        else: d.ellipse((x-RR, y-RR, x+RR, y+RR), fill=(16, 11, 7), outline=GOLD, width=3)
        d.text((x, y+2), L, font=lf, fill=WHITE, anchor="mm")
        if i == cur:
            r = RR + 11 + pulse
            d.ellipse((x-r, y-r, x+r, y+r), outline=(225, 50, 45), width=5)
            if prog is not None:
                r2 = RR + 20
                d.arc((x-r2, y-r2, x+r2, y+r2), -90, -90 + 360*prog, fill=GOLD, width=4)

# guvenli metin alani: halka yaricapi - balon yaricapi - pay; satirin dikey konumundaki kirisle de sinirli
SAFE_R = RAD - RR - 40
SAFE_W = min(720, 2*SAFE_R)
def safe_w(y0, y1):
    dy = max(abs(y0 - CY), abs(y1 - CY))
    return int(min(SAFE_W, 2*math.sqrt(max(0, SAFE_R**2 - dy**2)))) if dy < SAFE_R else 0
KUTU = []   # son center() cagrisinda cizilen metin kutulari (x0,y0,x1,y1), kontrol icin

def center(im, k, n, q, ans, hint, a_alpha, a_scale):
    d = ImageDraw.Draw(im); KUTU.clear()
    MW = SAFE_W
    if k is not None:
        d.text((CX, 840), f"{k} / {n}", font=F("Montserrat-900", 40), fill=GOLD, anchor="ms")
    y = 875
    if q:
        for sz in range(50, 33, -2):
            f, ls = fitlines(d, q, "Montserrat-700", sz, MW, 3, sz)
            h = int(f.size*1.3)
            if all(d.textlength(l, font=f) <= safe_w(y + i*h, y + i*h + f.size) for i, l in enumerate(ls)) and len(ls) <= 3: break
        for l in ls:
            d.text((CX, y), l, font=f, fill=WHITE, anchor="mt"); b = d.textbbox((CX, y), l, font=f, anchor="mt"); KUTU.append(b); y += int(f.size*1.3)
    if ans and a_alpha > 0:
        lay = Image.new("RGBA", (W, 620), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        top = max(y + 20, 1060 - 10) if len(q or "") else 1000
        f, ls = fitlines(ld, ans, "Cinzel-700", 84, MW, 2, 48)
        yy = 10; lb = []
        while True:  # cevap satirlari halkanin kirisine sigana kadar kucult
            h = int(f.size*1.18)
            if all(ld.textlength(l, font=f) <= safe_w(top + yy + i*h, top + yy + i*h + f.size) for i, l in enumerate(ls)) or f.size <= 40: break
            f, ls = fitlines(ld, ans, "Cinzel-700", f.size - 4, MW, 2, f.size - 4)
        for l in ls: ld.text((CX, yy), l, font=f, fill=GOLD + (255,), anchor="mt"); lb.append(ld.textbbox((CX, yy), l, font=f, anchor="mt")); yy += int(f.size*1.18)
        if hint:
            ht = f"•  {hint}  •"; yy += 18
            for sz in range(34, 21, -2):  # alt bilgi: once kucult, sigmazsa 2 satira bol
                hf = F("Montserrat-900", sz); hl = [ht] if ld.textlength(ht, font=hf) <= safe_w(top + yy, top + yy + sz) else wrap(ld, hint, hf, safe_w(top + yy, top + yy + int(sz*2.4)))
                if len(hl) <= 2 and all(ld.textlength(l, font=hf) <= safe_w(top + yy + i*int(sz*1.25), top + yy + (i+1)*int(sz*1.25)) for i, l in enumerate(hl)): break
            for l in hl: ld.text((CX, yy), l, font=hf, fill=(225, 210, 190, 255), anchor="mt"); lb.append(ld.textbbox((CX, yy), l, font=hf, anchor="mt")); yy += int(hf.size*1.25)
            yy += 20
        lay = lay.crop((0, 0, W, yy + 10))
        if a_scale != 1:
            lay = lay.resize((int(W*a_scale), int(lay.height*a_scale)), Image.LANCZOS)
        if a_alpha < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v*a_alpha)))
        ox, oy = CX - lay.width//2, top + int((1 - a_scale)*60)
        im.paste(lay, (ox, oy), lay)
        for b in lb: KUTU.append((int(ox + b[0]*a_scale), int(oy + b[1]*a_scale), int(ox + b[2]*a_scale + 1), int(oy + b[3]*a_scale + 1)))

TR = str.maketrans("iı", "İI")
def up(t): return t.translate(TR).upper()

def silences(wav, d=0.12):
    o = subprocess.run(["ffmpeg", "-i", wav, "-af", f"silencedetect=n=-35dB:d={d}", "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [float(l.split("silence_start: ")[1]) for l in o.splitlines() if "silence_start" in l]
    en = [float(l.split("silence_end: ")[1].split()[0]) for l in o.splitlines() if "silence_end" in l]
    return list(zip(st, en))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("wav"); ap.add_argument("out")
    ap.add_argument("--timed"); ap.add_argument("--kapak")
    ap.add_argument("--pause", type=float, default=2.5); ap.add_argument("--hold", type=float, default=0.7)
    ap.add_argument("--tempo", type=float, default=1.08)
    ap.add_argument("--no-wm", action="store_true", help="filigrani kapat")
    a = ap.parse_args()
    import numpy as np
    SJ = json.load(open(a.script)); S = [" ".join(x["lines"]) for x in SJ["sahneler"]]
    n = (len(S) - 2)//2; Q = []
    for k in range(n):
        q = S[1+2*k]; L, rest = q.split(" harfi.", 1)
        Q.append((L.strip(), rest.strip(), up(S[2+2*k].strip().rstrip("."))))
    HINT = {"A": "Soyadı Kanunu · 1934", "B": "1326 · Orhan Bey", "C": "Türkiye Cumhuriyeti · 1923", "D": "Divan-ı Hümayun",
            "E": "I. Murad döneminde başkent", "F": "29 Mayıs 1453", "G": "Çanakkale Cephesi · 1915", "H": "İstanbul kuşatması · 1453",
            "İ": "Başkent · 1453–1922", "K": "46 yıl · 1520–1566", "M": "Mohaç Meydan Muharebesi · 1526", "N": "Niğbolu Savaşı · 1396",
            "O": "Osmanlı Beyliği · 1299", "P": "Preveze Deniz Savaşı · 1538", "R": "Balkanlar", "S": "Süleymaniye · Selimiye",
            "Ş": "Osman Gazi'nin kayınpederi", "T": "Padişahın imzası", "U": "İstanbul'un Fethi · 1453", "V": "I. Viyana Kuşatması · 1529",
            "Y": "I. Selim · 1517", "Z": "Büyük Taarruz · 1922"}
    HINT = json.load(open(a.script)).get("alt_bilgi") or HINT
    letters = [x[0] for x in Q]
    # quiz 3+: sorularin zorlugu (sahneler[soru]["zorluk"] = kolay/orta/zor) ve istege bagli tematik arka plan
    ZOR = {k for k in range(n) if SJ["sahneler"][1+2*k].get("zorluk") == "zor"}
    BGSRC = None
    if SJ.get("arkaplan"):
        yol = os.path.join(os.path.dirname(os.path.abspath(a.script)), SJ["arkaplan"])
        if not os.path.exists(yol): sys.exit(f"HATA: arkaplan bulunamadi: {yol}")
        BGSRC = arkaplan_hazirla(yol)
    KB = bool(SJ.get("arkaplan_kenburns")) and BGSRC is not None
    B = base(arkaplan_kare(BGSRC, 0, 1, False) if BGSRC is not None else None)
    if a.kapak:
        im = B.copy(); d = ImageDraw.Draw(im); ring(d, letters, set(range(n)), None)
        d.text((CX, 1010), "KAÇINI", font=F("Cinzel-700", 104), fill=GOLD, anchor="ms")
        d.text((CX, 1130), "BİLDİN?", font=F("Cinzel-700", 104), fill=GOLD, anchor="ms")
        d.text((CX, 1200), f"{n} HARF · {n} SORU", font=F("Montserrat-900", 34), fill=WHITE, anchor="ms")
        im.save(a.kapak, quality=93)
    # segmentler.json (Hizli Studyo: satir satir TTS ya da onaylanmis dis ses sinirlari) varsa AYNEN kullanilir, sessizlik tespiti yapilmaz
    SEGY = os.path.join(os.path.dirname(os.path.abspath(a.script)), "segmentler.json")
    SEG = json.load(open(SEGY))["segmentler"] if os.path.exists(SEGY) else None
    if SEG is not None:
        if len(SEG) != 2*n + 2: sys.exit(f"HATA: segmentler.json {len(SEG)} satır içeriyor, {2*n + 2} olmalı (giriş + {n} soru/cevap + kapanış)")
        a.tempo = float(SJ.get("tempo") or 1.12)
    a.pause = float(SJ.get("dusunme") or a.pause); a.hold = float(SJ.get("bekleme") or a.hold)
    # --- sesi sessizliklerle 2n+2 parcaya bol
    SR = 48000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.wav, "-af", f"atempo={a.tempo}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    au = np.frombuffer(raw, np.float32); tot = len(au)/SR
    if SEG is not None:
        segs = []
        for x in SEG:  # zaman cizelgesi atempo sonrasina olceklenir
            sg = au[int(x["bas"]/a.tempo*SR):int(x["bit"]/a.tempo*SR)].copy()
            if len(sg) < 480: sg = np.zeros(int(0.3*SR), np.float32)
            f = min(240, len(sg)//2); r = np.linspace(0, 1, f, dtype=np.float32); sg[:f] *= r; sg[len(sg)-f:] *= r[::-1]
            segs.append(sg)
        # sure siniri 177 sn (2:57): once bekleme, sonra ZOR ek suresi, sonra dusunme suresi (en az 2 sn) kisalir
        konusma = sum(len(x) for x in segs)/SR; zb = float(SJ.get("zor_ek", 1.0))
        top = lambda: konusma + 0.2 + n*(a.pause + a.hold + 0.25) + len(ZOR)*zb + 1.0
        while top() > 177 and a.hold > 0.3: a.hold = round(max(0.3, a.hold - 0.05), 3)
        if top() > 177: zb = 0.0
        while top() > 177 and a.pause > 2.0: a.pause = round(max(2.0, a.pause - 0.05), 3)
        if top() > 177: sys.exit(f"HATA: Video {top():.1f} sn olur, sınır 177 sn (2:57). Düşünme 2 sn'ye, bekleme 0.3 sn'ye indirildi yine de sığmıyor; soru sayısını azalt ya da soruları kısalt.")
        print(f"zaman cizelgesi: konusma {konusma:.1f} sn, dusunme {a.pause} sn, bekleme {a.hold} sn, toplam {top():.1f} sn")
    else:
        zb = float(SJ.get("zor_ek", 1.0))
        fr = np.sqrt((au[:len(au)//480*480].reshape(-1, 480)**2).mean(1)); q = fr < 10**(-42/20); sil = []; j = 0
        while j < len(q):  # kendi enerji tabanli sessizlik tespiti (10 ms kare, -42 dB, >=80 ms)
            if q[j]:
                k = j
                while k < len(q) and q[k]: k += 1
                if k - j >= 8: sil.append((j*0.01, k*0.01))
                j = k
            else: j += 1
        q35 = fr < 10**(-35/20); sil35 = []; j = 0
        while j < len(q35):
            if q35[j]:
                k = j
                while k < len(q35) and q35[k]: k += 1
                if k - j > 40: sil35.append((j*0.01, k*0.01))
                j = k
            else: j += 1
        sil = [x for x in sil if x[0] > 0.05 and x[1] < tot - 0.05]
        if a.timed:
            sc = json.load(open(a.timed))["scenes"]; assert len(sc) == 2*n + 2
            gaps = []
            for k in range(1, len(sc)):
                b = (sc[k-1]["end"] + sc[k]["start"])/2
                g = min(sil, key=lambda g: abs((g[0]+g[1])/2 - b))
                gaps.append(g if abs((g[0]+g[1])/2 - b) < 0.4 and g not in gaps else (b - 0.08, b + 0.06))
        else:
            # once metin tabanli bolme (Whisper kelime zamanlari); guven dusukse sessizlik DP'sine don
            try:
                from ses_hizala import satir_sinirlari; sn = satir_sinirlari(au, SR, S)
            except Exception as e: print("uyari: metin hizalama calismadi:", e); sn = None
            gaps = [(b - 0.08, b + 0.06) for b in sn[1:-1]] if sn else None
        if gaps is None:
            # metin uzunluguna gore DP hizalama: en uzun sessizlikleri secmek cumle-ici duraklari
            # sahne siniri sanip soru/cevap seslerini kaydiriyordu (sessiz soru hatasi)
            ch = [len(x) for x in S]; rate = tot/sum(ch); m = len(sil); K = 2*n + 1
            mid = lambda j: (sil[j][0]+sil[j][1])/2
            def cost(t0, t1, c):
                return math.log(max(t1 - t0, 0.05)/(rate*c))**2
            def pen(k, i, j):  # yapi: soru "X harfi." + kisa durakla baslar; cevap tek parca (ic durak yok)
                ins = sil[i+1:j]
                if k % 2 == 1: return 0 if any(0.25 < g[0] - sil[i][1] < 1.0 for g in ins) else 3.0
                return 3.0 * sum(1 for g in ins if g[1] - g[0] > 0.2)
            INF = float("inf"); D = [[INF]*m for _ in range(K)]; P = [[-1]*m for _ in range(K)]
            cost0 = cost; cost = lambda t0, t1, c: cost0(t0, t1, c)
            for j in range(m): D[0][j] = cost(0, mid(j), ch[0])
            for k in range(1, K):
                for j in range(k, m):
                    for i in range(k-1, j):
                        v = D[k-1][i] + cost(mid(i), mid(j), ch[k]) - 1.5*(sil[j][1]-sil[j][0]) + pen(k, i, j)
                        if v < D[k][j]: D[k][j] = v; P[k][j] = i
            j = min(range(m), key=lambda j: D[K-1][j] + cost(mid(j), tot, ch[-1])); idx = []
            for k in range(K-1, -1, -1): idx.append(j); j = P[k][j]
            gaps = [sil[j] for j in reversed(idx)]
        assert len(set(gaps)) == 2*n + 1, "sessizlik sayisi yetmiyor"
        edges = [(0.0, None)] + gaps + [(None, tot)]
        segs = []
        for k in range(2*n + 2):
            s0 = edges[k][1] - 0.06 if edges[k][1] is not None else 0.0
            s1 = edges[k+1][0] + 0.08 if edges[k+1][0] is not None else tot
            sg = au[int(max(0, s0)*SR):int(s1*SR)].copy()
            # 0.4 sn'den uzun ic sessizlikleri 0.25 sn'ye kisalt
            ins = [g for g in sil35 if g[0] > s0 + 0.05 and g[1] < s1 - 0.05 and g[1] - g[0] > 0.4]
            for g in reversed(ins):
                c0 = int((g[0] - s0 + 0.125)*SR); c1 = int((g[1] - s0 - 0.125)*SR); sg = np.concatenate([sg[:c0], sg[c1:]])
            f = min(240, len(sg)//2); r = np.linspace(0, 1, f, dtype=np.float32); sg[:f] *= r; sg[len(sg)-f:] *= r[::-1]
            segs.append(sg)
    z = lambda t: np.zeros(int(t*SR), np.float32)
    parts, t = [segs[0], z(0.2)], len(segs[0])/SR + 0.2
    ev = []  # (q_start, q_end, a_start, a_end, gone)
    for k in range(n):
        qa, aa = segs[1+2*k], segs[2+2*k]
        qs = t; qe = qs + len(qa)/SR; as_ = qe + a.pause + (zb if len(ev) in ZOR else 0); ae = as_ + len(aa)/SR; gone = ae + a.hold + 0.25
        parts += [qa, z(a.pause + (zb if len(ev) in ZOR else 0)), aa, z(a.hold + 0.25)]; ev.append((qs, qe, as_, ae, gone)); t = gone
    outro = t; parts += [segs[-1], z(1.0)]
    A = np.concatenate(parts); dur = len(A)/SR
    tmpa = a.out + ".a.wav"
    import wave
    with wave.open(tmpa, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(A, -1, 1)*32767).astype("<i2").tobytes())
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", tmpa, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    # hirsizliga karsi filigran: orta alanda yavasca gezinen yari saydam (~30% beyaz) "@animasyon.tarih"
    WMf = F("Montserrat-900", 44); wb = WMf.getbbox("@animasyon.tarih")
    WM = Image.new("RGBA", (wb[2]+8, wb[3]+8), (0, 0, 0, 0)); ImageDraw.Draw(WM).text((4, 4), "@animasyon.tarih", font=WMf, fill=(255, 255, 255, 43))
    kutular = {}   # kart -> cevap tam gorunurken metin kutulari + filigran kutusu
    for fi in range(int(dur*FPS)):
        t = fi / FPS
        if KB and fi % 2 == 0: B = base(arkaplan_kare(BGSRC, t, dur, True))
        im = B.copy(); d = ImageDraw.Draw(im)
        if t >= outro:
            ring(d, letters, set(range(n)), None, zor=ZOR)
            center(im, None, n, "", "ZORLARIN KAÇINI BİLDİN?" if ZOR else "KAÇINI BİLDİN?", f"{len(ZOR)} ZOR SORU · YORUMLARA YAZ" if ZOR else "YORUMLARA YAZ", min(1, (t-outro)/0.3), 1)
        elif t < ev[0][0]:
            ring(d, letters, set(), None, zor=ZOR)
            center(im, None, n, "", f"{n} HARF", f"{n} SORU", min(1, t/0.4), 1)
        else:
            cur = max(i for i, e in enumerate(ev) if t >= e[0]); qs, qe, as_, ae, gone = ev[cur]
            ansv = t >= as_; done = set(range(cur + (1 if ansv else 0)))
            ring(d, letters, done, cur, 0 if ansv else int(3*math.sin(t*8)), zor=ZOR)
            if qe <= t < as_:  # sessiz bekleme: kirmizi yay 12'den saat yonunde dolar
                r2 = 392; dd = ImageDraw.Draw(im)
                dd.arc((CX-r2, CY-r2, CX+r2, CY+r2), -90, -90 + 360*min(1, (t-qe)/(as_-qe)), fill=(200, 60, 50), width=6)
            bg = im.copy()
            if qe <= t < as_ and SJ.get("geri_sayim", True):  # buyuk geri sayim rakami (3-2-1), sorunun altinda, halkanin icinde
                kal = as_ - t; rk = str(max(1, math.ceil(kal))); fz = 1 - (math.ceil(kal) - kal)
                cf = F("Cinzel-700", int(110 + 20*max(0, fz - 0.8)/0.2)); ImageDraw.Draw(im).text((CX, 1215), rk, font=cf, fill=GOLD, anchor="mm")
            if ansv:
                k = min(1, (t - as_)/0.3); center(im, cur+1, n, Q[cur][1], Q[cur][2], up(HINT.get(Q[cur][0], "")), k, 0.9 + 0.1*k)
            else:
                center(im, cur+1, n, Q[cur][1], "", "", 0, 1)
            if cur in ZOR and qs <= t < qs + 1.2:  # kisa "ZOR SORU" flasi: sayacin ustunde kirmizi hap, parlayip soner
                fa = min(1, (t - qs)/0.15, (qs + 1.2 - t)/0.3); fl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(fl)
                ff = F("Montserrat-900", 40); w = fd.textlength("ZOR SORU", font=ff) + 50; yb = 770
                fd.rounded_rectangle((CX - w/2, yb - 30, CX + w/2, yb + 30), 30, fill=ZOR_RENK + (int(235*fa),), outline=GOLD + (int(255*fa),), width=3)
                fd.text((CX, yb + 2), "ZOR SORU", font=ff, fill=(255, 240, 215, int(255*fa)), anchor="mm")
                im = im.convert("RGBA"); im.alpha_composite(fl); im = im.convert("RGB")
            al = min(1, (t - qs)/0.25, max(0, (gone - t)/0.25))
            if al < 1: im = Image.blend(bg, im, al)
        acik = ev[0][0] <= t < outro and t >= ev[cur][2]
        if not a.no_wm:
            wx = int(CX - WM.width/2 + 230*math.sin(t*0.21)); wy = int(CY - WM.height/2 + 330*math.sin(t*0.13 + 1.1))
        if not a.no_wm:  # filigran HER karede: soluk (%17), kesintisiz suzulur, yazilarin ustunden gecer
            im = im.convert("RGBA"); im.alpha_composite(WM, (wx, wy)); im = im.convert("RGB")
        if acik and ev[cur][2] + 0.35 <= t and cur not in kutular:
            kutular[cur] = dict(metin=[list(b) for b in KUTU], filigran=None if a.no_wm else [wx, wy, wx + WM.width, wy + WM.height])
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait(); os.remove(tmpa)
    json.dump([dict(harf=Q[i][0], soru_t=round(e[0], 2), soru_bit=round(e[1], 2), cevap_t=round(e[2], 2), cevap_bit=round(e[3], 2)) for i, e in enumerate(ev)], open(a.out + ".times.json", "w"), ensure_ascii=False)
    bal = [[round(x), round(y), RR] for x, y in (pos(i, n) for i in range(n))]
    json.dump(dict(balonlar=bal, kartlar={Q[i][0]: v for i, v in kutular.items()}), open(a.out + ".kutular.json", "w"), ensure_ascii=False)
    print("sure", dur)

if __name__ == "__main__": main()
