"""Deprem / veri animasyonları (koddan çizilir, yapay zekâ görseli gerekmez).

project.json sahnesinde  "anim": {"tur": ..., ...}
  tur = "halka"       : deprem merkezinden yayılan halkalar, halka değdikçe yanan şehirler
        {"merkez": [lon, lat], "buyukluk": "7,4", "sehirler": {"İstanbul": [lon, lat], ...},
         "ust": "17 AĞUSTOS 1999 · 03.02", "alt": "45 SANİYE", "sayac": [16, "MİLYON KİŞİ ETKİLENDİ"]}
  tur = "fay"         : kırılmış (kırmızı, düz) ve kırılmamış (kesik, nabız atan) fay parçaları
        {"kirik": [[lon, lat], ...], "kirik_yazi": "...", "kirilmamis": [[lon, lat], ...], "kirilmamis_yazi": "...",
         "sehirler": {...}, "ust": "...", "cam": [[lon, lat, genislik_derece], [lon, lat, genislik_derece]]}
  tur = "ilce_harita" : İstanbul ilçeleri, orana göre yeşilden kırmızıya boyanır, en uçtaki ilçelere rozet
        {"oran": {"Fatih": 35.6, ...}, "ust": "...", "alt": "...", "rozet": 5}
  tur = "ilce_tablo"  : en yüksek ve en düşük N ilçe, çubuklar dolarak, yüzdeler sayarak
        {"oran": {...}, "n": 5, "ust_baslik": "EN RİSKLİ 5 İLÇE", "alt_baslik": "EN AZ RİSKLİ 5 İLÇE", "birim": "%"}
"""
import os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from core import W, H, GOLD, WHITE, F, clamp, ease, inout, text, put

HERE = os.path.dirname(os.path.abspath(__file__)); MAPDIR = os.path.join(HERE, "map")
KIRMIZI = (226, 64, 52); YESIL = (86, 190, 120); AMBER = (255, 176, 64)


def renk(t):
    """0 → yeşil, 0.5 → sarı, 1 → kırmızı"""
    t = clamp(t); a = [(70, 170, 100), (232, 196, 80), (214, 52, 44)]
    if t < .5: u = t / .5; p, q = a[0], a[1]
    else: u = (t - .5) / .5; p, q = a[1], a[2]
    return tuple(int(p[i] + (q[i] - p[i]) * u) for i in range(3))


def yuzde(v): return f"{v:.1f}".replace(".", ",")


class Harita:
    """Altlık: varsa uydu (Sentinel-2 cloudless 2016 + yakın plan için yüksek çözünürlüklü İstanbul), yoksa çizim altlık."""
    _cache = {}
    ATIF = "Uydu: Sentinel-2 cloudless 2016 · EOX · CC BY 4.0"

    def __init__(self, stil="uydu"):
        R = json.load(open(os.path.join(MAPDIR, "regions.json")))["marmara"]
        self.C = math.cos(math.radians(R["clat"])); self.katman = []
        uj = os.path.join(MAPDIR, "uydu.json")
        if stil == "uydu" and os.path.exists(uj):
            for ad, (lon0, lon1, lat0, lat1, k) in json.load(open(uj))["bolgeler"].items():
                self.katman.append((self._yukle(f"uydu_{ad}.jpg", True), (lon0, lon1, lat0, lat1)))
            self.katman.sort(key=lambda k: (k[1][1] - k[1][0]))  # en dar (en net) önce
            self.uydu = True
        else:
            Rr = R; Wb = (Rr["lon1"] - Rr["lon0"]) * Rr["k"] * self.C
            self.katman.append((self._yukle("basemap_marmara.jpg", False), (Rr["lon0"], Rr["lon1"], Rr["lat0"], Rr["lat1"])))
            self.uydu = False

    def _yukle(self, ad, uydu):
        if ad not in Harita._cache:
            im = Image.open(os.path.join(MAPDIR, ad)).convert("RGB")
            if uydu:  # videonun karanlık, sinematik tonuna uydur: biraz koyu, hafif soğuk gölgeler, az doygun
                a = np.asarray(im).astype(np.float32) / 255.
                lum = a @ np.array([.299, .587, .114], np.float32)
                a = lum[..., None] + (a - lum[..., None]) * .85
                a = np.clip((a - .04) * 1.12, 0, 1) ** 1.12 * .82
                a[..., 2] = a[..., 2] * 1.04 + .015
                im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
            Harita._cache[ad] = im
        return Harita._cache[ad]

    def kare(self, cam):
        lon, lat, wdeg = cam; hdeg = wdeg * H / W * self.C  # ekrandaki enlem aralığı
        b = (lon - wdeg / 2, lon + wdeg / 2, lat - hdeg / 2, lat + hdeg / 2)
        img, (L0, L1, A0, A1) = next(((i, bb) for i, bb in self.katman if bb[0] <= b[0] and b[1] <= bb[1] and bb[2] <= b[2] and b[3] <= bb[3]), self.katman[-1])
        sx, sy = img.width / (L1 - L0), img.height / (A1 - A0)
        x0, x1 = (b[0] - L0) * sx, (b[1] - L0) * sx; y0, y1 = (A1 - b[3]) * sy, (A1 - b[2]) * sy
        dx = min(0, x0) or max(0, x1 - img.width); dy = min(0, y0) or max(0, y1 - img.height)
        x0, x1, y0, y1 = x0 - dx, x1 - dx, y0 - dy, y1 - dy
        fr = img.resize((W, H), Image.BILINEAR, box=(max(0, x0), max(0, y0), min(img.width, x1), min(img.height, y1))).convert("RGBA")
        lonL = L0 + x0 / sx; latT = A1 - y0 / sy; s = W / (x1 - x0)
        def to(lo, la): return ((lo - lonL) * sx * s, (latT - la) * sy * s)
        return fr, to, s


def parlak_cizgi(fr, pts, col, w, glow=14, dash=None, a=1.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if dash:
            L = math.dist(p, q); n = max(1, int(L / dash))
            for j in range(0, n, 2):
                u0, u1 = j / n, min(1, (j + 1) / n)
                d.line([(p[0] + (q[0] - p[0]) * u0, p[1] + (q[1] - p[1]) * u0), (p[0] + (q[0] - p[0]) * u1, p[1] + (q[1] - p[1]) * u1)], fill=col + (255,), width=w)
        else: d.line([p, q], fill=col + (255,), width=w, joint="curve")
    if a < 1: lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
    fr.alpha_composite(lay.filter(ImageFilter.GaussianBlur(glow))); fr.alpha_composite(lay)


def kismi(pts, p):
    """çizginin baştan p (0..1) kadarlık kısmı"""
    if p >= 1: return pts
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; want = sum(seg) * clamp(p); acc = 0; out = [pts[0]]
    for i, sl in enumerate(seg):
        if acc + sl <= want: out.append(pts[i + 1]); acc += sl
        else:
            k = (want - acc) / sl if sl else 0; out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k)); break
    return out


def nokta(fr, x, y, col, a=1.0, r=11, pulse=0.0):
    g = Image.new("RGBA", (140, 140), (0, 0, 0, 0)); rr = 30 * (1 + pulse)
    ImageDraw.Draw(g).ellipse([70 - rr, 70 - rr, 70 + rr, 70 + rr], fill=col + (120,)); g = g.filter(ImageFilter.GaussianBlur(9))
    ImageDraw.Draw(g).ellipse([70 - r, 70 - r, 70 + r, 70 + r], fill=(255, 240, 225, 255), outline=col + (255,), width=4)
    put(fr, g, x, y, a)


def etiket(fr, s, x, y, a=1.0, size=34, col=WHITE):
    put(fr, text(s, "sans9", size, col, spacing=2), x, y, a)


def baslik(fr, ust, alt, lt, out=1.0):
    if ust: put(fr, text(ust, "serif", 62 if len(ust) < 22 else 50, GOLD, glow=GOLD, spacing=4), W / 2, 300, clamp(lt / .5) * out)
    if alt: put(fr, text(alt, "sans9", 32, WHITE, spacing=6), W / 2, 385, clamp((lt - .3) / .5) * out)


class DepremAnim:
    def __init__(self, proje_dir, cfg):
        self.c = cfg; self.h = Harita(cfg.get("stil", "uydu")); self._ilce = None

    def frame(self, lt, dur):
        fr = getattr(self, "_" + self.c["tur"])(lt, dur)
        if self.h.uydu and self.c["tur"] != "ilce_tablo":
            put(fr, text(Harita.ATIF, "sans", 20, (230, 230, 230), spacing=1, shadow=True), W / 2, 1868, .75)
        return fr

    # ── 1999: merkezden yayılan halkalar ──
    def _halka(self, lt, dur):
        c = self.c; cam0, cam1 = c.get("cam", [[30.1, 40.35, 5.0], [30.0, 40.45, 4.6]])
        p = inout(lt / max(dur, 1)); cam = [cam0[j] + (cam1[j] - cam0[j]) * p for j in range(3)]
        fr, to, s = self.h.kare(cam); ex, ey = to(*c["merkez"])
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        hiz = 420  # piksel/sn
        for k in range(8):
            r = (lt - 0.35 - k * 0.5) * hiz
            if r <= 0: continue
            a = clamp(1 - r / 1400) * 230
            if a <= 2: continue
            d.ellipse([ex - r, ey - r, ex + r, ey + r], outline=KIRMIZI + (int(a),), width=6)
        fr.alpha_composite(lay.filter(ImageFilter.GaussianBlur(8))); fr.alpha_composite(lay)
        r0 = max(0, (lt - 0.35) * hiz)
        for ad, ll in c.get("sehirler", {}).items():
            x, y = to(ll[0], ll[1]); dist = math.dist((x, y), (ex, ey))
            if r0 < dist: continue
            q = (r0 - dist) / hiz; a = clamp(q / .25)
            nokta(fr, x, y, KIRMIZI, a, r=9, pulse=0.3 * (1 - clamp(q / .6)))
            yon = ll[2] if len(ll) > 2 else ("r" if x < W - 230 else "l")  # etiket yönü: r, l, u, d
            im = text(ad.upper(), "sans9", 30, WHITE, spacing=2)
            ox, oy = {"r": (im.width / 2 - 20, 0), "l": (-im.width / 2 + 20, 0), "u": (0, -44), "d": (0, 44)}[yon]
            put(fr, im, x + ox, y + oy - 2, a)
        # merkez rozeti
        a = clamp((lt - .1) / .25); sc = 1 + .5 * (1 - ease((lt - .1) / .35))
        g = Image.new("RGBA", (260, 260), (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
        dg.ellipse([50, 50, 210, 210], fill=KIRMIZI + (150,)); g = g.filter(ImageFilter.GaussianBlur(18))
        ImageDraw.Draw(g).ellipse([82, 82, 178, 178], fill=(150, 28, 24, 255), outline=(255, 210, 200, 255), width=5)
        put(fr, g, ex, ey, a, sc); put(fr, text(c.get("buyukluk", ""), "sans9", 46, WHITE, spacing=0, shadow=False), ex, ey - 4, a, sc)
        baslik(fr, c.get("ust"), c.get("alt"), lt, clamp((dur - lt) / .35))
        if c.get("sayac"):
            v, birim = c["sayac"]; q = lt - dur * .45
            if q > 0:
                n = int(round(v * ease(q / 1.0))); a = clamp(q / .3) * clamp((dur - lt) / .35)
                y0 = c.get("sayac_y", 520)
                put(fr, text(f"{n} {birim.split()[0]}", "serif", 92, (255, 232, 220), glow=KIRMIZI, spacing=4), W / 2, y0, a)
                put(fr, text(" ".join(birim.split()[1:]), "sans9", 30, WHITE, spacing=6), W / 2, y0 + 82, a)
        return fr

    # ── fay: kırılan ve kırılmayan parça ──
    def _fay(self, lt, dur):
        c = self.c; cam0, cam1 = c.get("cam", [[30.0, 40.45, 4.6], [28.95, 40.85, 3.3]])
        p = inout(lt / max(dur * .45, 1)); cam = [cam0[j] + (cam1[j] - cam0[j]) * p for j in range(3)]
        fr, to, s = self.h.kare(cam)
        A = [to(*q) for q in c["kirik"]]; B = [to(*q) for q in c["kirilmamis"]]
        pa = ease((lt - .2) / 1.0)
        if pa > 0: parlak_cizgi(fr, kismi(A, pa), KIRMIZI, 9, glow=16)
        pb = ease((lt - 1.2) / 1.1)
        if pb > 0:
            nab = .55 + .45 * (0.5 + 0.5 * math.sin(lt * 6)) if pb >= 1 else 1
            parlak_cizgi(fr, kismi(B, pb), AMBER, 9, glow=18, dash=26, a=nab)
        for ad, ll in c.get("sehirler", {}).items():
            x, y = to(*ll); nokta(fr, x, y, GOLD, clamp(lt / .4), r=10); etiket(fr, ad.upper(), x, y - 46, clamp(lt / .4), 34)
        if c.get("kirik_yazi") and pa > .6:
            x, y = A[len(A) // 2]; etiket(fr, c["kirik_yazi"], x, y + 64, clamp((lt - .9) / .4), 30, (255, 170, 160))
        if c.get("kirilmamis_yazi") and pb > .6:
            x, y = B[len(B) // 2]; etiket(fr, c["kirilmamis_yazi"], x, y + 70, clamp((lt - 2.0) / .4), 32, AMBER)
        baslik(fr, c.get("ust"), c.get("alt"), lt, clamp((dur - lt) / .35))
        return fr

    # ── İstanbul ilçeleri ──
    def _ilce_veri(self):
        if self._ilce is None:
            g = json.load(open(os.path.join(MAPDIR, "istanbul_ilceler.json"), encoding="utf-8")); out = []
            for f in g["features"]:
                geom = f["geometry"]; polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
                ring = max((p[0] for p in polys), key=len); cx = sum(x for x, y in ring) / len(ring); cy = sum(y for x, y in ring) / len(ring)
                out.append((f["properties"]["name"], polys, (cx, cy)))
            self._ilce = out
        return self._ilce

    def _ilce_harita(self, lt, dur):
        c = self.c; oran = c["oran"]; cam0, cam1 = c.get("cam", [[28.95, 40.9, 3.3], [28.95, 41.15, 2.2]])
        p = inout(lt / 1.4); cam = [cam0[j] + (cam1[j] - cam0[j]) * p for j in range(3)]
        fr, to, s = self.h.kare(cam); vs = sorted(oran.values()); lo, hi = vs[0], vs[-1]
        sira = sorted(oran, key=lambda k: oran[k])  # boyama sırası: az riskliden çok riskliye
        fill = Image.new("RGBA", (W, H), (0, 0, 0, 0)); df = ImageDraw.Draw(fill)
        edge = Image.new("RGBA", (W, H), (0, 0, 0, 0)); de = ImageDraw.Draw(edge)
        for ad, polys, _ in self._ilce_veri():
            v = oran.get(ad)
            k = sira.index(ad) if ad in sira else 0; q = clamp((lt - 1.2 - k * 0.035) / 0.35)
            for poly in polys:
                pts = [to(x, y) for x, y in poly[0]]
                if v is not None and q > 0: df.polygon(pts, fill=renk((v - lo) / (hi - lo)) + (int((150 if self.h.uydu else 205) * q),))
                de.line(pts + [pts[0]], fill=(255, 236, 200, int(170 * clamp((lt - .5) / .6))), width=2)
        fr.alpha_composite(fill); fr.alpha_composite(edge)
        n = c.get("rozet", 5); ilce = {a: m for a, _, m in self._ilce_veri()}
        uc = [(a, True) for a in sorted(oran, key=lambda k: -oran[k])[:n]] + [(a, False) for a in sorted(oran, key=lambda k: oran[k])[:n]]
        for j, (ad, risk) in enumerate(uc):
            q = lt - 2.8 - j * 0.12
            if q <= 0 or ad not in ilce: continue
            x, y = to(*c.get("konum", {}).get(ad, ilce[ad])); a = clamp(q / .25); col = KIRMIZI if risk else YESIL
            g = Image.new("RGBA", (70, 70), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([8, 8, 62, 62], fill=col + (255,), outline=(255, 255, 255, 255), width=4)
            put(fr, g, x, y, a, 1 + .4 * (1 - ease(q / .3)))
            put(fr, text(str(j % n + 1), "sans9", 28, WHITE, shadow=False), x, y - 2, a)
        # ölçek
        a = clamp((lt - 1.5) / .5)
        if a > 0:
            bar = Image.new("RGBA", (620, 120), (0, 0, 0, 0)); db = ImageDraw.Draw(bar)
            for xx in range(560): db.line([(30 + xx, 40), (30 + xx, 64)], fill=renk(xx / 559) + (255,))
            db.text((30, 76), f"%{yuzde(lo)}", font=F("sans9", 26), fill=WHITE); db.text((590, 76), f"%{yuzde(hi)}", font=F("sans9", 26), fill=WHITE, anchor="ra")
            put(fr, bar, W / 2, 1290, a)
        baslik(fr, c.get("ust"), c.get("alt"), lt, clamp((dur - lt) / .35))
        return fr

    def _ilce_tablo(self, lt, dur):
        c = self.c; oran = c["oran"]; n = c.get("n", 5)
        fr = self._ilce_harita(99, 100) if c.get("arka_harita", True) else Image.new("RGBA", (W, H), (10, 16, 26, 255))
        fr = fr.filter(ImageFilter.GaussianBlur(10)); fr.alpha_composite(Image.new("RGBA", (W, H), (6, 10, 18, 190)))
        top = sorted(oran, key=lambda k: -oran[k])[:n]; bot = sorted(oran, key=lambda k: oran[k])[:n]; mx = max(oran.values())
        out = clamp((dur - lt) / .35)
        def blok(y0, baslik_, liste, col, t0):
            a = clamp((lt - t0) / .4) * out
            put(fr, text(baslik_, "sans9", 44, col, glow=col, spacing=6), W / 2, y0, a)
            for j, ad in enumerate(liste):
                q = lt - t0 - .25 - j * .16; y = y0 + 88 + j * 84
                if q <= 0: continue
                a = clamp(q / .3) * out; v = oran[ad]; pb = ease(q / .9)
                row = Image.new("RGBA", (W - 100, 76), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
                d.rounded_rectangle([0, 0, W - 101, 75], 16, fill=(255, 255, 255, 18), outline=col + (90,), width=2)
                d.text((34, 38), str(j + 1), font=F("sans9", 34), fill=col + (255,), anchor="mm")
                d.text((70, 38), ad.upper(), font=F("sans9", 34), fill=(255, 255, 255, 255), anchor="lm")
                bx0, bx1 = 430, 790; d.rounded_rectangle([bx0, 28, bx1, 48], 10, fill=(255, 255, 255, 30))
                d.rounded_rectangle([bx0, 28, bx0 + max(20, (bx1 - bx0) * v / mx * pb), 48], 10, fill=col + (255,))
                d.text((W - 125, 38), f"%{yuzde(v * pb)}", font=F("sans9", 36), fill=(255, 255, 255, 255), anchor="rm")
                put(fr, row, W / 2, y, a)
        blok(c.get("y1", 360), c.get("ust_baslik", f"EN RİSKLİ {n} İLÇE"), top, KIRMIZI, .1)
        blok(c.get("y2", 880), c.get("alt_baslik", f"EN AZ RİSKLİ {n} İLÇE"), bot, YESIL, .9)
        if c.get("not"): put(fr, text(c["not"], "sans", 26, (220, 220, 220), spacing=1), W / 2, c.get("y2", 880) + 88 + n * 84 + 10, clamp((lt - 1.6) / .5) * out)
        return fr
