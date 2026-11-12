"""İnşa / yıkım animasyonları: aynı açıdan çekilmiş iki kare arasında taş taş geçiş (yapay zekâ videosu gerekmez).

project.json sahnesinde  "insa": {"tur": ..., ...}   (sahnenin "image" alanı = varılacak kare)
  tur = "ins"  : taşlar yukarıdan düşüp sıra sıra oturur, yapı aşağıdan yukarı yükselir
  tur = "sok"  : eski parça yukarıdan aşağı taş taş sökülür, altından yeni kare çıkar
  tur = "ucur" : maskedeki parça (ör. külah) rüzgârla kopup uçar
  tur = "dur"  : animasyon yok; sadece kamera önceki sahnenin bıraktığı yerden kesintisiz sürer
  ortak alanlar: "onceki": "images/x.jpg" (başlangıç karesi), "maske": "images/m.png" (değişen bölge, beyaz),
                 "bas": saniye (başlama) ya da "bas_satir": n (sahnenin n. cümlesiyle başla), "sure": saniye, "dis": true (maske dışı da hızlıca yeni kareye geçsin),
                 "giris": "flas" (sahneye sert girişte beyaz parlama + kamera vuruşu), "sira": taş sırası yüksekliği (px)
Bu sahnelerde motor yumuşak karışma yapmaz; kamera "kb" değerleriyle bir önceki sahneden kesintisiz devam eder.
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from core import W, H, clamp, ease, inout, load_image, put
from fx import spr

SICAK = np.array([52, 42, 24], np.float32)


def _kare(yol):
    im = load_image(yol)
    return np.asarray(im if im.size == (W, H) else im.resize((W, H), Image.LANCZOS), np.float32)


class Insa:
    def __init__(self, d, s):
        c = s["insa"]; self.c = c; self.tur = c.get("tur", "dur"); self.kb = s.get("kb", [1.04, 1.1, .5, .5, .5, .5])
        self.B = _kare(os.path.join(d, s["image"]))
        self.A = _kare(os.path.join(d, c["onceki"])) if c.get("onceki") else self.B
        if c.get("maske"):
            m = Image.open(os.path.join(d, c["maske"])).convert("L")
            self.M = np.asarray(m if m.size == (W, H) else m.resize((W, H)), np.float32) / 255
        else: self.M = np.zeros((H, W), np.float32)
        self.rng = np.random.default_rng(c.get("tohum", 7))
        self.s = s
        if self.tur in ("ins", "sok"): self._bloklar()
        if self.tur == "ucur": self._parca()

    # ── taş blokları: her blok için oturma anı (0..1) ──
    def _bloklar(self):
        M = self.M; ys, xs = np.where(M > .5); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        hr = int(self.c.get("sira", 26)); n = math.ceil((y1 - y0) / hr); up = self.tur == "ins"; r = self.rng
        TL = np.full((H, W), 9.0, np.float32); E = np.zeros((H, W), np.float32); bl = []
        for k in range(n):
            if up: b = y1 - k * hr; a = max(y0, b - hr)
            else: a = y0 + k * hr; b = min(y1, a + hr)
            x = x0 - int(r.integers(0, 60)); row = []
            while x < x1:
                w = int(r.integers(50, 104)); xa, xb = max(x, x0), min(x + w, x1); x += w
                if xb > xa and M[a:b, xa:xb].max() > .5: row.append((xa, xb))
            if k % 2: row = row[::-1]
            for j, (xa, xb) in enumerate(row):
                t = k + 1.5 * j / max(1, len(row)) + float(r.uniform(0, .3))
                TL[a:b, xa:xb] = t; E[a:a + 2, xa:xb] = 1; E[a:b, xa:xa + 2] = 1; bl.append([t, a, b, xa, xb])
        tm = max(x[0] for x in bl)
        for x in bl: x[0] /= tm
        self.TL = TL / tm; self.E = E * M; self.bl = sorted(bl)

    def _parca(self):
        M = self.M; ys, xs = np.where(M > .3); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rgba = np.dstack([self.A[y0:y1, x0:x1], M[y0:y1, x0:x1] * 255]).astype(np.uint8)
        self.parca = Image.fromarray(rgba, "RGBA"); self.pm = ((x0 + x1) / 2, (y0 + y1) / 2); self.pk = (x0, y0, x1, y1)
        r = self.rng
        self.cizgi = [(float(r.uniform(-.3, 1)), float(r.uniform(.03, .75)), float(r.uniform(150, 420)), float(r.uniform(.5, 1)), float(r.uniform(1700, 2900))) for _ in range(34)]
        self.kirinti = [(float(r.uniform(x0, x1)), float(r.uniform(y0, y1)), float(r.uniform(350, 1100)), float(r.uniform(-520, -60)), int(r.integers(3, 9))) for _ in range(46)]

    # ── kamera: kesintisiz yakınlaşma + sarsıntı ──
    def _kamera(self, arr, p, sx=0., sy=0., zm=1.):
        z0, z1, cx0, cy0, cx1, cy1 = self.kb; e = inout(p)
        z = (z0 + (z1 - z0) * e) * zm; cx = cx0 + (cx1 - cx0) * e; cy = cy0 + (cy1 - cy0) * e
        bw, bh = W / z, H / z
        x0 = min(max(cx * W - bw / 2 + sx, 0), W - bw); y0 = min(max(cy * H - bh / 2 + sy, 0), H - bh)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB") if isinstance(arr, np.ndarray) else arr
        return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh)).convert("RGBA")

    def frame(self, lt, dur):
        c = self.c; lt = max(0., lt); p = clamp(lt / max(.1, dur)); sx = sy = 0.; zm = 1.; toz = []; ust = None
        bas = c.get("bas", .25); sa = self.s.get("satir_abs"); n = c.get("bas_satir")
        if n is not None and sa and n < len(sa): bas = max(.1, sa[n] - self.s["start"] + c.get("bas_ek", 0))   # animasyon o cümleyle başlar
        sure = max(.5, min(c.get("sure", 3.0), dur - bas - .3))
        if self.tur in ("ins", "sok"):
            img, toz, amp = self._tas(lt, bas, sure)
            sx = math.sin(lt * 83) * amp * .6; sy = math.sin(lt * 97 + 1) * amp
        elif self.tur == "ucur":
            img, ust, amp = self._ucur(lt, bas)
            sx = math.sin(lt * 71) * amp; sy = math.sin(lt * 89 + 2) * amp * .7
        else: img = self.B
        g = c.get("giris") == "flas" and lt < .32
        if g: zm = 1 + .16 * (1 - ease(lt / .32))
        fr = self._kamera(img, p, sx, sy, zm)
        if toz or ust is not None:
            z0, z1, cx0, cy0, cx1, cy1 = self.kb; e = inout(p); z = (z0 + (z1 - z0) * e) * zm
            ox = min(max((cx0 + (cx1 - cx0) * e) * W - W / z / 2 + sx, 0), W - W / z); oy = min(max((cy0 + (cy1 - cy0) * e) * H - H / z / 2 + sy, 0), H - H / z)
            for (x, y, a, s) in toz: put(fr, spr("dust", 22), (x - ox) * z, (y - oy) * z, a, s * z)
            if ust is not None: fr.alpha_composite(ust.resize((W, H), Image.BILINEAR, box=(ox, oy, ox + W / z, oy + H / z)))
        if g: fr.alpha_composite(Image.new("RGBA", (W, H), (255, 244, 226, int(215 * (1 - lt / .32) ** 2))))
        return fr

    # ── taş taş inşa / söküm ──
    def _tas(self, lt, bas, sure):
        A, B, M, TL = self.A, self.B, self.M, self.TL; u = (lt - bas) / sure; ins = self.tur == "ins"
        done = (TL <= u).astype(np.float32)
        dis = clamp((lt - bas) / .3) if self.c.get("dis") else 1.
        al = M * done + (1 - M) * dis
        img = A + (B - A) * al[..., None]
        if 0 < u < 1.35:
            yas = (u - TL) * sure; taze = M * done
            if ins:
                img = img * (1 - (.5 * self.E * taze * np.clip(1 - yas / .8, 0, 1))[..., None])
                img = img + (taze * np.clip(1 - yas / .2, 0, 1))[..., None] * SICAK
        fn = .17 / sure; toz = []
        for k, (t, a, b, xa, xb) in enumerate(self.bl):
            if ins:
                q = (u - (t - fn)) / fn
                if 0 < q < 1:   # düşen taş: yukarıdan hızlanarak gelir, arkasında iz bırakır
                    for gh, ga in ((0, min(1., q * 3)), (1, .34), (2, .16)):
                        off = int(-(1 - (q - gh * .07) ** 2) * 190) if q - gh * .07 > 0 else None
                        if off is None or a + off < 0: continue
                        mb = (M[a:b, xa:xb] * ga)[..., None]; hed = img[a + off:b + off, xa:xb]
                        hed += (B[a:b, xa:xb] * 1.06 - hed) * mb
            else:
                q = (u - t) / fn
                if 0 < q < 1:   # sökülen taş: yerinden kopup yukarı savrulur ve silinir
                    off = int(-q * q * 150); dx = int((((k * 37) % 7) - 3) * 9 * q)
                    if a + off >= 0 and xa + dx >= 0 and xb + dx <= W:
                        mb = (M[a:b, xa:xb] * (1 - q))[..., None]; hed = img[a + off:b + off, xa + dx:xb + dx]
                        hed += (A[a:b, xa:xb] - hed) * mb
            ya = (u - t) * sure
            if 0 < ya < .5 and k % 2 == 0: toz.append(((xa + xb) / 2, b if ins else a, (1 - ya / .5) * .42, .8 + ya * 3.4))
        son = lt - (bas + sure)
        amp = (2.6 if 0 < u < 1 else 0) + (8 * math.exp(-son * 7) if 0 <= son < .8 and ins else 0)
        if 0 <= son < .7 and ins:   # son taş oturunca tabandan toz bulutu
            ys, xs = np.where(M > .5); yb = ys.max()
            for j in range(9): toz.append((xs.min() + (xs.max() - xs.min()) * j / 8, yb + 6, (1 - son / .7) * .5, 1.6 + son * 5))
        return img, toz, amp

    # ── külahın uçması ──
    def _ucur(self, lt, bas):
        A, B, M = self.A, self.B, self.M; tk = bas + .45; q = (lt - tk) / .8   # tk: kopma anı
        if lt < tk: img = A
        else: img = A + (B - A) * (M + (1 - M) * clamp((lt - tk) / .35))[..., None]
        ust = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(ust)
        zarf = clamp((lt - bas + .15) / .3) * clamp((tk + 1.5 - lt) / .5)
        if zarf > 0:   # rüzgâr çizgileri
            for (x, y, uz, a, hiz) in self.cizgi:
                px = ((x * W + (lt - bas) * hiz) % (W * 1.6)) - W * .3; py = y * H - (px / W) * 90
                g.line([(px, py), (px + uz, py - uz * .085)], fill=(255, 250, 240, int(120 * a * zarf)), width=3)
            ust = ust.filter(ImageFilter.GaussianBlur(1.4)); g = ImageDraw.Draw(ust)
        if 0 <= q < 1.25:
            cx, cy = self.pm
            for gh, ga in ((.09, .22), (.045, .4), (0, 1.)):   # arkada bulanık izler, önde parça
                qq = q - gh
                if qq < 0: continue
                im = self.parca.rotate(-62 * qq ** 1.4, resample=Image.BICUBIC, expand=True)
                put(ust, im, cx + 900 * qq * qq, cy - 430 * qq ** 1.25 + 60 * qq, ga * clamp((1.2 - qq) / .3))
            for (x, y, vx, vy, r) in self.kirinti:
                t = lt - tk; kx = x + vx * t; ky = y + vy * t + 900 * t * t; a = int(230 * clamp(1 - t / 1.1))
                if a > 0 and 0 <= kx < W and 0 <= ky < H: g.rectangle([kx, ky, kx + r, ky + r * .7], fill=(70, 62, 54, a))
        amp = 3 * clamp((lt - bas) / .3) * clamp((tk + .9 - lt) / .5) + (9 * math.exp(-(lt - tk) * 6) if lt >= tk else 0)
        return img, ust, amp
