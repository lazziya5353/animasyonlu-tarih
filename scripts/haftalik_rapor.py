"""Haftalık Instagram raporu (her pazartesi 09:10 İstanbul): data/instagram.json'dan hafta-hafta karşılaştırma,
en iyi 3 video, en iyi format, takipçi artışı, en iyi saatler + Gemini ile 3 somut öneri (olmazsa şablon).
Çıktı: data/haftalik_rapor.json (son rapor + arşiv)."""
import os, sys, json, datetime, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, set_status
from format_sinif import sinifla, kurallar
import gemini

IG = os.path.join(ROOT, "data", "instagram.json")
OUT = os.path.join(ROOT, "data", "haftalik_rapor.json")


def oku(p, bos):
    try: return json.load(open(p))
    except Exception: return bos


def zaman(v):
    try: return datetime.datetime.strptime((v.get("zaman") or "")[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
    except Exception: return None


def toplam(L, k): return sum((v.get(k) or 0) for v in L)


def takipci_artisi(g, simdi):
    gec = {x["tarih"]: x["takipci"] for x in g.get("gecmis", []) if x.get("takipci") is not None}
    bugun = (g.get("hesap") or {}).get("takipci")
    once = [t for t in sorted(gec) if t <= (simdi - datetime.timedelta(days=7)).strftime("%Y-%m-%d")]
    if bugun is not None and once: return bugun - gec[once[-1]], "kendi kayıtlarımız"
    fc = (g.get("gunluk") or {}).get("follower_count") or []
    if fc: return sum((x.get("deger") or 0) for x in fc[-7:]), "Instagram günlük verisi"
    return None, None


def main():
    g = oku(IG, {}); medya = g.get("medya") or []
    if not medya: set_status("haftalik", "bekliyor", "Instagram verisi yok"); print("veri yok"); return
    simdi = datetime.datetime.now(datetime.timezone.utc); K = kurallar()
    for v in medya: v["format"] = sinifla(v.get("baslik"), K)
    bu = [v for v in medya if zaman(v) and zaman(v) > simdi - datetime.timedelta(days=7)]
    once = [v for v in medya if zaman(v) and simdi - datetime.timedelta(days=14) < zaman(v) <= simdi - datetime.timedelta(days=7)]
    ozet = lambda L: {"gonderi": len(L), "izlenme": toplam(L, "izlenme"), "kaydetme": toplam(L, "kaydetme"), "paylasim": toplam(L, "paylasim"), "begeni": toplam(L, "begeni")}
    havuz = bu or medya
    en_iyi = [{"baslik": v.get("baslik"), "izlenme": v.get("izlenme"), "kaydetme": v.get("kaydetme"), "url": v.get("url"), "kapak": v.get("kapak"), "format": v["format"]}
              for v in sorted(havuz, key=lambda v: v.get("izlenme") or 0, reverse=True)[:3]]
    fmt = {}
    for v in medya:
        if v.get("izlenme"): fmt.setdefault(v["format"], []).append(v["izlenme"])
    fmt_ort = sorted(((k, round(statistics.mean(x)), len(x)) for k, x in fmt.items()), key=lambda t: t[1], reverse=True)
    artis, kaynak = takipci_artisi(g, simdi)
    saatler = [f"{x['saat']:02d}:00" for x in g.get("en_iyi_saatler", [])]
    veri = {"bu_hafta": ozet(bu), "gecen_hafta": ozet(once), "en_iyi_3": en_iyi,
            "en_iyi_format": fmt_ort[0][0] if fmt_ort else None, "formatlar": [{"ad": a, "ort_izlenme": o, "adet": n} for a, o, n in fmt_ort],
            "takipci": (g.get("hesap") or {}).get("takipci"), "takipci_artisi": artis, "takipci_kaynak": kaynak,
            "en_iyi_saatler": saatler, "en_iyi_gun": g.get("en_iyi_gun")}
    ozet_metni, oneriler, kaynak_ai = None, None, "şablon"
    if gemini.hazir():
        try:
            r = gemini.sor([
                "Bir Türk tarih Instagram sayfasının (Reels) haftalık verisi aşağıda. Türkçe, samimi ve kısa yaz. "
                "JSON döndür: {\"ozet\": \"2-3 cümle, rakamlarla bu haftayı geçen haftayla kıyasla\", \"oneriler\": [\"3 tane somut, uygulanabilir gelecek hafta önerisi (hangi format, hangi gün/saat, ne tür konu)\"]}.\n"
                + json.dumps(veri, ensure_ascii=False)], sicaklik=0.5, sure=60)
            if isinstance(r, dict) and r.get("ozet") and len(r.get("oneriler") or []) >= 3:
                ozet_metni, oneriler, kaynak_ai = str(r["ozet"])[:800], [str(x)[:300] for x in r["oneriler"][:3]], "gemini"
        except Exception as e:
            print("Gemini olmadı, şablon kullanılıyor:", str(e)[:160])
    if not ozet_metni:
        b, o = veri["bu_hafta"], veri["gecen_hafta"]
        nk = lambda x: f"{x:,}".replace(",", ".")
        fark = (f"%{round((b['izlenme'] - o['izlenme']) * 100 / o['izlenme'])}" if o["izlenme"] else "—")
        ozet_metni = (f"Bu hafta {b['gonderi']} gönderi, toplam {nk(b['izlenme'])} izlenme (geçen hafta {nk(o['izlenme'])}, değişim {fark}). "
                      + (f"Takipçi değişimi: {artis:+d}. " if artis is not None else "") + (f"En iyi format: {veri['en_iyi_format']}." if veri["en_iyi_format"] else ""))
        s = saatler[0] if saatler else "19:00"
        oneriler = [f"{veri['en_iyi_format'] or 'En iyi giden'} formatından bu hafta en az 2 video daha paylaş.",
                    f"Paylaşımları {veri.get('en_iyi_gun') or 'hafta içi'} {s} civarına planla.",
                    f"En çok izlenen video ({(en_iyi[0]['baslik'] if en_iyi else '')[:40]}) tarzında bir devam videosu çek."]
    rapor = {"zaman": simdi.strftime("%Y-%m-%dT%H:%M:%SZ"), "hafta": (simdi - datetime.timedelta(days=7)).strftime("%d.%m") + " – " + simdi.strftime("%d.%m.%Y"),
             "ozet": ozet_metni, "oneriler": oneriler, "kaynak": kaynak_ai, **veri}
    db = oku(OUT, {"arsiv": []})
    db["arsiv"] = ([rapor] + [x for x in db.get("arsiv", []) if x.get("hafta") != rapor["hafta"]])[:26]
    db["son"] = rapor
    json.dump(db, open(OUT, "w"), ensure_ascii=False, indent=1)
    set_status("haftalik", "tamam", f"Haftalık rapor hazır ({rapor['hafta']}, {kaynak_ai})"); print(ozet_metni)


if __name__ == "__main__":
    main()
