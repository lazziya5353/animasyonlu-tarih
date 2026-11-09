"""Gemini'nin ücretsiz kotasıyla metin / görsel / ses anlama (kontrolcü ve yorum ajanları için).
Görsel ÜRETMEZ; sadece bakıp yorumlar. Anahtar yoksa ya da kota doluysa GeminiYok fırlatır, çağıran ajan o kısmı atlar."""
import os, json, base64, time, urllib.request, urllib.error, io

API = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
# İlk çalışan model kullanılır; Google model adlarını değiştirirse sıradaki denenir.
MODELLER = [m for m in [os.environ.get("GEMINI_TEXT_MODEL"), "gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"] if m]
_calisan = None


class GeminiYok(Exception):
    pass


def hazir():
    return bool(os.environ.get("GEMINI_API_KEY"))


def _post(model, body):
    req = urllib.request.Request(API.format(m=model), data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    return json.load(urllib.request.urlopen(req, timeout=180))


def sor(parts, json_cevap=True, sicaklik=0.2):
    """parts: metin ve/veya {"inline_data": {...}} listesi. JSON istenirse sözlük döner."""
    global _calisan
    if not hazir(): raise GeminiYok("GEMINI_API_KEY tanımlı değil")
    body = {"contents": [{"parts": [p if isinstance(p, dict) else {"text": p} for p in parts]}],
            "generationConfig": {"temperature": sicaklik, **({"responseMimeType": "application/json"} if json_cevap else {})}}
    son_hata = ""
    for model in ([_calisan] if _calisan else []) + [m for m in MODELLER if m != _calisan]:
        for deneme in range(3):
            try:
                r = _post(model, body); _calisan = model
                txt = "".join(p.get("text", "") for c in r.get("candidates", []) for p in c.get("content", {}).get("parts", []))
                if not json_cevap: return txt
                try: return json.loads(txt)
                except json.JSONDecodeError:
                    a, b = txt.find("{"), txt.rfind("}")
                    return json.loads(txt[a:b + 1]) if a >= 0 else {}
            except urllib.error.HTTPError as e:
                son_hata = f"{e.code}: {e.read().decode()[:200]}"
                if e.code == 404 or "limit: 0" in son_hata: break          # bu model yok/kapalı → sıradaki
                if e.code in (429, 500, 503) and deneme < 2: time.sleep(20 * (deneme + 1)); continue
                break
            except (urllib.error.URLError, TimeoutError) as e:
                son_hata = str(e)
                if deneme < 2: time.sleep(5); continue
                break
    raise GeminiYok(f"Gemini yanıt vermedi ({son_hata[:160]})")


def resim_parca(path, max_h=900):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if im.height > max_h: im = im.resize((int(im.width * max_h / im.height), max_h))
    b = io.BytesIO(); im.save(b, "JPEG", quality=85)
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}


def ses_parca(path):
    return {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(open(path, "rb").read()).decode()}}
