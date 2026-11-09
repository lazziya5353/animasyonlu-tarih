"""Araştırmacı ajan: önümüzdeki haftanın 'Tarihte Bugün' olaylarını ve bir savaş önerisini çıkarır.
Çıktı: reports/<YIL>-W<HAFTA>.json ve reports/latest.json"""
import os, json, datetime, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import claude, extract_json, set_status, ROOT

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

def main():
    today = datetime.date.today()
    start = today + datetime.timedelta(days=(7 - today.weekday()) % 7 or 7) if os.environ.get("BU_HAFTA") != "1" else today - datetime.timedelta(days=today.weekday())
    days = [start + datetime.timedelta(days=i) for i in range(7)]
    wk = f"{start.isocalendar()[0]}-W{start.isocalendar()[1]:02d}"
    set_status("arastirmaci", "calisiyor", f"{wk} haftası araştırılıyor")
    gecmis = []
    for f in sorted(os.listdir(os.path.join(ROOT, "projects"))):
        pj = os.path.join(ROOT, "projects", f, "project.json")
        if os.path.exists(pj): gecmis.append(json.load(open(pj)).get("title", f))
    system = ("Sen 'Animasyonlu Tarih' adlı Türkçe Instagram/TikTok tarih sayfasının araştırmacısısın. 60 saniyelik dikey videolar üretiliyor: "
              "Tarihte Bugün, savaşlar ve dünya tarihi. Doğruluk her şeyden önemli: yalnızca tarihi kesin, kaynakta doğrulanabilen olayları yaz. "
              "Son 50 yılın tartışmalı/süren çatışmalarından ve vahşet odaklı konulardan kaçın. Sadece JSON döndür.")
    user = f"""Şu tarihler için (yıl fark etmez, gün ve ay eşleşsin) en iyi video konularını bul:
{chr(10).join(f'- {d.isoformat()} {GUNLER[d.weekday()]} → {d.day} {d.strftime("%m")}. ay' for d in days)}

Her gün için 1-3 olay yaz (Türk tarihi ve dünya tarihi karışık). Her olaya 1-5 arası 'yildiz' ver: Türk izleyicide izlenme potansiyeli, görsellik, duygusal etki.
Ayrıca tarihten bağımsız 1 'savas_onerisi' ver (harita animasyonuna uygun, iki taraf, sonuç). Daha önce yapılan konuları tekrar önerme: {gecmis}
En iyi 3 konuyu 'onerilen' listesine koy.

JSON şeması:
{{"hafta":"{wk}","gunler":[{{"tarih":"YYYY-MM-DD","gun":"Pazartesi","olaylar":[{{"yil":1938,"baslik":"kısa başlık","ozet":"1-2 cümle","yildiz":5,"neden":"neden izlenir","tur":"tarihte-bugun|savas|dunya","kaynak":"url"}}]}}],
"savas_onerisi":{{"baslik":"","yil":0,"taraflar":"","sonuc":"","ozet":"","neden":"","harita_bolgesi":"avrupa_ortadogu|bati_avrupa|orta_asya|akdeniz|anadolu"}},
"onerilen":[{{"baslik":"","tarih":"YYYY-MM-DD veya boş","tur":""}}]}}"""
    txt = claude(system, user, "arastirmaci", max_tokens=5000, web_search=int(os.environ.get("ARAMA_SAYISI", "4")))
    rep = extract_json(txt, "arastirmaci"); rep["olusturma"] = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    for d in rep.get("gunler", []):
        for o in d.get("olaylar", []): o.setdefault("durum", "bekliyor")
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    for name in (f"{wk}.json", "latest.json"):
        json.dump(rep, open(os.path.join(ROOT, "reports", name), "w"), ensure_ascii=False, indent=1)
    set_status("arastirmaci", "tamam", f"{wk} raporu hazır", f"reports/{wk}.json")
    print(json.dumps(rep, ensure_ascii=False)[:2000])

if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        set_status("arastirmaci", "hata", str(e)[:300]); raise
