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
GORSEL_TURLER = ("gorsel_zoom",)
KIRMIZI = (226, 64, 52); YESIL = (86, 190, 120); AMBER = (255, 176, 64)


def renk(t):
    """0 → yeşil, 0.5 → sarı, 1 → kırmızı"""
    t = clamp(t); a = [(70, 170, 100), (232, 196, 80), (214, 52, 44)]
    if t < .5: u = t / .5; p, q = a[0], a[1]
    else: u = (t - .5) / .5; p, q = a[1], a[2]
    return tuple(int(p[i] + (q[i] - p[i]) * u) for i in range(3))


def tr_upper(s): return s.replace("i", "İ").replace("ı", "I").upper()


def yuzde(v): return f"{v:.1f}".replace(".", ",")


class Harita:
    """Altlık: varsa uydu (Sentinel-2 cloudless 2016 + yakın plan için yüksek çözünürlüklü İstanbul), yoksa çizim altlık."""
    _cache = {}
    ATIF = "Uydu: NASA Blue Marble · Sentinel-2 cloudless 2016 (EOX, CC BY 4.0)"

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


def etiket_kenarli(fr, s, x, y, a=1.0, size=34, col=WHITE):
    """koyu kenarlı + koyu parıltılı etiket: uydu altlığı üstünde her zaman okunur; ekran içinde tutulur"""
    f = F("sans9", size); tw = int(f.getlength(s) + 3 * len(s)) + 60; th = int(size * 1.6) + 40
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(im); xx = 30
    for ch in s: d.text((xx, 20), ch, font=f, fill=col + (255,), stroke_width=max(3, size // 9), stroke_fill=(10, 8, 6, 255)); xx += f.getlength(ch) + 3
    g = Image.new("RGBA", im.size, (0, 0, 0, 0)); g.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .9)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(im)
    x = min(max(x, tw / 2 + 20), W - tw / 2 - 20)
    put(fr, out, x, y, a)


def baslik(fr, ust, alt, lt, out=1.0):
    if ust: put(fr, text(ust, "serif", 62 if len(ust) < 22 else 50, GOLD, glow=GOLD, spacing=4), W / 2, 300, clamp(lt / .5) * out)
    if alt: put(fr, text(alt, "sans9", 32, WHITE, spacing=6), W / 2, 385, clamp((lt - .3) / .5) * out)


class DepremAnim:
    def __init__(self, proje_dir, cfg):
        self.c = cfg; self.dir = proje_dir; self._ilce = None
        self.h = None if cfg["tur"] in GORSEL_TURLER else Harita(cfg.get("stil", "uydu"))

    def frame(self, lt, dur):
        fr = getattr(self, "_" + self.c["tur"])(lt, dur)
        if self.h and self.h.uydu and self.c["tur"] != "ilce_tablo":
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
            im = text(tr_upper(ad), "sans9", 30, WHITE, spacing=2)
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
            x, y = to(*ll); nokta(fr, x, y, GOLD, clamp(lt / .4), r=10); etiket(fr, tr_upper(ad), x, y - 46, clamp(lt / .4), 34)
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
                d.text((70, 38), tr_upper(ad), font=F("sans9", 34), fill=(255, 255, 255, 255), anchor="lm")
                bx0, bx1 = 430, 790; d.rounded_rectangle([bx0, 28, bx1, 48], 10, fill=(255, 255, 255, 30))
                d.rounded_rectangle([bx0, 28, bx0 + max(20, (bx1 - bx0) * v / mx * pb), 48], 10, fill=col + (255,))
                d.text((W - 125, 38), f"%{yuzde(v * pb)}", font=F("sans9", 36), fill=(255, 255, 255, 255), anchor="rm")
                put(fr, row, W / 2, y, a)
        blok(c.get("y1", 360), c.get("ust_baslik", f"EN RİSKLİ {n} İLÇE"), top, KIRMIZI, .1)
        blok(c.get("y2", 880), c.get("alt_baslik", f"EN AZ RİSKLİ {n} İLÇE"), bot, YESIL, .9)
        if c.get("not"): put(fr, text(c["not"], "sans", 26, (220, 220, 220), spacing=1), W / 2, c.get("y2", 880) + 88 + n * 84 + 10, clamp((lt - 1.6) / .5) * out)
        return fr


# ── uydudan yakınlaşma: geniş görünümden hedefe iner, istenirse bir çizgi (ör. Çin Seddi) çizer ──
def _zoom(self, lt, dur):
    c = self.c; a0, a1 = c["from"], c["to"]; zs = c.get("zoom_sure", min(dur * .7, 5.0))
    u = inout(clamp(lt / max(.1, zs)))
    lon = a0[0] + (a1[0] - a0[0]) * u; lat = a0[1] + (a1[1] - a0[1]) * u
    w = math.exp(math.log(a0[2]) + (math.log(a1[2]) - math.log(a0[2])) * u)
    fr, to, s = self.h.kare((lon, lat, w * (1 - .03 * clamp((lt - zs) / max(.1, dur - zs)))))
    for ad, lo, la in c.get("etiketler", []):
        x, y = to(lo, la); etiket(fr, ad, x, y - 46, clamp((u - .2) / .3) * clamp((.92 - u) / .15 + (1 if not c.get("etiket_sonra_gizle") else 0)), size=30)
    if c.get("cizgi"):
        p = ease((lt - zs) / max(.1, c.get("cizgi_sure", 2.5)))
        pts = [to(lo, la) for lo, la in c["cizgi"]]
        if p > 0:
            q = clamp((lt - zs) / .6)                                      # çizgi başlarken harita kararsın, çizgi öne çıksın
            if q > 0: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(110 * q))))
            kp = kismi(pts, p); kal = c.get("cizgi_kalinlik", 7); renk_ = tuple(c.get("cizgi_renk", (255, 170, 60)))
            parlak_cizgi(fr, kp, renk_, kal + 6, glow=22); parlak_cizgi(fr, kp, (255, 245, 225), max(3, kal // 3), glow=4)
            if p < 1: nokta(fr, kp[-1][0], kp[-1][1], renk_, 1.0, r=12, pulse=.5)
            if c.get("cizgi_ad") and p > .35:
                m = pts[len(pts) // 2]; put(fr, text(c["cizgi_ad"], "serif", 64, (255, 235, 200), glow=renk_, spacing=6), m[0], m[1] + 110, clamp((p - .35) / .3))
        for ad, lo, la, kaydir in c.get("cizgi_etiketler", []):
            x, y = to(lo, la); etiket(fr, ad, x, y + kaydir, clamp((lt - zs - .3) / .5), size=30, col=GOLD)
    if c.get("cizgiler"):                                                  # birden çok akan çizgi (ör. iki nehir birleşiyor)
        q = clamp((lt - zs) / .6)
        if q > 0: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(90 * q))))
        for cz in c["cizgiler"]:
            p = ease((lt - zs - cz.get("gecikme", 0)) / max(.1, cz.get("sure", 3.0)))
            if p <= 0: continue
            pts = [to(lo, la) for lo, la in cz["pts"]]; kp = kismi(pts, p); renk_ = tuple(cz.get("renk", (80, 170, 255))); kal = cz.get("kalinlik", 9)
            parlak_cizgi(fr, kp, renk_, kal + 6, glow=22); parlak_cizgi(fr, kp, (235, 248, 255), max(3, kal // 3), glow=4)
            if p < 1: nokta(fr, kp[-1][0], kp[-1][1], renk_, 1.0, r=12, pulse=.5)
            if cz.get("ad") and p > .3:
                lo, la = cz.get("ad_yer", cz["pts"][len(pts) // 2]); x, y = to(lo, la)
                put(fr, text(cz["ad"], "serif", 54, (255, 255, 255), glow=renk_, spacing=5), x, y, clamp((p - .3) / .3))
    if c.get("pinler"):                                                    # sırayla yanan raptiyeler, koyu kenarlı okunur etiketlerle
        for pn in c["pinler"]:
            q = clamp((lt - pn.get("t", 0)) / .35)
            if q <= 0: continue
            x, y = to(pn["lon"], pn["lat"]); col = tuple(pn.get("renk", GOLD))
            if pn.get("alan"):                                           # semt alanı: yarı saydam, kenarı parlayan bölge (nokta bu alanın içinde)
                alo, ala, km = pn["alan"]; ax, ay = to(alo, ala)
                rx = abs(to(alo + km / (111.32 * math.cos(math.radians(ala))), ala)[0] - ax); ry = abs(to(alo, ala + km / 110.57)[1] - ay)
                ka = Image.new("RGBA", fr.size, (0, 0, 0, 0)); kd = ImageDraw.Draw(ka)
                kd.ellipse([ax - rx, ay - ry, ax + rx, ay + ry], fill=col + (int(42 * q),), outline=col + (int(235 * q),), width=6)
                ka = Image.alpha_composite(ka.filter(ImageFilter.GaussianBlur(3)), ka) if q > 0 else ka
                fr.alpha_composite(ka)
            nokta(fr, x, y, col, q, r=pn.get("r", 11), pulse=.2 * math.sin(lt * 4 + x) + .2)
            if pn.get("ad"): etiket_kenarli(fr, pn["ad"], x + pn.get("dx", 0), y + pn.get("dy", -60), q, size=pn.get("boyut", 34), col=tuple(pn.get("yazi_renk", WHITE)))
            if pn.get("ad2"): etiket_kenarli(fr, pn["ad2"], x + pn.get("dx", 0), y + pn.get("dy", -60) + pn.get("boyut", 34) * 1.15, q, size=pn.get("boyut2", 40), col=tuple(pn.get("yazi_renk2", GOLD)))
    if c.get("hedef"):
        lo, la, ad = c["hedef"]; x, y = to(lo, la); q = clamp((lt - zs * .85) / .4)
        if q > 0:
            nokta(fr, x, y, GOLD, q, pulse=.25 * math.sin(lt * 4) + .25)
            etiket(fr, ad, x, y - 70, q, size=40, col=WHITE)
    return fr


DepremAnim._zoom = _zoom


# ── yazıt kartı: taş dokulu arka plan, başlık, metin satır satır daktiloyla yazılır (izleyici durdurup okusun) ──
def _yazit(self, lt, dur):
    c = self.c
    if not hasattr(self, "_taş"):
        rng = np.random.default_rng(7); n = rng.random((H // 4, W // 4)).astype(np.float32)
        im = Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(3))
        a = np.asarray(im).astype(np.float32) / 255.; yy = np.linspace(-1, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
        vig = np.clip(1 - .55 * (xx ** 2 + yy ** 2), 0, 1); v = (.10 + .10 * a) * vig
        rgb = np.stack([v * 1.25, v * 1.08, v * .85], -1)
        self._taş = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    fr = self._taş.copy(); out = clamp((dur - lt) / .4)
    put(fr, text(c.get("baslik", "YAZIT"), "sans9", 34, GOLD, spacing=10), W / 2, 520, clamp(lt / .4) * out)
    satirlar = c["satirlar"]; toplam = sum(len(s) for s in satirlar); hiz = toplam / max(1., c.get("yazma_sure", dur * .75))
    kalan = int(max(0, lt - .5) * hiz); y = 640
    for s in satirlar:
        g = s[:max(0, kalan)]; kalan -= len(s)
        if g: put(fr, text(g, "serif", c.get("boyut", 50), (240, 226, 196), glow=(120, 90, 40), spacing=1), W / 2, y, out)
        y += int(c.get("boyut", 50) * 1.45)
    if c.get("imza") and kalan > 0: put(fr, text(c["imza"], "sans9", 28, (210, 190, 150), spacing=4), W / 2, y + 40, clamp(kalan / 20) * out)
    return fr


DepremAnim._yazit = _yazit


# ── görselde yakınlaşma: tek bir büyük görsel (ör. arma) üzerinde kamera gezer, sembolleri vurgular ──
#   {"tur": "gorsel_zoom", "gorsel": "engine/map/arma.png",
#    "kamera": [[t, cx, cy, w], ...]   t: sahne süresinin oranı (0-1), cx/cy: görselde 0-1 konum, w: ekrana sığan görsel genişliği oranı
#    "vurgu":  [[t0, t1, cx, cy, r, "AD"], ...]  t0/t1 oran, r: görsel genişliğine oranla yarıçap; etrafı kararır, altın halka + etiket
#    "atif": "..."}  (alt satırda küçük atıf)
class Gorsel:
    _cache = {}

    def __init__(self, yol):
        if yol not in Gorsel._cache:
            Image.MAX_IMAGE_PIXELS = None
            im = Image.open(yol).convert("RGBA"); bg = Image.new("RGBA", im.size, (0, 0, 0, 255)); bg.alpha_composite(im)
            lv = [bg.convert("RGB")]
            while lv[-1].width > 1400: lv.append(lv[-1].resize((lv[-1].width // 2, lv[-1].height // 2), Image.LANCZOS))
            Gorsel._cache[yol] = lv
        self.lv = Gorsel._cache[yol]; self.W0, self.H0 = self.lv[0].size

    def kare(self, cx, cy, w):
        """cx, cy (0-1), w: görünen genişlik (görsel genişliği oranı) → kare ve görsel(0-1)→ekran dönüşümü"""
        bw = w * self.W0; bh = bw * H / W; x0 = cx * self.W0 - bw / 2; y0 = cy * self.H0 - bh / 2
        s = W / bw; k = 0
        while k + 1 < len(self.lv) and bw / 2 ** (k + 1) >= W * 1.0: k += 1   # kaynak/ekran ≤ 2 olacak seviye
        im = self.lv[k]; f = self.W0 / im.width
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        ix0, iy0, ix1, iy1 = max(0, x0), max(0, y0), min(self.W0, x0 + bw), min(self.H0, y0 + bh)
        if ix1 > ix0 and iy1 > iy0:
            dx0, dy0 = int(round((ix0 - x0) * s)), int(round((iy0 - y0) * s)); dx1, dy1 = int(round((ix1 - x0) * s)), int(round((iy1 - y0) * s))
            if dx1 > dx0 and dy1 > dy0:
                parca = im.resize((dx1 - dx0, dy1 - dy0), Image.BICUBIC if s * f > 1 else Image.BILINEAR, box=(ix0 / f, iy0 / f, ix1 / f, iy1 / f))
                fr.paste(parca, (dx0, dy0))
        def to(u, v): return ((u * self.W0 - x0) * s, (v * self.H0 - y0) * s)
        return fr, to, s * self.W0


def _kamera(kf, p):
    """anahtar kareler arasında yumuşak geçiş; genişlik logaritmik (yakınlaşma hızı sabit hissettirsin)"""
    kf = sorted(kf)
    if p <= kf[0][0]: return kf[0][1:]
    for a, b in zip(kf, kf[1:]):
        if p <= b[0]:
            u = inout((p - a[0]) / max(1e-6, b[0] - a[0]))
            return (a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u, math.exp(math.log(a[3]) + (math.log(b[3]) - math.log(a[3])) * u))
    return kf[-1][1:]


def _gorsel_zoom(self, lt, dur):
    c = self.c
    if not hasattr(self, "_g"):
        yol = c["gorsel"]
        if not os.path.isabs(yol):
            yol = next((y for y in (os.path.join(self.dir, yol), os.path.join(HERE, "..", yol), os.path.join(HERE, yol)) if os.path.exists(y)), yol)
        self._g = Gorsel(yol)
    p = clamp(lt / max(.1, dur)); cx, cy, w = _kamera(c.get("kamera", [[0, .5, .5, 1.0]]), p)
    fr, to, olc = self._g.kare(cx, cy, w)
    for t0, t1, vx, vy, r, ad in c.get("vurgu", []):
        q = clamp((p - t0) / .06) * clamp((t1 - p) / .06)
        if q <= 0: continue
        x, y = to(vx, vy); R = r * olc; ri = int(R)
        # spot: halkanın dışı kararır
        m = Image.new("L", (W // 4, H // 4), int(150 * q)); ImageDraw.Draw(m).ellipse([(x - R) / 4, (y - R) / 4, (x + R) / 4, (y + R) / 4], fill=0)
        m = m.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
        k = Image.new("RGBA", (W, H), (0, 0, 0, 0)); k.putalpha(m); fr.alpha_composite(k)
        # parlayan altın halka (çizilerek kapanır)
        ac = 360 * ease(clamp((p - t0) / .1)); puls = 1 + .015 * math.sin(lt * 4)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); RR = R * puls
        d.arc([x - RR, y - RR, x + RR, y + RR], -90, -90 + ac, fill=GOLD + (int(255 * q),), width=7)
        fr.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14))); fr.alpha_composite(lay)
        if ad:
            im = text(ad, "sans9", 44, WHITE, glow=GOLD, spacing=4)
            ly = y + R + 60 if y + R + 60 < H - 330 else y - R - 60
            ly = min(max(ly, 520), H - 330); lx = min(max(x, im.width / 2 + 10), W - im.width / 2 - 10)
            put(fr, im, lx, ly, clamp((p - t0 - .04) / .06) * q)
    if c.get("okunur"):                                                     # yazılar okunsun: üst ve altta koyu geçiş
        g = Image.new("L", (1, H), 0); px = g.load()
        for yy in range(H):
            a = 0
            if yy < 760: a = 185 * (1 - yy / 760) ** 1.3
            if yy > 1180: a = max(a, 215 * ((yy - 1180) / (H - 1180)) ** .9)
            px[0, yy] = int(a)
        k = Image.new("RGBA", (W, H), (0, 0, 0, 0)); k.putalpha(g.resize((W, H))); fr.alpha_composite(k)
    if c.get("atif", True):
        put(fr, text(c.get("atif") if isinstance(c.get("atif"), str) else "Arma: Wikimedia Commons (kamu malı)", "sans", 20, (230, 230, 230), spacing=1, shadow=True), W / 2, 1868, .7)
    return fr


DepremAnim._gorsel_zoom = _gorsel_zoom
