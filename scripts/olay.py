"""Canlı olay bildirimi: ajanlar çalışırken yaptıkları adımları panele (Kurgu Stüdyosu) anlık gönderir.
İşi asla yavaşlatmaz/bozmaz: olaylar arka planda toplu gönderilir, ağ hatası olursa sessizce atlanır.
Kullanım:  from olay import olay;  olay("kurgucu", "yazi", "cümle yerleşti", slug=..., t0=1.2, t1=3.4, sahne=2)
İzin: GitHub Actions'ın kendi GITHUB_TOKEN'ı ile; panel bu anahtarın bu repoya erişimi olduğunu GitHub'a sorarak doğrular."""
import os, json, time, threading, queue, urllib.request, atexit

PANEL = (os.environ.get("PANEL_URL") or "https://animasyonlu-tarih.netlify.app").rstrip("/")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
AKTIF = bool(TOKEN and os.environ.get("GITHUB_ACTIONS") and os.environ.get("OLAY_KAPALI") != "1")
_q = queue.Queue()
_SLUG = os.environ.get("SLUG", "")


def slug_ayarla(s):
    global _SLUG
    _SLUG = s


def olay(ajan, tur, mesaj, slug=None, **veri):
    """tur: yazi | gorsel | efekt | harita | ses | muzik | kontrol | bilgi | ilerleme"""
    if not AKTIF: return
    _q.put({"ajan": ajan, "tur": tur, "mesaj": str(mesaj)[:200], "slug": slug or _SLUG, "z": round(time.time(), 2),
            **{k: v for k, v in veri.items() if v is not None}})


def _gonder(paket):
    by = {}
    for o in paket: by.setdefault(o.get("slug") or "_genel", []).append(o)
    for slug, ol in by.items():
        try:
            req = urllib.request.Request(PANEL + "/api", data=json.dumps({"action": "olay", "slug": slug, "olaylar": ol}).encode(),
                                         headers={"content-type": "application/json", "x-gh-token": TOKEN})
            urllib.request.urlopen(req, timeout=8).read()
        except Exception as e:
            print("(olay gönderilemedi:", str(e)[:80], ")")


def _isci():
    while True:
        paket = [_q.get()]
        time.sleep(0.8)                          # kısa aralıkla gelenleri tek istekte topla
        while not _q.empty() and len(paket) < 40: paket.append(_q.get_nowait())
        _gonder(paket)
        for _ in paket: _q.task_done()


if AKTIF:
    threading.Thread(target=_isci, daemon=True).start()

    @atexit.register
    def _bitir():
        t = time.time() + 12
        while _q.unfinished_tasks and time.time() < t: time.sleep(0.2)
