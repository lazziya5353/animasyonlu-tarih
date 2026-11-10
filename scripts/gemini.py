"""Gemini'nin ücretsiz kotasıyla metin / görsel / ses anlama (kontrolcü ve yorum ajanları için).
Görsel ÜRETMEZ; sadece bakıp yorumlar. Anahtar yoksa ya da kota doluysa GeminiYok fırlatır, çağıran ajan o kısmı atlar."""
import os, json, base64, time, urllib.request, urllib.error, io

API = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
# İlk çalışan model kullanılır. Google model adlarını sık değiştirdiği için bulunamazsa mevcut modeller listesinden
# en yeni "flash" modeli otomatik seçilir.
MODELLER = [m for m in [os.environ.get("GEMINI_TEXT_MODEL"), "gemini-flash-latest", "gemini-2.5-flash"] if m]
_calisan = None
_kesfedildi = False


def _kesfet():
    """API'deki modelleri listeleyip metin+görsel anlayabilen en yeni flash modellerini döndürür."""
    import re
    try:
        req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        ms = json.load(urllib.request.urlopen(req, timeout=60)).get("models", [])
    except Exception as e:
        print("Model listesi alınamadı:", e); return []
    aday = []
    for m in ms:
        ad = m.get("name", "").split("/")[-1]
        if "generateContent" not in m.get("supportedGenerationMethods", []) or re.search(r"tts|image|audio|live|native|thinking", ad): continue
        r = re.fullmatch(r"gemini-(\d+(?:\.\d+)?)-flash(?:-preview(?:-[\w-]+)?)?", ad)
        if r: aday.append((float(r.group(1)), "preview" not in ad, ad))
    aday.sort(reverse=True)
    print("Bulunan flash modelleri:", [a[2] for a in aday[:5]])
    return [a[2] for a in aday[:4]]


class GeminiYok(Exception):
    pass


def hazir():
    return bool(os.environ.get("GEMINI_API_KEY"))


def _post(model, body, timeout=120):
    req = urllib.request.Request(API.format(m=model), data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    return json.load(urllib.request.urlopen(req, timeout=max(10, timeout)))


_dusunme_kapali = True   # yeni modeller varsayılan olarak uzun "düşünüyor"; kontrol işleri için gereksiz ve yavaş


def sor(parts, json_cevap=True, sicaklik=0.2, sure=120):
    """parts: metin ve/veya {"inline_data": {...}} listesi. JSON istenirse sözlük döner."""
    global _calisan, _dusunme_kapali
    if not hazir(): raise GeminiYok("GEMINI_API_KEY tanımlı değil")
    body = {"contents": [{"parts": [p if isinstance(p, dict) else {"text": p} for p in parts]}],
            "generationConfig": {"temperature": sicaklik, **({"responseMimeType": "application/json"} if json_cevap else {})}}
    if _dusunme_kapali: body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}
    global _kesfedildi
    son_hata = ""
    sira = ([_calisan] if _calisan else []) + [m for m in MODELLER if m != _calisan]
    i = 0; bitis = time.time() + max(240, sure * 2)          # kontrol işi Gemini yüzünden uzamasın
    while i < len(sira) and time.time() < bitis:
        model = sira[i]; i += 1
        for deneme in range(3):
            kalan = bitis - time.time()
            if kalan < 10: break
            try:
                t0 = time.time(); r = _post(model, body, timeout=min(sure, kalan)); _calisan = model
                print(f"Gemini: {model} yanıt verdi ({time.time() - t0:.0f} sn)")
                txt = "".join(p.get("text", "") for c in r.get("candidates", []) for p in c.get("content", {}).get("parts", []))
                if not json_cevap: return txt
                try: return json.loads(txt)
                except json.JSONDecodeError:
                    a, b = txt.find("{"), txt.rfind("}")
                    return json.loads(txt[a:b + 1]) if a >= 0 else {}
            except urllib.error.HTTPError as e:
                son_hata = f"{model} {e.code}: {e.read().decode()[:300]}"
                print("Gemini:", son_hata[:200].replace("\n", " "))
                if e.code == 400 and "thinking" in son_hata.lower() and "thinkingConfig" in body["generationConfig"]:
                    body["generationConfig"].pop("thinkingConfig"); _dusunme_kapali = False; continue   # bu model ayarı tanımıyor
                if e.code == 404 or "limit: 0" in son_hata or "PerDay" in son_hata: break   # model yok / günlük kota bitti → sıradaki
                if e.code in (429, 500, 503) and deneme < 2: time.sleep(15 * (deneme + 1)); continue
                break
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                son_hata = f"{model}: {e}"; print("Gemini:", son_hata[:200])
                break                                    # zaman aşımında aynı modeli tekrar bekleme, sıradakine geç
        if i == len(sira) and not _kesfedildi:                  # listedekiler bitti → API'den güncel modelleri bul
            _kesfedildi = True; sira += [m for m in _kesfet() if m not in sira]
    raise GeminiYok(f"Gemini yanıt vermedi ({son_hata[:160]})")


def resim_parca(path, max_h=900):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if im.height > max_h: im = im.resize((int(im.width * max_h / im.height), max_h))
    b = io.BytesIO(); im.save(b, "JPEG", quality=85)
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}


def ses_parca(path):
    return {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(open(path, "rb").read()).decode()}}
