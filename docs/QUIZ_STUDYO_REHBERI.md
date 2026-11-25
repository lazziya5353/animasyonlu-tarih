# Quiz Stüdyo Rehberi (7 yeni format, tarih + spor teması)

Bu rehber Quiz Stüdyo'nun tek kaynağıdır: panel, ajanlar (senarist `write_script.py` bu dosyayı quiz projelerinde otomatik yükler) ve elle üretim aynı kuralları kullanır. Eski iki format kendi rehberindedir: **Her Harfe Bir Soru** → [QUIZ_REHBERI.md](QUIZ_REHBERI.md), **Harflerden Bul** → [HARF_BUL_REHBERI.md](HARF_BUL_REHBERI.md). Genel kurallar: [URETIM_KURALLARI.md](URETIM_KURALLARI.md).

Her şey ücretsizdir: GitHub Actions + Gemini ücretsiz kotası (ses, isteğe bağlı arka plan, isteğe bağlı soru taslağı). Claude gerekmez.

---

## 1. Akış

1. **Sorular:** Panel → sekme (ANİMASYON TARİH VİDEO ya da SPOR TARİHİ VİDEO) → **QUIZ** → format seç.
   - **Elle yaz:** her format için yapılandırılmış form (satır ekle/sil, doğrulama).
   - **Ajan hazırlasın:** konu + kolay/orta/zor sayısı. Netlify'da `GEMINI_API_KEY` varsa panel fonksiyonu Gemini'ye taslak yazdırır, ardından Google aramalı ikinci bir **doğruluk kontrolü** geçişi yapar. Yoksa `quiz_taslak.yml` (secret `GEMINI_API_KEY`) aynı istemleri `scripts/quiz_taslak.py` ile çalıştırır, sonucu `projects/_taslak/<id>.json` dosyasına yazar; panel bekler ve taslağı forma doldurur.
   - Taslak her zaman düzenlenebilir. **Onay ("Onayla ve Üret") olmadan video üretilmez.**
2. **Üret:** panel `projects/<format>-<n>/script.json` (+ logo/arka plan/soru görselleri `images/`) yazar ve `quiz_studyo.yml`'ı başlatır. Durum panelde "Üretimler" listesinde görünür; bitince kapak + video açılır.
3. **Elle / ajan ile (panelsiz):** klasörü aç, script.json yaz, commit at, başlat:
   ```
   gh api -X POST repos/lazziya5353/animasyonlu-tarih/actions/workflows/quiz_studyo.yml/dispatches -f ref=main -f 'inputs[slug]=yili-tahmin-2'
   ```
   `quiz_studyo.yml` adımları: `quiz_studyo.py hazirla` (şema doğrulama + ses satırları) → arka plan (istenirse Gemini) → ses (`quiz_studyo_ses.py`) → `quiz_studyo.py video` + `kapak` → `quiz_studyo_kontrol.py --bekci` → release `video-<slug>` (`video.mp4`, `kapak.jpg`). Süre ~8–10 dk. **Aynı concurrency grubunda (repo-yazma) bekleyen yalnızca 1 iş tutulur: birden çok video için bir öncekinin bitmesini bekleyip sırayla başlat.**
4. **Yerel hızlı önizleme (ses yok, saniyeler):** `python scripts/quiz_studyo.py onizle projects/<slug>/script.json onizle.jpg` → her soru için (soru+sayaç, cevap) kareleri. Kural kontrolü: `python scripts/quiz_studyo.py dogrula projects/<slug>/script.json`.
5. **Instagram'a asla otomatik paylaşılmaz.** Paylaşım ayrı ve elle onaylıdır.

## 2. script.json (ortak alanlar)

| Alan | Açıklama |
|---|---|
| `slug` | Klasör adı (`<format>-<n>`), örn. `bu-kim-2` |
| `format` | `hangisi-once` · `dogru-yanlis` · `bu-kim` · `haritada-bul` · `yili-tahmin` · `emoji-tarih` · `kelime-eksik` |
| `tema` | `tarih` (kahverengi/altın, Cinzel + Montserrat) ya da `spor` (lacivert/koyu yeşil stadyum, Bebas Neue + Barlow Condensed) |
| `takim` | Sadece spor: `{"ana": "#RRGGBB", "ikinci": "#RRGGBB"}` (isteğe bağlı) |
| `logo` | İsteğe bağlı `images/logo.png` (başlığın üstünde). Logo olmadan da çalışır. |
| `arkaplan` | İsteğe bağlı yüklenen resim `images/arka.jpg` → kapla-kırp, bulanık, %38 parlaklık |
| `arkaplan_uret` | İsteğe bağlı sahne tarifi: workflow Gemini (yoksa ücretsiz yedek) ile `images/arka.jpg` çizer. Çizilemezse tema zemini. |
| `sorular` | 6–15 soru (video için **8–15** önerilir; test videoları 6–8). Her soruda `zorluk`: `kolay`/`orta`/`zor` |
| `giris`, `kapanis` | İsteğe bağlı. Boşsa: "<Format>! N soru, bakalım kaçını bileceksin?" / "Kaçını bildin? Yorumlara yaz!" |
| `bolum` | İsteğe bağlı, kapakta "N. BÖLÜM" |
| `kaynaklar`, `kontrol_notlari` | Doğrulama notları (iki kaynak) |

`hazirla` adımı `sahneler` (her ses satırı bir sahne), `seslendirme_metni` (sayılar yazıyla) ve temanın `ses_stil`'ini ekler; elle yazma.

Handle ve tema ayarları tek dosyada: **`config/quiz_tema.json`** (spor handle şimdilik yer tutucu `@spor.tarihi`; sayfa adı kesinleşince sadece burayı değiştir). Spor sesi aynı Gemini sesi, enerjik spor spikeri stil talimatıyla.

## 3. Format şemaları (soru başına)

Örnekler `dashboard/quiz/semalar.json` içinde de durur (panel ve taslak ajanı oradan okur).

**Hangisi Önce?** `{"a": {"metin": "Malazgirt Savaşı", "yil": 1071, "gorsel": "images/s1a.jpg"?}, "b": {...}, "dogru": "A"}`
- İki kart A/B, isteğe bağlı resim. Cevapta doğru kart yeşil, iki yıl kartlarda ve alt bilgide ("A · 1071 · B · 1176") görünür.
- Yıllar tam sayı ve farklı; `dogru` yılı küçük olan (doğrulama kontrol eder). Olay adı ≤ 6 kelime.

**Doğru mu Yanlış mı?** `{"ifade": "...", "dogru": false, "duzeltme": "Ankara, 13 Ekim 1923'te başkent oldu."}`
- Cevapta kart ve kutu DOĞRU (yeşil) / YANLIŞ (kırmızı); alt bilgi = tek satırlık düzeltme (doğrularda kısa kanıt). Cevap sesi "Doğru!/Yanlış! + düzeltme".
- İfade ≤ 18 kelime, ~yarısı yanlış.

**Bu Kim?** `{"ipuclari": ["...", "...", "..."], "cevap": "Piri Reis", "alt_bilgi": "Osmanlı amirali · ö. 1553", "gorsel": "images/s2.jpg"?}`
- Soru evresinde 3 ipucu, kendi ses satırıyla aynı anda tek tek açılır (sayaçtan önce). Portre varsa soru evresinde bulanık + "?", cevapta net; yoksa genel siluet.
- İpuçlarında cevabın adı/kökü geçmez ("Mimar Sinan" için "baş mimarlık" da sızmadır; doğrulama yakalar). Zordan kolaya sırala.

**Haritada Bul** `{"soru": "...", "secenekler": [{"ad": "Erzurum", "lat": 39.90, "lon": 41.27}, ... 4 adet], "dogru": 1, "alt_bilgi": "...", "min_genislik": 2.5?}`
- `engine/deprem.py` Harita (uydu katmanları) ile yakınlaştırılmış panel, A–D iğneleri; cevapta doğru iğne yeşil nabız atar, yer adı etiketi çıkar.
- Koordinatlar gerçek (ondalık derece). Seçenekler aynı bölgede ama ≥ ~40 km ayrı: iğneler 70 px'ten yakınsa ya da panel dışına düşerse render durur.

**Yılı Tahmin Et** `{"soru": "...", "secenekler": [1919, 1920, 1921, 1923], "dogru": 1, "alt_bilgi": "23 Nisan 1920"}`
- 2x2 yıl ızgarası; doğru yeşil, diğerleri sönük. 4 farklı yıl; doğrunun yerini karıştır.

**Emoji ile Tarih** `{"emoji": ["🐴", "🪵", "⚔️", "🏛️"], "ipucu": "Antik bir hile", "cevap": "Truva Atı", "alt_bilgi": "Homeros · İlyada"}`
- Büyük emojiler Noto Color Emoji ile (workflow fontu indirir; olmazsa apt). 2–6 emoji, **bayrak kullanma**. ZWJ birleşikleri (👨‍🚀) çalışır.
- Tofu koruması: `dogrula` her kod noktasını font cmap'inde arar; renderer her emojiyi çizip renkli piksel ve tek glif genişliği kontrol eder; kontrol betiği karedeki emoji kutusunun dolu olduğuna bakar.

**Bir Kelime Eksik** `{"soz": "Ben size taarruzu emretmiyorum, ___ emrediyorum.", "secenekler": [4], "dogru": 0, "soyleyen": "Mustafa Kemal · Çanakkale 1915"}`
- Sözde tam bir `___`; cevapta boşluk doğru kelimeyle (BÜYÜK harf) dolar, doğru seçenek yeşil, alt bilgi "— söyleyen".
- **Sadece birebir doğru, kaynağı kesin sözler.** Atfı tartışmalı sözler (ör. "Ya ben İstanbul'u alırım...", "Gel, ne olursan ol gel") kullanılmaz. Doğru kelime sözün başka yerinde geçmesin (sızma: "Yurtta sulh, cihanda ___" yerine "___ sulh, cihanda sulh").

## 4. Görsel ve zaman kuralları (hepsi ortak)

- 1080×1920, 30 fps. Üst: "ANİMASYONLU TARİH QUIZ / SPOR TARİHİ QUIZ" + format adı; sayaç "k / n" (+ ZOR hapı); soru metni (≤ 3 satır, 505–715 px); format gövdesi (740–1450 px); cevap kutusu / sayaç (1470–1730 px); altta handle (y 1830). Kayan filigran (tema handle'ı, %17) her karede.
- Akış: soru sesi (her satır ayrı parça, aralarda 0.3 sn) → **3 sn yay sayacı (ZOR: 4 sn)** → cevap (0.3 sn açılış) + alt bilgi → 1.3 sn bekleme → geçiş. ZOR sorularda başta 1.2 sn "ZOR SORU" flaşı.
- Toplam 60–120 sn. Kabaca: Bu Kim ~16 sn/soru (7 soru ≈ 2 dk sınırı), diğerleri 8–11 sn/soru.
- Giriş: format adı + N SORU + "KAÇINI BİLECEKSİN?" (+ "N ZOR SORU"). Kapanış: "KAÇINI BİLDİN? / YORUMLARA YAZ / TAKİP ET". Kapak: başlık + ilk sorunun cevapsız görünümü + soru/ZOR sayısı.

## 5. Ses

- `scripts/quiz_studyo_ses.py`: tek Gemini TTS çağrısı; ses beklenen sürenin %60'ından kısaysa metni 6 satırlık parçalara bölüp her parçayı ayrı üretir (en çok 3 deneme) ve birleştirir.
- Satır sınırları **Whisper kelime zamanlarıyla** bulunur (metin ↔ kelime eşleştirme, ≥ %60 eşleşmezse "ses metinle uyuşmuyor" hatası), kesim sınır penceresindeki en sessiz noktadan yapılır. 0.4 sn'den uzun iç sessizlikler 0.25 sn'ye kısaltılır.

## 6. Otomatik kontroller (`quiz_studyo_kontrol.py`, hata varsa iş kırmızı)

| Kontrol | Anlamı / çözüm |
|---|---|
| `sure` | 55–125 sn dışı → soru sayısını değiştir |
| `kayma` | ses/görüntü süresi farkı > 0.15 sn |
| `BEKCI giris` | giriş sesi Whisper ile giriş metnine benzemiyor → başka projenin sesi; `ses=1` ile yeniden üret |
| `satir N: ses ekrandaki metinle uyusmuyor` | satır kesimi kaymış ya da TTS kelime atlamış → `ses=1` ile yeniden üret |
| `ses yok` / `ic durak` | sessiz parça ya da > 0.45 sn iç durak |
| `cevap sizmasi` | soru sesinde cevap geçiyor → ipucunu/soruyu değiştir |
| `sayac bitmeden cevap rengi` | cevap rengi sayaç bitmeden göründü (görsel sızma) |
| `cevap acilinca dogru/yanlis rengi yok` | cevap vurgusu çizilmedi |
| `alt bilgi satiri gorunmuyor` | alt bilgi boş ya da görünmüyor |
| `ust uste` / `tasiyor` | metin kutuları çakışıyor ya da kartından/ekrandan taşıyor → metni kısalt |
| `emoji bos/tofu` | emoji fontta yok → başka emoji seç |

Kontrol sonrası elle: kapak + soru/sayaç/cevap karelerinden küçük bir kontrol sayfası çıkar ve bak (Türkçe karakterler, emoji, iğne yerleri, renkler, çakışma).

## 7. Dersler

- **Gemini TTS uzun çok satırlı metni ilk cümlede kesebiliyor** (yili-tahmin-1 ilk denemede 90 kelime → 4 sn ses). Süre kontrolü + parçalı üretim bu yüzden var.
- `str.title()` Türkçe "İ"yi bozuyor ("Tahmi̇n"): giriş cümleleri sabit Türkçe adlardan (`GIRIS`) gelir, `.title()` kullanma.
- Bu Kim'de "Üç padişaha baş mimarlık yaptı" ipucu "Mimar Sinan" cevabını sızdırıyordu: ipucunda cevabın kökü olmamalı.
- Haritada altlık kenarında kamera kayabilir; renderer iğneler sığana kadar uzaklaşır, sığmazsa durur.
- Panel bekleyen işi tek tutar (concurrency): toplu üretimde sırayla başlat.
- GitHub GraphQL ve artifact indirme ajan oturumlarında kapalı: release dosyalarını `https://github.com/<repo>/releases/download/video-<slug>/video.mp4` ile, zamanları iş logundaki kontrol satırlarından al.
