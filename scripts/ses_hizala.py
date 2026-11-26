"""Metin tabanli ses bolme: Whisper kelime zamanlari + monoton bulanik hizalama (Needleman-Wunsch).

satir_sinirlari(au, SR, satirlar) -> [0, c1, ..., tot] (satir sayisi + 1 kesim noktasi) ya da
guven dusukse None (cagiran eski sessizlik yontemine doner). Kesimler, ardisik iki satir
arasindaki en dusuk enerjili noktaya oturtulur. Dis ses (ElevenLabs) soru icinde, sayi ve
tarihlerde durakladigi icin sessizlik tabanli bolme kayiyordu."""
import os, re, sys, difflib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kontrol import kelimeler

# harf adlari (Whisper "Ş harfi"ni "şeyh harfi", "C"yi "ce/cee" vb. duyabiliyor)
HARF = {"a": "a", "b": "be", "c": "ce", "ç": "çe", "d": "de", "e": "e", "f": "fe", "g": "ge", "ğ": "yumuşakge",
        "h": "he", "ı": "ı", "i": "i", "j": "je", "k": "ke", "l": "le", "m": "me", "n": "ne", "o": "o", "ö": "ö",
        "p": "pe", "r": "re", "s": "se", "ş": "şe", "t": "te", "u": "u", "ü": "ü", "v": "ve", "y": "ye", "z": "ze"}
FON = str.maketrans({"ğ": "g", "ı": "i", "ö": "o", "ü": "u", "ş": "s", "ç": "c", "x": "k", "w": "v", "q": "k"})

def toks(t):
    out = []
    for w in kelimeler(t):
        out.append(HARF.get(w, w) if len(w) == 1 else w)
    return out

def benzer(a, b):
    if a == b: return 1.0
    fa, fb = a.translate(FON), b.translate(FON)
    if fa == fb: return 0.95
    r = difflib.SequenceMatcher(None, fa, fb).ratio()
    if min(len(fa), len(fb)) >= 4 and (fa.startswith(fb[:4]) or fb.startswith(fa[:4])): r = max(r, 0.75)  # ek farki
    return r

def hizala(S, W):
    """S: metin tokenlari, W: duyulan tokenlar. Monoton global hizalama; S[i] -> W[j] eslesmeleri."""
    n, m = len(S), len(W); GAP = -0.45
    D = np.full((n + 1, m + 1), -1e9, np.float32); B = np.zeros((n + 1, m + 1), np.int8)
    D[0, :] = np.arange(m + 1)*GAP; D[:, 0] = np.arange(n + 1)*GAP; B[0, 1:] = 2; B[1:, 0] = 1
    for i in range(1, n + 1):
        si = S[i-1]
        sc = np.array([benzer(si, w) for w in W], np.float32)
        sc = np.where(sc >= 0.6, sc*2 - 0.6, sc - 1.0)  # >=0.6 odul, altinda ceza
        for j in range(1, m + 1):
            a = D[i-1, j-1] + sc[j-1]; b = D[i-1, j] + GAP; c = D[i, j-1] + GAP
            if a >= b and a >= c: D[i, j] = a; B[i, j] = 0
            elif b >= c: D[i, j] = b; B[i, j] = 1
            else: D[i, j] = c; B[i, j] = 2
    M = {}; i, j = n, m
    while i > 0 and j > 0:
        if B[i, j] == 0:
            if benzer(S[i-1], W[j-1]) >= 0.6: M[i-1] = j-1
            i -= 1; j -= 1
        elif B[i, j] == 1: i -= 1
        else: j -= 1
    return M

def transkript(au, SR):
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), compute_type="int8")
    a16 = au[::SR//16000].astype(np.float32) if SR % 16000 == 0 else au.astype(np.float32)
    segs, _ = m.transcribe(a16, language="tr", word_timestamps=True, vad_filter=False, beam_size=5,
                           condition_on_previous_text=False)
    ww = []
    for s in segs:
        for w in s.words:
            for t in toks(w.word): ww.append((w.start, w.end, t))
    return ww

def satir_sinirlari(au, SR, satirlar, ww=None, rapor=True):
    if ww is None: ww = transkript(au, SR)
    sw = [(k, t) for k, s in enumerate(satirlar) for t in toks(s)]
    M = hizala([t for _, t in sw], [t for _, _, t in ww])
    K = len(satirlar); tot = len(au)/SR
    ilk, son, say = {}, {}, [0]*K; top = [0]*K
    for i, (k, _) in enumerate(sw):
        top[k] += 1
        if i in M: ilk.setdefault(k, ww[M[i]][0]); son[k] = ww[M[i]][1]; say[k] += 1
    oran = sum(say)/max(1, len(sw))
    zayif = [k for k in range(K) if say[k] == 0 or (top[k] >= 3 and say[k]/top[k] < 0.4)]
    if rapor:
        print(f"hizalama: {sum(say)}/{len(sw)} kelime eslesti ({oran:.0%}); zayif satirlar: {zayif}")
        for k in range(K):
            if k in ilk:
                duy = " ".join(t for a, b, t in ww if a >= ilk[k] - 0.01 and b <= son[k] + 0.01)
                print(f"  [{k:2d}] {ilk[k]:7.2f}-{son[k]:7.2f} {say[k]}/{top[k]} | METIN: {' '.join(t for kk, t in sw if kk == k)}\n{'':28}| SES  : {duy}")
    if oran < 0.6 or len(zayif) > max(1, K//10): return None
    for k in range(K):  # eslesmeyen satir: komsulardan tahmin
        if k not in ilk:
            p = max([j for j in range(k) if j in son], default=None); nx = min([j for j in range(k+1, K) if j in ilk], default=None)
            t0 = son[p] if p is not None else 0.0; t1 = ilk[nx] if nx is not None else tot
            ilk[k], son[k] = t0 + 0.05, max(t0 + 0.1, t1 - 0.05); print(f"uyari: satir {k} eslesmedi, tahmin")
    for k in range(1, K):
        if ilk[k] < son[k-1] - 0.05: print(f"uyari: satir {k-1}/{k} ust uste ({son[k-1]:.2f} > {ilk[k]:.2f})")
    fr = np.sqrt((au[:len(au)//480*480].reshape(-1, 480)**2).mean(1))  # 10 ms (SR=48k)
    fs = 480/SR; sinir = [0.0]
    for k in range(K - 1):
        a, b = min(son[k], ilk[k+1]) - 0.1, max(son[k], ilk[k+1]) + 0.1
        a = max(a, sinir[-1] + 0.05); b = max(b, a + 0.02)
        i0, i1 = int(a/fs), max(int(b/fs), int(a/fs) + 1); w = fr[i0:i1]
        if len(w) == 0: sinir.append((a + b)/2); continue
        thr = max(10**(-42/20), float(w.min())*1.5); q = w <= thr; best = (0, 0, 1); j = 0
        while j < len(q):  # pencere icindeki en uzun dusuk enerjili bolgenin ortasi
            if q[j]:
                e = j
                while e < len(q) and q[e]: e += 1
                if e - j > best[0]: best = (e - j, j, e)
                j = e
            else: j += 1
        sinir.append((i0 + (best[1] + best[2])/2)*fs)
    sinir.append(tot); return sinir

if __name__ == "__main__":  # test: python ses_hizala.py script.json ses.wav [tempo]
    import json, subprocess
    SJ = json.load(open(sys.argv[1])); S = [" ".join(x["lines"]) for x in SJ["sahneler"]]
    tempo = sys.argv[3] if len(sys.argv) > 3 else "1.08"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[2], "-af", f"atempo={tempo}", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    au = np.frombuffer(raw, np.float32); s = satir_sinirlari(au, 48000, S)
    print("SONUC:", "dusuk guven -> sessizlik yontemi" if s is None else f"{len(s)-1} satir, kesimler {[round(x, 2) for x in s]}")
