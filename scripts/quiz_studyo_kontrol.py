"""Quiz Studyo otomatik kontrolleri. Kullanim: quiz_studyo_kontrol.py video.mp4 script.json [--bekci]
(video.mp4.times.json gerekir). Hata varsa cikis kodu 1. Kontroller:
 sure 55-125 sn, ses/goruntu kaymasi; her soru satiri ve cevap: ses var, ic durak <= 0.45 sn, Whisper metni satirla eslesir;
 soru sesinde cevap sizmasi yok; sayac bitmeden yesil/kirmizi cevap rengi yok; cevapta alt bilgi var;
 metin kutulari ust uste binmiyor, kabindan/ekrandan tasmiyor; emoji karelerinde renkli glif var (tofu yok)."""
import json, sys, os, re, difflib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quiz_kontrol import pcm, frame, max_pause
from quiz_studyo import norm, DOGRU, YANLIS, satirlar, CEVAP
from sayi_yazi import metni_yaziya

def oran(a, b): return difflib.SequenceMatcher(None, norm(metni_yaziya(a)).replace(" ", ""), norm(metni_yaziya(b)).replace(" ", "")).ratio()
def renk_say(fr, c, y0=740, y1=1730): return int((np.abs(fr[y0:y1] - c).sum(2) < 45).sum())
def kesis(a, b): return min(a[2], b[2]) - max(a[0], b[0]) > 2 and min(a[3], b[3]) - max(a[1], b[1]) > 2

def main(v, script, bekci=False):
    """f0: ilk soru satiri biterken; f1: sayacin %60i; f2: cevap tam acikken."""
    T = json.load(open(v + ".times.json")); S = json.load(open(script)); fmt = S["format"]; Q = S["sorular"]; h = []
    pr = lambda k: float(__import__("subprocess").run(["ffprobe", "-v", "error", "-select_streams", k, "-show_entries", "stream=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip())
    va, aa = pr("v:0"), pr("a:0")
    if abs(va - aa) > 0.15: h.append(f"kayma: video {va:.2f} / ses {aa:.2f}")
    if not 55 <= va <= 125: h.append(f"sure {va:.1f} sn (60-120 olmali)")
    try:
        from faster_whisper import WhisperModel; wm = WhisperModel("small", compute_type="int8")
    except Exception as e: wm = None; h.append(f"whisper yuklenemedi: {e}")
    yaz = lambda a: " ".join(s.text for s in wm.transcribe(a, language="tr")[0]) if wm else ""
    if bekci and wm:
        g = yaz(pcm(v, 0, T["sorular"][0]["bas"])); r = oran(g, S["sahneler"][0]["lines"][0]); print(f"BEKCI giris: {r:.2f} {g!r}")
        if r < 0.55: h.append(f"bekci giris: ses kartla eslesmiyor ({g!r})")
    for e in T["sorular"]:
        i = e["i"]; q = Q[i]; k = f"soru {i+1}"
        parc = [(f"{k} satir {j+1}", a, b, m) for j, (a, b, m) in enumerate(e["satir"])] + [(f"{k} cevap", e["cevap"], e["cevap_bit"], e["cevap_satir"])]
        for ad, a, b, m in parc:
            x = pcm(v, a, b)
            if len(x) == 0 or np.sqrt((x**2).mean()) < 0.005: h.append(f"{ad}: ses yok"); continue
            if max_pause(x) > 0.45: h.append(f"{ad}: {max_pause(x):.2f} sn ic durak")
            if wm:
                txt = yaz(x); r = oran(txt, m); print(f"{ad} [{a:.1f}-{b:.1f}] {r:.2f}: {txt}")
                if r < 0.55: h.append(f"{ad}: ses ekrandaki metinle uyusmuyor ({r:.2f}: {txt!r})")
                sz = [q["cevap"]] if fmt in ("bu-kim", "emoji-tarih") else [q["secenekler"][q["dogru"]]] if fmt == "kelime-eksik" else []
                if "cevap" not in ad:
                    for w in sz:
                        w0 = norm(w).split()[0]
                        if re.search(r"\b" + re.escape(w0[:max(4, len(w0) - 2)]), norm(txt)): h.append(f"{ad}: cevap sizmasi ({txt!r})")
        L = e["cevap"] - e["bekle"]; f1 = frame(v, e["bekle"] + L*0.6); f2 = frame(v, min(e["cevap_bit"], e["bit"] - 0.4))
        renk = YANLIS if fmt == "dogru-yanlis" and not q["dogru"] else DOGRU
        f0 = frame(v, e["satir"][0][1])  # soru karti tam gorunurken (emoji vb. kendi yesili olabilir: referans)
        once = renk_say(f1, DOGRU) + renk_say(f1, YANLIS) - renk_say(f0, DOGRU) - renk_say(f0, YANLIS); sonra = renk_say(f2, renk) - renk_say(f0, renk)
        if once > 400: h.append(f"{k}: sayac bitmeden cevap rengi gorunuyor ({once} piksel)")
        if sonra < 3000: h.append(f"{k}: cevap acilinca dogru/yanlis rengi yok ({sonra} piksel)")
        mut = np.array(T["mut"]); y0 = CEVAP[1] + 150
        alt = int((np.abs(f2[y0:CEVAP[3]] - mut).sum(2) < 60).sum()) - int((np.abs(f1[y0:CEVAP[3]] - mut).sum(2) < 60).sum())
        K = T["kutular"].get(str(i), [])
        if not any(n == "alt" for n, _, _ in K) or alt < 120: h.append(f"{k}: alt bilgi satiri gorunmuyor ({alt})")
        for n, b, kap in K:
            if not (20 <= b[0] and b[2] <= 1060 and 60 <= b[1] and b[3] <= 1790): h.append(f"{k}: '{n}' ekrandan tasiyor {b}")
            if kap and not (b[0] >= kap[0] - 3 and b[2] <= kap[2] + 3 and b[1] >= kap[1] - 6 and b[3] <= kap[3] + 6): h.append(f"{k}: '{n}' kutusundan tasiyor {b} / {kap}")
        for a in range(len(K)):
            for b in range(a):
                if kesis(K[a][1], K[b][1]): h.append(f"{k}: '{K[a][0]}' ile '{K[b][0]}' ust uste {K[a][1]} {K[b][1]}")
        if fmt == "emoji-tarih":
            for n, b, _ in K:
                if n != "emoji": continue
                bl = f2[b[1]:b[3], b[0]:b[2]]; zem = np.median(bl.reshape(-1, 3), 0); dol = (np.abs(bl - zem).sum(2) > 60).mean()
                if dol < 0.15: h.append(f"{k}: emoji bos/tofu olabilir {b} (doluluk {dol:.2f})")
    print(json.dumps({"sure": round(va, 1), "hatalar": h}, ensure_ascii=False, indent=1))
    return 1 if h else 0

if __name__ == "__main__": sys.exit(main(sys.argv[1], sys.argv[2], "--bekci" in sys.argv[3:]))
