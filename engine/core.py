"""Ortak çizim yardımcıları: yazı tipleri, metin görüntüleri, Ken Burns, katmanlar."""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = {
    "serif": os.path.join(HERE, "fonts", "Cinzel-700.ttf"),
    "sans": os.path.join(HERE, "fonts", "Montserrat-700.ttf"),
    "sans9": os.path.join(HERE, "fonts", "Montserrat-900.ttf"),
    "mono": os.path.join(HERE, "fonts", "DejaVuSansMono-Bold.ttf"),
}
GOLD = (232, 196, 120); WHITE = (255, 255, 255)
_f = {}
def F(name, s):
    path = FONT.get(name, name)
    if (path, s) not in _f: _f[(path, s)] = ImageFont.truetype(path, s)
    return _f[(path, s)]

def clamp(x): return max(0., min(1., x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def inout(x): x = clamp(x); return x * x * (3 - 2 * x)

def rmask(sz, r):
    m = Image.new("L", sz, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, sz[0] - 1, sz[1] - 1], r, fill=255); return m

_tc = {}
def text(txt, font, size, col, glow=None, spacing=0, shadow=True):
    k = (txt, font, size, col, glow, spacing, shadow)
    if k in _tc: return _tc[k]
    f = F(font, size)
    w = int(sum(f.getlength(c) for c in txt) + spacing * max(0, len(txt) - 1)) + 80
    h = int(size * 1.5) + 40
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 40
    for c in txt: d.text((x, 20), c, font=f, fill=col); x += f.getlength(c) + spacing
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    if shadow:
        s = Image.new("RGBA", im.size, (0, 0, 0, 0)); s.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * .85))); out.alpha_composite(s, (0, 4))
    if glow:
        g = Image.new("RGBA", im.size, tuple(glow) + (0,)); g.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * .55))); out.alpha_composite(g)
    out.alpha_composite(im); _tc[k] = out; return out

def put(fr, im, cx, cy, a=1.0, s=1.0):
    if a <= 0.004: return
    if abs(s - 1) > .003: im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if a < .999: im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def wrap(txt, f, maxw):
    words = txt.split(); lines = []; cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) > maxw and cur: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur); return lines

_cc = {}
def caption_img(txt, size=50):
    if (txt, size) in _cc: return _cc[(txt, size)]
    f = F("sans", size); lines = wrap(txt, f, 900); lh = int(size * 1.4)
    im = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, l in enumerate(lines): d.text((W / 2, 20 + i * lh + lh / 2), l, font=f, fill=WHITE, anchor="mm")
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); s = Image.new("RGBA", im.size, (0, 0, 0, 0))
    s.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: min(255, int(v * 1.2)))); out.alpha_composite(s, (0, 3)); out.alpha_composite(im)
    _cc[(txt, size)] = out; return out

_im = {}
def load_image(path):
    if path not in _im:
        im = Image.open(path).convert("RGB")
        # 9:16 değilse ortadan kırp
        r = im.width / im.height
        if r > W / H + 0.01:
            nw = int(im.height * W / H); x0 = (im.width - nw) // 2; im = im.crop((x0, 0, x0 + nw, im.height))
        _im[path] = ImageEnhance.Color(im).enhance(0.92)
    return _im[path]

def kenburns(path, p, z0, z1, cx0, cy0, cx1, cy1):
    src = load_image(path); e = inout(p)
    z = z0 + (z1 - z0) * e; cx = cx0 + (cx1 - cx0) * e; cy = cy0 + (cy1 - cy0) * e
    bw = src.width / z; bh = bw * H / W
    if bh > src.height / z * 1.0001: bh = src.height / z; bw = bh * W / H
    x0 = min(max(cx * src.width - bw / 2, 0), src.width - bw); y0 = min(max(cy * src.height - bh / 2, 0), src.height - bh)
    return src.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh)).convert("RGBA")

def _vignette():
    yy, xx = np.mgrid[0:H, 0:W]; d = ((xx / W - .5) ** 2 * 1.6 + (yy / H - .5) ** 2) ** .5
    a = np.clip((d - .35) / .45, 0, 1) ** 1.6 * 200
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0)); v.putalpha(Image.fromarray(a.astype(np.uint8))); return v
def _bands():
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for y in range(620): d.line([(0, y), (W, y)], fill=(0, 0, 0, int(170 * (1 - y / 620) ** 1.5)))
    for y in range(760): d.line([(0, H - 1 - y), (W, H - 1 - y)], fill=(0, 0, 0, int(215 * (1 - y / 760) ** 1.3)))
    return g
def _grain(n=6, seed=3):
    rng = np.random.default_rng(seed); out = []
    for i in range(n):
        z = rng.normal(0, 1, (H // 2, W // 2)); a = np.clip(np.abs(z) * 14, 0, 40).astype(np.uint8)
        col = np.where(z > 0, 255, 0).astype(np.uint8)
        out.append(Image.merge("RGBA", [Image.fromarray(col)] * 3 + [Image.fromarray(a)]).resize((W, H), Image.NEAREST))
    return out
VIG = _vignette(); BANDS = _bands(); GRAIN = _grain()

def gold_card(fr, cx, cy, big, small, p, w=600, h=230):
    if p <= 0: return
    # yazı sığmıyorsa kartı genişlet (en fazla ekran genişliği - 80)
    w = int(min(W - 80, max(w, F("serif", 96).getlength(big) + 90, F("sans9", 30).getlength(small) + 70)))
    box = (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))
    reg = ImageEnhance.Brightness(fr.crop(box).filter(ImageFilter.GaussianBlur(22))).enhance(0.55)
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); c.alpha_composite(reg.convert("RGBA")); c.alpha_composite(Image.new("RGBA", (w, h), (10, 8, 4, 90)))
    d = ImageDraw.Draw(c); d.rounded_rectangle([2, 2, w - 3, h - 3], 26, outline=GOLD + (220,), width=3)
    d.rounded_rectangle([12, 12, w - 13, h - 13], 20, outline=GOLD + (70,), width=1)
    d.text((w / 2, h * 0.42), big, font=F("serif", 96), fill=GOLD, anchor="mm")
    d.text((w / 2, h * 0.78), small, font=F("sans9", 30), fill=(245, 235, 215), anchor="mm")
    c.putalpha(rmask((w, h), 26))
    s = 0.88 + 0.12 * (1 - (1 - clamp(p)) ** 3)
    put(fr, c, cx, cy + (1 - ease(p)) * 30, clamp(p * 1.5), s)
