"""Seslendirmeyi cümlelere hizalar (sessizlik tespitiyle). Model indirmeye gerek yok.

Yöntem: her cümlenin süresi OKUNAN metnin uzunluğuyla orantılı kabul edilir ("1905" değil "bin dokuz yüz beş").
Böylece her cümle sonunun beklenen zamanı bulunur; sesteki gerçek duraksamalar bu beklenen zamanlara
dinamik programlamayla eşlenir. Virgüldeki kısa duraksamalar cümle sonu sanılmaz (beklenen zamana uzak kalır),
duraksamasız cümle geçişleri ise beklenen zamana yerleştirilir."""
import re, subprocess

SUREC = "sn"


def silences(wav, noise="-35dB", d=0.15):
    out = subprocess.run(["ffmpeg", "-i", wav, "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"], capture_output=True, text=True).stderr
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav]).decode())
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    sil = [(s, e) for s, e in zip(st, en + [dur] * (len(st) - len(en)))]
    return sil, dur


def _w(t):
    """Okunan cümlenin konuşma 'ağırlığı': harf sayısı (+ rakam varsa kabaca okunuş uzunluğu)."""
    t = re.sub(r"\d", "xxxx", t)
    return max(4, len(re.sub(r"[^\wçğıöşüâîû]", "", t.lower())))


V = "aeıioöuüâîû"


def hece(t):
    """Okunan metindeki hece sayısı (Türkçede her ünlü bir hece). Kısaltmalar harf harf okunur."""
    n = sum(1 for ch in t.lower() if ch in V)
    for k in re.findall(r"\b[A-ZÇĞİÖŞÜ]{2,5}\b", t):
        n += max(0, len(k) - sum(1 for ch in k.lower() if ch in V))
    return max(1, n)


def hece_vuruslari(wav):
    """Sesteki hece çekirdekleri (enerji tepeleri) zamanları; 10 ms çözünürlük."""
    import numpy as np
    from scipy.signal import find_peaks
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar", "16000", "-af", "highpass=f=250,lowpass=f=2500",
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    fr = np.sqrt(np.convolve(x ** 2, np.ones(400) / 400, "same")[::160] + 1e-9)
    h = np.hanning(7); env = np.convolve(fr, h / h.sum(), "same"); db = 20 * np.log10(env + 1e-6)
    pk, _ = find_peaks(db, prominence=2, distance=8, height=db.max() - 35)
    return [p * 0.01 for p in pk]


def align(wav, sentences, spoken=None):
    """Önce konuşma tanımayla (Whisper) dener; olmazsa hece saati + duraksamalarla hizalar."""
    src = spoken if spoken and len(spoken) == len(sentences) else sentences
    try:
        words = asr_kelimeler(wav, " ".join(src))
        if words:
            _, dur = silences(wav)
            r = asr_align(sentences, src, words, dur)
            if r:
                print(f"hizalama: Whisper ({len(words)} kelime)", flush=True); return r, dur
            print("hizalama: Whisper sonucu tutarsız, hece yöntemine geçiliyor", flush=True)
    except Exception as e:
        print("hizalama: Whisper çalışmadı:", e, flush=True)
    print("hizalama: hece + duraksama", flush=True)
    return align_hece(wav, sentences, spoken)


def align_hece(wav, sentences, spoken=None):
    """sentences: ekranda görünecek cümleler; spoken: aynı sırayla okunan halleri (varsa süre tahmini bundan yapılır)."""
    sil, dur = silences(wav)
    N = len(sentences); src = spoken if spoken and len(spoken) == N else sentences
    w = [_w(s) for s in src]; W = sum(w)
    # konuşmanın başı/sonu (baştaki ve sondaki sessizlikleri at)
    t0 = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    t1 = sil[-1][0] if sil and sil[-1][1] >= dur - 0.05 else dur
    inner = [(s, e) for s, e in sil if s > t0 + 0.05 and e < t1 - 0.05]
    # beklenen sınırlar: "konuşma zamanı" (sessizlikler hariç) içinde harf oranıyla, sonra duvar saatine çevir
    speech = (t1 - t0) - sum(e - s for s, e in inner)

    def wall(x):  # konuşma-zamanı -> gerçek zaman
        t = t0; left = x
        for s, e in inner:
            if s - t >= left: return t + left
            left -= (s - t); t = e
        return min(t1, t + left)

    cum = 0; E = []
    try:
        pk = hece_vuruslari(wav); hs = [hece(s) for s in src]; H = sum(hs)
        if len(pk) < 0.5 * H: raise ValueError("hece tespiti zayıf")
        for k in range(N - 1):
            cum += hs[k]; f = cum / H * len(pk)  # hece saatindeki konum
            a = min(len(pk) - 1, int(f)); b = min(len(pk) - 1, a + 1)
            E.append(pk[a] + (pk[b] - pk[a]) * (f - int(f)) + 0.08)
    except Exception:
        for k in range(N - 1):
            cum += w[k]; E.append(wall(speech * cum / W))
    # DP: her sınır ya bir sessizliğe atanır ya da (sessizlik yoksa) beklenen zamana konur
    M = len(inner); K = N - 1; INF = float("inf")
    sig = 0.7
    NONE = 6.0  # sessizliksiz sınır cezası
    best = [[INF] * (M + 1) for _ in range(K + 1)]; back = [[None] * (M + 1) for _ in range(K + 1)]
    best[0] = [0.0] * (M + 1)  # best[k][j]: ilk k sınır, son kullanılan sessizlik indeksi < j
    for k in range(1, K + 1):
        for j in range(M + 1):
            # seçenek 1: k. sınır sessizliksiz
            if best[k - 1][j] + NONE < best[k][j]: best[k][j] = best[k - 1][j] + NONE; back[k][j] = ("yok", j)
            # seçenek 2: k. sınır j-1 numaralı sessizliğe
            if j >= 1:
                s, e = inner[j - 1]; mid = (s + e) / 2
                c = ((mid - E[k - 1]) / sig) ** 2 - min(e - s, 0.8) * 2.0
                for jj in range(j):
                    v = best[k - 1][jj] + c
                    if v < best[k][j]: best[k][j] = v; back[k][j] = ("ses", jj)
    j = min(range(M + 1), key=lambda x: best[K][x])
    bounds = [None] * K
    for k in range(K, 0, -1):
        typ, pj = back[k][j]
        if typ == "ses": bounds[k - 1] = inner[j - 1]; j = pj
        else:
            m = E[k - 1]; bounds[k - 1] = (m, m); j = pj
    # duraksamasız sınırlar: iki gerçek duraksama arasındaki parçayı cümlelerin hece sayısına göre böl
    try: hs
    except NameError: hs = w
    k = 0
    while k < K:
        if bounds[k][0] != bounds[k][1]: k += 1; continue
        a0 = k; 
        while k < K and bounds[k][0] == bounds[k][1]: k += 1
        left = t0 if a0 == 0 else bounds[a0 - 1][1]; right = t1 if k >= K else bounds[k][0]
        seg = hs[a0:k + 1]; tot = sum(seg); acc = 0
        for m in range(a0, k):
            acc += hs[m]; x = left + (right - left) * acc / tot; bounds[m] = (x, x)
    out = []; st = t0
    for i in range(N):
        en = bounds[i][0] if i < K else t1
        out.append({"start": round(st, 2), "end": round(max(en, st + 0.3), 2), "text": sentences[i]})
        if i < K: st = bounds[i][1]
    return out, dur


# ───────── Konuşma tanımayla (Whisper) kelime düzeyinde hizalama ─────────
_BIR = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_ON = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]


def sayi_yazi(n):
    n = int(n)
    if n == 0: return "sıfır"
    if n >= 1_000_000: return str(n)
    p = []
    if n >= 1000: b = n // 1000; p += ([] if b == 1 else sayi_yazi(b).split()) + ["bin"]; n %= 1000
    if n >= 100: y = n // 100; p += ([] if y == 1 else [_BIR[y]]) + ["yüz"]; n %= 100
    if n >= 10: p.append(_ON[n // 10]); n %= 10
    if n: p.append(_BIR[n])
    return " ".join(p)


def harfler(t):
    """Karşılaştırma için sade harf dizisi: küçük harf, rakamlar okunuşa çevrilmiş, boşluk/noktalama yok."""
    t = t.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"\d+", lambda m: sayi_yazi(m.group()), t)
    t = t.replace("â", "a").replace("î", "i").replace("û", "u")
    return re.sub(r"[^a-zçğıöşü]", "", t)


def asr_kelimeler(wav, ipucu=""):
    """faster-whisper ile kelime zamanları; kurulu değilse None."""
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return None
    import os
    m = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    segs, _ = m.transcribe(wav, language="tr", word_timestamps=True, beam_size=5, initial_prompt=ipucu[:600] or None)
    return [(w.word, w.start, w.end) for s in segs for w in (s.words or [])]


def asr_align(sentences, spoken, words, dur):
    """Okunan metni tanınan kelimelerle harf düzeyinde eşleştirip her cümlenin başlangıç/bitiş zamanını bulur."""
    import difflib
    asr = ""; owner = []
    for k, (w, a, b) in enumerate(words):
        h = harfler(w); asr += h; owner += [k] * len(h)
    exp = ""; bas = []
    for s in spoken:
        bas.append(len(exp)); exp += harfler(s)
    bas.append(len(exp))
    if not asr or not exp: return None
    sm = difflib.SequenceMatcher(None, exp, asr, autojunk=False)
    eş = {}
    for blk in sm.get_matching_blocks():
        for d in range(blk.size): eş[blk.a + d] = blk.b + d
    if len(eş) < 0.6 * len(exp): return None  # tanıma metinle yeterince örtüşmüyor
    out = []
    for i, s in enumerate(sentences):
        xs = [x for x in range(bas[i], bas[i + 1]) if x in eş]
        if len(xs) < max(2, 0.3 * (bas[i + 1] - bas[i])):
            out.append(None); continue
        k0, k1 = owner[eş[xs[0]]], owner[eş[xs[-1]]]
        # ilk/son harfler tanınmadıysa eksik kısmı ortalama harf süresiyle tahmin et
        hs = max(0.04, min(0.09, (words[k1][2] - words[k0][1]) / max(1, eş[xs[-1]] - eş[xs[0]] + 1)))
        out.append([words[k0][1], words[k1][2], (xs[0] - bas[i]) * hs, (bas[i + 1] - 1 - xs[-1]) * hs])
    # eşleşmeyen cümleleri komşularının arasına yerleştir, sırayı ve çakışmaları düzelt
    for i in range(len(out)):
        if out[i] is None:
            a = out[i - 1][1] if i and out[i - 1] else 0.0
            b = next((o[0] for o in out[i + 1:] if o), dur)
            out[i] = [a + 0.05, max(a + 0.35, b - 0.05), 0.0, 0.0]
    for i in range(1, len(out)):
        if out[i][0] < out[i - 1][0] + 0.2: return None  # tanınan zamanlar bile sırasız: güvenme
    for i in range(len(out)):  # tanınmayan baş/son harfler için payı ekle, komşuya taşmadan
        lo = out[i - 1][1] if i else 0.0
        hi = out[i + 1][0] if i + 1 < len(out) else dur
        out[i] = [max(lo, out[i][0] - out[i][2]), min(hi, out[i][1] + out[i][3])]
    for i in range(1, len(out)):
        out[i - 1][1] = min(out[i - 1][1], out[i][0] - 0.03)
    return [{"start": round(a, 2), "end": round(max(b, a + 0.3), 2), "text": t} for (a, b), t in zip(out, sentences)]
