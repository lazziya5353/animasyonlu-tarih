"""Harf quiz kapagi (Kapak_Her_Harfe stili). Kullanim: quiz_kapak.py script.json kapak.jpg [--bolum N] [--format harf-bul]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harf_quiz import base, ring, up, F, CX, GOLD, WHITE
from PIL import Image, ImageDraw, ImageFilter

def kapak(script, out, bolum=None):
    SJ = json.load(open(script)); S = [" ".join(x["lines"]) for x in SJ["sahneler"]]
    n = (len(S) - 2)//2; letters = [S[1+2*k].split(" harfi.", 1)[0].strip() for k in range(n)]
    nz = sum(1 for k in range(n) if SJ["sahneler"][1+2*k].get("zorluk") == "zor")
    im = base(); d = ImageDraw.Draw(im); ring(d, letters, set(range(n)), None)
    g = Image.new("L", im.size, 0); ImageDraw.Draw(g).ellipse((CX-330, 1060-330, CX+330, 1060+330), fill=110)
    g = g.filter(ImageFilter.GaussianBlur(120)); im = Image.composite(Image.new(im.mode, im.size, (150, 110, 60)), im, g); d = ImageDraw.Draw(im)
    if bolum: d.text((CX, 880), f"{bolum}. BÖLÜM", font=F("Montserrat-900", 28), fill=(225, 210, 190), anchor="ms")
    d.text((CX, 945), f"{n} SORU", font=F("Montserrat-900", 40), fill=WHITE, anchor="ms")
    if nz:  # quiz 3+: zor soru sayisi, kirmizi hap
        zf = F("Montserrat-900", 32); zt = f"{nz} ZOR SORU"; w = d.textlength(zt, font=zf) + 44
        d.rounded_rectangle((CX - w/2, 1215, CX + w/2, 1267), 26, fill=(196, 48, 40), outline=(232, 196, 120), width=2)
        d.text((CX, 1242), zt, font=zf, fill=(250, 235, 210), anchor="mm")
    d.text((CX, 1075), "KAÇINI", font=F("Cinzel-700", 104), fill=GOLD, anchor="ms")
    d.text((CX, 1180), "BİLECEKSİN?", font=F("Cinzel-700", 80), fill=GOLD, anchor="ms")
    im.convert("RGB").save(out, quality=93)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("out"); ap.add_argument("--bolum", type=int)
    ap.add_argument("--format", default="", help="harf-bul = 'HARFLERDEN BUL' kapagi (script.json format alani da secer)")
    a = ap.parse_args()
    if a.format == "harf-bul" or json.load(open(a.script)).get("format") == "harf-bul":
        from harf_bul import kapak as hb_kapak; hb_kapak(a.script, a.out, a.bolum)
    else: kapak(a.script, a.out, a.bolum)
