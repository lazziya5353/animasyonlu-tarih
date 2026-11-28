"""Harf quiz otomatik kontrolleri. Kullanim: quiz_kontrol.py video.mp4 script.json  (video.mp4.times.json gerekir)
Ses var mi, soru klibinde cevap sizmasi, 0.4 sn'den uzun ic durak, ses/goruntu kaymasi, alt bilgi satiri, sure ~3:00. Hata varsa cikis kodu 1."""
import json, subprocess, sys, re
import numpy as np
from PIL import Image

def pcm(v, t0, t1, sr=16000):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", v, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(r, np.float32)

def frame(v, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", v, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(r, np.uint8).reshape(1920, 1080, 3).astype(int)

def max_pause(a, sr=16000):
    f = np.sqrt((a[:len(a)//160*160].reshape(-1, 160)**2).mean(1)); s = f < 10**(-42/20)
    nz = np.where(~s)[0]
    if len(nz) == 0: return 99
    s = s[nz[0]:nz[-1]+1]; best = cur = 0
    for x in s: cur = cur + 1 if x else 0; best = max(best, cur)
    return best*0.01

def norm(t): return re.sub(r"[^a-zçğıöşü ]", "", t.replace("İ", "i").replace("I", "ı").lower().translate(str.maketrans("âîûÂÎÛ", "aiuaiu")))

def bekci(v, S, T, wm, seg=False):
    """Ses bekcisi: giris + 1., 11. ve 22. soru kartinin sesi Whisper ile yaziya dokulur; her biri o kartin
    script.json'daki metniyle bulanik eslesmeli (baska projenin sesi / kayma yakalanir). Whisper yoksa HATA."""
    import difflib, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from kontrol import kelimeler
    if wm is None: return ["bekci: whisper yuklenemedi, ses dogrulanamadi"]
    h = []; parca = [("giris", 0.0, T[0]["soru_t"], S["sahneler"][0]["lines"][0])]
    if seg and T[0]["soru_t"] < 0.8: parca = []  # dis seste giris kaydedilmemis (bos segment)
    # segment haritasi varsa: HER sorunun sesi yalnizca kendi satiriyla karsilastirilir (kayma olamaz, ornekleme gereksiz)
    for k in (range(1, len(T) + 1) if seg else (1, 11, 22)):
        if k <= len(T): x = T[k-1]; parca.append((f"soru {k} ({x['harf']})", x["soru_t"], x["soru_bit"], S["sahneler"][1+2*(k-1)]["lines"][0]))
        else: h.append(f"bekci: {k}. soru yok")
    for ad, t0, t1, metin in parca:
        txt = " ".join(s.text for s in wm.transcribe(pcm(v, t0, t1), language="tr")[0])
        a, b = " ".join(kelimeler(txt)), " ".join(kelimeler(metin))
        r = difflib.SequenceMatcher(None, a, b).ratio(); ok = r >= 0.6
        print(f"BEKCI {ad}: oran {r:.2f} {'ESLESTI' if ok else 'ESLESMEDI'}\n  ses : {a}\n  kart: {b}")
        if not ok: h.append(f"bekci {ad}: ses kartla eslesmiyor (oran {r:.2f}: {a!r})")
    return h

def yerlesim(v):
    """Metin kutusu (soru/cevap/alt bilgi) hicbir harf balonuna degmemeli; filigran cevap metnine binmemeli."""
    import os
    if not os.path.exists(v + ".kutular.json"): return ["yerlesim: kutular.json yok"]
    K = json.load(open(v + ".kutular.json")); h = []
    for L, k in K["kartlar"].items():
        for x0, y0, x1, y1 in k["metin"]:
            for bx, by, r in K["balonlar"]:
                dx = max(x0 - bx, 0, bx - x1); dy = max(y0 - by, 0, by - y1)
                if dx*dx + dy*dy < (r + 4)**2: h.append(f"{L}: metin kutusu harf balonuna degiyor ({x0},{y0},{x1},{y1})")
    print(f"yerlesim: {len(K['kartlar'])} kart kontrol edildi, {len(h)} sorun")
    return h

def main(v, script, bekci_ac=False):
    T = json.load(open(v + ".times.json")); S = json.load(open(script)); hata = []
    qs = {x["harf"]: S["sahneler"][1+2*i]["lines"][0].split(" harfi.", 1)[1] for i, x in enumerate(T)}
    ans = {x["harf"]: S["sahneler"][2+2*i]["lines"][0].rstrip(".") for i, x in enumerate(T)}
    pr = lambda k: subprocess.run(["ffprobe", "-v", "error", "-select_streams", k, "-show_entries", "stream=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip()
    va, aa = float(pr("v:0")), float(pr("a:0"))
    if abs(va - aa) > 0.1: hata.append(f"kayma: video {va:.2f} / ses {aa:.2f}")
    import os; seg = os.path.exists(os.path.join(os.path.dirname(os.path.abspath(script)), "segmentler.json"))
    if seg:
        if va > 177.5: hata.append(f"sure {va:.1f} sn (en fazla 177 sn / 2:57)")
    elif not 150 <= va <= 210: hata.append(f"sure {va:.1f} sn (~180 beklenir)")
    try:
        from faster_whisper import WhisperModel; wm = WhisperModel("small", compute_type="int8")
    except Exception as e: wm = None; print("uyari: whisper yok, sizma kontrolu atlandi", e)
    hata += yerlesim(v)
    if bekci_ac: hata += bekci(v, S, T, wm, seg)
    for x in T:
        L = x["harf"]
        for tip, t0, t1 in (("soru", x["soru_t"], x["soru_bit"]), ("cevap", x["cevap_t"], x["cevap_bit"])):
            a = pcm(v, t0, t1)
            if len(a) == 0 or np.sqrt((a**2).mean()) < 0.005: hata.append(f"{L} {tip}: ses yok")
            elif max_pause(a) > 0.4: hata.append(f"{L} {tip}: {max_pause(a):.2f} sn ic durak")
            if wm and len(a):
                txt = norm(" ".join(s.text for s in wm.transcribe(a, language="tr")[0]))
                w = norm(ans[L]).split()[0]; print(f"{L} {tip} [{t0:.1f}-{t1:.1f}]: {txt}")
                if tip == "soru":
                    govde = re.sub(r"^.*?\bharf[iı]\b", "", txt, count=1)  # "X harfi" duyurusu harf adiyla karisabilir (S -> seyh)
                    if re.search(r"\b" + w[:max(4, len(w)-2)], govde) and not re.search(r"\b" + w[:max(4, len(w)-2)], norm(qs[L])): hata.append(f"{L} soru: cevap sizmasi ({txt!r})")
                    bek = [x[:4] for x in norm(qs[L]).split() if len(x) > 3]
                    if bek and sum(x in txt for x in bek) / len(bek) < 0.5: hata.append(f"{L} soru: ses ekrandaki soruyla uyusmuyor ({txt!r})")
                elif (fon := lambda z: z.replace("x", "ks").replace("w", "v").replace("q", "k")) and fon(w)[:3] not in fon(txt) and __import__("difflib").SequenceMatcher(None, fon(norm(ans[L])).replace(" ", ""), fon(txt).replace(" ", "")).ratio() < 0.6: hata.append(f"{L} cevap: ses ekrandaki cevapla uyusmuyor ({txt!r})")
        # alt bilgi: cevap karesinde, soru karesine gore yeni acik-krem piksel satiri (225,210,190)
        def krem(fr): return (np.abs(fr - [225, 210, 190]).sum(2) < 40)[1150:1750].sum()
        if krem(frame(v, x["cevap_bit"] + 0.3)) - krem(frame(v, x["soru_bit"] + 1.0)) < 150: hata.append(f"{L}: alt bilgi satiri gorunmuyor")
    print(json.dumps({"sure": round(va, 1), "hatalar": hata}, ensure_ascii=False, indent=1))
    return 1 if hata else 0

if __name__ == "__main__": sys.exit(main(sys.argv[1], sys.argv[2], "--bekci" in sys.argv[3:]))
