"""Karşılaştırma tablosu sahnesi: hazır bir tablo görselinde (ör. Gemini'de üretilmiş) satırları sesle senkron yakar,
çubukları soldan doldurur, sayıları 0'dan saydırır, vurgulu satırlarda (ör. Galatasaray) parlama yapar.

project.json sahnesinde:
  "tablo": {
    "rows":  [[y0, y1], ...]            # satır kutuları (kaynak görsel pikseli)
    "bars":  [[by0, by1, bx1], ...]     # çubuk bandı ve dolu çubuğun bittiği x
    "values": [26, 19, ...],
    "vurgu": [0, 4],                     # parlayacak satırlar
    "sira":  [null, 3, 2, 1, 0, null, ...]  # sahnedeki her cümle hangi satırı yakar (null = başlık cümlesi)
    "bar_x0": 303, "num_x": [1150, 1316], "row_x": [110, 1330],
    "bos_iz": [y_merkez, x]             # boş çubuk izi örneği (dolmamış çubuk görünümü)
    "logo": {"img": "images/x.png", "ovaller": [[x0, y0, x1, y1], ...]}   # isteğe bağlı: hatalı logoyu değiştir
  }
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = os.path.join(os.path.dirname(__file__), "fonts", "Montserrat-900.ttf")


def _ease(x):
    x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3


class Tablo:
    def __init__(self, proje_dir, img, cfg, W=1080, H=1920):
        self.c = cfg; self.W, self.H = W, H
        im = Image.open(os.path.join(proje_dir, img)).convert("RGB")
        lg = cfg.get("logo")
        if lg:
            L0 = Image.open(os.path.join(proje_dir, lg["img"])).convert("RGB"); a = np.array(L0).astype(np.int16)
            # internetten alınan PNG'lerdeki "sahte şeffaflık" dama desenini (açık gri/beyaz kareler) düz beyaza çevir
            gri = (a.max(axis=2) - a.min(axis=2) < 24) & (a.min(axis=2) > 170); a[gri] = 255
            L0 = Image.fromarray(a.astype(np.uint8))
            ys, xs = np.where(a.min(axis=2) < 235); L0 = L0.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
            for x0, y0, x1, y1 in lg["ovaller"]:
                ImageDraw.Draw(im).ellipse((x0, y0, x1, y1), fill=(255, 255, 255))
                w, h = x1 - x0 - 18, y1 - y0 - 18; s = min(w / L0.width, h / L0.height)
                L = L0.resize((max(1, int(L0.width * s)), max(1, int(L0.height * s))), Image.LANCZOS)
                px, py = (x0 + x1) // 2 - L.width // 2, (y0 + y1) // 2 - L.height // 2
                m = Image.new("L", im.size, 0); ImageDraw.Draw(m).ellipse((x0 + 2, y0 + 2, x1 - 2, y1 - 2), fill=255)
                tmp = im.copy(); tmp.paste(L, (px, py)); im = Image.composite(tmp, im, m)
        self.sw, self.sh = im.size
        self.k = W / self.sw; self.oy = int((self.sh * self.k - H) / 2)  # genişliğe sığdır, dikeyde ortadan kırp
        full = np.array(im).astype(np.float32); emp = full.copy()
        bx0 = cfg.get("bar_x0", 303); nx0, nx1 = cfg.get("num_x", [1150, 1316])
        iy, ix = cfg.get("bos_iz", [923, 1118])
        for (by0, by1, bx1) in cfg["bars"]:
            c = (by0 + by1) // 2; hh = (by1 - by0) // 2 + 5
            col = full[iy - hh:iy + hh + 1, ix:ix + 1, :]
            emp[c - hh:c + hh + 1, bx0:ix + 6, :] = np.repeat(col, ix + 6 - bx0, axis=1)
        for (y0, y1) in cfg["rows"]:
            L = full[y0 + 4:y1 - 3, nx0:nx0 + 1, :]; R = full[y0 + 4:y1 - 3, nx1:nx1 + 1, :]
            t = np.linspace(0, 1, nx1 - nx0)[None, :, None]
            emp[y0 + 4:y1 - 3, nx0:nx1, :] = L * (1 - t) + R * t
        self.full, self.emp = full, emp
        self.font = ImageFont.truetype(FONT, 104); self._num = {}

    def _numimg(self, n, h):
        key = (n, h)
        if key in self._num: return self._num[key]
        txt = str(n); Wd = 400; d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bb = d0.textbbox((0, 0), txt, font=self.font); x = (Wd - (bb[2] - bb[0])) // 2 - bb[0]; y = (h - (bb[3] - bb[1])) // 2 - bb[1]
        sh = Image.new("RGBA", (Wd, h), (0, 0, 0, 0)); ImageDraw.Draw(sh).text((x + 3, y + 5), txt, font=self.font, fill=(0, 0, 0, 200))
        g = Image.new("RGBA", (Wd, h), (0, 0, 0, 0)); ImageDraw.Draw(g).text((x, y), txt, font=self.font, fill=(240, 222, 180, 255))
        out = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)), g).resize((int(Wd * 0.74), h), Image.LANCZOS)
        a = np.array(out).astype(np.float32) / 255; self._num[key] = a; return a

    def frame(self, lt, act):
        """lt: sahne içi zaman; act: her satırın yanma zamanı (sahne içi saniye)."""
        c = self.c; out = self.emp.copy(); rx0, rx1 = c.get("row_x", [110, 1330])
        bx0 = c.get("bar_x0", 303); nx0, nx1 = c.get("num_x", [1150, 1316]); vurgu = set(c.get("vurgu", []))
        for i, (y0, y1) in enumerate(c["rows"]):
            ta = act[i] if i < len(act) and act[i] is not None else 1e9
            a = _ease((lt - ta) / 0.3) if lt >= ta else 0.0
            out[y0 - 2:y1 + 3, rx0:rx1, :] *= 0.32 + 0.68 * a
            if lt < ta: continue
            p = _ease((lt - ta - 0.1) / 0.9); by0, by1, bx1 = c["bars"][i]; cc = (by0 + by1) // 2; hh = (by1 - by0) // 2 + 5
            xe = int(bx0 + p * (bx1 + 6 - bx0)); out[cc - hh:cc + hh + 1, bx0:xe, :] = self.full[cc - hh:cc + hh + 1, bx0:xe, :]
            q = (lt - ta - 0.1) / 0.9
            if q >= 1.15:
                out[y0 + 4:y1 - 3, nx0:nx1, :] = self.full[y0 + 4:y1 - 3, nx0:nx1, :]
            else:
                n = int(round(c["values"][i] * _ease(min(q, 1)))) if q > 0 else 0
                h = y1 - y0 - 8; ni = self._numimg(n, h); nw = ni.shape[1]; cx = (nx0 + nx1) // 2
                reg = out[y0 + 4:y0 + 4 + h, cx - nw // 2:cx - nw // 2 + nw, :]; al = ni[:, :, 3:4]
                reg[:] = reg * (1 - al) + ni[:, :, :3] * 255 * al
                if q > 1.0:
                    f = (q - 1.0) / 0.15; sl = (slice(y0 + 4, y1 - 3), slice(nx0, nx1))
                    out[sl] = out[sl] * (1 - f) + self.full[sl] * f
            if i in vurgu:
                g = lt - ta - 1.0
                if 0 < g < 0.8:
                    s = math.sin(g / 0.8 * math.pi) * 0.35
                    out[y0 - 2:y1 + 3, rx0:rx1, :] = np.minimum(255, out[y0 - 2:y1 + 3, rx0:rx1, :] * (1 + s) + np.array([60, 40, 0], np.float32) * s)
        im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((self.W, int(self.sh * self.k)), Image.BILINEAR)
        return im.crop((0, self.oy, self.W, self.oy + self.H)).convert("RGBA")
