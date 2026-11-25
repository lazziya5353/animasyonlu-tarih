"""Harflerden Bul otomatik kontrolleri. Kullanim: harf_bul_kontrol.py video.mp4 script.json [--bekci]
(video.mp4.times.json + video.mp4.kutular.json gerekir). Hata varsa cikis kodu 1.
- maske: her acik_harfler cevapla ayni uzunluk/bosluk/tire, acik harfler cevapla ayni, en az bir harf kapali
- ses: her soru/cevap klibinde ses var, 0.4 sn'den uzun ic durak yok; ses/goruntu kaymasi yok; sure 75-115 sn
- sizma: soru klibinin yazisinda cevap (ya da koku) gecmiyor; soru sesi ekrandaki soruyla, cevap sesi cevapla uyusuyor
- bekci (--bekci): giris + 1., 6., 12. soru Whisper ile kart metnine bulanik eslesmeli (oran >= 0.6); Whisper yoksa HATA
- yerlesim: kayitli karelerde metin/kutu/yay kutulari birbirine degmiyor ve guvenli genislikte
- gorsel: cevap karesinde kutular yesil, alt bilgi satiri gorunuyor"""
import json, sys, re, os, difflib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quiz_kontrol import pcm, frame, max_pause, norm
from harf_bul import maske_coz, up

def maske_kontrol(S):
    h = []
    for k, q in enumerate(S["sorular"]):
        try: maske_coz(q)
        except ValueError as e: h.append(f"soru {k+1} maske: {e}")
    print(f"maske: {len(S['sorular'])} soru, {len(h)} sorun"); return h

def yerlesim(v):
    if not os.path.exists(v + ".kutular.json"): return ["yerlesim: kutular.json yok"]
    K = json.load(open(v + ".kutular.json")); x0s, x1s = K["guvenli"]; h = []
    for ad, bx in K["kareler"].items():
        for i, a in enumerate(bx):
            if a[0] < x0s - 2 or a[2] > x1s + 2 or a[1] < 0 or a[3] > 1920: h.append(f"kare {ad}: kutu guvenli alan disinda {a}")
            for b in bx[i+1:]:
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]: h.append(f"kare {ad}: ust uste binme {a} / {b}")
    print(f"yerlesim: {len(K['kareler'])} kare kontrol edildi, {len(h)} sorun"); return h

def bekci(v, S, T, wm):
    from kontrol import kelimeler
    if wm is None: return ["bekci: whisper yuklenemedi, ses dogrulanamadi"]
    h = []; sah = S["sahneler"]; parca = [("giris", 0.0, T[0]["soru_t"], sah[0]["lines"][0])]
    for k in (1, 6, 12):
        if k <= len(T): x = T[k-1]; parca.append((f"soru {k}", x["soru_t"], x["soru_bit"], sah[2*k-1]["lines"][0]))
    for ad, t0, t1, metin in parca:
        txt = " ".join(s.text for s in wm.transcribe(pcm(v, t0, t1), language="tr")[0])
        a, b = " ".join(kelimeler(txt)), " ".join(kelimeler(metin)); r = difflib.SequenceMatcher(None, a, b).ratio()
        print(f"BEKCI {ad}: oran {r:.2f} {'ESLESTI' if r >= 0.6 else 'ESLESMEDI'}\n  ses : {a}\n  kart: {b}")
        if r < 0.6: h.append(f"bekci {ad}: ses kartla eslesmiyor (oran {r:.2f}: {a!r})")
    return h

def main(v, script, bekci_ac=False):
    T = json.load(open(v + ".times.json")); S = json.load(open(script)); Q = S["sorular"]; hata = maske_kontrol(S)
    pr = lambda k: __import__("subprocess").run(["ffprobe", "-v", "error", "-select_streams", k, "-show_entries", "stream=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip()
    va, aa = float(pr("v:0")), float(pr("a:0"))
    if abs(va - aa) > 0.1: hata.append(f"kayma: video {va:.2f} / ses {aa:.2f}")
    if not 75 <= va <= 115: hata.append(f"sure {va:.1f} sn (~90 beklenir)")
    hata += yerlesim(v)
    try:
        from faster_whisper import WhisperModel; wm = WhisperModel("small", compute_type="int8")
    except Exception as e: wm = None; print("uyari: whisper yok", e)
    if bekci_ac: hata += bekci(v, S, T, wm)
    for x, q in zip(T, Q):
        k = x["no"]; cev = norm(up(q["cevap"]).replace("-", " "))
        for tip, t0, t1 in (("soru", x["soru_t"], x["soru_bit"]), ("cevap", x["cevap_t"], x["cevap_bit"])):
            a = pcm(v, t0, t1)
            if len(a) == 0 or np.sqrt((a**2).mean()) < 0.005: hata.append(f"{k} {tip}: ses yok"); continue
            if max_pause(a) > 0.4: hata.append(f"{k} {tip}: {max_pause(a):.2f} sn ic durak")
            if not wm: continue
            txt = norm(" ".join(s.text for s in wm.transcribe(a, language="tr")[0])); print(f"{k} {tip} [{t0:.1f}-{t1:.1f}]: {txt}")
            if tip == "soru":
                for w in cev.split():
                    if len(w) >= 3 and re.search(r"\b" + w[:max(3, len(w)-2)], txt) and w[:max(3, len(w)-2)] not in norm(q["soru"]):
                        hata.append(f"{k} soru: cevap sizmasi ({w!r} -> {txt!r})")
                bek = [y[:4] for y in norm(q["soru"]).split() if len(y) > 3]
                if bek and sum(y in txt for y in bek)/len(bek) < 0.5: hata.append(f"{k} soru: ses ekrandaki soruyla uyusmuyor ({txt!r})")
            elif cev.split()[0][:3] not in txt and difflib.SequenceMatcher(None, cev.replace(" ", ""), txt.replace(" ", "")).ratio() < 0.6:
                hata.append(f"{k} cevap: ses ekrandaki cevapla uyusmuyor ({txt!r})")
        fr = frame(v, x["cevap_bit"] + 0.25)
        yes = (np.abs(fr - [40, 120, 70]).sum(2) < 30)[850:1350].sum()
        krem = lambda f: (np.abs(f - [225, 210, 190]).sum(2) < 40)[1150:1450].sum()
        if yes < 3000: hata.append(f"{k}: cevap kutulari yesil degil ({yes})")
        if krem(fr) - krem(frame(v, x["soru_bit"] + 1.0)) < 150: hata.append(f"{k}: alt bilgi satiri gorunmuyor")
    print(json.dumps({"sure": round(va, 1), "hatalar": hata}, ensure_ascii=False, indent=1))
    return 1 if hata else 0

if __name__ == "__main__": sys.exit(main(sys.argv[1], sys.argv[2], "--bekci" in sys.argv[3:]))
