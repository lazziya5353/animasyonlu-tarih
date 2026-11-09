"""Telifsiz fon müziği üretir: ağır yaylılar, alçak drone, kilit anlarda davul, istenirse kalp atışı ritmi.
music: {"booms":[...], "major_from": t, "heartbeat":[t0,t1], "mood":"epic"}"""
import numpy as np, soundfile as sf
from scipy.signal import butter, lfilter

SR = 44100
def lp(x, f, o=2): b, a = butter(o, f / (SR / 2)); return lfilter(b, a, x)
m2f = lambda m: 440 * 2 ** ((m - 69) / 12)

MINOR = [[50, 57, 62, 65], [46, 53, 58, 62], [53, 57, 60, 65], [48, 55, 60, 63]]
MAJOR = [50, 57, 62, 66, 69]

def make(out, dur, booms=(), major_from=None, heartbeat=None, seed=7):
    n = int(SR * dur); t = np.arange(n) / SR; rng = np.random.default_rng(seed); L = np.zeros(n); R = np.zeros(n)
    def strings(notes, t0, t1, g):
        i0, i1 = int(max(0, t0) * SR), min(n, int(t1 * SR)); m = i1 - i0
        if m <= 0: return
        x = np.arange(m) / SR; s = np.zeros(m)
        for q in notes:
            f = m2f(q)
            for dt in (-0.12, 0, 0.11):
                ph = rng.random() * 6.28; vib = 1 + 0.0025 * np.sin(2 * np.pi * 5.2 * x + ph)
                s += sum(np.sin(2 * np.pi * f * h * (1 + dt / 100) * x * vib + ph * h) / h ** 1.6 for h in range(1, 6))
        s = lp(s, 2200) / (len(notes) * 3); env = np.minimum(x / 1.6, 1) * np.minimum((m / SR - x) / 1.6, 1)
        L[i0:i1] += s * env * g; R[i0:i1] += np.roll(s, 300) * env * g
    seg = 8.6; k = 0; t0 = 0.0
    while t0 < dur:
        t1 = min(dur, t0 + seg)
        if major_from is not None and t0 >= major_from - 0.1: notes, g = MAJOR, 0.75
        else:
            notes, g = MINOR[k % 4], 0.5 + 0.03 * k
            if major_from is not None and t0 < major_from < t1: t1 = major_from
        strings(notes, t0 - 0.8, t1 + 0.8, min(g, 0.7)); t0 = t1; k += 1
    dr = np.sin(2 * np.pi * m2f(38) * t) * 0.12 + np.sin(2 * np.pi * m2f(26) * t) * 0.08; L += dr * np.minimum(t / 3, 1); R += dr * np.minimum(t / 3, 1)
    for tt in booms:
        m = int(3 * SR); x = np.arange(m) / SR
        b = np.sin(2 * np.pi * np.cumsum(55 + 40 * np.exp(-x * 6)) / SR) * np.exp(-x * 1.6) + lp(rng.standard_normal(m), 300) * np.exp(-x * 5) * 0.6
        i = int(tt * SR); kk = min(m, n - i)
        if kk > 0: L[i:i + kk] += b[:kk] * 0.9; R[i:i + kk] += b[:kk] * 0.9
    if heartbeat:
        for tt in np.arange(heartbeat[0], heartbeat[1], 1.25):
            m = int(0.5 * SR); x = np.arange(m) / SR; b = np.sin(2 * np.pi * 48 * x) * np.exp(-x * 9) * 0.45
            i = int(tt * SR); kk = min(m, n - i)
            if kk > 0: L[i:i + kk] += b[:kk]; R[i:i + kk] += b[:kk]
    f = np.ones(n); f[-int(3 * SR):] = np.linspace(1, 0, int(3 * SR)); f[:SR] = np.linspace(0, 1, SR)
    mus = np.stack([L * f, R * f], 1); mus /= np.abs(mus).max(); sf.write(out, mus, SR)
