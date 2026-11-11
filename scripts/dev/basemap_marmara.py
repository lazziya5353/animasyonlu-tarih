"""Marmara altlığı (bir kez çalıştırılır): global-land-mask (~1 km) ile kıyıları ayrıntılı, motorun harita tarzında.
pip install global-land-mask  →  python scripts/dev/basemap_marmara.py"""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from global_land_mask import globe
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "engine"))
from core import GOLD
MAPDIR = os.path.join(os.path.dirname(__file__), "..", "..", "engine", "map")
R = json.load(open(os.path.join(MAPDIR, "regions.json")))["marmara"]
C = math.cos(math.radians(R["clat"]))
WM, HM = int((R["lon1"] - R["lon0"]) * R["k"] * C), int((R["lat1"] - R["lat0"]) * R["k"])
lon = R["lon0"] + (np.arange(WM) + .5) / (R["k"] * C); lat = R["lat1"] - (np.arange(HM) + .5) / R["k"]
LO, LA = np.meshgrid(lon, lat)
m = globe.is_land(LA, LO).astype(np.uint8) * 255
land = Image.fromarray(m).filter(ImageFilter.GaussianBlur(2.2)).point(lambda v: 255 if v > 127 else 0)
rng = np.random.default_rng(1)
def noise(sc):
    n = rng.random((HM // sc + 2, WM // sc + 2)); return np.array(Image.fromarray((n * 255).astype(np.uint8)).resize((WM, HM), Image.BICUBIC)) / 255.
tex = 0.55 * noise(60) + 0.3 * noise(18) + 0.15 * noise(5); L = np.array(land) / 255.
img = np.stack([10 + 8 * tex, 16 + 9 * tex, 26 + 12 * tex], -1) * (1 - L[..., None]) + np.stack([62 + 34 * tex, 48 + 26 * tex, 32 + 16 * tex], -1) * L[..., None]
im = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
edge = land.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
gl = Image.new("RGBA", im.size, GOLD + (0,)); gl.putalpha(edge.filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * .45))); im.alpha_composite(gl)
ln = Image.new("RGBA", im.size, (214, 178, 110, 0)); ln.putalpha(edge.point(lambda v: int(v * .75))); im.alpha_composite(ln)
im.convert("RGB").save(os.path.join(MAPDIR, "basemap_marmara.jpg"), quality=88); print(WM, HM)
