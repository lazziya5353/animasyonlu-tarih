"""Quiz Studyo sesi (Gemini TTS, ucretsiz). Kullanim: quiz_studyo_ses.py <slug>
Ders: Gemini TTS uzun, cok satirli metni bazen ilk cumlede kesiyor (yili-tahmin-1: 90 kelimelik metin 4 sn ses).
Bu yuzden once tek parca denenir, sure beklenenin %60'indan kisaysa metin ~6 satirlik parcalara bolunur,
her parca ayri uretilip sure kontrol edilir (en cok 3 deneme) ve 0.45 sn araliklarla birlestirilir."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_assets import voice, ses_metni_dogrula, GeminiError
from common import ROOT

def sure(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout or 0)
def bekle(t): return len(t)/16.5  # ~16.5 karakter/sn (atempo 1.1 sonrasi), alt sinir icin

def uret(metin, out, stil, deneme=3):
    for k in range(deneme):
        try:
            if voice(metin, out, stil) and sure(out) >= 0.6*bekle(metin): return True
            print(f"  kisa ses: {sure(out):.1f} sn / beklenen ~{bekle(metin):.1f} sn (deneme {k+1})")
        except GeminiError as e: print("  TTS hatasi:", e)
    return False

def main(slug):
    d = os.path.join(ROOT, "projects", slug); S = json.load(open(os.path.join(d, "script.json"))); ses_metni_dogrula(S, slug)
    out = os.path.join(d, "ses.wav"); satir = S["seslendirme_metni"].split("\n"); stil = S.get("ses_stil")
    if uret(S["seslendirme_metni"], out, stil, 1): print(f"ses tek parca: {sure(out):.1f} sn"); return
    parca = [satir[i:i+6] for i in range(0, len(satir), 6)]; wavs = []
    for j, p in enumerate(parca):
        w = os.path.join(d, f".parca{j}.wav")
        if not uret("\n".join(p), w, stil): sys.exit(f"HATA: {j+1}. ses parcasi uretilemedi")
        wavs.append(w); print(f"parca {j+1}/{len(parca)}: {sure(w):.1f} sn")
    sess = os.path.join(d, ".sessiz.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.45", sess], check=True)
    lst = os.path.join(d, ".liste.txt"); open(lst, "w").write("".join(f"file '{os.path.abspath(w)}'\nfile '{os.path.abspath(sess)}'\n" for w in wavs))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ar", "24000", "-ac", "1", out], check=True)
    for f in wavs + [sess, lst]: os.remove(f)
    print(f"ses {len(parca)} parcadan: {sure(out):.1f} sn")

if __name__ == "__main__": main(sys.argv[1])
