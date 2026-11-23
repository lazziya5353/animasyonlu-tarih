#!/usr/bin/env python3
"""Harf quiz Reel renderer.
Kullanim: harf_quiz.py sorular.json project.timed.json ses.wav cikti.mp4 [--kapak kapak.jpg] [--pause 1.5]
sorular.json: [[harf, soru, CEVAP(büyük harf), ipucu, okunan_cevap], ...]
timed.json sahneleri: 0=intro, sonra her harf icin (soru, cevap), son=outro (her sahne tek satir).
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

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("q"); ap.add_argument("timed"); ap.add_argument("wav"); ap.add_argument("out")
    ap.add_argument("--kapak"); ap.add_argument("--pause", type=float, default=3.0)
    a = ap.parse_args()
    Q = json.load(open(a.q)); letters = [x[0] for x in Q]; n = len(Q)
    B = base()
    if a.kapak:
        im = B.copy(); d = ImageDraw.Draw(im); ring(d, letters, set(range(n)), None)
        d.text((CX, 1010), "KAÇINI", font=F("Cinzel-700", 104), fill=GOLD, anchor="ms")
        d.text((CX, 1130), "BİLDİN?", font=F("Cinzel-700", 104), fill=GOLD, anchor="ms")
        d.text((CX, 1200), f"{n} HARF · {n} SORU", font=F("Montserrat-900", 34), fill=WHITE, anchor="ms")
        im.save(a.kapak, quality=93)
    T = json.load(open(a.timed)); sc = T["scenes"]; off = T.get("voice_offset", 0)
    assert len(sc) == 2*n + 2, (len(sc), n)
    # sahne zamanlari video zamaninda; ses dosyasi zamani = t - off
    cuts = [sc[1 + 2*i]["end"] for i in range(n)]   # soru bitisleri (video zamani)
    P = a.pause
    def sh(t): return t + P*sum(1 for c in cuts if t >= c - 1e-6)
    # ses: segmentler + sessizlik
    filt, labs, prev = [], [], 0.0
    pts = [c - off for c in cuts]
    for j, p in enumerate(pts + [None]):
        tr = f"atrim=start={prev}" + (f":end={p}" if p is not None else "")
        filt.append(f"[0:a]{tr},asetpts=PTS-STARTPTS[s{j}]"); labs.append(f"[s{j}]")
        if p is not None:
            filt.append(f"anullsrc=r=48000:cl=mono,atrim=duration={P}[z{j}]"); labs.append(f"[z{j}]"); prev = p
    filt.append(f"{''.join(labs)}concat=n={len(labs)}:v=0:a=1,adelay={int(off*1000)}:all=1,apad=pad_dur=1.2[aout]")
    tmpa = a.out + ".a.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.wav, "-filter_complex", ";".join(filt), "-map", "[aout]", "-ac", "1", "-ar", "48000", "-c:a", "aac", "-b:a", "160k", tmpa], check=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", tmpa]))
    ev = []  # (k, q_start, a_start, a_end)
    for i in range(n):
        qs, qe = sc[1+2*i]["start"], sc[1+2*i]["end"]; as_ = sc[2+2*i]["start"]
        ev.append((i, sh(qs), sh(as_), sh(sc[2+2*i]["end"]), sh(qe - 1e-3) + 1e-3))
    intro_end = sc[1]["start"]; outro = sh(sc[-1]["start"])
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", tmpa, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for fi in range(int(dur*FPS)):
        t = fi / FPS; im = B.copy(); d = ImageDraw.Draw(im)
        if t >= outro:
            ring(d, letters, set(range(n)), None)
            center(im, None, n, "", "KAÇINI BİLDİN?", "YORUMLARA YAZ", min(1, (t-outro)/0.3), 1)
        elif t < intro_end:
            ring(d, letters, set(), None)
            center(im, None, n, "", f"{n} HARF", f"{n} SORU", min(1, t/0.4), 1)
        else:
            cur = max(i for i, qs, *_ in ev if t >= qs - 0.05) if t >= ev[0][1] - 0.05 else 0
            i, qs, as_, ae, qe = ev[cur]
            done = set(range(cur)); ansv = t >= as_
            if ansv: done.add(cur)
            pulse = int(3*math.sin(t*8)) if not ansv else 0
            dd = ImageDraw.Draw(im); ring(dd, letters, done, cur, pulse)
            if t < as_:  # zamanlayici yayi: sorudan cevaba kadar saat yonunde azalir
                rem = 1 - (t - qs) / max(0.01, as_ - qs); r2 = 392
                if rem > 0: dd.arc((CX-r2, CY-r2, CX+r2, CY+r2), -90 + 360*(1-rem), 270, fill=(200, 60, 50), width=6)
            if ansv:
                k = min(1, (t - as_)/0.25); center(im, cur+1, n, Q[cur][1], Q[cur][2], Q[cur][3], k, 0.85 + 0.15*k)
            else:
                center(im, cur+1, n, Q[cur][1], "", "", 0, 1)
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait(); os.remove(tmpa)
    json.dump([dict(harf=Q[i][0], cevap_t=round(e[2], 2)) for i, e in enumerate(ev)], open(a.out + ".times.json", "w"), ensure_ascii=False)
    print("sure", dur)

if __name__ == "__main__": main()
