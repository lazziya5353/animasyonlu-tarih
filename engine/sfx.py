"""Hafif arka plan efekt sesleri (koddan üretilir, ses dosyası gerekmez). Anlatıcının altında, kısık.

project.json sahnesinde  "sfx": "tas" | "deprem" | "ruzgar" | "yangin"
  ya da {"tur": "tas", "bas": 0.0, "son": 1.0}  (sahnenin hangi bölümünde; 0..1)
"""
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

SR = 44100


def _f(x, lo=None, hi=None):
    if lo and hi: sos = butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
    elif hi: sos = butter(2, hi, "lowpass", fs=SR, output="sos")
    else: sos = butter(2, lo, "highpass", fs=SR, output="sos")
    return sosfilt(sos, x)


def _zarf(n, gir=.25, cik=.4):
    e = np.ones(n); a = min(n // 2, int(gir * SR)); b = min(n // 2, int(cik * SR))
    if a: e[:a] = np.linspace(0, 1, a)
    if b: e[-b:] *= np.linspace(1, 0, b)
    return e


def _tak(r, guc=1.0):
    """Tek taş vuruşu: kısa sert tık + tok gövde."""
    n = int(.16 * SR); t = np.arange(n) / SR
    tik = _f(r.standard_normal(n), float(r.uniform(700, 1400)), float(r.uniform(2400, 4200))) * np.exp(-t / .018)
    govde = np.sin(2 * np.pi * float(r.uniform(70, 120)) * t) * np.exp(-t / .05)
    return (tik * .7 + govde * .9) * guc


def _tas(n, r, sik=5.5):
    y = np.zeros(n + SR); t = 0.0
    while t < n / SR:
        v = _tak(r, float(r.uniform(.35, 1.0))); i = int(t * SR); y[i:i + len(v)] += v
        t += float(r.exponential(1 / sik)) + .05
    return y[:n] * _zarf(n, .15, .3)


def _deprem(n, r):
    g = _f(np.cumsum(r.standard_normal(n)) / 60, 28, 110); g /= (np.abs(g).max() + 1e-9)
    t = np.arange(n) / SR; titre = .75 + .25 * np.sin(2 * np.pi * 7 * t)
    return g * titre * _zarf(n, .5, .9) * 1.4 + _tas(n, r, 3) * .45


def _ruzgar(n, r):
    t = np.arange(n) / SR; g = r.standard_normal(n)
    y = _f(g, 180, 900) * (.6 + .4 * np.sin(2 * np.pi * .45 * t + 1)) + _f(g, 900, 2600) * (.25 + .25 * np.sin(2 * np.pi * .8 * t))
    return y * _zarf(n, .7, 1.0) * .8


def _yangin(n, r):
    y = _f(r.standard_normal(n), 120, 700) * .25; k = r.random(n) < 14 / SR
    return (y + _f(k * r.uniform(.5, 1, n) * 9, 1500)) * _zarf(n, .4, .6)

TUR = {"tas": _tas, "deprem": _deprem, "ruzgar": _ruzgar, "yangin": _yangin}


def make(yol, dur, olaylar, tohum=11):
    """olaylar: [(tur, bas_sn, son_sn)]"""
    r = np.random.default_rng(tohum); y = np.zeros(int(dur * SR) + SR)
    for tur, a, b in olaylar:
        if tur not in TUR or b - a < .3: continue
        n = int((b - a) * SR); i = int(max(0, a) * SR); v = TUR[tur](n, r); y[i:i + n] += v[:len(y) - i]
    m = np.abs(y).max()
    if m > 0: y = y / m * .8
    sf.write(yol, y[:int(dur * SR)].astype(np.float32), SR)
