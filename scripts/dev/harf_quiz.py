#!/usr/bin/env python3
"""Harf quiz Reel renderer (soru -> 3 sn yay -> cevap akisi).
Kullanim: harf_quiz.py script.json ses.wav cikti.mp4 [--timed project.timed.json] [--kapak kapak.jpg]
script.json sahneleri: 0=intro, her harf icin (soru "X harfi. ...", cevap), son=outro.
Ses, sessizliklere (silencedetect) gore kesilip yeniden dizilir: soru sesi, 3.0 sn sessiz yay,
cevap sesi, 1.2 sn bekleme, 0.3 sn kararma. timed.json verilirse sinirlar en yakin sessizlige oturtulur,
verilmezse sessizlikler sirayla kullanilir.
"""
import json, math, subprocess, sys, os, argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
R = os.path.dirname(os.path.abspath(__file__)) + "/../../engine/fonts/"
W, H, FPS = 1080, 1920, 30
GOLD = (232, 196, 120); WHITE = (255, 255, 255); BG = (14, 10, 7)
F = lambda n, s: ImageFont.truetype(R + n + ".ttf", s)
CX, CY, RAD, RR = 540, 1060, 440, 36

def base():
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

def ring(d, letters, done, cur, pulse=0, prog=None):
    lf = F("Montserrat-900", 34); n = len(letters)
    for i, L in enumerate(letters):
        x, y = pos(i, n)
        if i in done: d.ellipse((x-RR, y-RR, x+RR, y+RR), fill=(40, 120, 70), outline=(80, 190, 120), width=4)
        else: d.ellipse((x-RR, y-RR, x+RR, y+RR), fill=(16, 11, 7), outline=GOLD, width=3)
        d.text((x, y+2), L, font=lf, fill=WHITE, anchor="mm")
        if i == cur:
            r = RR + 11 + pulse
            d.ellipse((x-r, y-r, x+r, y+r), outline=(225, 50, 45), width=5)
            if prog is not None:
                r2 = RR + 20
                d.arc((x-r2, y-r2, x+r2, y+r2), -90, -90 + 360*prog, fill=GOLD, width=4)

def center(im, k, n, q, ans, hint, a_alpha, a_scale):
    d = ImageDraw.Draw(im)
    MW = 2*(RAD-RR) - 150
    if k is not None:
        d.text((CX, 840), f"{k} / {n}", font=F("Montserrat-900", 40), fill=GOLD, anchor="ms")
    y = 875
    if q:
        f, ls = fitlines(d, q, "Montserrat-700", 50, MW, 3)
        for l in ls: d.text((CX, y), l, font=f, fill=WHITE, anchor="mt"); y += int(f.size*1.3)
    if ans and a_alpha > 0:
        lay = Image.new("RGBA", (W, 520), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        f, ls = fitlines(ld, ans, "Cinzel-700", 84, MW, 2, 48)
        yy = 10
        for l in ls: ld.text((CX, yy), l, font=f, fill=GOLD + (255,), anchor="mt"); yy += int(f.size*1.18)
        if hint: ld.text((CX, yy + 18), f"•  {hint}  •", font=F("Montserrat-900", 34), fill=(225, 210, 190, 255), anchor="mt"); yy += 70
        lay = lay.crop((0, 0, W, yy + 10))
        if a_scale != 1:
            lay = lay.resize((int(W*a_scale), int(lay.height*a_scale)), Image.LANCZOS)
        if a_alpha < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v*a_alpha)))
        top = max(y + 20, 1060 - 10) if len(q or "") else 1000
        im.paste(lay, (CX - lay.width//2, top + int((1 - a_scale)*60)), lay)

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
    ap.add_argument("--pause", type=float, default=3.0); ap.add_argument("--hold", type=float, default=1.2)
    a = ap.parse_args()
    import numpy as np
    S = [" ".join(x["lines"]) for x in json.load(open(a.script))["sahneler"]]
    n = (len(S) - 2)//2; Q = []
    for k in range(n):
        q = S[1+2*k]; L, rest = q.split(" harfi.", 1)
        Q.append((L.strip(), rest.strip(), up(S[2+2*k].strip().rstrip("."))))
    letters = [x[0] for x in Q]
    B = base()
    if a.kapak:
        im = B.copy(); d = ImageDraw.Draw(im); ring(d, letters, set(range(n)), None)
        d.text((CX, 1010), "KAÇINI", font=F("Cinzel-700", 104), fill=GOLD, anchor="ms")
        d.text((CX, 1130), "BİLDİN?", font=F("Cinzel-700", 104), fill=GOLD, anchor="ms")
        d.text((CX, 1200), f"{n} HARF · {n} SORU", font=F("Montserrat-900", 34), fill=WHITE, anchor="ms")
        im.save(a.kapak, quality=93)
    # --- sesi sessizliklerle 2n+2 parcaya bol
    SR = 48000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.wav, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    au = np.frombuffer(raw, np.float32); tot = len(au)/SR
    sil = [x for x in silences(a.wav) if x[0] > 0.05 and x[1] < tot - 0.05]
    if a.timed:
        sc = json.load(open(a.timed))["scenes"]; assert len(sc) == 2*n + 2
        gaps = []
        for k in range(1, len(sc)):
            b = (sc[k-1]["end"] + sc[k]["start"])/2
            g = min(sil, key=lambda g: abs((g[0]+g[1])/2 - b))
            gaps.append(g if abs((g[0]+g[1])/2 - b) < 0.4 and g not in gaps else (b - 0.08, b + 0.06))
    else:
        gaps = sorted(sorted(sil, key=lambda g: g[0]-g[1])[:2*n+1])
    assert len(set(gaps)) == 2*n + 1, "sessizlik sayisi yetmiyor"
    edges = [(0.0, None)] + gaps + [(None, tot)]
    segs = []
    for k in range(2*n + 2):
        s0 = edges[k][1] - 0.06 if edges[k][1] is not None else 0.0
        s1 = edges[k+1][0] + 0.08 if edges[k+1][0] is not None else tot
        segs.append(au[int(max(0, s0)*SR):int(s1*SR)])
    z = lambda t: np.zeros(int(t*SR), np.float32)
    parts, t = [segs[0], z(0.3)], len(segs[0])/SR + 0.3
    ev = []  # (q_start, q_end, a_start, a_end, gone)
    for k in range(n):
        qa, aa = segs[1+2*k], segs[2+2*k]
        qs = t; qe = qs + len(qa)/SR; as_ = qe + a.pause; ae = as_ + len(aa)/SR; gone = ae + a.hold + 0.3
        parts += [qa, z(a.pause), aa, z(a.hold + 0.3)]; ev.append((qs, qe, as_, ae, gone)); t = gone
    outro = t; parts += [segs[-1], z(1.2)]
    A = np.concatenate(parts); dur = len(A)/SR
    tmpa = a.out + ".a.wav"
    import wave
    with wave.open(tmpa, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(A, -1, 1)*32767).astype("<i2").tobytes())
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", tmpa, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for fi in range(int(dur*FPS)):
        t = fi / FPS; im = B.copy(); d = ImageDraw.Draw(im)
        if t >= outro:
            ring(d, letters, set(range(n)), None)
            center(im, None, n, "", "KAÇINI BİLDİN?", "YORUMLARA YAZ", min(1, (t-outro)/0.3), 1)
        elif t < ev[0][0]:
            ring(d, letters, set(), None)
            center(im, None, n, "", f"{n} HARF", f"{n} SORU", min(1, t/0.4), 1)
        else:
            cur = max(i for i, e in enumerate(ev) if t >= e[0]); qs, qe, as_, ae, gone = ev[cur]
            ansv = t >= as_; done = set(range(cur + (1 if ansv else 0)))
            ring(d, letters, done, cur, 0 if ansv else int(3*math.sin(t*8)))
            if qe <= t < as_:  # sessiz bekleme: kirmizi yay 12'den saat yonunde dolar
                r2 = 392; dd = ImageDraw.Draw(im)
                dd.arc((CX-r2, CY-r2, CX+r2, CY+r2), -90, -90 + 360*min(1, (t-qe)/(as_-qe)), fill=(200, 60, 50), width=6)
            bg = im.copy()
            if ansv:
                k = min(1, (t - as_)/0.3); center(im, cur+1, n, Q[cur][1], Q[cur][2], "", k, 0.9 + 0.1*k)
            else:
                center(im, cur+1, n, Q[cur][1], "", "", 0, 1)
            al = min(1, (t - qs)/0.4, max(0, (gone - t)/0.3))
            if al < 1: im = Image.blend(bg, im, al)
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait(); os.remove(tmpa)
    json.dump([dict(harf=Q[i][0], soru_t=round(e[0], 2), cevap_t=round(e[2], 2)) for i, e in enumerate(ev)], open(a.out + ".times.json", "w"), ensure_ascii=False)
    print("sure", dur)

if __name__ == "__main__": main()
