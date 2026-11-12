"""Ortak yardımcılar: Claude API çağrısı, JSON ayıklama, harcama kaydı."""
import os, json, re, time, urllib.request, urllib.error, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USAGE = os.path.join(ROOT, "data", "usage.json")
MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-5-5"
# Tahmini fiyatlar (USD / 1M token). Gerçek fiyat değişirse repo ayarlarından CLAUDE_PRICE_IN / CLAUDE_PRICE_OUT değişkenleriyle güncellenir.
PRICE_IN = float(os.environ.get("CLAUDE_PRICE_IN") or 3.0)
PRICE_OUT = float(os.environ.get("CLAUDE_PRICE_OUT") or 15.0)
PRICE_SEARCH = float(os.environ.get("CLAUDE_PRICE_SEARCH") or 0.01)

def log_usage(agent, service, usd, detail=""):
    os.makedirs(os.path.dirname(USAGE), exist_ok=True)
    data = json.load(open(USAGE)) if os.path.exists(USAGE) else {"kayitlar": []}
    data["kayitlar"].append({"zaman": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "ajan": agent, "servis": service, "usd": round(usd, 4), "detay": detail})
    data["kayitlar"] = data["kayitlar"][-500:]
    json.dump(data, open(USAGE, "w"), ensure_ascii=False, indent=1)

def claude(system, user, agent, max_tokens=6000, web_search=0):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: raise SystemExit("ANTHROPIC_API_KEY tanımlı değil (GitHub > Settings > Secrets).")
    body = {"model": MODEL, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]}
    if web_search: body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": web_search}]
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=600)); break
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:500]
            if e.code in (429, 529, 500) and attempt < 2: time.sleep(20 * (attempt + 1)); continue
            raise SystemExit(f"Claude API hatası {e.code}: {msg}")
    u = r.get("usage", {}); searches = (u.get("server_tool_use") or {}).get("web_search_requests", 0)
    usd = u.get("input_tokens", 0) / 1e6 * PRICE_IN + u.get("output_tokens", 0) / 1e6 * PRICE_OUT + searches * PRICE_SEARCH
    log_usage(agent, "claude", usd, f"{u.get('input_tokens', 0)} giriş / {u.get('output_tokens', 0)} çıkış token, {searches} arama")
    if r.get("stop_reason") == "max_tokens": print("UYARI: cevap token sınırında kesildi; bloklar:", [b.get("type") for b in r.get("content", [])])
    return "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")

def extract_json(txt, agent="ajan"):
    # Ham cevabı sakla: ayrıştırma bozulsa bile ödenen cevap kaybolmasın.
    os.makedirs(os.path.join(ROOT, "data", "ham"), exist_ok=True)
    open(os.path.join(ROOT, "data", "ham", f"{agent}.txt"), "w").write(txt)
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", txt, re.S)
    s = m.group(1) if m else txt[txt.find("{"): txt.rfind("}") + 1]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        import json_repair  # tırnak/virgül hatalarını onarır
        out = json_repair.loads(s)
        if not isinstance(out, dict) or not out: raise
        return out

def slugify(s):
    import unicodedata
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    s = unicodedata.normalize("NFKD", s.translate(tr)).encode("ascii", "ignore").decode()   # â→a, î→i, û→u ("hikâyesi" bölünmesin)
    s = re.sub(r"['’`]", "", s)                                                              # "Üsküdar'ın" → uskudarin
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60].strip("-")

def set_status(agent, durum, mesaj, cikti=None):
    p = os.path.join(ROOT, "data", "status.json"); os.makedirs(os.path.dirname(p), exist_ok=True)
    data = json.load(open(p)) if os.path.exists(p) else {}
    eski = data.get(agent) or {}
    if durum == "bekliyor" and eski.get("durum") == durum and eski.get("mesaj") == mesaj: return  # her gün aynı "bağlı değil" kaydıyla repo kirlenmesin
    data[agent] = {"durum": durum, "mesaj": mesaj, "cikti": cikti, "zaman": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    json.dump(data, open(p, "w"), ensure_ascii=False, indent=1)


def yazar(system, user, agent, max_tokens=6000, web_search=0):
    """Metin yazan ajanlar için: varsayılan Claude API (doğruluk için). YAZAR=gemini ise ya da Claude anahtarı yoksa Gemini (ücretsiz kota, Google aramalı)."""
    if os.environ.get("YAZAR", "claude") == "claude" and os.environ.get("ANTHROPIC_API_KEY"):
        return claude(system, user, agent, max_tokens=max_tokens, web_search=web_search)
    import gemini
    txt = gemini.sor([user], json_cevap=False, sicaklik=0.5, sure=300, arama=bool(web_search), sistem=system)
    try: log_usage(agent, "gemini-metin", 0.0, "Gemini ücretsiz kota")
    except Exception: pass
    return txt
