"""Atmosfer efektleri (kıvılcım, kar, toz, yağmur, sis, duman, ışık hüzmesi) ve ay yıldız finali."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from core import W, H, clamp, ease

def sprite(r, col, soft=True):
    m = Image.new("L", (r * 4, r * 4), 0); ImageDraw.Draw(m).ellipse([r, r, 3 * r, 3 * r], fill=255)
    if soft: m = m.filter(ImageFilter.GaussianBlur(r * 0.6))
    s = Image.new("RGBA", m.size, col + (0,)); s.putalpha(m); return s
COLS = {"ember": (255, 150, 60), "snow": (245, 248, 255), "dust": (255, 228, 180), "gold": (255, 210, 120), "spark": (255, 245, 215)}
_spr = {}
def spr(kind, r):
    if (kind, r) not in _spr: _spr[(kind, r)] = sprite(r, COLS[kind])
    return _spr[(kind, r)]

class Field:
    def __init__(self, kind, n, seed):
        r = np.random.default_rng(seed); self.kind = kind; self.n = n
        self.x = r.random(n) * W; self.y = r.random(n) * H; self.ph = r.random(n) * 6.28
        self.sz = r.integers(2, 9 if kind == "snow" else 7, n); self.sp = 0.5 + r.random(n)
    def draw(self, fr, t, a=1.0):
        if a <= 0: return
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for i in range(self.n):
            if self.kind == "ember":
                y = (self.y[i] - t * 160 * self.sp[i]) % (H + 200) - 100; x = self.x[i] + 40 * math.sin(t * 1.3 * self.sp[i] + self.ph[i])
                al = (0.5 + 0.5 * math.sin(t * 8 * self.sp[i] + self.ph[i])) * clamp(y / H * 1.6)
            elif self.kind == "snow":
                y = (self.y[i] + t * 120 * self.sp[i]) % (H + 100) - 50; x = (self.x[i] + 30 * math.sin(t * 0.9 + self.ph[i]) + t * 20) % W; al = 0.85
            else:
                y = (self.y[i] - t * 14 * self.sp[i]) % H; x = (self.x[i] + t * 18 * self.sp[i] + 25 * math.sin(t * .5 + self.ph[i])) % W
                al = (0.35 + 0.35 * math.sin(t * 1.5 + self.ph[i])) * (1.6 if self.kind == "gold" else 1)
            if al <= 0.02: continue
            s = spr(self.kind, int(self.sz[i])); s2 = s.copy(); s2.putalpha(s.split()[3].point(lambda v: int(v * min(1, al * a))))
            lay.alpha_composite(s2, (int(x - s.width / 2), int(y - s.height / 2)))
        fr.alpha_composite(lay)

class Rain:
    def __init__(self, n, seed):
        r = np.random.default_rng(seed); self.x = r.random(n) * W; self.y = r.random(n) * H; self.sp = 0.7 + r.random(n) * 0.6; self.n = n
    def draw(self, fr, t, a=1.0):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for i in range(self.n):
            y = (self.y[i] + t * 1500 * self.sp[i]) % (H + 200) - 100; x = (self.x[i] - t * 200 * self.sp[i]) % W
            d.line([(x, y), (x + 9, y - 60 * self.sp[i])], fill=(200, 210, 230, int(90 * a)), width=2)
        fr.alpha_composite(lay)

def _fog_tex(seed):
    r = np.random.default_rng(seed); n = r.random((12, 22))
    im = Image.fromarray((n * 255).astype(np.uint8)).resize((W * 2, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(60))
    a = np.clip((np.asarray(im).astype(np.float32) - 110) * 1.4, 0, 255).astype(np.uint8)
    f = Image.new("RGBA", (W * 2, H), (220, 215, 205, 0)); f.putalpha(Image.fromarray(a)); return f
FOG = None
def fog(fr, t, a=0.6, smoke=False):
    global FOG
    if FOG is None: FOG = [_fog_tex(5), _fog_tex(9)]
    for k, f in enumerate(FOG):
        off = int((t * (40 + 25 * k)) % W); lay = f.crop((off, 0, off + W, H))
        if smoke: lay = Image.merge("RGBA", (*Image.new("RGB", (W, H), (120, 115, 110)).split(), lay.split()[3]))
        lay.putalpha(lay.split()[3].point(lambda v: int(v * a * (0.6 if k else 0.45)))); fr.alpha_composite(lay)

def rays(fr, t, cx=0.78, a=0.3):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); ox, oy = W * cx, -200
    for k in range(7):
        ang = math.radians(100 + k * 9 + 3 * math.sin(t * 0.4 + k)); w = 40 + 25 * math.sin(t * 0.7 + k * 2)
        x1, y1 = ox + math.cos(ang) * 2600, oy + math.sin(ang) * 2600; nx, ny = -math.sin(ang) * w, math.cos(ang) * w
        d.polygon([(ox, oy), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny)], fill=(255, 225, 170, int(40 * a / 0.35)))
    fr.alpha_composite(lay.filter(ImageFilter.GaussianBlur(30)))

FIELDS = {}
def _field(name):
    if name not in FIELDS:
        FIELDS[name] = {"ember": lambda: Field("ember", 70, 1), "ember_few": lambda: Field("ember", 22, 2), "snow": lambda: Field("snow", 170, 3),
                        "dust": lambda: Field("dust", 45, 4), "gold": lambda: Field("gold", 60, 5), "rain": lambda: Rain(160, 6)}[name]()
    return FIELDS[name]

def atmos(fr, effects, t, a=1.0):
    """effects: ["fog","smoke","rays","flicker","ember","ember_few","snow","dust","gold","rain"]"""
    for e in effects or []:
        if e == "fog": fog(fr, t, 0.55 * a)
        elif e == "smoke": fog(fr, t * 1.4, 0.75 * a, smoke=True)
        elif e == "rays": rays(fr, t, 0.78, 0.3 * a)
        elif e == "flicker":
            fl = 0.5 + 0.5 * math.sin(t * 13) * math.sin(t * 7.3 + 1)
            fr.alpha_composite(Image.new("RGBA", (W, H), (255, 140, 40, int(22 * fl * a))))
        else: _field(e).draw(fr, t, a)

# ── Ay yıldız finali ──
class AyYildiz:
    def __init__(self, t0, t1, t2, t3, cy=930, n=1300):
        self.t = (t0, t1, t2, t3); self.cy = cy
        m = Image.new("L", (800, 600), 0); d = ImageDraw.Draw(m)
        d.ellipse([60, 60, 540, 540], fill=255); d.ellipse([180, 120, 564, 504], fill=0)
        cx, cyy, R, r = 610, 300, 130, 52
        d.polygon([(cx + math.cos(math.pi + k * math.pi / 5) * (R if k % 2 == 0 else r), cyy + math.sin(math.pi + k * math.pi / 5) * (R if k % 2 == 0 else r)) for k in range(10)], fill=255)
        a = np.asarray(m); ys, xs = np.nonzero(a); edge = np.asarray(m.filter(ImageFilter.FIND_EDGES)); ey, ex = np.nonzero(edge)
        rg = np.random.default_rng(8); i1 = rg.choice(len(xs), n // 2, replace=False); i2 = rg.choice(len(ex), n - n // 2, replace=False)
        X = np.concatenate([xs[i1], ex[i2]]).astype(float); Y = np.concatenate([ys[i1], ey[i2]]).astype(float)
        self.CX = (X - 400) * 1.15 + W / 2; self.CY = (Y - 300) * 1.15 + cy
        r2 = np.random.default_rng(12); self.SX = r2.random(n) * W; self.SY = H * 0.55 + r2.random(n) * H * 0.5; self.PH = r2.random(n) * 6.28
        self.SHAPE = m.resize((int(800 * 1.15), int(600 * 1.15)), Image.BILINEAR)
    def draw(self, fr, tv):
        t0, t1, t2, t3 = self.t
        if not (t0 <= tv < t3): return
        k = ease((tv - t0) / (t1 - t0)) if tv < t1 else 1
        q = clamp((tv - t2) / (t3 - t2)) if tv >= t2 else 0; fa = 1 - q
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for j in range(len(self.CX)):
            x = self.SX[j] + (self.CX[j] - self.SX[j]) * k; y = self.SY[j] + (self.CY[j] - self.SY[j]) * k
            if q > 0: x += math.cos(self.PH[j]) * 260 * q; y += (math.sin(self.PH[j]) * 160 - 260) * q
            x += 4 * math.sin(tv * 3 + self.PH[j]); y += 4 * math.cos(tv * 2.5 + self.PH[j])
            s = spr("spark", 3 if j % 3 else 4); lay.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))
        glow = lay.filter(ImageFilter.GaussianBlur(10))
        if t1 - 0.3 <= tv < t2 + 0.6:
            h = clamp((tv - t1 + 0.3) / 0.6) * clamp((t2 + 0.6 - tv) / 0.8); S = self.SHAPE
            g2 = Image.new("RGBA", S.size, (255, 200, 110, 0)); g2.putalpha(S.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(min(255, v * 0.9) * h)))
            sh = Image.new("RGBA", S.size, (255, 222, 150, 0)); sh.putalpha(S.point(lambda v: int(v * 0.5 * h)))
            pos = (int(W / 2 - S.width / 2), int(self.cy - S.height / 2)); fr.alpha_composite(g2, pos); fr.alpha_composite(sh, pos)
        g = glow.copy(); g.putalpha(g.split()[3].point(lambda v: int(min(255, v * 3.0) * fa)))
        l2 = lay.copy(); l2.putalpha(lay.split()[3].point(lambda v: int(v * fa)))
        fr.alpha_composite(g); fr.alpha_composite(l2)
