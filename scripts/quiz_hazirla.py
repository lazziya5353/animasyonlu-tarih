#!/usr/bin/env python3
"""Her Harfe quiz hazirligi (quiz.yml, ses oncesi): seslendirme_metni sahnelerden yeniden kurulur (sayilar yaziyla,
kural 1) ve aciklama/hashtag bossa temaya gore (tarih/spor) hazir sablonla doldurulur. Kullanim: quiz_hazirla.py <slug>"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sayi_yazi import metni_yaziya

ACIKLAMA = {
    "tarih": ("Her harfe bir tarih sorusu! 🏛️\n\n{n} harf, {n} soru. Bakalım kaçını bileceksin? 🤔\nVideoyu durdurmak yok, puanını yorumlara yaz 👇\n\n{n}/{n} yapan gerçek tarih kurdu 🏆",
              "#tarih #quiz #tarihquiz #bilgiyarışması #genelkültür #türktarihi #osmanlı #herharfebirsoru #keşfet #reels"),
    "spor": ("Her harfe bir spor sorusu! ⚽\n\n{n} harf, {n} soru. Bakalım kaçını bileceksin? 🤔\nVideoyu durdurmak yok, puanını yorumlara yaz 👇\n\n{n}/{n} yapan gerçek futbol ansiklopedisi 🏆",
             "#futbol #spor #quiz #futbolquiz #süperlig #millitakım #bilgiyarışması #genelkültür #herharfebirsoru #galatasaray #fenerbahçe #beşiktaş #trabzonspor #keşfet #reels"),
}

def main(slug):
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects", slug, "script.json")
    S = json.load(open(p))
    if not S.get("otomatik"): print("otomatik degil, dokunulmadi"); return   # eski projelerin metni/sesi degismesin
    tema = "spor" if S.get("tema") == "spor" else "tarih"
    S["seslendirme_metni"] = metni_yaziya("\n".join(x["lines"][0] for x in S["sahneler"]))
    n = (len(S["sahneler"]) - 2)//2
    if not S.get("aciklama"): S["aciklama"] = ACIKLAMA[tema][0].format(n=n)
    if not S.get("hashtagler"): S["hashtagler"] = ACIKLAMA[tema][1]
    json.dump(S, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"{slug}: {n} soru, tema {tema}, seslendirme_metni {len(S['seslendirme_metni'])} karakter")

if __name__ == "__main__": main(sys.argv[1])
