"""3D (Blender) korku/gerilim serisi için birleştirici: render edilen kareleri sesle hizalar, üstüne yazıları ve sesi ekler.
Kullanım: python scripts/uc_boyut_birlestir.py --proje projects/otel-13-part-1 --kareler /tmp/kareler --fps 24 [--out video.mp4]

- Her 3D sahnenin süresi, o sahneye ait cümlelerin seste okunduğu zamana esnetilir (görüntü sesi bekler).
- Kural kartı daktilo efektiyle, altyazılar, PART rozeti, açılış kancası, sondaki seçim ekranı koddan çizilir.
- Ses: anlatım + koddan üretilen ortam uğultusu, telefon zili, su sesi, asansör "ding".
"""
import os, sys, json, math, argparse, subprocess, glob, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "engine"))
from core import W, H, F, GOLD, WHITE, clamp, ease, text, put, caption_img, VIG, GRAIN, rmask
from align import align

SR = 44100
# Blender tarafındaki sahne aralıkları (sn) — engine/blender/otel13.py ile aynı
SAHNE_ARALIK = {"koridor": (0.0, 5.0), "oda": (5.0, 9.6), "banyo": (9.6, 14.4), "asansor": (14.4, 20.0)}


def wav_oku(p):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).copy()


def wav_yaz(p, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype(np.int16)
    with wave.open(p, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())


def efektler(sure, olay):
    """olay: {"zil": (t0, t1), "su": (t0, t1), "ding": t}"""
    n = int(sure * SR); t = np.arange(n) / SR; rng = np.random.default_rng(7); x = np.zeros(n, np.float32)
    # ortam uğultusu: alçak sinüsler + filtrelenmiş gürültü, yavaş nefes alan genlik
    gur = rng.standard_normal(n).astype(np.float32); k = np.ones(400) / 400; gur = np.convolve(gur, k, "same")
    x += (0.05 * np.sin(2 * np.pi * 48 * t) + 0.03 * np.sin(2 * np.pi * 73.4 * t) + 0.35 * gur) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t))
    if "zil" in olay:  # eski telefon zili: 2 sn çal, 1 sn sus; ~20 Hz titreşimli iki ton
        a, b = olay["zil"]; m = (t >= a) & (t < b); tt = t[m] - a
        acik = ((tt % 3.0) < 1.6).astype(np.float32); titr = (np.sin(2 * np.pi * 20 * tt) > 0).astype(np.float32)
        x[m] += 0.16 * acik * titr * (np.sin(2 * np.pi * 950 * tt) + 0.6 * np.sin(2 * np.pi * 1150 * tt))
    if "su" in olay:  # akan su: bant geçiren gürültü + damla tıkırtıları
        a, b = olay["su"]; m = (t >= a) & (t < b); g = rng.standard_normal(m.sum()).astype(np.float32)
        g = g - np.convolve(g, np.ones(6) / 6, "same"); env = np.clip((t[m] - a) / 0.8, 0, 1) * np.clip((b - t[m]) / 0.8, 0, 1)
        x[m] += 0.10 * g * env
    if "ding" in olay:
        a = olay["ding"]; m = t >= a; tt = t[m] - a
        x[m] += 0.28 * np.exp(-tt * 2.2) * (np.sin(2 * np.pi * 784 * tt) + 0.5 * np.sin(2 * np.pi * 1568 * tt))
    return x


def kural_karti(metin, n):
    """eski kâğıt üstünde daktilo yazısı (n karakter görünür)"""
    w, h = 900, 300; c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 10, fill=(214, 203, 178, 238)); d.rounded_rectangle([10, 10, w - 11, h - 11], 8, outline=(120, 30, 25, 180), width=2)
    d.text((40, 30), "OTEL KURALLARI", font=F("mono", 34), fill=(120, 25, 20, 255))
    satirlar, cur = [], ""
    for k in metin.split():
        if F("mono", 34).getlength(cur + " " + k) > w - 80 and cur: satirlar.append(cur); cur = k
        else: cur = (cur + " " + k).strip()
    satirlar.append(cur); kalan = n; y = 95
    for s in satirlar:
        g = s[:max(0, kalan)]; kalan -= len(s) + 1
        d.text((40, y), g, font=F("mono", 34), fill=(30, 22, 18, 255)); y += 48
    return c


def secim_ekrani(fr, p, secenekler, alt):
    fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(200 * clamp(p * 2)))))
    a = clamp(p * 2.5)
    put(fr, text("SEN OLSAN NE YAPARDIN?", "sans9", 52, WHITE, spacing=4), W / 2, 640, a)
    for i, s in enumerate(secenekler):
        q = clamp((p - 0.15 - i * 0.12) * 3)
        if q <= 0: continue
        b = Image.new("RGBA", (860, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(b)
        renk = [(200, 40, 40), (60, 120, 210)][i % 2]
        d.rounded_rectangle([0, 0, 859, 149], 26, fill=renk + (235,)); d.text((60, 75), str(i + 1), font=F("sans9", 76), fill=(255, 255, 255), anchor="lm")
        d.text((150, 75), s, font=F("sans9", 50), fill=(255, 255, 255), anchor="lm")
        put(fr, b, W / 2, 820 + i * 190, q, 0.9 + 0.1 * ease(q))
    put(fr, text(alt, "sans9", 36, GOLD, spacing=4), W / 2, 1240, clamp((p - 0.5) * 3))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--proje", required=True); ap.add_argument("--kareler", required=True); ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--out", default=""); ap.add_argument("--onizleme", default=""); a = ap.parse_args()
    d = a.proje; sc = json.load(open(os.path.join(d, "script.json"), encoding="utf-8"))
    kareler = sorted(glob.glob(os.path.join(a.kareler, "*.png"))); NK = len(kareler); print("kare", NK)
    ses = os.path.join(d, "ses.wav"); OFF = 0.4
    satir = [l for s in sc["sahneler"] for l in s["lines"]]; sahip = [i for i, s in enumerate(sc["sahneler"]) for _ in s["lines"]]
    sp = [x for x in sc.get("seslendirme_metni", "").split("\n") if x.strip()]
    segs, vdur = align(ses, satir, sp if len(sp) == len(satir) else None)
    for g in segs: g["start"] += OFF; g["end"] += OFF
    SON = 3.2; sure = vdur + OFF + SON; print("ses", round(vdur, 2), "video", round(sure, 2))
    # her sahnenin seste kapladığı aralık
    sz = []
    for i, s in enumerate(sc["sahneler"]):
        mine = [g for g, o in zip(segs, sahip) if o == i]; sz.append([mine[0]["start"], mine[-1]["end"]])
    sz[0][0] = 0.0
    for i in range(1, len(sz)): sz[i][0] = sz[i - 1][1] = (sz[i - 1][1] + sz[i][0]) / 2
    sz[-1][1] = sure
    def kaynak_kare(t):
        for (t0, t1), s in zip(sz, sc["sahneler"]):
            if t0 <= t < t1 or s is sc["sahneler"][-1]:
                a0, a1 = SAHNE_ARALIK[s["sahne"]]; p = clamp((t - t0) / max(0.01, t1 - t0))
                f = int((a0 + (a1 - a0) * p) * a.fps); return min(NK - 1, max(0, f))
        return NK - 1
    # ses: anlatım + efektler
    v = wav_oku(ses); n = int(sure * SR); mix = np.zeros(n, np.float32); o = int(OFF * SR); mix[o:o + len(v)] += v[:n - o] * 1.0
    oda, banyo, asn = sz[1], sz[2], sz[3]
    mix += efektler(sure, {"zil": (oda[0] + 0.2, oda[1] - 0.1), "su": (banyo[0] + 0.3, banyo[1]), "ding": asn[0] + 0.15})
    mix *= 0.9 / max(1e-6, np.abs(mix).max()); tmpw = os.path.join(d, "_karisim.wav"); wav_yaz(tmpw, mix)
    out = a.out or os.path.join(d, "out", "video.mp4"); os.makedirs(os.path.dirname(out), exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-", "-i", tmpw,
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", out], stdin=subprocess.PIPE)
    kural = "Saat 03.00'te telefon çalarsa kaç kişi olduğunuzu söylemeyin."
    rozet = None; cache = {}
    if sc.get("seri"):
        g = text(sc["seri"], "sans9", 30, (255, 255, 255), spacing=6, shadow=False); pad = 18
        rozet = Image.new("RGBA", (g.width - 40 + 2 * pad, 64), (0, 0, 0, 0)); ImageDraw.Draw(rozet).rounded_rectangle([0, 0, rozet.width - 1, 63], 14, fill=(170, 24, 24, 230))
        rozet.alpha_composite(g, (pad - 40, (64 - g.height) // 2))
    onz = []
    for k in range(int(sure * 30)):
        t = k / 30; fi = kaynak_kare(t)
        if fi not in cache:
            cache.clear(); cache[fi] = Image.open(kareler[fi]).convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
        fr = cache[fi].copy()
        fr.alpha_composite(VIG); fr.alpha_composite(GRAIN[k % len(GRAIN)])
        if t < 3.0: put(fr, text("BU OTELİN TEK BİR KURALI VAR", "sans9", 40, WHITE, spacing=6), W / 2, 330, clamp(t / .4) * clamp((3.0 - t) / .4))
        g2 = segs[1]
        if g2["start"] - 0.2 <= t < sz[0][1]:
            q = t - (g2["start"] - 0.2); nn = int(len(kural) * clamp(q / max(0.5, g2["end"] - g2["start"])))
            put(fr, kural_karti(kural, nn), W / 2, 720, clamp(q / .3) * clamp((sz[0][1] - t) / .3))
        if rozet is not None: put(fr, rozet, 60 + rozet.width / 2, 215, clamp((t - .3) / .4))
        son = sure - SON
        if t < son:
            for g in segs:
                if g["start"] - .1 <= t < g["end"] + .05:
                    put(fr, caption_img(g["text"]), W / 2, 1500, clamp((t - g["start"] + .1) / .25) * clamp((g["end"] + .05 - t) / .2))
        else:
            secim_ekrani(fr, (t - son) / SON, ["BANYOYA BAK", "ASANSÖRE BİN"], "YORUMA YAZ · PART 2 YARIN")
        if t < .4: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / .4)))))
        rgb = fr.convert("RGB"); ff.stdin.write(rgb.tobytes())
        if a.onizleme and k in (int(1.5 * 30), int(sz[1][0] * 30 + 30), int(sz[2][0] * 30 + 45), int((sure - 1.2) * 30)): onz.append(rgb.resize((270, 480)))
    ff.stdin.close(); ff.wait(); os.remove(tmpw)
    if onz:
        im = Image.new("RGB", (270 * len(onz), 480)); [im.paste(x, (270 * i, 0)) for i, x in enumerate(onz)]; im.save(a.onizleme, quality=85)
    print("bitti", out)


if __name__ == "__main__":
    main()
