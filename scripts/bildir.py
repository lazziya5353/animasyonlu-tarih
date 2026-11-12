"""Telefona bildirim gönderir (panelde 🔔 açılmışsa). İşi asla bozmaz: hata olursa sessizce geçer.
Kullanım: python scripts/bildir.py "🎬 Video hazır" "{ad} izlemeye hazır" --slug galata-kulesi-1348-2026
{ad} yerine panel projenin başlığını koyar."""
import os, sys, json, argparse, urllib.request
a = argparse.ArgumentParser(); a.add_argument("baslik"); a.add_argument("metin"); a.add_argument("--slug", default=os.environ.get("SLUG", "")); a = a.parse_args()
T = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
if not T: print("(bildirim: anahtar yok, atlandı)"); sys.exit(0)
panel = (os.environ.get("PANEL_URL") or "https://animasyonlu-tarih.netlify.app").rstrip("/")
try:
    r = urllib.request.urlopen(urllib.request.Request(panel + "/api", data=json.dumps({"action": "bildirim", "slug": a.slug, "bildirim": {"baslik": a.baslik, "metin": a.metin}}).encode(),
                               headers={"content-type": "application/json", "x-gh-token": T}), timeout=20)
    print("bildirim:", r.read().decode()[:120])
except Exception as e:
    print("(bildirim gönderilemedi:", str(e)[:120], ")")
