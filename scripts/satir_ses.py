#!/usr/bin/env python3
"""Satir satir Gemini TTS (Her Harfe, ses_modu=satir). Sessizlik tespiti YOK.
  satir_ses.py <slug>
Her sahne satiri icin ayri istek; sonuc projects/<slug>/audio/<hash>.wav olarak repoda onbelleklenir
(ayni ses + metin tekrar uretilmez). Satirlar 0.25 sn arayla birlestirilir -> ses.wav, sinirlar -> segmentler.json.
"""
import base64, hashlib, json, os, subprocess, sys, time, urllib.request, urllib.error
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 24000
MODELLER = [os.environ.get("GEMINI_TTS_MODEL") or "gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"]
STIL = "Türkçe, net ve enerjik bir quiz sunucusu gibi, normal konuşma hızında oku: "
STIL_GIRIS = "Türkçe, neşeli, enerjik ve meydan okuyan bir quiz sunucusu gibi oku: "

def tts(metin, ses, stil):
    key = os.environ["GEMINI_API_KEY"]; son = ""
    body = {"contents": [{"parts": [{"text": stil + metin}]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": ses}}}}}
    for deneme in range(6):
        for m in MODELLER:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", data=json.dumps(body).encode(),
                                         headers={"content-type": "application/json", "x-goog-api-key": key})
            try: r = json.load(urllib.request.urlopen(req, timeout=180))
            except urllib.error.HTTPError as e:
                son = f"{m} {e.code}: {e.read().decode()[:200]}"
                if e.code in (429, 500, 503, 404): continue
                sys.exit(f"HATA: Gemini ses üretmedi ({son})")
            except Exception as e: son = f"{m}: {e}"; continue
            for c in r.get("candidates", []):
                for p in c.get("content", {}).get("parts", []):
                    if "inlineData" in p: return np.frombuffer(base64.b64decode(p["inlineData"]["data"]), "<i2").astype(np.float32) / 32768
            son = f"{m}: ses dönmedi"
        print("bekleniyor:", son); time.sleep(20 * (deneme + 1))
    sys.exit(f"HATA: Gemini ses üretmedi ({son})")

def kirp(a):
    """bas/son sessizligi kirp (10 ms kare, -40 dB); 40 ms on, 80 ms son pay"""
    f = np.sqrt((a[:len(a)//240*240].reshape(-1, 240)**2).mean(1)); v = np.where(f > 10**(-40/20))[0]
    if not len(v): return a
    return a[max(0, v[0]*240 - int(0.04*SR)):min(len(a), (v[-1]+1)*240 + int(0.08*SR))]

def ic_durak(a, maks=0.3):
    """satir ICI uzun duraklari (orn. 'N harfi.' sonrasi) 0.25 sn'ye indir; satirlar zaten ayri, bolme yapilmaz"""
    f = np.sqrt((a[:len(a)//240*240].reshape(-1, 240)**2).mean(1)) < 10**(-42/20); out, j, son = [], 0, 0
    while j < len(f):
        if f[j]:
            k = j
            while k < len(f) and f[k]: k += 1
            if (k - j)*0.01 > maks and j > 0 and k < len(f): out += [a[son:j*240 + 3000]]; son = k*240 - 3000
            j = k
        else: j += 1
    return np.concatenate(out + [a[son:]])

def main(slug):
    P = os.path.join(ROOT, "projects", slug); S = json.load(open(os.path.join(P, "script.json")))
    ses = S.get("ses") or os.environ.get("GEMINI_VOICE") or "Charon"
    os.makedirs(os.path.join(P, "audio"), exist_ok=True)
    parcalar, seg, t, yeni = [], [], 0.0, 0
    for i, sh in enumerate(S["sahneler"]):
        satir = sh["lines"][0].strip(); stil = STIL_GIRIS if i == 0 else STIL
        h = hashlib.sha256(f"{ses}|{stil}|{satir}".encode()).hexdigest()[:20]; yol = os.path.join(P, "audio", h + ".wav")
        if os.path.exists(yol):
            a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout, "<i2").astype(np.float32) / 32768
        else:
            a = kirp(tts(satir, ses, stil)); yeni += 1
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", yol], input=(np.clip(a, -1, 1)*32767).astype("<i2").tobytes(), check=True)
        a = ic_durak(a)
        print(f"{i+1}/{len(S['sahneler'])} {len(a)/SR:.2f} sn · {satir[:60]}")
        seg.append({"satir": satir, "bas": round(t, 3), "bit": round(t + len(a)/SR, 3)})
        parcalar += [a, np.zeros(int(0.25*SR), np.float32)]; t += len(a)/SR + 0.25
    A = np.concatenate(parcalar)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", os.path.join(P, "ses.wav")], input=(np.clip(A, -1, 1)*32767).astype("<i2").tobytes(), check=True)
    json.dump({"kaynak": "gemini-satir", "ses": ses, "segmentler": seg}, open(os.path.join(P, "segmentler.json"), "w"), ensure_ascii=False, indent=1)
    print(f"ses.wav {t:.1f} sn, {len(seg)} satır ({yeni} yeni istek)")

if __name__ == "__main__": main(sys.argv[1])
