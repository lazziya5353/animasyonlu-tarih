"""Harf quiz kapagi (Kapak_Her_Harfe stili). Kullanim: quiz_kapak.py script.json kapak.jpg [--bolum N]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harf_quiz import base, ring, up, F, CX, GOLD, WHITE
from PIL import Image, ImageDraw, ImageFilter

def kapak(script, out, bolum=None):
    S = [" ".join(x["lines"]) for x in json.load(open(script))["sahneler"]]
    n = (len(S) - 2)//2; letters = [S[1+2*k].split(" harfi.", 1)[0].strip() for k in range(n)]
    im = base(); d = ImageDraw.Draw(im); ring(d, letters, set(range(n)), None)
    g = Image.new("L", im.size, 0); ImageDraw.Draw(g).ellipse((CX-330, 1060-330, CX+330, 1060+330), fill=110)
    g = g.filter(ImageFilter.GaussianBlur(120)); im = Image.composite(Image.new(im.mode, im.size, (150, 110, 60)), im, g); d = ImageDraw.Draw(im)
    if bolum: d.text((CX, 880), f"{bolum}. BÖLÜM", font=F("Montserrat-900", 28), fill=(225, 210, 190), anchor="ms")
    d.text((CX, 945), f"{n} SORU", font=F("Montserrat-900", 40), fill=WHITE, anchor="ms")
    d.text((CX, 1075), "KAÇINI", font=F("Cinzel-700", 104), fill=GOLD, anchor="ms")
    d.text((CX, 1180), "BİLECEKSİN?", font=F("Cinzel-700", 80), fill=GOLD, anchor="ms")
    im.convert("RGB").save(out, quality=93)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("out"); ap.add_argument("--bolum", type=int)
    a = ap.parse_args(); kapak(a.script, a.out, a.bolum)
