"""Eski kağıt dokulu harita: altlık üretimi ve animasyonlu harita karesi (şehirler + yol çizgisi)."""
import os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from core import W, H, GOLD, clamp, ease, text, put

HERE = os.path.dirname(os.path.abspath(__file__))
MAPDIR = os.path.join(HERE, "map")
REGIONS = json.load(open(os.path.join(MAPDIR, "regions.json")))
CITIES = json.load(open(os.path.join(MAPDIR, "cities.json")))

def build_basemap(region):
    """Natural Earth kara verisinden (land.json) bölge altlığı üretir: map/basemap_<region>.jpg"""
    R = REGIONS[region]; LON0, LON1, LAT0, LAT1, K = R["lon0"], R["lon1"], R["lat0"], R["lat1"], R["k"]; C = math.cos(math.radians(R["clat"]))
    WM, HM = int((LON1 - LON0) * K * C), int((LAT1 - LAT0) * K)
    P = lambda lon, lat: ((lon - LON0) * K * C, (LAT1 - lat) * K)
    g = json.load(open(os.path.join(MAPDIR, "land.json")))
    land = Image.new("L", (WM, HM), 0); d = ImageDraw.Draw(land)
    for f in g["features"]:
        geom = f["geometry"]; cs = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in cs:
            for ri, ring in enumerate(poly):
                if not any(LON0 - 5 < x < LON1 + 5 and LAT0 - 5 < y < LAT1 + 5 for x, y in ring): continue
                d.polygon([P(x, y) for x, y in ring], fill=255 if ri == 0 else 0)
    rng = np.random.default_rng(1)
    def noise(sc):
        n = rng.random((HM // sc + 2, WM // sc + 2)); return np.array(Image.fromarray((n * 255).astype(np.uint8)).resize((WM, HM), Image.BICUBIC)) / 255.
    tex = 0.55 * noise(40) + 0.3 * noise(12) + 0.15 * noise(4); L = np.array(land) / 255.
    img = np.stack([14 + 8 * tex, 20 + 8 * tex, 28 + 10 * tex], -1) * (1 - L[..., None]) + np.stack([78 + 40 * tex, 60 + 30 * tex, 38 + 18 * tex], -1) * L[..., None]
    im = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
    edge = land.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    gl = Image.new("RGBA", im.size, GOLD + (0,)); gl.putalpha(edge.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * .5))); im.alpha_composite(gl)
    ln = Image.new("RGBA", im.size, (214, 178, 110, 0)); ln.putalpha(edge.point(lambda v: int(v * .8))); im.alpha_composite(ln)
    gr = Image.new("RGBA", im.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(gr)
    for lon in range(int(LON0), int(LON1) + 1, 5): dg.line([P(lon, LAT0), P(lon, LAT1)], fill=GOLD + (28,), width=2)
    for lat in range(int(LAT0), int(LAT1) + 1, 5): dg.line([P(LON0, lat), P(LON1, lat)], fill=GOLD + (28,), width=2)
    im.alpha_composite(gr); out = os.path.join(MAPDIR, f"basemap_{region}.jpg"); im.convert("RGB").save(out, quality=92); return out

class MapRenderer:
    def __init__(self, region, extra_cities=None):
        self.R = REGIONS[region]; path = os.path.join(MAPDIR, f"basemap_{region}.jpg")
        if not os.path.exists(path): build_basemap(region)
        self.base = Image.open(path).convert("RGB")
        self.cities = dict(CITIES); self.cities.update(extra_cities or {})
        self.C = math.cos(math.radians(self.R["clat"]))
    def P(self, lon, lat): return ((lon - self.R["lon0"]) * self.R["k"] * self.C, (self.R["lat1"] - lat) * self.R["k"])
    def frame(self, cam, lt, dur, routes, cities, title, label_off):
        lon, lat, wdeg = cam; K = self.R["k"] * self.C
        cw = wdeg * K; ch = cw * H / W
        if ch > self.base.height: ch = self.base.height; cw = ch * W / H
        cx, cy = self.P(lon, lat)
        x0 = min(max(cx - cw / 2, 0), self.base.width - cw); y0 = min(max(cy - ch / 2, 0), self.base.height - ch)
        fr = self.base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA"); s = W / cw
        def to(p):
            if isinstance(p, str): p = self.cities[p]
            X, Y = self.P(*p); return ((X - x0) * s, (Y - y0) * s)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        pr = ease((lt - 0.25) / (dur * 0.55))
        for r in routes:
            pts = [to(p) for p in r]; seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
            want = sum(seg) * pr; acc = 0; drawn = [pts[0]]
            for i, sl in enumerate(seg):
                if acc + sl <= want: drawn.append(pts[i + 1]); acc += sl
                else:
                    k = (want - acc) / sl if sl else 0; drawn.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k)); break
            for i in range(len(drawn) - 1):
                a, b = drawn[i], drawn[i + 1]; L = math.dist(a, b); n = max(1, int(L / 22))
                for j in range(0, n, 2):
                    u0, u1 = j / n, min(1, (j + 1) / n)
                    d.line([(a[0] + (b[0] - a[0]) * u0, a[1] + (b[1] - a[1]) * u0), (a[0] + (b[0] - a[0]) * u1, a[1] + (b[1] - a[1]) * u1)], fill=GOLD + (255,), width=7)
            if 0 < pr < 1:
                hx, hy = drawn[-1]; d.ellipse([hx - 11, hy - 11, hx + 11, hy + 11], fill=(255, 240, 210, 255))
        fr.alpha_composite(lay.filter(ImageFilter.GaussianBlur(9))); fr.alpha_composite(lay)
        for i, c in enumerate(cities):
            x, y = to(c); a = clamp((lt - 0.1 - i * 0.35) / 0.3)
            if a <= 0: continue
            pulse = 1 + 0.25 * math.sin(lt * 5 + i)
            g = Image.new("RGBA", (120, 120), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([60 - 30 * pulse, 60 - 30 * pulse, 60 + 30 * pulse, 60 + 30 * pulse], fill=GOLD + (110,))
            g = g.filter(ImageFilter.GaussianBlur(8)); ImageDraw.Draw(g).ellipse([47, 47, 73, 73], fill=(255, 236, 196, 255), outline=(120, 80, 30, 255), width=3)
            put(fr, g, x, y, a)
            ox, oy = label_off.get(c, (0, -62)); lab = text(c.upper(), "serif", 46, (255, 240, 215), spacing=3)
            lx = min(max(x + ox, lab.width / 2 - 20), W - lab.width / 2 + 20)  # kenardan taşmasın
            put(fr, lab, lx, y + oy, a)
        if title: put(fr, text(title, "sans9", 40, GOLD, spacing=6), W / 2, 640, clamp((lt - 0.1) / 0.4))
        return fr
