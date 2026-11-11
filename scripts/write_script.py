"""Senarist + doğruluk kontrolcüsü: seçilen konu için 60 sn metin, sahneler, Gemini promptları ve paylaşım açıklaması.
Çıktı: projects/<slug>/script.json ve project.json (zamanlar ses gelince otomatik hizalanır)."""
import os, json, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import claude, extract_json, set_status, slugify, ROOT

STYLE = "cinematic film still, photorealistic, 35mm, dramatic natural light, epic historical drama, warm muted color grade, vertical 9:16, no text, no watermark"
CITIES = json.load(open(os.path.join(ROOT, "engine", "map", "cities.json")))
REGIONS = json.load(open(os.path.join(ROOT, "engine", "map", "regions.json")))

def proje_yaz(sc, d):
    """script.json'dan motorun okuyacağı project.json'u üretir (zamanlar ses gelince hizalanır). Sohbette yazılan metinler için de kullanılır."""
    scenes = []
    for i, s in enumerate(sc["sahneler"]):
        kb = [[1.04, 1.18, .5, .55, .5, .5], [1.18, 1.04, .5, .5, .5, .55]][i % 2]
        scenes.append({"image": s["image"], "start": None, "end": None, "lines": s["lines"], "big": s.get("big"), "sub": s.get("sub"),
                       "year": s.get("year"), "label": s.get("label", str(s.get("year", ""))), "fx": s.get("fx", []), "kb": kb,
                       **({"effect": s["effect"]} if s.get("effect") in ("stamp", "type", "glow") else {}), **({"type_text": s["type_text"]} if s.get("type_text") else {}), **({"tablo": s["tablo"]} if s.get("tablo") else {}),
                       **{k: s[k] for k in ("anim", "etiket", "kaynak", "timeline") if k in s}, **({"kb": s["kb"]} if s.get("kb") else {})})
    proj = {"title": sc.get("baslik", sc.get("konu", "")), "voice": "ses.wav", "voice_offset": 0.3, "hook": sc.get("hook"), "map_region": sc.get("map_region", "avrupa_ortadogu"),
            "scenes": scenes, "eras": sc.get("eras", []), "outro_plan": sc.get("outro"), "maps_plan": sc.get("maps", []), "cards_plan": sc.get("cards", []),
            "music": {"booms": [0.3]}, "finale": sc.get("finale", "")}
    json.dump(proj, open(os.path.join(d, "project.json"), "w"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--konu", required=True); ap.add_argument("--tarih", default=""); ap.add_argument("--not", dest="notlar", default="")
    ap.add_argument("--slug", default=""); a = ap.parse_args()
    slug = a.slug or slugify(a.konu); d = os.path.join(ROOT, "projects", slug); os.makedirs(os.path.join(d, "images"), exist_ok=True)
    set_status("senarist", "calisiyor", f"'{a.konu}' metni yazılıyor")
    system = ("Sen 'Animasyon Tarih' (@animasyon.tarih) sayfasının senaristi ve doğruluk kontrolcüsüsün. 60-65 saniyelik, sakin bir erkek anlatıcının okuyacağı Türkçe metinler yazarsın. "
              "Kurallar: İlk cümle merak uyandıran bir kanca. Toplam 130-150 kelime. Kısa, net cümleler. Yıllar ve tarihler YAZIYLA (bin dört yüz elli üç) yazılır ki ses yapay zekası doğru okusun. "
              "Sadece kesin, kaynakta doğrulanabilir bilgiler; tartışmalı rakam ve uydurma sözlerden kaçın. Yıl, tarih ve saatleri metinde rakamla yaz (1953, 29 Ekim 1923, 09.05), yazıyla yazma. Gerçek kişilerin yüzünü görsel promptlarında gösterme (arkadan, siluet, uzaktan). "
              "Görsellerde yazı, hat, tuğra, bayrak hatası olmasın; dönemine uygun kıyafet. Kanlı/vahşet sahnesi yok. Sadece JSON döndür.")
    user = f"""Konu: {a.konu}
Tarih: {a.tarih or '-'}
Ek not: {a.notlar or '-'}

10-14 sahne üret. Her sahne 1-2 cümlelik anlatım ('lines'), ekrandaki büyük yazı ('big': yıl ya da tek kelime, en fazla 8 harf), alt yazı ('sub': BÜYÜK HARF, kısa), zaman çizelgesi için 'year' (sayı) ve 'label',
İngilizce görsel promptu ('prompt', sonunda stil yok, ben eklerim), atmosfer efektleri ('fx' şu listeden 0-3 tane: fog, smoke, rays, flicker, ember, ember_few, snow, dust, gold, rain).
Özel efekt ('effect', isteğe bağlı, videoda en fazla 3 sahnede): 'stamp' (tarih damga gibi basılır, kritik dönüm noktası), 'type' (belge/antlaşma tarihi daktiloyla yazılır; bu durumda 'type_text' ver, ör. '30 EKİM 1918 · MONDROS'), 'glow' (doruk/zafer anı parlayarak gelir).
İsteğe bağlı: konu Türk tarihinin zafer/kuruluş doruğuyla bitiyorsa 'finale':'ayyildiz' (son sahnelerde altın zerrelerden ay yıldız oluşur).
İsteğe bağlı: 1-3 harita geçişi ('maps'): sadece şu şehirler kullanılabilir {list(CITIES)}; bölge şunlardan biri {list(REGIONS)}.
İsteğe bağlı: 1-3 sayaç kartı ('cards': value sayı, unit, small) yalnızca kesin bilinen rakamlarla.
Ayrıca: 'hook' (ilk 3 sn üstte duran 2-4 kelime), 'eras' (zaman çizelgesi dönemleri, sahne indeksleriyle, isteğe bağlı), 'outro' {{"title","line"}}, paylaşım 'aciklama' (2-4 cümle + soru), 'hashtagler' (8-12), 'kaynaklar' (url listesi), 'kontrol_notlari' (doğruladığın kritik bilgiler ve kaynakları).

JSON şeması:
{{"baslik":"","hook":"","map_region":"avrupa_ortadogu","sahneler":[{{"lines":["..."],"big":"1071","sub":"MALAZGİRT","year":1071,"label":"1071","prompt":"...","fx":["dust"],"effect":"","type_text":""}}],"finale":"",
"maps":[{{"after_scene":2,"cities":["İstanbul","Viyana"],"route":["İstanbul","Belgrad","Viyana"],"title":"İSTANBUL — VİYANA"}}],
"cards":[{{"scene":3,"value":53,"unit":"GÜN","small":"SÜREN KUŞATMA"}}],"eras":[{{"name":"","from":0,"to":3}}],"outro":{{"title":"","line":""}},
"aciklama":"","hashtagler":[],"kaynaklar":[],"kontrol_notlari":[]}}"""
    sc = extract_json(claude(system, user, "senarist", max_tokens=24000, web_search=int(os.environ.get("ARAMA_SAYISI", "3"))), "senarist")
    sc["konu"] = a.konu; sc["tarih"] = a.tarih; sc["slug"] = slug; sc["durum"] = "onay-bekliyor"
    sc["seslendirme_metni"] = "\n".join(l for s in sc["sahneler"] for l in s["lines"])
    for i, s in enumerate(sc["sahneler"]): s["prompt_tam"] = f"{s['prompt']}, {STYLE}"; s["image"] = f"images/s{i + 1:02d}.jpg"
    json.dump(sc, open(os.path.join(d, "script.json"), "w"), ensure_ascii=False, indent=1)
    proje_yaz(sc, d)
    set_status("senarist", "tamam", f"'{a.konu}' metni onay bekliyor", f"projects/{slug}/script.json")
    print(slug)

if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        set_status("senarist", "hata", str(e)[:300]); raise
