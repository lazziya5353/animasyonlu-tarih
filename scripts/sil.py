"""Panelden silme: 'video' → sadece hazır videoyu (GitHub Release) siler, proje kalır (yeniden üretilebilir).
'hepsi' → projeyi tamamen siler: klasör, video, planlanmış paylaşımlar. Instagram'daki paylaşılmış gönderiye dokunmaz."""
import os, sys, json, re, shutil, subprocess, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, set_status

a = argparse.ArgumentParser(); a.add_argument("--slug", required=True); a.add_argument("--tur", choices=["video", "hepsi"], required=True); a = a.parse_args()
if not re.fullmatch(r"[a-z0-9-]{3,90}", a.slug): sys.exit("geçersiz proje adı")
d = os.path.join(ROOT, "projects", a.slug)
if not os.path.isdir(d): sys.exit(f"{a.slug} diye bir proje yok")

r = subprocess.run(["gh", "release", "delete", f"video-{a.slug}", "--yes", "--cleanup-tag"], capture_output=True, text=True)
print("video:", "silindi" if r.returncode == 0 else "zaten yoktu")
for f in ("onizleme.jpg", "out"):
    p = os.path.join(d, f)
    if os.path.isdir(p): shutil.rmtree(p)
    elif os.path.exists(p): os.remove(p)
if os.path.exists(os.path.join(d, "kontrol", "kurgu.json")): os.remove(os.path.join(d, "kontrol", "kurgu.json"))

if a.tur == "hepsi":
    shutil.rmtree(d)
    k = os.path.join(ROOT, "data", "yayin_kuyrugu.json")      # bu videonun bekleyen paylaşım planları da gitsin
    if os.path.exists(k):
        j = json.load(open(k, encoding="utf-8")); j["isler"] = [x for x in j.get("isler", []) if x.get("slug") != a.slug]
        json.dump(j, open(k, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("proje klasörü silindi")
set_status("kurgucu", "tamam", f"{a.slug}: " + ("proje tamamen silindi" if a.tur == "hepsi" else "video silindi (proje duruyor)"))
