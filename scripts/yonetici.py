"""Yönetici ajan: panelden yazılan serbest mesajı okur, hangi işin yapılacağına karar verir ve ilgili ajanları çalıştırır.
Yapabildikleri (başka bir şey yapamaz): yeni video metni yazdırmak, metin/başlık/kapanış/açıklama düzenlemek, görsel yeniden ürettirmek,
ses ve video üretmek, kontrol çalıştırmak, durumu anlatmak. Silme ve paylaşım yapmaz.
Kullanım (GitHub Actions): python scripts/yonetici.py --mesaj "..." [--slug proje]
"""
import os, sys, json, re, argparse, subprocess, datetime, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import yazar, extract_json, set_status, ROOT

GECMIS = os.path.join(ROOT, "data", "yonetici.json")
WF = {"senarist": "write-script.yml", "ses": "generate-assets.yml", "gorsel": "generate-assets.yml", "video": "render.yml", "kontrol": "kontrol.yml"}


def sh(*a, check=True):
    r = subprocess.run(a, capture_output=True, text=True)
    if check and r.returncode: raise RuntimeError(f"{' '.join(a[:3])}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def kaydet(mesaj):
    sh("git", "config", "user.name", "tarih-ajan"); sh("git", "config", "user.email", "ajan@users.noreply.github.com")
    sh("git", "add", "-A", "projects", "data")
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode:
        sh("git", "commit", "-m", mesaj)
        for _ in range(3):
            if subprocess.run(["git", "pull", "--rebase", "-q"]).returncode != 0:
                subprocess.run(["git", "rebase", "--abort"]); subprocess.run(["git", "pull", "--no-rebase", "--no-edit", "-X", "ours", "-q"])
            if subprocess.run(["git", "push", "-q"]).returncode == 0: return
            time.sleep(3)


def calistir(wf, **girdi):
    args = ["gh", "workflow", "run", WF[wf]]
    for k, v in girdi.items():
        if v not in (None, ""): args += ["-f", f"{k}={v}"]
    sh(*args)


def bekle(wf, once):
    """'once' zamanından sonra başlayan son çalıştırmanın bitmesini bekler (en fazla 25 dk)."""
    for _ in range(150):
        time.sleep(10)
        j = json.loads(sh("gh", "run", "list", "--workflow", WF[wf], "-L", "3", "--json", "databaseId,status,conclusion,createdAt"))
        j = [x for x in j if x["createdAt"] >= once]
        if j and j[0]["status"] == "completed": return j[0]["conclusion"] == "success"
    return False


def proje_oku(slug):
    d = os.path.join(ROOT, "projects", slug)
    sc = json.load(open(os.path.join(d, "script.json"), encoding="utf-8")) if os.path.exists(os.path.join(d, "script.json")) else None
    pj = json.load(open(os.path.join(d, "project.json"), encoding="utf-8")) if os.path.exists(os.path.join(d, "project.json")) else None
    return d, sc, pj


def proje_yaz(d, sc, pj):
    if sc is not None: json.dump(sc, open(os.path.join(d, "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if pj is not None: json.dump(pj, open(os.path.join(d, "project.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def baglam(mesaj, slug):
    pd = os.path.join(ROOT, "projects"); projeler = []
    for s in sorted(os.listdir(pd), key=lambda s: -os.path.getmtime(os.path.join(pd, s))):
        _, sc, _ = proje_oku(s)
        if sc: projeler.append({"slug": s, "baslik": sc.get("baslik", ""), "durum": sc.get("durum", ""), "sahne": len(sc.get("sahneler", [])),
                                "ses": os.path.exists(os.path.join(pd, s, "ses.wav"))})
    m = mesaj.lower(); ayrinti = []
    secili = [p for p in projeler if p["slug"] == slug or any(w in m for w in re.split(r"[-\s]", p["slug"]) if len(w) > 4)][:3] or projeler[:2]
    for p in secili:
        _, sc, pj = proje_oku(p["slug"])
        ayrinti.append({"slug": p["slug"], "baslik": sc.get("baslik"), "kapanis": sc.get("outro"), "aciklama": (sc.get("paylasim") or sc.get("aciklama") or "")[:300],
                        "sahneler": [{"no": i + 1, "metin": s.get("lines"), "buyuk_yazi": s.get("big"), "alt_yazi": s.get("sub"), "gorsel": (s.get("prompt") or "")[:160]}
                                     for i, s in enumerate(sc.get("sahneler", []))]})
    return projeler[:25], ayrinti


SISTEM = """Sen @animasyon.tarih Instagram sayfasının video ajanlarını yöneten "yönetici ajan"sın. Kullanıcı panelden Türkçe, serbest bir mesaj yazar.
Görevin: mesajı anla, aşağıdaki işlemlerden gerekenleri seç ve kısa, samimi bir Türkçe cevap yaz (kullanıcıya "kral" diye hitap edebilirsin).
Sadece bu işlemleri kullanabilirsin; başka bir şey (silme, paylaşım, ayar) isteniyorsa kibarca yapamadığını söyle.

İşlemler (JSON):
- {"tip":"yeni_video","konu":"...","notlar":"süre, ton, odak gibi istekler","tarih":""}  → senarist yeni metin yazar, kullanıcı panelde onaylar
- {"tip":"metin_duzenle","slug":"...","sahne":N,"satirlar":["cümle 1","cümle 2"]}  → o sahnenin seslendirme cümleleri (yıllar rakamla yazılabilir)
- {"tip":"yazi_duzenle","slug":"...","sahne":N,"buyuk_yazi":"...","alt_yazi":"..."}  → ekrandaki büyük başlık / alt başlık (birini boş bırakırsan değişmez)
- {"tip":"kapanis_duzenle","slug":"...","baslik":"...","satir":"..."}  → videonun sonundaki kapanış yazısı
- {"tip":"aciklama_duzenle","slug":"...","metin":"..."}  → Instagram paylaşım açıklaması (hashtagler dahil)
- {"tip":"gorsel_yenile","slug":"...","sahne":N,"prompt":"İngilizce yeni görsel tarifi (boşsa eskisi)"}  → o sahnenin görselini Gemini yeniden üretir
- {"tip":"ses_uret","slug":"..."}   - {"tip":"video_uret","slug":"..."}   - {"tip":"kontrol","slug":"..."}
Kurallar: metin_duzenle yaptıysan sesi yeniden üretmek gerekir; kullanıcı videoyu da istiyorsa "ardindan_video": true ekle (ses biter, video kendiliğinden üretilir).
Yazı/kapanış/görsel değişikliğinden sonra video isteniyorsa video_uret ekle. Hangi proje kastedildiği belirsizse işlem yapma, sor.
Bilgi sorularında (ör. hangi videolar hazır) işlem listesi boş kalır, cevapta anlatırsın.
Sadece şu JSON'u döndür: {"cevap":"...","islemler":[...],"ardindan_video":false}"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mesaj", required=True); ap.add_argument("--slug", default=""); a = ap.parse_args()
    gec = json.load(open(GECMIS, encoding="utf-8")) if os.path.exists(GECMIS) else {"mesajlar": []}
    simdi = lambda: datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    gec["mesajlar"].append({"kim": "sen", "metin": a.mesaj[:1500], "zaman": simdi()})
    set_status("yonetici", "calisiyor", "Mesajın işleniyor")
    projeler, ayrinti = baglam(a.mesaj, a.slug)
    onceki = [f"{m['kim']}: {m['metin'][:300]}" for m in gec["mesajlar"][-7:-1]]
    user = (f"Son konuşma:\n" + "\n".join(onceki) + f"\n\nYENİ MESAJ: {a.mesaj}\n" + (f"(Panelde açık proje: {a.slug})\n" if a.slug else "") +
            f"\nProjeler (en yeni önce): {json.dumps(projeler, ensure_ascii=False)}\n\nİlgili projelerin ayrıntısı: {json.dumps(ayrinti, ensure_ascii=False)}")
    try:
        plan = extract_json(yazar(SISTEM, user, "yonetici", max_tokens=3000), "yonetici")
    except Exception as e:
        plan = {"cevap": f"Mesajını işleyemedim: {e}", "islemler": []}
    yapilan, hatalar, ses_bekle, video_bekle = [], [], [], set()
    for op in (plan.get("islemler") or [])[:8]:
        try:
            tip = op.get("tip"); slug = op.get("slug", "")
            if tip != "yeni_video":
                if not re.fullmatch(r"[a-z0-9-]{1,60}", slug or "") or not os.path.isdir(os.path.join(ROOT, "projects", slug)): raise ValueError(f"proje bulunamadı: {slug}")
                d, sc, pj = proje_oku(slug)
            if tip == "yeni_video":
                calistir("senarist", konu=op.get("konu", "")[:300], tarih=op.get("tarih", "")[:40], notlar=op.get("notlar", "")[:300]); yapilan.append(f"Senarist çalıştı: {op.get('konu')}")
            elif tip == "metin_duzenle":
                i = int(op["sahne"]) - 1; L = [str(x).strip()[:400] for x in op.get("satirlar", []) if str(x).strip()][:6]
                if not L or not (0 <= i < len(sc["sahneler"])): raise ValueError("geçersiz sahne/metin")
                sc["sahneler"][i]["lines"] = L; sc.pop("seslendirme_metni_ozel", None)
                sc["seslendirme_metni"] = "\n".join(l for s in sc["sahneler"] for l in s["lines"])
                if pj and i < len(pj.get("scenes", [])): pj["scenes"][i]["lines"] = L; [s.update(start=None, end=None) for s in pj["scenes"]]; pj.pop("captions", None)
                proje_yaz(d, sc, pj); ses_bekle.append(slug); yapilan.append(f"{slug}: {i + 1}. sahne metni değişti")
            elif tip == "yazi_duzenle":
                i = int(op["sahne"]) - 1
                for k_op, k in (("buyuk_yazi", "big"), ("alt_yazi", "sub")):
                    if op.get(k_op) is not None and str(op.get(k_op)) != "":
                        v = str(op[k_op])[:60]; sc["sahneler"][i][k] = v
                        if pj: pj["scenes"][i][k] = v
                proje_yaz(d, sc, pj); yapilan.append(f"{slug}: {i + 1}. sahne yazısı değişti")
            elif tip == "kapanis_duzenle":
                o = dict(sc.get("outro") or {})
                if op.get("baslik"): o["title"] = str(op["baslik"])[:40]
                if op.get("satir"): o["line"] = str(op["satir"])[:80]
                sc["outro"] = o
                if pj: pj["outro_plan"] = o; pj.pop("outro", None)
                proje_yaz(d, sc, pj); yapilan.append(f"{slug}: kapanış yazısı değişti")
            elif tip == "aciklama_duzenle":
                sc["paylasim"] = str(op.get("metin", ""))[:2200]; proje_yaz(d, sc, None); yapilan.append(f"{slug}: açıklama güncellendi")
            elif tip == "gorsel_yenile":
                i = int(op["sahne"]) - 1
                if op.get("prompt"):
                    p = str(op["prompt"])[:900]; sc["sahneler"][i]["prompt"] = p
                    sc["sahneler"][i]["prompt_tam"] = p + ", cinematic film still, photorealistic, vertical 9:16, no text, no watermark"
                    proje_yaz(d, sc, None)
                yapilan.append(f"{slug}: {i + 1}. görsel yeniden üretilecek"); op["_gorsel"] = i + 1
            elif tip == "ses_uret": ses_bekle.append(slug)
            elif tip == "video_uret": video_bekle.add(slug)
            elif tip == "kontrol": op["_kontrol"] = True
            else: raise ValueError(f"bilinmeyen işlem {tip}")
        except Exception as e:
            hatalar.append(f"{op.get('tip')}: {e}")
    gec["mesajlar"].append({"kim": "ajan", "metin": str(plan.get("cevap", ""))[:2000], "islemler": yapilan, "hatalar": hatalar, "zaman": simdi()})
    gec["mesajlar"] = gec["mesajlar"][-60:]
    json.dump(gec, open(GECMIS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    kaydet(f"Yönetici: {a.mesaj[:60]}")              # değişiklikler repoya girsin, ajanlar güncel hâli görsün
    ardindan = bool(plan.get("ardindan_video")); once_g = simdi()
    for op in plan.get("islemler") or []:
        if op.get("_gorsel"): calistir("gorsel", slug=op["slug"], only=str(op["_gorsel"]))
        if op.get("_kontrol"): calistir("kontrol", slug=op["slug"], asama="hepsi")
    for slug in dict.fromkeys(ses_bekle):
        once = simdi(); calistir("ses", slug=slug, ses="1")
        if ardindan or slug in video_bekle:
            video_bekle.discard(slug)
            if bekle("ses", once): calistir("video", slug=slug); yapilan.append(f"{slug}: ses bitti, video üretiliyor")
            else: hatalar.append(f"{slug}: ses üretilemedi, video başlatılmadı")
    if any(op.get("_gorsel") for op in plan.get("islemler") or []) and video_bekle:
        bekle("gorsel", once_g)                         # görsel işi bitsin, sonra video
    for slug in video_bekle: calistir("video", slug=slug); yapilan.append(f"{slug}: video üretiliyor")
    son = gec["mesajlar"][-1]; son["islemler"] = yapilan; son["hatalar"] = hatalar
    json.dump(gec, open(GECMIS, "w", encoding="utf-8"), ensure_ascii=False, indent=1); kaydet("Yönetici: sonuç")
    set_status("yonetici", "hata" if hatalar else "tamam", (plan.get("cevap") or "")[:140])
    print(json.dumps(gec["mesajlar"][-1], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
