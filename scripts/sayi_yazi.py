"""Seslendirme metninde rakamları Türkçe yazıya çevirir: "1453'te" -> "bin dört yüz elli üçte", "II. Mahmud" -> "İkinci Mahmud"."""
import re
B=["","bir","iki","üç","dört","beş","altı","yedi","sekiz","dokuz"]; O=["","on","yirmi","otuz","kırk","elli","altmış","yetmiş","seksen","doksan"]
def yaz(n):
    if n==0: return "sıfır"
    p=[]
    for d,ad in ((10**9,"milyar"),(10**6,"milyon"),(1000,"bin")):
        if n>=d: k,n=divmod(n,d); p.append(("" if (d==1000 and k==1) else yaz(k)+" ")+ad)
    if n>=100: k,n=divmod(n,100); p.append(("" if k==1 else B[k]+" ")+"yüz")
    if n>=10: p.append(O[n//10]); n%=10
    if n: p.append(B[n])
    return " ".join(p)
SES="aeıioöuü"
def _ek(soz, ek):
    # ekin ünlüsünü sözcüğün son ünlüsüne uydurur; ek zaten uyumluysa olduğu gibi bırakılır (yaklaşık ama okunuş için yeterli)
    return soz + ek
SIRA={"bir":"birinci","iki":"ikinci","üç":"üçüncü","dört":"dördüncü","beş":"beşinci","altı":"altıncı","yedi":"yedinci","sekiz":"sekizinci","dokuz":"dokuzuncu","on":"onuncu","yirmi":"yirminci","otuz":"otuzuncu","kırk":"kırkıncı","elli":"ellinci","altmış":"altmışıncı","yetmiş":"yetmişinci","seksen":"sekseninci","doksan":"doksanıncı","yüz":"yüzüncü","bin":"bininci"}
def sira(n):
    w=yaz(n).split(); w[-1]=SIRA.get(w[-1],w[-1]); return " ".join(w)
def metni_yaziya(t):
    t=re.sub(r"\b(\d+)\. (?=[a-zçğıöşü])", lambda m: sira(int(m.group(1)))+" ", t)
    t=re.sub(r"\bII\. ", "İkinci ", t); t=re.sub(r"\bIII\. ", "Üçüncü ", t); t=re.sub(r"\bIV\. ", "Dördüncü ", t)
    t=re.sub(r"\bMÖ ", "Milattan önce ", t); t=re.sub(r"\bMS ", "Milattan sonra ", t)
    def r(m):
        n=int(m.group(1).replace(".","")); ek=m.group(2) or ""
        return yaz(n)+ek.replace("'","")
    return re.sub(r"(\d{1,3}(?:\.\d{3})+|\d+)('[a-zçğıöşü]+)?", r, t)
