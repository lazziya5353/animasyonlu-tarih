"""Quiz Studyo 'Ajan hazirlasin': Gemini ile soru taslagi + dogruluk kontrolu (ucretsiz kota).
  quiz_taslak.py --id abc123 --format yili-tahmin --konu "Osmanli savaslari" --adet 10 --kolay 4 --orta 4 --zor 2 [--tema spor]
Cikti: projects/_taslak/<id>.json  {durum, format, sorular, notlar}. Video URETMEZ; panelde kullanici duzenleyip onaylar.
Panel (Netlify) GEMINI_API_KEY varsa ayni istemleri kendisi calistirir; yoksa bu script quiz_taslak.yml ile calisir."""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT
from generate_assets import call
SEMA = json.load(open(os.path.join(ROOT, "dashboard", "quiz", "semalar.json")))
MODEL = os.environ.get("GEMINI_METIN_MODEL") or "gemini-flash-latest"

def istem(fmt, konu, adet, kar, tema):
    s = SEMA[fmt]; alan = "spor tarihi" if tema == "spor" else "tarih (ağırlıklı Türk ve dünya tarihi)"
    return (f"Türkçe bir Instagram {alan} quiz videosu için '{s['ad']}' formatında {adet} soru hazırla. Konu: {konu}.\n"
            f"Zorluk dağılımı: {kar['kolay']} kolay, {kar['orta']} orta, {kar['zor']} zor; zorları başa/ortaya/sona dağıt.\n"
            f"Kurallar: {s['kurallar']} Her bilgi kesin doğru ve iki kaynakla doğrulanabilir olmalı; tartışmalı ya da rivayet bilgileri kullanma. "
            f"Sorular kısa (en çok 14 kelime), alt_bilgi en çok 6 kelime. Türkçe karakterleri doğru yaz.\n"
            f"Sadece JSON döndür: {{\"sorular\": [ ... ]}}. Tek bir sorunun şeması (örnek): {json.dumps(s['ornek'], ensure_ascii=False)}")

def kontrol_istemi(fmt, sorular):
    return ("Aşağıdaki quiz sorularını tek tek doğruluk açısından denetle (Google araması kullan). Yanlış yıl, yanlış kişi, uydurma söz, "
            "birden fazla doğru cevabı olan soru, cevabı soruda ele veren ipucu ya da hatalı koordinat varsa DÜZELT; düzeltemiyorsan soruyu çıkar. "
            "Aynı şemayı koru. Sadece JSON döndür: {\"sorular\": [...], \"notlar\": [\"soru N: ne değişti ve neden (kaynak)\"]}.\n"
            + json.dumps({"format": fmt, "sorular": sorular}, ensure_ascii=False))

def metin(r): return "".join(p.get("text", "") for c in r.get("candidates", []) for p in c.get("content", {}).get("parts", []))
def js(t):
    t = re.sub(r"^```(json)?|```$", "", t.strip(), flags=re.M); return json.loads(t[t.index("{"):t.rindex("}") + 1])

def main():
    ap = argparse.ArgumentParser()
    for k in ("id", "format", "konu", "tema"): ap.add_argument("--" + k, default="")
    for k in ("adet", "kolay", "orta", "zor"): ap.add_argument("--" + k, type=lambda x: int(x or 0), default=0)
    a = ap.parse_args(); out = os.path.join(ROOT, "projects", "_taslak", f"{a.id}.json"); os.makedirs(os.path.dirname(out), exist_ok=True)
    if not re.fullmatch(r"[a-z0-9-]{4,40}", a.id) or a.format not in SEMA or SEMA[a.format].get("eski"): sys.exit("gecersiz id/format")
    adet = max(6, min(15, a.adet or 10)); kar = dict(kolay=a.kolay, orta=a.orta, zor=a.zor)
    if sum(kar.values()) != adet: kar = dict(kolay=round(adet*0.4), zor=round(adet*0.2)); kar["orta"] = adet - kar["kolay"] - kar["zor"]
    try:
        r = call(MODEL, {"contents": [{"parts": [{"text": istem(a.format, a.konu, adet, kar, a.tema)}]}], "generationConfig": {"temperature": 0.6, "responseMimeType": "application/json"}})
        sor = js(metin(r))["sorular"]; notlar = []
        try:
            r2 = call(MODEL, {"contents": [{"parts": [{"text": kontrol_istemi(a.format, sor)}]}], "tools": [{"google_search": {}}], "generationConfig": {"temperature": 0.2}})
            k = js(metin(r2)); sor = k.get("sorular") or sor; notlar = ["Doğruluk kontrolü (Google aramalı): " + (n if isinstance(n, str) else json.dumps(n, ensure_ascii=False)) for n in k.get("notlar", [])] or ["Doğruluk kontrolü: değişiklik yok"]
        except Exception as e: notlar = [f"UYARI: doğruluk kontrolü yapılamadı ({e}); soruları elle kontrol et"]
        from quiz_studyo import dogrula
        h = dogrula(dict(format=a.format, sorular=sor)); notlar += [f"Kural: {x}" for x in h]
        json.dump(dict(durum="hazir", format=a.format, konu=a.konu, tema=a.tema, sorular=sor, notlar=notlar), open(out, "w"), ensure_ascii=False, indent=1)
    except Exception as e:
        json.dump(dict(durum="hata", hata=str(e)[:300]), open(out, "w"), ensure_ascii=False); raise

if __name__ == "__main__": main()
