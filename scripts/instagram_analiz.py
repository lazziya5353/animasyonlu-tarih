"""Instagram Analiz (günlük, ücretsiz): hesap, 30 günlük hesap istatistikleri ve son ~50 gönderinin metriklerini
Instagram Graph API'den çeker → data/instagram.json (panelde "INSTAGRAM ANALİZ" bölümü).
Önce graph.instagram.com, olmazsa graph.facebook.com denenir. Desteklenmeyen metrikler sessizce atlanır."""
import os, sys, json, time, datetime, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, set_status
import instagram as IG

OUT = os.path.join(ROOT, "data", "instagram.json")
GUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
MEDYA_MET = ["views", "reach", "saved", "shares", "total_interactions", "likes", "comments"]
REELS_MET = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]
EK_MET = ["follows", "profile_visits"]   # Reels için çoğu zaman desteklenmiyor; olmazsa sessizce atlanır


def oku(p, bos):
    try: return json.load(open(p))
    except Exception: return bos


def deger(x):
    if "total_value" in x: return x["total_value"].get("value")
    v = x.get("values") or []
    return v[0].get("value") if v else None


def medya_ist(mid, metrikler):
    """Önce toplu ister; desteklenmeyen metrik hata verirse tek tek dener."""
    try:
        r = IG.get(f"{mid}/insights", metric=",".join(metrikler))
        return {x["name"]: deger(x) for x in r.get("data", [])}, []
    except IG.IGHata:
        pass
    out, yok = {}, []
    for m in metrikler:
        try:
            r = IG.get(f"{mid}/insights", metric=m)
            for x in r.get("data", []): out[x["name"]] = deger(x)
        except IG.IGHata:
            yok.append(m)
    return out, yok


def hesap_ist(uid, since, until):
    """30 günlük hesap metrikleri; her biri ayrı istenir, olmayan atlanır."""
    sonuc, gunluk, yok = {}, {}, []
    for m, tip in [("reach", "total_value"), ("views", "total_value"), ("profile_views", "total_value"),
                   ("accounts_engaged", "total_value"), ("total_interactions", "total_value"), ("follows_and_unfollows", "total_value")]:
        try:
            r = IG.get(f"{uid}/insights", metric=m, period="day", metric_type=tip, since=since, until=until)
            for x in r.get("data", []): sonuc[x["name"]] = deger(x)
        except IG.IGHata as e:
            yok.append(m); print(f"  hesap metriği yok: {m} ({str(e)[:120]})")
    for m in ["follower_count", "reach"]:
        try:
            r = IG.get(f"{uid}/insights", metric=m, period="day", since=since, until=until)
            for x in r.get("data", []):
                gunluk[x["name"]] = [{"tarih": v.get("end_time", "")[:10], "deger": v.get("value")} for v in x.get("values", [])]
        except IG.IGHata as e:
            if m == "follower_count": yok.append("follower_count (günlük)")
            print(f"  günlük seri yok: {m} ({str(e)[:120]})")
    return sonuc, gunluk, yok


def baglan():
    son = None
    for host in [os.environ.get("IG_API_HOST") or "graph.instagram.com", "graph.facebook.com"]:
        IG.HOST = host
        try:
            h = IG.get(IG.uid(), fields="id,username,name,profile_picture_url,followers_count,follows_count,media_count")
            print(f"Bağlandı: {host}"); return host, h
        except IG.IGHata as e:
            son = e; print(f"{host} olmadı: {str(e)[:160]}")
    raise son


def main():
    if not IG.hazir():
        set_status("instagram", "bekliyor", "IG_TOKEN yok"); print("IG_TOKEN yok; atlandı"); return
    eski = oku(OUT, {})
    simdi = datetime.datetime.now(datetime.timezone.utc)
    out = {"zaman": simdi.strftime("%Y-%m-%dT%H:%M:%SZ"), "gecmis": eski.get("gecmis", [])}
    try:
        host, h = baglan()
    except IG.IGHata as e:
        out.update({k: eski[k] for k in ("hesap", "ozet30", "gunluk", "medya") if k in eski})
        out["hata"] = "Instagram anahtarı geçersiz/süresi dolmuş" if IG.anahtar_hatasi(e) else f"Instagram'a bağlanılamadı: {e}"
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
        set_status("instagram", "hata", out["hata"]); print(out["hata"]); sys.exit(1)
    uid = IG.uid()
    out["host"] = host
    out["hesap"] = {"kullanici": h.get("username"), "ad": h.get("name"), "foto": h.get("profile_picture_url"),
                    "takipci": h.get("followers_count", 0), "takip": h.get("follows_count"), "gonderi": h.get("media_count", 0)}
    until = int(simdi.timestamp()); since = until - 30 * 86400 + 60
    ozet, gunluk, yok = hesap_ist(uid, since, until)
    out["ozet30"] = ozet; out["gunluk"] = gunluk
    # kendi günlük takipçi geçmişimiz (API serisi yoksa grafik buradan çizilir)
    bugun = simdi.strftime("%Y-%m-%d")
    out["gecmis"] = [g for g in out["gecmis"] if g.get("tarih") != bugun][-365:] + [{"tarih": bugun, "takipci": out["hesap"]["takipci"]}]

    medya, sayfa = [], IG.get(f"{uid}/media", fields="id,caption,media_type,media_product_type,permalink,thumbnail_url,media_url,timestamp,like_count,comments_count", limit=50)
    medya += sayfa.get("data", [])
    liste, med_yok = [], set()
    for p in medya[:50]:
        reels = p.get("media_product_type") == "REELS"
        met = MEDYA_MET + (REELS_MET if reels else [])
        st, y = medya_ist(p["id"], met); med_yok.update(y)
        try:
            r = IG.get(f"{p['id']}/insights", metric=",".join(EK_MET))
            for x in r.get("data", []): st[x["name"]] = deger(x)
        except IG.IGHata:
            pass
        ort = st.get("ig_reels_avg_watch_time")
        liste.append({"id": p["id"], "baslik": (p.get("caption") or "").strip().split("\n")[0][:90], "zaman": p.get("timestamp"),
                      "tur": p.get("media_product_type") or p.get("media_type"), "medya_turu": p.get("media_type"), "url": p.get("permalink"),
                      "kapak": p.get("thumbnail_url") or (p.get("media_url") if p.get("media_type") == "IMAGE" else None),
                      "begeni": p.get("like_count", st.get("likes")), "yorum": p.get("comments_count", st.get("comments")),
                      "izlenme": st.get("views"), "erisim": st.get("reach"), "kaydetme": st.get("saved"), "paylasim": st.get("shares"),
                      "etkilesim": st.get("total_interactions"), "ort_izleme_sn": round(ort / 1000, 1) if isinstance(ort, (int, float)) else None,
                      "takip": st.get("follows"), "profil_ziyaret": st.get("profile_visits")})
    liste.sort(key=lambda v: v["izlenme"] or 0, reverse=True)
    out["medya"] = liste

    # en iyi paylaşım saatleri (İstanbul saati, ortalama izlenmeye göre)
    saat = {}
    for v in liste:
        if not v["zaman"] or not v["izlenme"]: continue
        t = datetime.datetime.strptime(v["zaman"][:19], "%Y-%m-%dT%H:%M:%S") + datetime.timedelta(hours=3)
        saat.setdefault(t.hour, []).append(v["izlenme"])
    sira = sorted(saat.items(), key=lambda kv: statistics.mean(kv[1]), reverse=True)
    out["en_iyi_saatler"] = [{"saat": s, "ort_izlenme": round(statistics.mean(v)), "adet": len(v)} for s, v in sira[:3]]
    gun = {}
    for v in liste:
        if v["zaman"] and v["izlenme"]:
            t = datetime.datetime.strptime(v["zaman"][:19], "%Y-%m-%dT%H:%M:%S") + datetime.timedelta(hours=3)
            gun.setdefault(t.weekday(), []).append(v["izlenme"])
    if gun:
        g = max(gun.items(), key=lambda kv: statistics.mean(kv[1]))[0]; out["en_iyi_gun"] = GUN[g]
    if not any(v.get("takip") is not None for v in liste): med_yok.add("follows (gönderi başına)")
    out["desteklenmeyen"] = sorted(set(yok) | med_yok)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    msg = f"{out['hesap']['takipci']} takipçi · {len(liste)} gönderi analiz edildi"
    set_status("instagram", "tamam", msg); print(msg, "| host:", host, "| desteklenmeyen:", out["desteklenmeyen"])


if __name__ == "__main__":
    main()
