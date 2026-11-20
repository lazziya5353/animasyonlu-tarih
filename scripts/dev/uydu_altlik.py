"""Uydu altlıkları (bir kez çalışır, GitHub Actions'ta):
  - Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) → engine/map/uydu_marmara.jpg, uydu_istanbul.jpg
  - NASA Black Marble gece ışıkları (kamu malı)    → engine/map/gece_marmara.jpg
Atıf: "Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016 & 2017)"
"""
import io, os, re, sys, time, json, math, urllib.request
from PIL import Image

MAPDIR = os.path.join(os.path.dirname(__file__), "..", "..", "engine", "map")
UA = {"User-Agent": "animasyonlu-tarih/1.0 (github.com/lazziya5353/animasyonlu-tarih)"}
EOX = "https://tiles.maps.eox.at/wms"
GIBS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
BOLGE = {  # ad: (lon0, lon1, lat0, lat1, k = derece başına piksel (enlem))
    "marmara": (26.0, 33.0, 37.0, 44.2, 520),
    "istanbul": (27.8, 30.0, 40.55, 41.75, 2000),
    "dunya": (-20.0, 140.0, -5.0, 60.0, 16),
    "anadolu": (25.0, 46.0, 34.0, 43.5, 140),
    "adiyaman": (37.6, 39.6, 37.4, 38.6, 1400),
    "misir": (24.0, 37.0, 21.0, 33.0, 150),
    "giza": (31.05, 31.25, 29.93, 30.05, 12000),
    "cin": (73.0, 125.0, 22.0, 48.0, 45),
    "orta": (10.0, 62.0, 18.0, 52.0, 45),
    "dogu_anadolu": (34.0, 44.0, 35.5, 40.5, 450),
    "kahire": (30.4, 32.0, 29.4, 30.6, 1300),
    "kuzey_cin": (95.0, 122.0, 34.0, 43.0, 160),
    "mezopotamya": (35.0, 49.5, 29.0, 41.5, 150),
    "istanbul_bogaz": (28.93, 29.25, 40.98, 41.26, 8000),
}
BLUE_MARBLE = {"dunya", "orta", "cin", "kuzey_cin", "misir", "mezopotamya"}  # geniş açılar: NASA Blue Marble (kamu malı, kabartmalı, tek parça)
SADECE = [a for a in os.environ.get("BOLGELER", "").split(",") if a]


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r: return r.read()
        except Exception as e:
            print("tekrar:", e); time.sleep(3 + 4 * i)
    raise SystemExit(f"indirilemedi: {url}")


def eox_katman():
    cap = get(EOX + "?service=WMS&request=GetCapabilities&version=1.1.1").decode("utf-8", "replace")
    katmanlar = re.findall(r"<Layer[^>]*>\s*<Name>([^<]+)</Name>\s*<Title>([^<]+)</Title>", cap)
    print("EOX katmanları:"); [print("  ", n, "|", t) for n, t in katmanlar]
    for n, t in katmanlar:
        if "s2cloudless" in n and "2016" in (n + t) and "3857" not in n: return n, t
    names = [n for n, _ in katmanlar]
    if "s2cloudless" in names and any(re.match(r"s2cloudless-20\d\d", n) for n in names): return "s2cloudless", dict(katmanlar)["s2cloudless"]
    raise SystemExit("2016 katmanı bulunamadı; lisans gereği başka yılı kullanmıyoruz")


def wms(base, layer, lon0, lon1, lat0, lat1, Wp, Hp, fmt, extra="", v130=False, blok=2048):
    out = Image.new("RGB", (Wp, Hp))
    for y in range(0, Hp, blok):
        for x in range(0, Wp, blok):
            w, h = min(blok, Wp - x), min(blok, Hp - y)
            a0 = lon0 + (lon1 - lon0) * x / Wp; a1 = lon0 + (lon1 - lon0) * (x + w) / Wp
            b1 = lat1 - (lat1 - lat0) * y / Hp; b0 = lat1 - (lat1 - lat0) * (y + h) / Hp
            if v130: q = f"SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0&LAYERS={layer}&STYLES=&CRS=EPSG:4326&BBOX={b0},{a0},{b1},{a1}&WIDTH={w}&HEIGHT={h}&FORMAT={fmt}{extra}"
            else: q = f"service=WMS&request=GetMap&version=1.1.1&layers={layer}&styles=&srs=EPSG:4326&bbox={a0},{b0},{a1},{b1}&width={w}&height={h}&format={fmt}{extra}"
            data = get(base + "?" + q)
            try: im = Image.open(io.BytesIO(data)).convert("RGB")
            except Exception: raise SystemExit("görüntü değil: " + data[:300].decode("utf-8", "replace"))
            out.paste(im, (x, y)); print(layer, x, y, w, h); time.sleep(0.5)
    return out


def main():
    lay, title = eox_katman(); print("SEÇİLEN:", lay, "|", title)
    for ad, (lon0, lon1, lat0, lat1, k) in BOLGE.items():
        if SADECE and ad not in SADECE: continue
        C = math.cos(math.radians((lat0 + lat1) / 2)); Wp, Hp = int((lon1 - lon0) * k * C), int((lat1 - lat0) * k)
        if ad in BLUE_MARBLE:
            im = None
            for gl in ("BlueMarble_ShadedRelief_Bathymetry", "BlueMarble_NextGeneration", "BlueMarble_ShadedRelief"):
                try: im = wms(GIBS, gl, lon0, lon1, lat0, lat1, Wp, Hp, "image/jpeg", v130=True); print("blue marble:", gl); break
                except SystemExit as e: print("olmadı:", gl, e)
            if im is None: im = wms(EOX, lay, lon0, lon1, lat0, lat1, Wp, Hp, "image/jpeg")
        else: im = wms(EOX, lay, lon0, lon1, lat0, lat1, Wp, Hp, "image/jpeg")
        im.save(os.path.join(MAPDIR, f"uydu_{ad}.jpg"), quality=90); print("kaydedildi", ad, im.size)
    if SADECE: return _json(lay, title)
    lon0, lon1, lat0, lat1, k = BOLGE["marmara"]; C = math.cos(math.radians((lat0 + lat1) / 2))
    Wp, Hp = int((lon1 - lon0) * k * C), int((lat1 - lat0) * k)
    for gl in ("BlackMarble_2016", "VIIRS_Black_Marble"):
        try:
            g = wms(GIBS, gl, lon0, lon1, lat0, lat1, Wp, Hp, "image/jpeg", v130=True); g.save(os.path.join(MAPDIR, "gece_marmara.jpg"), quality=90); print("gece:", gl); break
        except SystemExit as e: print("gece katmanı olmadı:", gl, e)
    _json(lay, title)


def _json(lay, title):
    json.dump({"bolgeler": BOLGE, "eox_katman": lay, "eox_baslik": title, "atif": "Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016 & 2017)",
               "gece": "NASA Black Marble (kamu malı)"}, open(os.path.join(MAPDIR, "uydu.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
