"""Analist ajanı (haftalık, ücretsiz): Instagram'dan (ve varsa YouTube'dan) izlenme istatistiklerini toplar,
en iyi videoları ve en iyi paylaşım gün/saatini çıkarır → data/analiz.json (panelde gösterilir, araştırmacı da okur)."""
import os, sys, json, datetime, statistics, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, set_status
import instagram as IG

OUT = os.path.join(ROOT, "data", "analiz.json")
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def oku(p, bos):
    try: return json.load(open(p))
    except Exception: return bos


def youtube():
    key, kanal = os.environ.get("YT_API_KEY"), os.environ.get("YT_CHANNEL_ID")
    if not (key and kanal): return None
    g = lambda yol, **p: json.load(urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{yol}?" + urllib.parse.urlencode({**p, "key": key}), timeout=60))
    ch = g("channels", part="statistics,contentDetails", id=kanal)["items"][0]
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [x["contentDetails"]["videoId"] for x in g("playlistItems", part="contentDetails", playlistId=up, maxResults=25).get("items", [])]
    vids = g("videos", part="snippet,statistics", id=",".join(ids)).get("items", []) if ids else []
    return {"abone": int(ch["statistics"].get("subscriberCount", 0)), "videolar": [
        {"baslik": v["snippet"]["title"], "zaman": v["snippet"]["publishedAt"], "izlenme": int(v["statistics"].get("viewCount", 0)),
         "begeni": int(v["statistics"].get("likeCount", 0)), "yorum": int(v["statistics"].get("commentCount", 0)), "url": f"https://youtube.com/shorts/{v['id']}"} for v in vids]}


def main():
    eski = oku(OUT, {}); out = {"zaman": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "gecmis": eski.get("gecmis", [])[-52:]}
    notlar = []
    if IG.hazir():
        try:
            h = IG.hesap(); posts = [p for p in IG.son_gonderiler(30) if p.get("media_product_type") in ("REELS", None) or p.get("media_type") == "VIDEO"]
            yay = {v.get("instagram", {}).get("id"): k for k, v in oku(os.path.join(ROOT, "data", "yayinlar.json"), {}).items()}
            liste = []
            for p in posts:
                st = IG.istatistik(p["id"])
                izl = st.get("views") or 0; eri = st.get("reach") or 0
                liste.append({"id": p["id"], "proje": yay.get(p["id"]), "baslik": (p.get("caption") or "").split("\n")[0][:80], "url": p.get("permalink"),
                              "zaman": p.get("timestamp"), "izlenme": izl, "erisim": eri, "begeni": st.get("likes", p.get("like_count", 0)),
                              "yorum": st.get("comments", p.get("comments_count", 0)), "paylasim": st.get("shares", 0), "kaydetme": st.get("saved", 0),
                              "etkilesim_orani": round(100 * ((st.get("shares") or 0) + (st.get("saved") or 0) + (st.get("likes") or 0)) / eri, 1) if eri else None})
            liste.sort(key=lambda x: x["izlenme"] or 0, reverse=True)
            out["instagram"] = {"kullanici": h.get("username"), "takipci": h.get("followers_count", 0), "gonderi": h.get("media_count", 0), "videolar": liste}
            onceki = next((g for g in reversed(out["gecmis"]) if g.get("takipci") is not None), None)
            out["gecmis"].append({"zaman": out["zaman"], "takipci": h.get("followers_count", 0)})
            if onceki: notlar.append(f"Takipçi: {h.get('followers_count', 0)} ({h.get('followers_count', 0) - onceki['takipci']:+d} geçen kontrole göre)")
            if liste:
                notlar.append(f"En çok izlenen: “{liste[0]['baslik']}” · {liste[0]['izlenme']} izlenme")
                saat = {}
                for v in liste:
                    if not v["zaman"] or not v["izlenme"]: continue
                    t = datetime.datetime.strptime(v["zaman"][:19], "%Y-%m-%dT%H:%M:%S") + datetime.timedelta(hours=3)   # İstanbul
                    saat.setdefault((t.weekday(), t.hour), []).append(v["izlenme"])
                if len(liste) >= 5 and saat:
                    (g, s), vs = max(saat.items(), key=lambda kv: statistics.mean(kv[1]))
                    out["en_iyi_zaman"] = f"{GUNLER[g]} {s:02d}.00"; notlar.append(f"En iyi paylaşım zamanı şimdilik: {out['en_iyi_zaman']}")
        except IG.IGHata as e:
            notlar.append("Instagram anahtarının süresi dolmuş, yenilenmeli" if IG.anahtar_hatasi(e) else f"Instagram verisi alınamadı: {e}")
    try:
        yt = youtube()
        if yt: out["youtube"] = yt; notlar.append(f"YouTube: {yt['abone']} abone")
    except Exception as e:
        notlar.append(f"YouTube verisi alınamadı: {e}")
    if not IG.hazir() and "youtube" not in out:
        set_status("analist", "bekliyor", "Instagram/YouTube bağlı değil: docs/YAYIN_KURULUM.md"); print("Bağlı hesap yok; atlandı"); return
    out["notlar"] = notlar
    os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    set_status("analist", "tamam", " · ".join(notlar[:2]) or "Rapor hazır"); print("\n".join(notlar))


if __name__ == "__main__":
    main()
