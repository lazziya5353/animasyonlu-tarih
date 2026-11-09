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
        self.eras = c.get("eras", [])

    def auto_time(self):
        """Her sahnenin 'lines' (cümleler) alanı varsa sesi cümlelere hizalar ve sahne/altyazı zamanlarını yazar."""
        c = self.cfg; sents = []; owner = []
        for i, s in enumerate(c["scenes"]):
            for ln in s.get("lines", []): sents.append(ln); owner.append(i)
        segs, dur = align(self.voice, sents)
        for i, s in enumerate(c["scenes"]):
            mine = [g for g, o in zip(segs, owner) if o == i]
            if mine: s["start"], s["end"] = mine[0]["start"], mine[-1]["end"]
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
        s = self.S[i]; p = (tv - s["start"] + 0.5) / (s["end"] - s["start"] + 1.0)
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
            put(fr, text(big, "serif", 150, GOLD, glow=GOLD, spacing=14), W / 2 + shake, 330, clamp(lt / .12) * out, sc)
        elif eff == "glow":
            put(fr, text(big, "serif", 160, (255, 222, 150), glow=(255, 200, 110), spacing=int(40 - 26 * p)), W / 2, 330, clamp(lt / .5) * out, 1 + 0.02 * math.sin(lt * 3))
        else:
            put(fr, text(big, "serif", 150 if len(big) <= 4 else 118, GOLD, glow=GOLD, spacing=int(40 - 26 * p)), W / 2, 330, clamp(lt / .5) * out)
        if eff == "type" and s.get("type_text"):
            full = s["type_text"]; n = int(clamp((lt - .3) / 1.4) * len(full)); st = full[:n] + ("▌" if (int(lt * 4) % 2 == 0 and n < len(full)) else "")
            if st: put(fr, text(st, "mono", 36, (245, 235, 215), spacing=2), W / 2, 455, out)
        elif s.get("sub"):
            put(fr, text(s["sub"], "sans9", 34, WHITE, spacing=10), W / 2, 455, clamp((lt - .35) / .5) * out)

    def frame(self, T):
        c = self.cfg; tv = T - self.off; i = self.scene_at(tv); s = self.S[i]; lt = tv - s["start"]
        fr = self.scene_img(i, tv); atmos(fr, s.get("fx"), tv)
        if i > 0 and lt < 0.5:
            pv = self.scene_img(i - 1, tv); atmos(pv, self.S[i - 1].get("fx"), tv); fr = Image.blend(pv, fr, inout(lt / 0.5))
        m = next((m for m in self.maps if m["start"] <= tv < m["end"]), None)
        if m:
            ml = tv - m["start"]; mp = ml / (m["end"] - m["start"]); c0, c1 = m["cam_from"], m["cam_to"]
            cam = tuple(c0[j] + (c1[j] - c0[j]) * inout(mp) for j in range(3))
            mv = self.mapr.frame(cam, ml, m["end"] - m["start"], m.get("routes", []), m.get("cities", []), m.get("title"), {k: tuple(v) for k, v in m.get("labels", {}).items()})
            fr = Image.blend(fr, mv, clamp(ml / .35) * clamp((m["end"] - tv) / .4))
        if self.ay: self.ay.draw(fr, tv)
        fr.alpha_composite(Image.new("RGBA", (W, H), (60, 35, 10, 16))); fr.alpha_composite(BANDS); fr.alpha_composite(VIG)
        fr.alpha_composite(GRAIN[int(T * 24) % len(GRAIN)])
        if c.get("hook") and T < 3.2: put(fr, text(c["hook"], "sans9", 40, WHITE, spacing=8), W / 2, 150, clamp(T / .5) * clamp((3.2 - T) / .5))
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
        for cp in self.caps:
            if cp["start"] - .1 <= tv < cp["end"] + .05:
                put(fr, caption_img(cp["text"]), W / 2, 1500, clamp((tv - cp["start"] + .1) / .3) * clamp((cp["end"] + .05 - tv) / .25))
        o = c.get("outro")
        if o is None or tv < o["start"] + 0.3: self.timeline(fr, i, lt, clamp(T / 1.0) * (clamp((o["start"] + 0.3 - tv) / .6) if o else 1))
        if o and tv >= o["start"]:
            l2 = tv - o["start"]; dk = clamp((T - (self.dur - 2.2)) / 1.9)
            ta = max(clamp(l2 / .8), dk * .9); la = max(clamp((tv - o.get("line_at", o["start"] + 2)) / .4), dk * .9)
            if dk > 0: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dk * .82))))
            if o.get("title"): put(fr, text(o["title"], "serif", 70, GOLD, glow=GOLD, spacing=6), W / 2, 760, ta)
            if o.get("line"):
                sz = 76; im = text(o["line"], "serif", sz, WHITE, glow=GOLD, spacing=4)
                while im.width > W - 110 and sz > 40: sz -= 4; im = text(o["line"], "serif", sz, WHITE, glow=GOLD, spacing=4)
                put(fr, im, W / 2, 900, la)
        if T < .5: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - T / .5)))))
        return fr.convert("RGB")

    def audio(self):
        out = os.path.join(self.dir, "out"); os.makedirs(out, exist_ok=True)
        mus = os.path.join(out, "music.wav"); mix = os.path.join(out, "mix.wav"); mc = self.cfg.get("music", {})
        MUSIC.make(mus, self.dur, booms=mc.get("booms", [self.off]), major_from=mc.get("major_from"), heartbeat=mc.get("heartbeat"))
        ms = int(self.off * 1000)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mus, "-i", self.voice, "-filter_complex",
                        f"[1:a]aresample=44100,adelay={ms}|{ms},apad=whole_dur={self.dur},highpass=f=60,acompressor=threshold=-18dB:ratio=2.5:attack=8:release=150[v];[v]asplit=2[v1][v2];"
                        f"[0:a]volume={mc.get('volume', 0.32)}[m];[m][v2]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400[md];"
                        f"[md][v1]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5,atrim=0:{self.dur}[o]", "-map", "[o]", "-ar", "44100", mix], check=True)
        return mix

    def render(self, out=None, crf=28):
        out = out or os.path.join(self.dir, "out", "video.mp4"); mix = self.audio()
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", mix,
                              "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                              "-c:a", "aac", "-b:a", "192k", "-t", f"{self.dur:.2f}", "-movflags", "+faststart", out + ".tmp.mp4"], stdin=subprocess.PIPE)
        N = int(self.dur * FPS)
        for n in range(N):
            p.stdin.write(self.frame(n / FPS).tobytes())
            if n % 300 == 0: print(f"{n}/{N}", flush=True)
        p.stdin.close(); p.wait()
        if p.returncode == 0: os.replace(out + ".tmp.mp4", out)
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
