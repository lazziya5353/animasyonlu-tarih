"""Sesteki uzun duraklamaları kısaltır: python scripts/trim_pauses.py giris.wav cikis.wav 0.4"""
import sys, re, subprocess, numpy as np, soundfile as sf
src, dst, keep = sys.argv[1], sys.argv[2], float(sys.argv[3])
a, sr = sf.read(src, dtype="float32")
log = subprocess.run(["ffmpeg","-i",src,"-af","silencedetect=n=-35dB:d=0.3","-f","null","-"],capture_output=True,text=True).stderr
st=[float(x) for x in re.findall(r"silence_start: ([\d.]+)",log)]; en=[float(x) for x in re.findall(r"silence_end: ([\d.]+)",log)]
out=[]; pos=0
for s,e in zip(st,en):
    if e-s <= keep: continue
    lead = 0.25 if s < 0.05 else keep/2  # baştaki sessizlik kısa
    cut0=int((s+ (keep/2 if s>=0.05 else 0))*sr); cut1=int((e-keep/2)*sr)
    if s < 0.05: cut0=0; cut1=int((e-0.15)*sr)
    out.append(a[pos:cut0]); pos=cut1
out.append(a[pos:])
sf.write(dst, np.concatenate(out), sr)
