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
    system = ("Sen 'Animasyon Tarih' (@animasyon.tarih) adlı Türkçe Instagram/TikTok tarih sayfasının araştırmacısısın. 60 saniyelik dikey videolar üretiliyor: "
              "Tarihte Bugün, savaşlar ve dünya tarihi. Doğruluk her şeyden önemli: yalnızca tarihi kesin, kaynakta doğrulanabilen olayları yaz. "
              "Son 50 yılın tartışmalı/süren çatışmalarından ve vahşet odaklı konulardan kaçın. Sadece JSON döndür; açıklama yazma, metinleri kısa tut.")
    # Analistin ve yorum ajanının bulguları (ücretsiz toplanır, birkaç satır = önemsiz token)
    ipucu = []
    try:
        an = json.load(open(os.path.join(ROOT, "data", "analiz.json")))
        vids = (an.get("instagram") or {}).get("videolar") or []
        if vids: ipucu.append("En çok izlenen videolarımız: " + "; ".join(f"{v['baslik'][:50]} ({v['izlenme']} izlenme)" for v in vids[:3]))
    except Exception: pass
    try:
        fk = json.load(open(os.path.join(ROOT, "data", "yorumlar.json"))).get("fikirler") or []
        if fk: ipucu.append("İzleyicilerin istediği konular: " + ", ".join(f["konu"] for f in fk[-6:]))
    except Exception: pass
    ipucu = ("\nİzleyici verisi (önerilerinde dikkate al):\n" + "\n".join(ipucu) + "\n") if ipucu else ""
    user = f"""Şu tarihler için (yıl fark etmez, gün ve ay eşleşsin) en iyi video konularını bul:
{chr(10).join(f'- {d.isoformat()} {GUNLER[d.weekday()]} → {d.day} {d.strftime("%m")}. ay' for d in days)}

Her gün için 1-2 olay yaz (Türk tarihi ve dünya tarihi karışık). Her olaya 1-5 arası 'yildiz' ver: Türk izleyicide izlenme potansiyeli, görsellik, duygusal etki.
Ayrıca tarihten bağımsız 1 'savas_onerisi' ver (harita animasyonuna uygun, iki taraf, sonuç). Daha önce yapılan konuları tekrar önerme: {gecmis}
En iyi 3 konuyu 'onerilen' listesine koy.{ipucu}

JSON şeması:
{{"hafta":"{wk}","gunler":[{{"tarih":"YYYY-MM-DD","gun":"Pazartesi","olaylar":[{{"yil":1938,"baslik":"kısa başlık","ozet":"tek kısa cümle","yildiz":5,"neden":"en fazla 8 kelime","tur":"tarihte-bugun|savas|dunya","kaynak":"url"}}]}}],
"savas_onerisi":{{"baslik":"","yil":0,"taraflar":"","sonuc":"","ozet":"","neden":"","harita_bolgesi":"avrupa_ortadogu|bati_avrupa|orta_asya|akdeniz|anadolu"}},
"onerilen":[{{"baslik":"","tarih":"YYYY-MM-DD veya boş","tur":""}}]}}"""
    txt = claude(system, user, "arastirmaci", max_tokens=16000, web_search=int(os.environ.get("ARAMA_SAYISI", "4")))
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
