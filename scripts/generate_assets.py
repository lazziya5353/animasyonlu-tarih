"""Görsel yönetmeni: script.json'daki promptlarla Gemini'ye görselleri, seslendirme metniyle sesi ürettirir.
GEMINI_API_KEY yoksa hiçbir şey yapmaz (görsel/ses elle yüklenir).
  python scripts/generate_assets.py --slug malazgirt-1071            # hepsi
  python scripts/generate_assets.py --slug malazgirt-1071 --only 3   # sadece 3. görsel
  python scripts/generate_assets.py --slug malazgirt-1071 --ses       # sadece ses"""
import os, sys, json, base64, argparse, subprocess, urllib.request, urllib.error, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from olay import olay, slug_ayarla
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

GEMINI_GORSEL_KAPALI = False

def pollinations(prompt, out, sahne=0):
    """Ücretsiz yedek çizer (Pollinations, FLUX). Anahtarsız da çalışır (15 sn'de 1 istek);
    POLLINATIONS_KEY gizli anahtarı varsa sınır kalkar ve filigran olmaz."""
    from urllib.parse import quote
    key = os.environ.get("POLLINATIONS_KEY", "").strip()
    url = (f"https://image.pollinations.ai/prompt/{quote(prompt[:900])}?width=1080&height=1920&model=flux"
           f"&nologo=true&enhance=false&safe=false&seed={1000 + sahne}" + (f"&token={quote(key)}" if key else ""))
    h = {"user-agent": "animasyonlu-tarih/1.0", "referer": "https://animasyonlu-tarih.netlify.app"}
    if key: h["authorization"] = f"Bearer {key}"
    for deneme in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=240)
            veri = r.read()
            if not r.headers.get("content-type", "").startswith("image") or len(veri) < 15000:
                raise GeminiError(f"Pollinations görsel yerine başka bir şey döndürdü ({len(veri)} bayt)")
            tmp = out + ".raw"; open(tmp, "wb").write(veri)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-q:v", "2", out], check=True); os.remove(tmp)
            log_usage("gorsel", "pollinations-gorsel", 0.0, os.path.basename(out) + " (ücretsiz)"); return True
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 530) and deneme < 3: time.sleep(20 * (deneme + 1)); continue
            raise GeminiError(f"Pollinations hatası {e.code}: {e.read().decode(errors='ignore')[:200]}")
        except (urllib.error.URLError, TimeoutError) as e:
            if deneme < 3: time.sleep(15); continue
            raise GeminiError(f"Pollinations'a ulaşılamadı: {e}")
    return False

def ciz(prompt, out, sahne=0):
    """Önce Gemini; Gemini'nin ücretsiz görsel kotası kapalıysa ücretsiz yedeğe (Pollinations) geçer. Dönüş: (ok, kaynak)"""
    global GEMINI_GORSEL_KAPALI
    if not GEMINI_GORSEL_KAPALI and os.environ.get("GORSEL_KAYNAK", "") != "pollinations":
        try: return image(prompt, out), "Gemini"
        except GeminiError as e:
            print("Gemini görsel çizemedi, ücretsiz yedeğe geçiliyor:", e); GEMINI_GORSEL_KAPALI = True
    if not os.environ.get("POLLINATIONS_KEY"): time.sleep(16)   # anahtarsız sınır: 15 sn'de 1 istek
    return pollinations(prompt, out, sahne), "Pollinations"

def voice(text, out, stil=None):
    style = stil or os.environ.get("GEMINI_SES_STIL") or "Derin sesli bir erkek belgesel anlatıcısı gibi sakin ve vakur ama akıcı, normal konuşma hızında oku. Cümle aralarında çok kısa duraksa, uzun sessizlik bırakma. Metin 60 saniyelik bir video için:\n"
    r = call(TTS_MODEL, {"contents": [{"parts": [{"text": style + text}]}],
                         "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}})
    for d in inline_parts(r):
        pcm = out + ".pcm"; open(pcm, "wb").write(base64.b64decode(d["data"]))
        raw = out + ".ham.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", pcm, raw], check=True); os.remove(pcm)
        # uzun sessizlikleri 0.4 sn'ye indir, hafif hızlandır (ses tonu değişmez)
        trimmed = out + ".kisa.wav"
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "trim_pauses.py"), raw, trimmed, "0.4"], check=True)
        tempo = os.environ.get("GEMINI_SES_TEMPO") or "1.1"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", trimmed, "-af", f"atempo={tempo}", out], check=True)
        os.remove(raw); os.remove(trimmed)
        u = r.get("usageMetadata", {}); usd = u.get("promptTokenCount", 0) / 1e6 * 0.5 + u.get("candidatesTokenCount", 0) / 1e6 * 10
        log_usage("ses", "gemini-ses", usd if os.environ.get("GEMINI_UCRETLI") == "1" else 0.0, f"{VOICE} sesi" + ("" if os.environ.get("GEMINI_UCRETLI") == "1" else " (ücretsiz kota)")); return True
    return False

def asama(ad, durum, mesaj, **k):
    """Kurgu Stüdyosu'ndaki aşama çubuğu için: hangi iş yapılıyor, kaçıncı adımda."""
    olay("gorsel" if ad == "gorsel" else "ses", "asama", mesaj, asama=ad, durum=durum, **k)

def onizleme(yol):
    """Stüdyoda canlı göstermek için görselin küçük jpeg hali (base64)."""
    try:
        from PIL import Image; import io
        im = Image.open(yol).convert("RGB"); im.thumbnail((300, 534))
        b = io.BytesIO(); im.save(b, "JPEG", quality=72); return base64.b64encode(b.getvalue()).decode()
    except Exception as e:
        print("(önizleme yapılamadı:", e, ")"); return None

def ses_metni_dogrula(sc, slug):
    """Ses her zaman projenin KENDI metninden uretilir. Baska projeden kopyalanmis script.json
    (slug alani / seslendirme_metni eski kalmis) sessizce yanlis ses uretmesin diye yuksek sesle durur."""
    if sc.get("slug") and sc["slug"] != slug:
        sys.exit(f"HATA: projects/{slug}/script.json icindeki slug '{sc['slug']}' (baska projeden kopya?). Ses uretilmedi.")
    if sc.get("sahneler") and sc.get("seslendirme_metni"):
        sys.path.insert(0, os.path.join(ROOT, "scripts")); from kontrol import kelimeler
        bek = kelimeler(" ".join(l for x in sc["sahneler"] for l in x["lines"])); var = set(kelimeler(sc["seslendirme_metni"]))
        eksik = [w for w in bek if w not in var]
        if len(eksik) > 0.15 * max(1, len(bek)):
            sys.exit(f"HATA: {slug} seslendirme_metni sahnelerle uyusmuyor ({len(eksik)}/{len(bek)} kelime eksik, orn. {eksik[:6]}). Ses uretilmedi.")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", required=True); ap.add_argument("--only", type=int); ap.add_argument("--ses", action="store_true"); a = ap.parse_args()
    if not os.environ.get("GEMINI_API_KEY"):
        set_status("gorsel", "bekliyor", "GEMINI_API_KEY yok: görselleri ve sesi panelden elle yükle"); print("GEMINI_API_KEY yok, atlandı."); return
    d = os.path.join(ROOT, "projects", a.slug); sc = json.load(open(os.path.join(d, "script.json")))
    ses_metni_dogrula(sc, a.slug)
    set_status("gorsel", "calisiyor", f"{a.slug} ses ve görseller üretiliyor"); slug_ayarla(a.slug)
    notes = []
    if a.ses or not a.only:  # önce ses: görseller kapalı olsa bile ses üretilsin
        if not os.path.exists(os.path.join(d, "ses.wav")) or a.ses:
            try:
                asama("ses", "calisiyor", "Seslendirme yapılıyor")
                olay("ses", "ses", f"Seslendirme başladı: {len(sc['seslendirme_metni'])} karakter, erkek anlatıcı")
                print("ses", voice(sc["seslendirme_metni"], os.path.join(d, "ses.wav"), sc.get("ses_stil"))); notes.append("ses hazır")
                sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(d, "ses.wav")], capture_output=True, text=True).stdout or 0)
                olay("ses", "ses", f"Ses hazır: {sure:.0f} sn, duraklamalar kısaltıldı", t0=0, t1=sure)
                asama("ses", "bitti", f"Ses hazır ({sure:.0f} sn)")
            except GeminiError as e:
                print("SES HATASI:", e); notes.append(f"ses üretilemedi ({e})"); asama("ses", "hata", f"Ses üretilemedi: {e}")
    if not a.ses:
        made = 0; yap = []
        for i, s in enumerate(sc["sahneler"], 1):
            if a.only and i != a.only: continue
            out = os.path.join(d, s["image"]); os.makedirs(os.path.dirname(out), exist_ok=True)
            if os.path.exists(out) and not a.only: continue
            if s.get("anim"): continue  # koddan çizilen animasyon sahnesi, görsel gerekmez
            yap.append((i, s, out))
        n = len(yap)
        if n: asama("gorsel", "calisiyor", f"{n} görsel çizilecek", adim=0, toplam=n)
        for k, (i, s, out) in enumerate(yap, 1):
            asama("gorsel", "calisiyor", f"Görsel {k}/{n} çiziliyor: Sahne {i}" + (f" · {s['big']}" if s.get("big") else ""), adim=k - 1, toplam=n, sahne=i)
            try:
                ok, kaynak = ciz(s["prompt_tam"], out, i); made += bool(ok); print("görsel", i, ok, kaynak)
                if not ok: raise GeminiError("görsel boş döndü")
                olay("gorsel", "gorsel", f"Sahne {i} çizildi ({k}/{n}) · {kaynak}", sahne=i, adim=k, toplam=n, onizleme=onizleme(out))
            except GeminiError as e:
                print("GÖRSEL HATASI:", e); notes.append(f"görseller elle yüklenecek: {e}")
                asama("gorsel", "hata", f"Görsel {k}/{n} çizilemedi: {e}", adim=k - 1, toplam=n); break
        else:
            if n: asama("gorsel", "bitti", f"{made} görsel hazır", adim=n, toplam=n)
        if made: notes.append(f"{made} görsel üretildi")
    bad = any(("üretilemedi" in x or "elle yüklenecek" in x) for x in notes)
    set_status("gorsel", "hata" if bad else "tamam", f"{a.slug}: " + ", ".join(notes or ["yapılacak bir şey yok"]), f"projects/{a.slug}")
    if bad: sys.exit(1)   # iş kırmızı görünsün; sonraki adım (video) eksik görselle başlamasın

if __name__ == "__main__":
    main()
