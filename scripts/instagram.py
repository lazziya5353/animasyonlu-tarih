"""Instagram'ın resmi API'si (Instagram ile Giriş yolu, ücretsiz). Yayıncı, Analist ve Yorum ajanları kullanır.
Gerekli GitHub secret'ları: IG_TOKEN (uzun ömürlü erişim anahtarı), IG_USER_ID (Instagram profesyonel hesap kimliği).
Kurulum: docs/YAYIN_KURULUM.md"""
import os, json, time, urllib.request, urllib.parse, urllib.error

HOST = os.environ.get("IG_API_HOST") or "graph.instagram.com"
SURUM = os.environ.get("IG_API_VERSION") or "v25.0"


class IGHata(Exception):
    pass


def hazir():
    return bool(os.environ.get("IG_TOKEN") and os.environ.get("IG_USER_ID"))


def _istek(method, yol, params=None, json_govde=None, deneme=3):
    if not hazir(): raise IGHata("IG_TOKEN / IG_USER_ID tanımlı değil (kurulum: docs/YAYIN_KURULUM.md)")
    params = dict(params or {})
    url = f"https://{HOST}/{SURUM}/{yol.lstrip('/')}"
    headers = {"Authorization": f"Bearer {os.environ['IG_TOKEN']}"}
    data = None
    if method == "GET":
        if params: url += "?" + urllib.parse.urlencode(params)
    elif json_govde is not None:
        data = json.dumps(json_govde).encode(); headers["content-type"] = "application/json"
    else:
        data = urllib.parse.urlencode(params).encode(); headers["content-type"] = "application/x-www-form-urlencoded"
    for k in range(deneme):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=120))
        except urllib.error.HTTPError as e:
            govde = e.read().decode()[:400]
            if e.code in (500, 502, 503) and k < deneme - 1: time.sleep(10 * (k + 1)); continue
            try: mesaj = json.loads(govde).get("error", {}).get("message", govde)
            except Exception: mesaj = govde
            raise IGHata(f"Instagram {e.code}: {mesaj}")
        except urllib.error.URLError as e:
            if k < deneme - 1: time.sleep(5); continue
            raise IGHata(f"Instagram'a ulaşılamadı: {e}")


def get(yol, **p): return _istek("GET", yol, p)
def post(yol, **p): return _istek("POST", yol, p)
def uid(): return os.environ["IG_USER_ID"]


def hesap():
    return get("me", fields="user_id,username,followers_count,media_count")


def baglan_host():
    """Token Instagram ile Giriş ya da Facebook ile Giriş olabilir; çalışan API adresini seçer."""
    global HOST
    son = None
    for h in [HOST, "graph.facebook.com" if HOST != "graph.facebook.com" else "graph.instagram.com"]:
        HOST = h
        try: get(uid(), fields="id,username"); return h
        except IGHata as e: son = e
    raise son


def yayin_kotasi():
    """Son 24 saatte API ile yapılan paylaşım sayısı (limit 25). Bilinmiyorsa None."""
    try:
        d = (get(f"{uid()}/content_publishing_limit", fields="quota_usage,config").get("data") or [{}])[0]
        return d.get("quota_usage"), (d.get("config") or {}).get("quota_total", 25)
    except IGHata:
        return None, 25


def reels_yayinla(video_url, aciklama, kapak_ms=None, log=print, akisa=True, kapak_url=None, deneme=False):
    """Herkese açık (kısa süreli imzalı da olabilir) bir video adresinden Reels paylaşır. Döner: {"id", "permalink"}
    deneme=True: sadece kap oluşturur ve işlenmesini bekler, PAYLAŞMAZ."""
    p = {"media_type": "REELS", "video_url": video_url, "caption": aciklama[:2200], "share_to_feed": "true" if akisa else "false"}
    if kapak_url: p["cover_url"] = kapak_url
    elif kapak_ms is not None: p["thumb_offset"] = str(int(kapak_ms))
    cont = post(f"{uid()}/media", **p)["id"]; log(f"Kap oluşturuldu: {cont}")
    for k in range(40):                                   # en fazla ~10 dk bekle
        time.sleep(15)
        st = get(cont, fields="status_code,status")
        log(f"Durum: {st.get('status_code')}")
        if st.get("status_code") == "FINISHED": break
        if st.get("status_code") in ("ERROR", "EXPIRED"): raise IGHata(f"Instagram videoyu işleyemedi: {st.get('status') or st.get('status_code')}")
    else:
        raise IGHata("Instagram videoyu 10 dakikada işleyemedi")
    if deneme: return {"id": None, "kap": cont, "permalink": None, "deneme": True}
    mid = post(f"{uid()}/media_publish", creation_id=cont)["id"]
    bilgi = get(mid, fields="permalink,timestamp")
    return {"id": mid, "permalink": bilgi.get("permalink"), "zaman": bilgi.get("timestamp")}


def son_gonderiler(n=25):
    return get(f"{uid()}/media", fields="id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count", limit=n).get("data", [])


METRIKLER = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions"]


def istatistik(media_id):
    """Instagram metrik adlarını zaman zaman değiştiriyor; desteklenmeyeni çıkarıp tekrar dener."""
    m = list(METRIKLER)
    while m:
        try:
            r = get(f"{media_id}/insights", metric=",".join(m))
            return {x["name"]: (x.get("values") or [{}])[0].get("value", x.get("total_value", {}).get("value")) for x in r.get("data", [])}
        except IGHata as e:
            bozuk = next((x for x in m if x in str(e)), None)
            if not bozuk: return {}
            m.remove(bozuk)
    return {}


def yorumlar(media_id):
    return get(f"{media_id}/comments", fields="id,text,username,timestamp,like_count,hidden", limit=50).get("data", [])


def yanitla(comment_id, mesaj): return post(f"{comment_id}/replies", message=mesaj[:2000])
def gizle(comment_id): return post(comment_id, hide="true")



def anahtar_hatasi(e):
    """Süresi dolmuş/iptal anahtar mı? (Meta hata kodu 190) — panele anlaşılır mesaj yazmak için."""
    t = str(e).lower()
    return "190" in t or "expired" in t or "session has" in t or "invalid oauth" in t or "access token" in t
