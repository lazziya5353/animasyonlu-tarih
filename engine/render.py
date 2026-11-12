"""Animasyonlu Tarih video motoru.
Kullanım:
  python engine/render.py projects/<proje>                 # tam video -> projects/<proje>/out/video.mp4
  python engine/render.py projects/<proje> --preview 5 20  # seçilen saniyelerden önizleme karesi -> out/preview.jpg
Proje klasöründe project.json, images/ ve ses dosyası olmalı. Zamanlar yoksa ses dosyasına göre otomatik hizalanır."""
import sys, os, json, math, subprocess, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
from core import W, H, FPS, GOLD, WHITE, F, clamp, ease, inout, text, put, caption_img, kenburns, VIG, BANDS, GRAIN, gold_card
from fx import atmos, AyYildiz
from maps import MapRenderer
import music as MUSIC
from align import align
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
try:
    from olay import olay
except Exception:  # olay sistemi yoksa motor yine çalışır
    def olay(*a, **k): pass

HERE = os.path.dirname(os.path.abspath(__file__))
try: MARKA = json.load(open(os.path.join(HERE, "assets", "marka.json")))
except Exception: MARKA = {}
_LOGO = os.path.join(HERE, "assets", "logo_mark.png")
LOGO = Image.open(_LOGO).convert("RGBA") if os.path.exists(_LOGO) else None
# gezen imzanın uğradığı yerler: altyazı, başlık ve Instagram butonlarından uzak orta bölgeler
GEZEN = [(540, 720), (700, 1000), (420, 880), (660, 1160), (540, 960)]
UYARILAR = []  # kurgu kontrolcüsü için: sığmadığı için küçültülen yazılar

def fit_size(txt, font, size, maxw=W - 90, min_size=40, spacing=0, glow=None):
    """Son (animasyon bittiğindeki) harf aralığıyla sığan boyut; animasyon boyunca boyut sabit kalsın diye."""
    s0 = size
    while size > min_size and text(txt, font, size, (255, 255, 255), glow=glow, spacing=spacing).width > maxw: size -= 4
    if size != s0 and txt not in UYARILAR: UYARILAR.append(txt)
    return size


def fit(txt, font, size, col, maxw=W - 90, min_size=40, **kw):
    """Yazıyı genişliğe sığana kadar küçültür; taşma imkânsız."""
    im = text(txt, font, size, col, **kw); s0 = size
    while im.width > maxw and size > min_size:
        size -= 4; im = text(txt, font, size, col, **kw)
    if size != s0 and txt not in UYARILAR: UYARILAR.append(txt)
    return im

ERA_DEFAULT_COL = [(120, 200, 160), (232, 196, 120), (200, 150, 110), (170, 120, 120), (230, 80, 80), (130, 170, 230)]

class Project:
    def __init__(self, d):
        self.dir = d; self.cfg = json.load(open(os.path.join(d, "project.json")))
        c = self.cfg; self.off = c.get("voice_offset", 0.3)
        self.voice = os.path.join(d, c.get("voice", "ses.wav"))
        if any(s.get("start") is None for s in c["scenes"]): self.auto_time()
        self.S = c["scenes"]; self.caps = c.get("captions", [])
        self.dur = c.get("duration") or (self.S[-1]["end"] + self.off + 0.2)
        self.tl = [i for i, s in enumerate(self.S) if s.get("timeline", True)]
        self.maps = c.get("maps", []); self.mapr = MapRenderer(c.get("map_region", "avrupa_ortadogu"), c.get("cities")) if self.maps else None
        self.jumps = c.get("jumps", []); self.cards = c.get("cards", [])
        ay = c.get("ayyildiz"); self.ay = AyYildiz(*ay) if ay else None
        self.eras = c.get("eras", []); self._tablo = {}

    def auto_time(self):
        """Her sahnenin 'lines' (cümleler) alanı varsa sesi cümlelere hizalar ve sahne/altyazı zamanlarını yazar."""
        c = self.cfg; sents = []; owner = []
        for i, s in enumerate(c["scenes"]):
            for ln in s.get("lines", []): sents.append(ln); owner.append(i)
        spoken = None
        try:  # okunan metin (rakamlar yazıyla) varsa süre tahmini ve tanıma eşleşmesi ondan yapılır
            sp = json.load(open(os.path.join(self.dir, "script.json"), encoding="utf-8")).get("seslendirme_metni", "").split("\n")
            sp = [x for x in sp if x.strip()]
            if len(sp) == len(sents): spoken = sp
        except Exception: pass
        segs, dur = align(self.voice, sents, spoken)
        for i, s in enumerate(c["scenes"]):
            mine = [g for g, o in zip(segs, owner) if o == i]
            if mine: s["start"], s["end"] = mine[0]["start"], mine[-1]["end"]
            if mine and s.get("insa"): s["satir_abs"] = [g["start"] for g in mine]
            if s.get("tablo") and mine:
                # her cümle bir satırı yakar: satır, okunduğu cümlenin başladığı an yanar
                act = [None] * len(s["tablo"]["rows"])
                for g, r in zip(mine, s["tablo"].get("sira", [])):
                    if r is not None and r < len(act): act[r] = g["start"]
                s["tablo"]["act_abs"] = act
        sc = c["scenes"]
        for i, s in enumerate(sc):
            if s.get("start") is None: s["start"] = sc[i - 1]["end"] if i else 0.0; s["end"] = s["start"] + 3
        sc[0]["start"] = 0.0
        for i in range(1, len(sc)):
            sc[i]["start"] = max(sc[i - 1]["start"] + 0.5, sc[i]["start"] - 0.15); sc[i - 1]["end"] = sc[i]["start"]
        c["scenes"][-1]["end"] = dur + 2.2
        self.plans(c, dur)
        if not c.get("captions"):
            c["captions"] = [{"start": g["start"], "end": g["end"], "text": g["text"]} for g in segs if not g["text"].strip().rstrip(".").isdigit()]
        json.dump(c, open(os.path.join(self.dir, "project.timed.json"), "w"), ensure_ascii=False, indent=1)

    def plans(self, c, voice_dur):
        """Senaristin planlarını (harita, kart, kapanış, yıl atlama) zamanlı öğelere çevirir."""
        sc = c["scenes"]
        if c.get("maps_plan") and not c.get("maps"):
            from maps import CITIES
            cities_all = dict(CITIES); cities_all.update(c.get("cities", {})); c["maps"] = []
            for m in c["maps_plan"]:
                k = min(len(sc) - 1, int(m.get("scene", m.get("after_scene", 0) + 1))); names = [x for x in m.get("cities", []) + m.get("route", []) if x in cities_all]
                if not names: continue
                lons = [cities_all[x][0] for x in names]; lats = [cities_all[x][1] for x in names]
                wdeg = max(4.5, (max(lons) - min(lons)) * 1.9, (max(lats) - min(lats)) * 1.9 * 0.56 / 0.75)
                cx, cy = (max(lons) + min(lons)) / 2, (max(lats) + min(lats)) / 2
                t0 = sc[k]["start"]; t1 = min(sc[k]["end"] - 0.3, t0 + 2.3)
                c["maps"].append({"start": t0, "end": t1, "cam_from": [cx, cy, wdeg * 1.12], "cam_to": [cx, cy, wdeg], "routes": [m["route"]] if m.get("route") else [],
                                  "cities": [x for x in m.get("cities", []) if x in cities_all], "title": m.get("title", ""), "labels": m.get("labels", {})})
        if c.get("cards_plan") and not c.get("cards"):
            c["cards"] = [{"start": sc[min(len(sc) - 1, k["scene"])]["start"] + 1.2, "end": sc[min(len(sc) - 1, k["scene"])]["end"] - 0.3,
                           "value": k["value"], "unit": k.get("unit", ""), "small": k.get("small", "")} for k in c["cards_plan"]]
        if c.get("finale") == "ayyildiz" and not c.get("ayyildiz"):
            # ay yıldız son sahnenin başında toplanır; kapanış yazısı ondan sonra gelir
            t0 = max(1.0, (sc[-1]["start"] - 0.4) if len(sc) > 1 else voice_dur - 6)
            c["ayyildiz"] = [t0, t0 + 1.9, t0 + 4.5, t0 + 6.1]
        if c.get("outro_plan") and not c.get("outro"):
            st = max(sc[-1]["start"], voice_dur - 3.5, (c.get("ayyildiz") or [0, 0, 0, 0])[3])
            c["outro"] = {"start": st, "title": c["outro_plan"].get("title", ""), "line": c["outro_plan"].get("line", ""), "line_at": max(voice_dur - 1.2, st + 1.0)}
            if not c.get("duration"): c["duration"] = round(max(sc[-1]["end"] + c.get("voice_offset", 0) + 0.2, st + 3.6), 2)
        if not c.get("jumps"):
            c["jumps"] = []; yrs = [(i, s.get("year")) for i, s in enumerate(sc) if isinstance(s.get("year"), (int, float))]
            for (i0, y0), (i1, y1) in zip(yrs, yrs[1:]):
                if y1 - y0 >= 50 and not any(m["start"] <= sc[i1]["start"] < m["end"] for m in c.get("maps", [])): c["jumps"].append({"t": sc[i1]["start"], "value": int(y1 - y0)})

    def scene_at(self, tv):
        for i, s in enumerate(self.S):
            if s["start"] <= tv < s["end"]: return i
        return len(self.S) - 1
    def scene_img(self, i, tv):
        s = self.S[i]
        if s.get("anim"):  # koddan çizilen veri/harita animasyonu (engine/deprem.py)
            if i not in self._tablo:
                from deprem import DepremAnim
                self._tablo[i] = DepremAnim(self.dir, s["anim"])
            return self._tablo[i].frame(tv - s["start"], s["end"] - s["start"])
        if s.get("video"):  # hazır video klip, sahne süresine uydurulur (engine/klip.py)
            if i not in self._tablo:
                from klip import Klip
                self._tablo[i] = Klip(self.dir, s)
            return self._tablo[i].frame(tv - s["start"], s["end"] - s["start"])
        if s.get("insa"):  # taş taş inşa / söküm / uçma (engine/insa.py); kamera kesintisiz sürer
            if i not in self._tablo:
                from insa import Insa
                self._tablo[i] = Insa(self.dir, s)
            return self._tablo[i].frame(tv - s["start"], s["end"] - s["start"])
        if s.get("tablo"):
            if i not in self._tablo:
                from tablo import Tablo
                self._tablo[i] = Tablo(self.dir, s["image"], s["tablo"], W, H)
            act = [(a - s["start"]) if a is not None else None for a in s["tablo"].get("act_abs", [])]
            if not any(a is not None for a in act):  # hizalama yoksa satırları sahneye eşit dağıt
                n = len(s["tablo"]["rows"]); d = max(1.0, s["end"] - s["start"] - 1.5); act = [0.6 + d * k / n for k in range(n)]
            return self._tablo[i].frame(tv - s["start"], act)
        p = (tv - s["start"] + 0.5) / (s["end"] - s["start"] + 1.0)
        return kenburns(os.path.join(self.dir, s["image"]), p, *s.get("kb", [1.04, 1.16, .5, .5, .5, .5]))

    # ── zaman çizelgesi + dönem şeridi ──
    def timeline(self, fr, i, lt, a):
        if a <= 0 or i not in self.tl: return
        n = len(self.tl); k = self.tl.index(i); TX0, TX1 = 110, 970
        tick = lambda j: TX0 + (TX1 - TX0) * j / max(1, n - 1)
        g = Image.new("RGBA", (W, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(g); y = 110
        pos = k if lt >= 0.8 or k == 0 else (k - 1) + ease(lt / 0.8); xp = TX0 + (TX1 - TX0) * pos / max(1, n - 1)
        d.line([(TX0, y), (TX1, y)], fill=(255, 255, 255, 60), width=3); d.line([(TX0, y), (xp, y)], fill=GOLD + (255,), width=5)
        for j in range(n):
            x = tick(j); d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(GOLD + (255,)) if j <= pos + 0.01 else (255, 255, 255, 90))
        if self.eras:
            cur = round(pos)
            for e_i, e in enumerate(self.eras):
                col = tuple(e.get("color", ERA_DEFAULT_COL[e_i % len(ERA_DEFAULT_COL)]))
                x0 = tick(e["from"]) - (TX1 - TX0) / (2 * (n - 1)) + 4; x1 = tick(e["to"]) + (TX1 - TX0) / (2 * (n - 1)) - 4
                act = e["from"] <= cur <= e["to"]
                d.rounded_rectangle([x0, y + 30, x1, y + 38], 4, fill=col + (255 if act else 70,))
                if act or (x1 - x0) > 120:
                    d.text(((x0 + x1) / 2, y + 62), e["name"], font=F("sans9", 21 if act else 18), fill=(col + (255,)) if act else (255, 255, 255, 110), anchor="mm")
        gl = Image.new("RGBA", g.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([xp - 22, y - 22, xp + 22, y + 22], fill=GOLD + (150,)); g.alpha_composite(gl.filter(ImageFilter.GaussianBlur(10)))
        ImageDraw.Draw(g).ellipse([xp - 10, y - 10, xp + 10, y + 10], fill=(255, 240, 210, 255))
        cur_s = self.S[i]; lab = str(cur_s.get("label", cur_s.get("year", "")))
        if k > 0 and lt < 0.8:
            a0 = self.S[self.tl[k - 1]].get("year"); a1 = cur_s.get("year")
            if isinstance(a0, (int, float)) and isinstance(a1, (int, float)) and a0 != a1: lab = str(int(round(a0 + (a1 - a0) * ease(lt / 0.8))))
        d.text((xp, y - 42), lab, font=F("serif", 34), fill=(255, 236, 200, 255), anchor="mm")
        put(fr, g, W / 2, 1752, a)

    def titles(self, fr, i, tv, lt):
        s = self.S[i]; big = s.get("big"); out = clamp((s["end"] - tv) / .35)
        if not big: return
        p = ease(lt / .9); eff = s.get("effect")
        if eff == "stamp":
            sc = 1 + 1.2 * (1 - clamp(lt / 0.18)) ** 2; shake = (6 * math.sin(lt * 90) * clamp((0.45 - lt) / 0.3)) if lt < 0.45 else 0
            put(fr, fit(big, "serif", 150, GOLD, glow=GOLD, spacing=14), W / 2 + shake, 330, clamp(lt / .12) * out, sc)
        elif eff == "glow":
            sz = fit_size(big, "serif", 160, spacing=14, glow=(255, 200, 110)); sp = int(40 - 26 * p)
            while sp > 14 and text(big, "serif", sz, (255, 222, 150), glow=(255, 200, 110), spacing=sp).width > W - 60: sp -= 4
            put(fr, text(big, "serif", sz, (255, 222, 150), glow=(255, 200, 110), spacing=sp), W / 2, 330, clamp(lt / .5) * out, 1 + 0.02 * math.sin(lt * 3))
        else:
            sz = fit_size(big, "serif", 150 if len(big) <= 4 else 118, spacing=14, glow=GOLD); sp = int(40 - 26 * p)
            while sp > 14 and text(big, "serif", sz, GOLD, glow=GOLD, spacing=sp).width > W - 60: sp -= 4
            put(fr, text(big, "serif", sz, GOLD, glow=GOLD, spacing=sp), W / 2, 330, clamp(lt / .5) * out)
        if eff == "type" and s.get("type_text"):
            full = s["type_text"]; n = int(clamp((lt - .3) / 1.4) * len(full)); st = full[:n] + ("▌" if (int(lt * 4) % 2 == 0 and n < len(full)) else "")
            sz = 36
            while sz > 24 and text(full + "▌", "mono", sz, (245, 235, 215), spacing=2).width > W - 90: sz -= 2
            if st: put(fr, text(st, "mono", sz, (245, 235, 215), spacing=2), W / 2, 455, out)
        elif s.get("sub"):
            put(fr, fit(s["sub"], "sans9", 34, WHITE, min_size=22, spacing=10), W / 2, 455, clamp((lt - .35) / .5) * out)

    def frame(self, T):
        c = self.cfg; tv = T - self.off; i = self.scene_at(tv); s = self.S[i]; lt = tv - s["start"]
        fr = self.scene_img(i, tv); atmos(fr, s.get("fx"), tv)
        if i > 0 and lt < 0.5 and not s.get("insa") and not (s.get("video") and s.get("video") == self.S[i - 1].get("video")):  # aynı klibin devamıysa karıştırma
            pv = self.scene_img(i - 1, tv); atmos(pv, self.S[i - 1].get("fx"), tv); fr = Image.blend(pv, fr, inout(lt / 0.5))
        m = next((m for m in self.maps if m["start"] <= tv < m["end"]), None)
        if m:
            ml = tv - m["start"]; mp = ml / (m["end"] - m["start"]); c0, c1 = m["cam_from"], m["cam_to"]
            cam = tuple(c0[j] + (c1[j] - c0[j]) * inout(mp) for j in range(3))
            mv = self.mapr.frame(cam, ml, m["end"] - m["start"], m.get("routes", []), m.get("cities", []), m.get("title"), {k: tuple(v) for k, v in m.get("labels", {}).items()})
            fr = Image.blend(fr, mv, clamp(ml / .35) * clamp((m["end"] - tv) / .4))
        if self.ay: self.ay.draw(fr, tv)
        if not c.get("sade"):   # "sade": true -> film filtresi yok (kahverengi ton, kararan kenarlar, kumlanma); hazır video kliplerde renkler olduğu gibi kalır
            fr.alpha_composite(Image.new("RGBA", (W, H), (60, 35, 10, 16))); fr.alpha_composite(BANDS); fr.alpha_composite(VIG)
            fr.alpha_composite(GRAIN[int(T * 24) % len(GRAIN)])
        if c.get("hook") and T < 3.2: put(fr, fit(c["hook"], "sans9", 40, WHITE, min_size=24, spacing=8), W / 2, 150, clamp(T / .5) * clamp((3.2 - T) / .5))
        if not m or (tv - m["start"]) > (m["end"] - m["start"]) - 0.2:
            self.titles(fr, i, tv, lt)
            for j in self.jumps:
                q = tv - j["t"]
                if 0 <= q < 1.5:
                    n = int(round(int(j["value"]) * ease(q / 0.7))); al = clamp(q / .2) * clamp((1.5 - q) / .35)
                    put(fr, text(f"+{n}", "serif", 120, (255, 236, 200), glow=GOLD, spacing=6), W / 2, 900, al, 1 + 0.06 * (1 - ease(q / .5)))
                    put(fr, text(j.get("unit", "YIL SONRA"), "sans9", 34, GOLD, spacing=12), W / 2, 1010, al)
        for cd in self.cards:
            if cd["start"] <= tv < cd["end"]:
                q = tv - cd["start"]; p = clamp(q / .35) * clamp((cd["end"] - tv) / .35)
                gold_card(fr, W / 2, cd.get("y", 800), f"{int(round(cd['value'] * ease(q / 1.1)))} {cd.get('unit', '')}".strip(), cd.get("small", ""), p)
        for cp in ([] if s.get("tablo") else self.caps):
            if cp["start"] - .1 <= tv < cp["end"] + .05:
                put(fr, caption_img(cp["text"]), W / 2, 1500, clamp((tv - cp["start"] + .1) / .3) * clamp((cp["end"] + .05 - tv) / .25))
        if c.get("seri"):  # dizi rozeti: ör. "PART 1/2" (sol üst, tüm video boyunca)
            if not hasattr(self, "_seri"):
                g = text(c["seri"], "sans9", 30, (255, 255, 255), spacing=6, shadow=False); pad = 18
                b = Image.new("RGBA", (g.width - 40 + 2 * pad, 64), (0, 0, 0, 0)); ImageDraw.Draw(b).rounded_rectangle([0, 0, b.width - 1, 63], 14, fill=(170, 24, 24, 230))
                b.alpha_composite(g, (pad - 40, (64 - g.height) // 2)); self._seri = b
            put(fr, self._seri, 60 + self._seri.width / 2, 215, clamp((T - .3) / .4))
        sa = clamp(lt / .4) * clamp((s["end"] - tv) / .3)
        if s.get("etiket"):  # ör. "TEMSİLİ": yapay zekâ görseli gerçek fotoğraf sanılmasın
            put(fr, text(s["etiket"], "sans9", 24, (255, 255, 255), spacing=6), W - 150, 215, sa * .85)
        if s.get("kaynak"):
            put(fr, text(s["kaynak"], "sans", 24, (225, 225, 225), spacing=1), W / 2, 1610, sa * .9)
        o = c.get("outro")
        if o is None or tv < o["start"] + 0.3: self.timeline(fr, i, lt, clamp(T / 1.0) * (clamp((o["start"] + 0.3 - tv) / .6) if o else 1))
        if o and tv >= o["start"]:
            l2 = tv - o["start"]; dk = clamp((T - (self.dur - 2.2)) / 1.9)
            ta = max(clamp(l2 / .8), dk * .9); la = max(clamp((tv - o.get("line_at", o["start"] + 2)) / .4), dk * .9)
            if dk > 0: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dk * .82))))
            if o.get("title"): put(fr, fit(o["title"], "serif", 70, GOLD, glow=GOLD, spacing=6), W / 2, 760, ta)
            if o.get("line"):
                put(fr, fit(o["line"], "serif", 76, WHITE, maxw=W - 110, glow=GOLD, spacing=4), W / 2, 900, la)
        self.watermark(fr, T, kose=not (s.get("tablo") or s.get("anim")))
        if T < .5: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - T / .5)))))
        return fr.convert("RGB")

    def watermark(self, fr, T, kose=True):
        """Köşede küçük logo + sayfa adı; kırpılıp silinmesin diye arada ekranın farklı yerinde beliren soluk imza."""
        mk = {**MARKA, **(self.cfg.get("filigran") or {})}
        if not mk.get("filigran", True) or not mk.get("handle"): return
        if not hasattr(self, "_wm"):
            ht = text(mk["handle"], "sans", 25, (255, 244, 220), shadow=True, spacing=1)
            lg = LOGO.resize((int(LOGO.width * 46 / LOGO.height), 46), Image.LANCZOS) if LOGO else None
            w = (lg.width + 10 if lg else 0) + ht.width; h = max(46, ht.height)
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            if lg: im.alpha_composite(lg, (0, (h - lg.height) // 2))
            im.alpha_composite(ht, ((lg.width + 10) if lg else 0, (h - ht.height) // 2))
            self._wm = im; self._wm2 = text(mk["handle"], "sans9", 40, (255, 255, 255), shadow=False, spacing=3)
        # sol orta-alt: Instagram'ın üst çubuğu, sağdaki butonlar ve alttaki açıklama alanının dışında
        if kose: put(fr, self._wm, 44 + self._wm.width / 2, 1305, 0.55 * clamp((T - 1.0) / .6) * clamp((self.dur - 2.4 - T) / .6))
        per = float(mk.get("gezen_imza_aralik", 15) or 0)
        if per > 0 and 6 < T < self.dur - 4:
            k = int(T // per); q = T - k * per
            if k > 0 and q < 2.2:
                x, y = GEZEN[k % len(GEZEN)]
                put(fr, self._wm2, x, y, 0.30 * clamp(q / .5) * clamp((2.2 - q) / .5))

    def audio(self):
        """Varsayılan: sadece anlatıcının sesi (temizlenmiş, sabit seviyede). Müzik ancak project.json'da music.aktif=true ise eklenir."""
        out = os.path.join(self.dir, "out"); os.makedirs(out, exist_ok=True)
        mus = os.path.join(out, "music.wav"); mix = os.path.join(out, "mix.wav"); mc = self.cfg.get("music", {}) or {}
        ms = int(self.off * 1000)
        ses = (f"aresample=44100,adelay={ms}|{ms},apad=whole_dur={self.dur},highpass=f=70,afftdn=nf=-30,"
               f"acompressor=threshold=-18dB:ratio=2.5:attack=8:release=150")
        ol = []
        for sn in self.S:   # sahnelerdeki hafif efekt sesleri (engine/sfx.py)
            x = sn.get("sfx")
            if not x: continue
            x = x if isinstance(x, dict) else {"tur": x}; d = sn["end"] - sn["start"]
            ol.append((x["tur"], self.off + sn["start"] + d * x.get("bas", 0), self.off + sn["start"] + d * x.get("son", 1)))
        if ol and not mc.get("aktif"):
            import sfx as SFX
            ef = os.path.join(out, "sfx.wav"); SFX.make(ef, self.dur, ol)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.voice, "-i", ef, "-filter_complex",
                            f"[0:a]{ses}[v];[1:a]volume={self.cfg.get('sfx_seviye', 0.22)}[e];"
                            f"[v][e]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5,atrim=0:{self.dur}[o]", "-map", "[o]", "-ar", "44100", mix], check=True)
            return mix
        if not mc.get("aktif"):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.voice, "-filter_complex",
                            f"[0:a]{ses},loudnorm=I=-14:TP=-1.5,atrim=0:{self.dur}[o]", "-map", "[o]", "-ar", "44100", mix], check=True)
            return mix
        MUSIC.make(mus, self.dur, booms=mc.get("booms", [self.off]), major_from=mc.get("major_from"), heartbeat=mc.get("heartbeat"), drone=mc.get("drone", False))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mus, "-i", self.voice, "-filter_complex",
                        f"[1:a]{ses}[v];[v]asplit=2[v1][v2];"
                        f"[0:a]highpass=f=110,lowpass=f=7000,volume={mc.get('volume', 0.24)}[m];[m][v2]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=450[md];"
                        f"[md][v1]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5,atrim=0:{self.dur}[o]", "-map", "[o]", "-ar", "44100", mix], check=True)
        return mix

    def olay_plan(self):
        """Kurgu Stüdyosu'ndaki canlı imleçler için: kurgucunun zaman çizelgesine yerleştirdiği her şeyi bildirir."""
        slug = os.path.basename(os.path.normpath(self.dir)); off = self.off
        O = lambda tur, msg, **k: olay("kurgucu", tur, msg, slug=slug, **k)
        O("ses", f"Ses analiz ediliyor: {len(self.caps)} cümle, {self.dur:.0f} sn", t0=0, t1=self.dur)
        for i, s in enumerate(self.S):
            O("gorsel", f"Sahne {i + 1} · {s.get('big') or ''} yerleştirildi", t0=s["start"] + off, t1=s["end"] + off, sahne=i + 1)
            for c in self.caps:
                if s["start"] - .05 <= c["start"] < s["end"]: O("yazi", f"“{c['text'][:48]}” sese hizalandı", t0=c["start"] + off, t1=c["end"] + off, sahne=i + 1)
            if s.get("fx") or s.get("effect"):
                olay("efekt", "efekt", f"Sahne {i + 1}: {', '.join((s.get('fx') or []) + ([s['effect']] if s.get('effect') else []))}", slug=slug, t0=s["start"] + off, t1=min(s["end"], s["start"] + 2.6) + off, sahne=i + 1)
        for m in self.maps: O("harita", f"Harita: {m.get('title', '')}", t0=m["start"] + off, t1=m["end"] + off)
        for c in self.cards: olay("efekt", "efekt", f"Sayaç kartı: {c.get('value')} {c.get('unit', '')}", slug=slug, t0=c["start"] + off, t1=c["end"] + off)
        for j in self.jumps: olay("efekt", "efekt", f"Zaman atlaması: +{j.get('value')} yıl", slug=slug, t0=j["t"] + off, t1=j["t"] + off + 1.4)
        if self.cfg.get("ayyildiz"): a = self.cfg["ayyildiz"]; olay("efekt", "efekt", "Ay yıldız finali", slug=slug, t0=a[0] + off, t1=a[3] + off)
        if (self.cfg.get("music") or {}).get("aktif"): O("muzik", "Müzik besteleniyor, sese göre kısılacak", t0=0, t1=self.dur)
        else: O("ses", "Müzik yok: sadece anlatıcı sesi, temizleniyor", t0=0, t1=self.dur)
        olay("efekt", "efekt", f"Filigran: {MARKA.get('handle', '')}", slug=slug, t0=1.0, t1=self.dur - 2.4)

    def render(self, out=None, crf=28):
        out = out or os.path.join(self.dir, "out", "video.mp4"); self.olay_plan(); mix = self.audio()
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", mix,
                              "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                              "-c:a", "aac", "-b:a", "192k", "-t", f"{self.dur:.2f}", "-movflags", "+faststart", out + ".tmp.mp4"], stdin=subprocess.PIPE)
        N = int(self.dur * FPS); slug = os.path.basename(os.path.normpath(self.dir)); adim = max(1, N // 20)
        for n in range(N):
            p.stdin.write(self.frame(n / FPS).tobytes())
            if n % 300 == 0: print(f"{n}/{N}", flush=True)
            if n % adim == 0: olay("kurgucu", "ilerleme", f"Kareler işleniyor %{100 * n // N}", slug=slug, t0=n / FPS, yuzde=100 * n // N)
        p.stdin.close(); p.wait()
        if p.returncode != 0: raise SystemExit(f"ffmpeg başarısız oldu (kod {p.returncode}); video üretilemedi")
        os.replace(out + ".tmp.mp4", out)
        json.dump(UYARILAR, open(os.path.join(os.path.dirname(out), "uyarilar.json"), "w"), ensure_ascii=False)
        olay("kurgucu", "bilgi", "Video hazır ✓", slug=slug, yuzde=100)
        return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--preview", nargs="*", type=float); ap.add_argument("--out"); ap.add_argument("--crf", type=int, default=28)
    a = ap.parse_args(); P = Project(a.project)
    if a.preview:
        os.makedirs(os.path.join(a.project, "out"), exist_ok=True)
        ims = [P.frame(t).resize((360, 640)) for t in a.preview]; o = Image.new("RGB", (360 * len(ims), 640))
        for j, im in enumerate(ims): o.paste(im, (360 * j, 0))
        dst = a.out or os.path.join(a.project, "out", "preview.jpg"); o.save(dst, quality=85); print(dst)
    else:
        print(P.render(a.out, a.crf))
