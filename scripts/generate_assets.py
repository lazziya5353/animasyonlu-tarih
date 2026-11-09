"""Görsel yönetmeni: script.json'daki promptlarla Gemini'ye görselleri, seslendirme metniyle sesi ürettirir.
GEMINI_API_KEY yoksa hiçbir şey yapmaz (görsel/ses elle yüklenir).
  python scripts/generate_assets.py --slug malazgirt-1071            # hepsi
  python scripts/generate_assets.py --slug malazgirt-1071 --only 3   # sadece 3. görsel
  python scripts/generate_assets.py --slug malazgirt-1071 --ses       # sadece ses"""
import os, sys, json, base64, argparse, subprocess, urllib.request, urllib.error, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, log_usage, set_status

API = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
IMG_MODEL = os.environ.get("GEMINI_IMAGE_MODEL") or "gemini-2.5-flash-image"
TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL") or "gemini-2.5-flash-preview-tts"
VOICE = os.environ.get("GEMINI_VOICE") or "Charon"
IMG_USD = float(os.environ.get("GEMINI_IMG_USD") or 0.039)

class GeminiError(Exception):
    pass

def call(model, body):
    key = os.environ["GEMINI_API_KEY"]
    req = urllib.request.Request(API.format(m=model), data=json.dumps(body).encode(), headers={"content-type": "application/json", "x-goog-api-key": key})
    for attempt in range(4):
        try: return json.load(urllib.request.urlopen(req, timeout=300))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code == 429 and "limit: 0" in msg: raise GeminiError("Ücretsiz planda bu model kapalı (kota 0)")
            if e.code in (429, 500, 503) and attempt < 3: time.sleep(30 * (attempt + 1)); continue
            raise GeminiError(f"Gemini hatası {e.code}: {msg}")

def inline_parts(r):
    for c in r.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            if "inlineData" in p: yield p["inlineData"]

def image(prompt, out):
    r = call(IMG_MODEL, {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}}})
    for d in inline_parts(r):
        raw = base64.b64decode(d["data"]); tmp = out + ".raw"
        open(tmp, "wb").write(raw); subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-q:v", "2", out], check=True); os.remove(tmp)
        log_usage("gorsel", "gemini-gorsel", IMG_USD, os.path.basename(out)); return True
    return False

def voice(text, out):
    style = os.environ.get("GEMINI_SES_STIL") or "Derin sesli bir erkek belgesel anlatıcısı gibi sakin ve vakur ama akıcı, normal konuşma hızında oku. Cümle aralarında çok kısa duraksa, uzun sessizlik bırakma. Metin 60 saniyelik bir video için:\n"
    r = call(TTS_MODEL, {"contents": [{"parts": [{"text": style + text}]}],
                         "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}})
    for d in inline_parts(r):
        pcm = out + ".pcm"; open(pcm, "wb").write(base64.b64decode(d["data"]))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", pcm, out], check=True); os.remove(pcm)
        u = r.get("usageMetadata", {}); usd = u.get("promptTokenCount", 0) / 1e6 * 0.5 + u.get("candidatesTokenCount", 0) / 1e6 * 10
        log_usage("ses", "gemini-ses", usd, f"{VOICE} sesi"); return True
    return False

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", required=True); ap.add_argument("--only", type=int); ap.add_argument("--ses", action="store_true"); a = ap.parse_args()
    if not os.environ.get("GEMINI_API_KEY"):
        set_status("gorsel", "bekliyor", "GEMINI_API_KEY yok: görselleri ve sesi panelden elle yükle"); print("GEMINI_API_KEY yok, atlandı."); return
    d = os.path.join(ROOT, "projects", a.slug); sc = json.load(open(os.path.join(d, "script.json")))
    set_status("gorsel", "calisiyor", f"{a.slug} ses ve görseller üretiliyor")
    notes = []
    if a.ses or not a.only:  # önce ses: görseller kapalı olsa bile ses üretilsin
        if not os.path.exists(os.path.join(d, "ses.wav")) or a.ses:
            try: print("ses", voice(sc["seslendirme_metni"], os.path.join(d, "ses.wav"))); notes.append("ses hazır")
            except GeminiError as e: print("SES HATASI:", e); notes.append(f"ses üretilemedi ({e})")
    if not a.ses:
        made = 0
        for i, s in enumerate(sc["sahneler"], 1):
            if a.only and i != a.only: continue
            out = os.path.join(d, s["image"]); os.makedirs(os.path.dirname(out), exist_ok=True)
            if os.path.exists(out) and not a.only: continue
            try:
                ok = image(s["prompt_tam"], out); made += bool(ok); print("görsel", i, ok)
            except GeminiError as e:
                print("GÖRSEL HATASI:", e); notes.append(f"görseller elle yüklenecek: {e}"); break
        if made: notes.append(f"{made} görsel üretildi")
    bad = any("üretilemedi" in n for n in notes)
    set_status("gorsel", "hata" if bad else "tamam", f"{a.slug}: " + ", ".join(notes or ["yapılacak bir şey yok"]), f"projects/{a.slug}")

if __name__ == "__main__":
    main()
