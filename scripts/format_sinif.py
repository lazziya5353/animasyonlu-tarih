"""Video formatı sınıflandırma (panel ile aynı kurallar: data/format_kurallari.json)."""
import os, re, json
from common import ROOT

FORMATLAR = ["Quiz", "Harflerden Bul", "Padişah serisi", "Harita/Gezi/Yer", "Diğer"]


def kurallar():
    try: return json.load(open(os.path.join(ROOT, "data", "format_kurallari.json"))).get("sira", [])
    except Exception: return []


def sinifla(metin, K=None):
    t = (metin or "").lower()
    for k in (K if K is not None else kurallar()):
        if any(w in t for w in k.get("kelimeler", [])) or any(re.search(d, t) for d in k.get("desenler", [])): return k["ad"]
    return "Diğer"
