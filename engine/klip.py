"""Video klipli sahneler: hazır bir video (ör. Higgsfield) sahnenin süresine, yani anlatıcının cümlelerine uydurulur.

project.json sahnesinde:  "video": "videos/k1.mp4", "v_bas": 0.0, "v_son": 8.0   (klibin kullanılacak aralığı, saniye; yoksa tamamı)
Parça sahne süresine yayılır: cümle kısaysa hızlanır, uzunsa yavaşlar. Cümle parçadan çok uzunsa görüntü donmaz: giderek yavaşlar ve son kareye cümleyle birlikte varır; ayrıca hafif bir yakınlaşma sürer. Yavaşlatırken ara kareler karıştırılarak yumuşatılır.
"""
import os, glob, subprocess, tempfile
from PIL import Image
from core import W, H, clamp

EN_YAVAS = 1.5


class Klip:
    def __init__(self, d, s):
        yol = os.path.join(d, s["video"]); self.dir = tempfile.mkdtemp(prefix="klip_")
        if not os.path.exists(yol) and s.get("video_url"):   # klip repoda yoksa (ör. Higgsfield adresi) sunucuda indirilir
            import urllib.request; os.makedirs(os.path.dirname(yol), exist_ok=True)
            urllib.request.urlretrieve(s["video_url"], yol)
        arg = ["ffmpeg", "-v", "error", "-y"]
        # sahne sınırlarında 0,3 sn pay: yapay zekâ klibindeki gerçek kesim tam saniyede olmayabilir, komşu sahneden kare sızmasın
        vb = (s.get("v_bas") or 0) + (0.3 if s.get("v_bas") else 0); vs = s.get("v_son")
        if vs is not None and not s.get("v_son_tam"): vs = vs - 0.3
        if vb: arg += ["-ss", str(vb)]
        if vs is not None: arg += ["-t", str(max(0.5, vs - vb))]
        arg += ["-i", yol, "-vf", f"fps=30,scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}", "-q:v", "3", os.path.join(self.dir, "%05d.jpg")]
        subprocess.run(arg, check=True)
        self.k = sorted(glob.glob(os.path.join(self.dir, "*.jpg"))); self.n = len(self.k); self._c = {}
        if not self.n: raise RuntimeError(f"Videodan kare çıkmadı: {yol}")
        kapak = os.path.join(d, s.get("image") or "")                       # panelde sahne görseli görünsün: klibin ortasından bir kare
        if s.get("image") and not os.path.exists(kapak):
            os.makedirs(os.path.dirname(kapak), exist_ok=True); Image.open(self.k[self.n // 2]).convert("RGB").save(kapak, quality=85)

    def _al(self, i):
        if i not in self._c:
            if len(self._c) > 8: self._c.pop(next(iter(self._c)))
            self._c[i] = Image.open(self.k[i]).convert("RGB")
        return self._c[i]

    def frame(self, lt, dur):
        n = self.n; sure = n / 30.0; lt = max(0., lt); u = clamp(lt / max(.1, dur)); r = dur / sure
        if r <= EN_YAVAS: pos = u * (n - 1)                                 # parçayı sahne süresine tam yay
        else: pos = (n - 1) * (1 - (1 - u) ** (r / 1.25))                   # çok uzun cümle: donmak yerine giderek yavaşlar, son kareye cümleyle birlikte varır
        i = int(pos); f = pos - i; a = self._al(i)
        if f > .05 and i + 1 < n: a = Image.blend(a, self._al(i + 1), f)
        z = 1 + .07 * u; bw, bh = W / z, H / z                              # hafif, kesintisiz yakınlaşma: görüntü hiçbir an tam durmaz
        return a.resize((W, H), Image.BILINEAR, box=((W - bw) / 2, (H - bh) / 2, (W + bw) / 2, (H + bh) / 2)).convert("RGBA")
