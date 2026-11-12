"""Galata projesi için tek seferlik hazırlık: kule maskeleri ve kulesiz zemin karesi (taş taş inşa animasyonu için).
  python scripts/dev/galata_maske.py projects/galata-kulesi-1348-2026"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

d = sys.argv[1]; I = lambda n: Image.open(os.path.join(d, "images", n)).convert("RGB")
W, H = 1080, 1920

def kaydet(m, ad, yumusak=2.5):
    Image.fromarray((np.clip(m, 0, 1) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(yumusak)).save(os.path.join(d, "images", ad))

# 1) 1348 kulesi (s03): elle çizilen sınır
m = Image.new("L", (W, H), 0); g = ImageDraw.Draw(m)
g.polygon([(393, 700), (688, 700), (692, 1000), (697, 1492), (384, 1492), (388, 1000)], fill=255)      # gövde
g.ellipse([384, 1462, 697, 1516], fill=255)                                                              # taban kavisi
g.polygon([(358, 585), (716, 585), (716, 660), (700, 722), (378, 722), (358, 660)], fill=255)            # mazgallı taç
g.polygon([(540, 372), (690, 566), (664, 600), (416, 600), (392, 566)], fill=255)                         # ahşap külah
g.rectangle([531, 300, 549, 392], fill=255); g.rectangle([514, 322, 566, 338], fill=255)                 # haç
g.polygon([(655, 1232), (720, 1232), (720, 1530), (640, 1530)], fill=0)                                  # öndeki sur
g.polygon([(384, 1440), (470, 1478), (560, 1490), (700, 1470), (700, 1530), (380, 1530)], fill=0)       # öndeki taş yığınları
M3 = np.asarray(m, np.float32) / 255
kaydet(M3, "m03.png")

# kulesiz zemin: kulenin sağındaki ve solundaki dokuyu ayna gibi içeri katla
B = np.asarray(I("s03.jpg"), np.float32); P = B.copy()
G = ndi.binary_dilation(M3 > .5, iterations=7)
for y in range(H):
    xs = np.where(G[y])[0]
    if not len(xs): continue
    a, b = xs.min(), xs.max(); n = b - a + 1; k = np.arange(n)
    sol = B[y, np.clip(a - 1 - k, 0, W - 1)]; sag = B[y, np.clip(b + 1 + (n - 1 - k), 0, W - 1)]
    w = np.clip((k - n / 2) / 46 + .5, 0, 1)[:, None]
    P[y, a:b + 1] = sol * (1 - w) + sag * w
Pb = np.asarray(Image.fromarray(P.astype("uint8")).filter(ImageFilter.GaussianBlur(1.6)), np.float32)
f = np.asarray(Image.fromarray((G * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(5)), np.float32)[..., None] / 255
Image.fromarray((B * (1 - f) + Pb * f).astype("uint8")).save(os.path.join(d, "images", "s03_bos.jpg"), quality=92)

# 2) sonraki dönemler: iki kare arasındaki farktan maske
def fark(a, b, kutu, ad, esik=46):
    A = np.asarray(I(a).filter(ImageFilter.GaussianBlur(3)), np.int32); Bb = np.asarray(I(b).filter(ImageFilter.GaussianBlur(3)), np.int32)
    x0, y0, x1, y1 = kutu; D = np.zeros((H, W), bool); D[y0:y1, x0:x1] = (np.abs(A - Bb).sum(2) > esik)[y0:y1, x0:x1]
    D = ndi.binary_closing(D, iterations=9); D = ndi.binary_fill_holes(D); D = ndi.binary_opening(D, iterations=4)
    lab, n = ndi.label(D)
    if n > 1: D = lab == (1 + np.argmax(ndi.sum(D, lab, range(1, n + 1))))
    D = ndi.binary_dilation(D, iterations=5); kaydet(D.astype(np.float32), ad, 3)
fark("s03.jpg", "s04.jpg", (340, 290, 740, 735), "m04.png")
fark("s04.jpg", "s05.jpg", (345, 110, 745, 1010), "m05.png")
fark("s05.jpg", "s06.jpg", (345, 90, 745, 705), "m06.png")
