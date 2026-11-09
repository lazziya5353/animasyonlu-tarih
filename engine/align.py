"""Seslendirmeyi cümlelere hizalar (sessizlik tespitiyle). Model indirmeye gerek yok.
Cümle sayısı N, konuşma parçası M: M > N ise en kısa boşluklar birleştirilir, M < N ise en uzun parça harf sayısına göre bölünür."""
import re, subprocess

def speech_chunks(wav, noise="-35dB", d=0.3):
    out = subprocess.run(["ffmpeg", "-i", wav, "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"], capture_output=True, text=True).stderr
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav]).decode())
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    chunks = []; cur = 0.0
    for s, e in zip(st, en + [dur] * (len(st) - len(en))):
        if s - cur > 0.15: chunks.append([cur, s])
        cur = e
    if dur - cur > 0.15: chunks.append([cur, dur])
    return chunks, dur

def _weight(t):
    import re as _re
    t = _re.sub(r"\d", "xxxx", t)  # rakamlar yüksek sesle daha uzun okunur
    return max(4, len(t))

def align(wav, sentences):
    """Konuşma parçalarını cümlelere, cümle uzunluğuyla orantılı süre beklentisine göre (dinamik programlama) dağıtır."""
    import math
    chunks, dur = speech_chunks(wav)
    N = len(sentences)
    while len(chunks) < N:
        lens = [c[1] - c[0] for c in chunks]; i = lens.index(max(lens)); a, b = chunks[i]; m = (a + b) / 2
        chunks[i:i + 1] = [[a, m], [m, b]]
    M = len(chunks); w = [_weight(s) for s in sentences]; speech = sum(c[1] - c[0] for c in chunks)
    exp = [speech * x / sum(w) for x in w]
    INF = float("inf"); best = [[INF] * (M + 1) for _ in range(N + 1)]; prev = [[0] * (M + 1) for _ in range(N + 1)]; best[0][0] = 0
    for i in range(1, N + 1):
        for j in range(i, M - (N - i) + 1):
            for k in range(i - 1, j):
                if best[i - 1][k] == INF: continue
                d = sum(chunks[x][1] - chunks[x][0] for x in range(k, j))
                cost = best[i - 1][k] + math.log(max(d, 0.05) / exp[i - 1]) ** 2
                if cost < best[i][j]: best[i][j] = cost; prev[i][j] = k
    out = []; j = M
    for i in range(N, 0, -1):
        k = prev[i][j]; out.append({"start": round(chunks[k][0], 2), "end": round(chunks[j - 1][1], 2), "text": sentences[i - 1]}); j = k
    return out[::-1], dur
