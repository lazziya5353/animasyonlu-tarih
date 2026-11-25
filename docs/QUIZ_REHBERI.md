# Quiz Üretim Rehberi: "Her Harfe Bir Tarih Sorusu"

Bu rehber, repodaki ajanların hatasız bir quizi tek seferde üretmesi için yazıldı. Genel kurallar `docs/URETIM_KURALLARI.md` içinde. Bu dosya quize özeldir ve çeliştiği yerde bu dosya geçerlidir.

---

## 1. Adım adım akış

### 1.1 Soruları seç
- **Sayı ve harfler:** 22 soru, sırasıyla A B C D E F G H İ K M N O P R S Ş T U V Y Z. Harfler kapak ve halkayla aynı olmalı.
- **Cevap harfi:** Cevap o harfle başlar (Türkçe büyük harfe göre: "İzmir" İ ile başlar, I ile değil).
- **Zorluk karışımı (quiz 3'ten itibaren):** yaklaşık 8 kolay, 9 orta, 5 zor. Zor sorular başa, ortaya ve sona dağıtılır, sona yığılmaz. Örnek dağılım: 4., 9., 13., 17. ve 21. soru.
- **Tekrar yok:** Önceki quizlerde (`projects/her-harfe-tarih-*/script.json`) çıkan bir cevap ya da aynı olayı soran bir soru kullanılmaz. Yazmadan önce eski quizlerin cevaplarını listele ve karşılaştır.
- **Tarihler doğru olmalı:** Her yılı ve günü iki ayrı kaynaktan doğrula. Kaynakları `kaynaklar`, şüpheli noktaları `kontrol_notlari` alanına yaz. Sık geçen ve doğrusu kesin olanlar:
  - İstanbul'un Fethi: 29 Mayıs 1453
  - TBMM'nin açılışı: 23 Nisan 1920
  - Cumhuriyetin ilanı: 29 Ekim 1923
  - Malazgirt: 26 Ağustos 1071
  - Gülhane Hatt-ı Hümayunu: 3 Kasım 1839
- **Kısa sorular:** Soru en çok 3 satıra, cevap en çok 2 satıra sığmalı. Soru metni cevabı ya da cevabın kökünü içermez (sızma kontrolü bunu yakalar).

### 1.2 YENİ proje klasörü aç
- `projects/her-harfe-tarih-<N>/` klasörünü sıfırdan oluştur.
- **Eski bir quiz klasörünü kopyalayıp düzenleme.** Kopyalarsan aşağıdakileri silip yeniden üret:
  - `slug`
  - `seslendirme_metni`
  - `ses.wav`
  - `ses.kaynak`
  - `out/`

  Quiz 2 tam olarak bu yüzden quiz 1'in sesiyle çıktı.

### 1.3 script.json alanları
| Alan | Açıklama |
|---|---|
| `slug` | Klasör adının aynısı. Farklıysa ses üretimi hata verir. |
| `baslik`, `hook` | Örn. "Her Harfe Bir Tarih Sorusu 3" / "HER HARFE BİR TARİH SORUSU" |
| `sahneler` | 0: giriş. Sonra her harf için 2 sahne: `"X harfi. <soru>?"` ve `"<Cevap>."`. Sonda kapanış. Her sahnede `lines`, `big`, `sub`, `label: "QUIZ"`, `fx: []`, `image: "images/bg.jpg"`, `prompt: "quiz"` olur. |
| `sahneler[soru].zorluk` | `kolay` / `orta` / `zor` (quiz 3+) |
| `alt_bilgi` | `{ "A": "23 Nisan 1920 · TBMM'nin açılışı", ... }`: her harf için o kartın **kendi** cevabına ait kısa bilgi. 22 harfin hepsi dolu olmalı. |
| `seslendirme_metni` | Sahne satırlarının birleşimi; sayılar yazıyla (`scripts/sayi_yazi.py` → `metni_yaziya`). Elle yazma, sahnelerden üret. |
| `ses_stil` | Gemini TTS stil talimatı (giriş tonu vb.). Boşsa belgesel anlatıcı tonu kullanılır. |
| `arkaplan` | İsteğe bağlı, örn. `"images/arka.jpg"`. Boşsa kahverengi/altın gradyan kullanılır. |
| `arkaplan_kenburns` | `true`: çok yavaş yakınlaşma |
| `aciklama`, `hashtagler`, `kaynaklar`, `kontrol_notlari`, `konu`, `tarih`, `durum` | Yayın ve kontrol bilgileri |

### 1.4 Giriş cümlesi
Kalıp: `"Her harfe bir tarih sorusu. Bakalım kaçını bileceksin?"`. İstenirse önüne bölüme özel bir cümle eklenir (quiz 2: "Geçen quiz çok kolay dediniz, bu sefer zorlaştırdık!"). Tonu `ses_stil` ile ver: gülümseyen, oyunbaz, hafif takılan.

### 1.5 Commit at ve quiz.yml'ı başlat
`gh workflow run` engelli; REST ile başlat:
```
gh api -X POST repos/lazziya5353/animasyonlu-tarih/actions/workflows/quiz.yml/dispatches \
  -f ref=main -f 'inputs[slug]=her-harfe-tarih-<N>' -f 'inputs[bolum]=<N>'
```
- Akış: ses (metin/stil özeti `ses.kaynak` ile karşılaştırılır, değiştiyse ses yeniden üretilir) → `harf_quiz.py` → `quiz_kapak.py` → `quiz_kontrol.py --bekci` → `video-<slug>` release'i.
- Süre yaklaşık 7–8 dakika. Beklerken sürekli durum sorgulama; tek bir uzun bekleme yeter.

### 1.6 Kontrol sonucunu oku
- Koşu başarısızsa "Otomatik kontroller" adımının logunda `BEKCI ...`, `yerlesim: ...` satırlarını ve `"hatalar"` listesini oku.
- Her hatanın anlamı ve çözümü 3. bölümde.

### 1.7 Release'i indir ve son kontrolü yap
- İndir: `https://github.com/lazziya5353/animasyonlu-tarih/releases/download/video-<slug>/video.mp4` ve `kapak.jpg`.
- Teslim etmeden önce 5. bölümdeki elle kontrol listesinin tamamını uygula.

---

## 2. Tasarım kuralları

- **Tuval:** 1080×1920, 30 fps. Halka merkezi (540, 1060), yarıçap 440, harf balonu yarıçapı 36.
- **Renkler:**
  - Altın `#E8C478`, beyaz, krem `#E1D2BE`
  - Zemin `#0E0A07` üzerine kahverengi `(70,45,22)` ışıma
  - Doğru harf yeşili `(40,120,70)`, kenarı `(80,190,120)`
  - Aktif harf halkası kırmızısı `(225,50,45)`
  - ZOR kırmızısı `(196,48,40)`
- **Fontlar:**
  - Başlık: Cinzel-700 ("TARİH SORUSU", cevaplar)
  - Metin: Montserrat-900 / Montserrat-700 (üst satır, soru, alt bilgi, sayaç)
- **Üst başlık:** "HER HARFE BİR" / "TARİH SORUSU" / "kaçını bileceksin?". En altta sabit `@animasyon.tarih`.
- **Halka:**
  - Sıradaki harf kırmızı halkayla nabız gibi atar.
  - Cevaplanan harf yeşile döner ve sonuna kadar yeşil kalır.
- **Zamanlama:**
  - Soru sesi biter, 2,5 sn sessiz düşünme süresi başlar. Bu sürede kırmızı yay saat 12'den saat yönünde dolar. Zor soruda süre +1 sn.
  - Cevap sesi gelir, 0,7 sn bekleme ve 0,25 sn kararmayla sonraki karta geçilir.
- **Cevap çıkışı:** Altın Cinzel yazı 0,3 sn'de belirir ve %90'dan %100'e büyür. Altında "•  ALT BİLGİ  •" krem renkte durur.
- **Sayaç:** Sorunun üstünde altın renkte "k / 22".
- **Güvenli metin genişliği:**
  - Soru, cevap ve alt bilgi en çok 720 px genişliğinde olur. Ayrıca her satır, kendi yüksekliğindeki halka kirişine sığmak zorunda: (440 − 36 − 40) = 364 px yarıçaplı daire.
  - Sığmayan metin önce küçülür, gerekirse 2 satıra bölünür. Hiçbir yazı balona ya da halkaya değmez.
- **Filigran (kullanıcının istediği gibi, değiştirme):**
  - `@animasyon.tarih` Montserrat-900 44 px, **%17 beyaz** (alfa 43).
  - **Her karede görünür**; ortada sinüs yoluyla kesintisiz süzülür (x ±230, y ±330).
  - Yazıların üstünden soluk geçer. **Asla gizlenmez, kaçmaz, sönüp belirmez.** Varsayılan açık; `--no-wm` yalnızca test içindir.
- **ZOR etiketleri (quiz 3+):**
  - Zor sorunun balonunun altında baştan küçük kırmızı "ZOR" hapı durur.
  - Zor soru gelince sayacın üstünde 1,2 sn'lik "ZOR SORU" flaşı çıkar.
  - Kapanış: "ZORLARIN KAÇINI BİLDİN?" / "N ZOR SORU · YORUMLARA YAZ".
  - Stil bizimdir; rakip kanalın tasarımı kopyalanmaz.
- **Arka plan (isteğe bağlı):** Konuya uygun tarihi sahne; %38 parlaklık, hafif bulanık, isteğe bağlı %8 yavaş yakınlaşma. Yazılar okunmuyorsa görsel değiştirilir.
- **Giriş ve kapanış kartları:**
  - Giriş: "22 HARF / • 22 SORU •"
  - Kapanış: tüm harfler yeşil, "KAÇINI BİLDİN? / • YORUMLARA YAZ •"
- **Kapak (`quiz_kapak.py`):**
  - Yeşil halka, ortada sıcak ışıma.
  - "N. BÖLÜM" (`bolum` girdisi), "22 SORU", "KAÇINI / BİLECEKSİN?".
  - Zor soru varsa altında kırmızı "N ZOR SORU" hapı.

---

## 3. Otomatik kontroller ve ne anlama geldikleri

| Kontrol (nerede) | Hata mesajı | Anlamı | Çözüm |
|---|---|---|---|
| Slug denetimi (`generate_assets.py`) | `script.json icindeki slug ... (baska projeden kopya?)` | script.json başka quizden kopyalanmış | `slug` alanını klasör adıyla aynı yap. |
| Metin denetimi (`generate_assets.py`) | `seslendirme_metni sahnelerle uyusmuyor` | Ses metni eski ya da başka quizin | `seslendirme_metni`'ni sahnelerden yeniden üret (`metni_yaziya`). |
| Ses varlığı (quiz.yml) | `ses.wav uretilemedi` / `ses.wav yok` | TTS başarısız oldu | Gemini kotasını ve anahtarını kontrol et, yeniden başlat. Başka projenin sesi asla kullanılmaz. |
| Ses bekçisi (`quiz_kontrol.py --bekci`) | `bekci giris/soru k: ses kartla eslesmiyor (oran ...)` | Giriş, 1., 11. veya 22. sorunun sesi kartın metniyle uyuşmuyor (eşik 0,6) | Yanlış ses ya da kayma var. Ses metnini ve sahneleri karşılaştır, `ses: "1"` ile sesi yeniden üret. |
| Ses bekçisi | `whisper yuklenemedi` | Ses doğrulanamadı | Koşuyu yeniden başlat; bu durumda geçiş yok. |
| Kayma | `kayma: video X / ses Y` | Görüntü ve ses süresi 0,1 sn'den fazla farklı | `harf_quiz.py` birleştirmesine bak. |
| Süre | `sure X sn (~180 beklenir)` | Video 150–210 sn dışında | Soru veya cevapları kısalt ya da uzat. |
| Ses var mı | `X soru/cevap: ses yok` | O klip sessiz (sessizlik bölmesi kaymış) | Ses metnindeki noktalamayı düzelt (soru ile cevap arası ayrı satır), sesi yeniden üret. |
| İç durak | `X: 0.xx sn ic durak` | Klip içinde 0,4 sn'den uzun boşluk | Genelde TTS duraklaması; sesi yeniden üret. |
| Sızma | `X soru: cevap sizmasi` | Soru klibinde cevabın sesi var | Soru metni cevabı içeriyor ya da bölme kaymış. Soruyu yeniden yaz veya sesi yeniden üret. |
| Soru eşleşmesi | `X soru: ses ekrandaki soruyla uyusmuyor` | Soru sesi başka bir kartın | Kayma ya da yanlış ses; yukarıdaki gibi çöz. |
| Cevap eşleşmesi | `X cevap: ses ekrandaki cevapla uyusmuyor` | Cevap sesi yanlış | Bulanık eşleşme Whisper'ın yazım farklarını tolere eder. Yine de düşüyorsa sesi gerçekten dinle. |
| Alt bilgi | `X: alt bilgi satiri gorunmuyor` | Cevap karesinde krem satır yok | `alt_bilgi` içinde o harfi doldur. |
| Yerleşim (`quiz_kontrol.py`) | `X: metin kutusu harf balonuna degiyor` | Yazı balona taşıyor | Soru, cevap veya alt bilgiyi kısalt. Güvenli genişlik kodu zaten küçültür ve 2 satıra böler. |
| Yerleşim | `kutular.json yok` | Render eski kodla yapılmış | `harf_quiz.py`'yi güncel haliyle çalıştır. |

---

## 4. Bir daha asla: geçmiş hatalar

1. **Quiz 1'in sesi quiz 2'ye gitti.** script.json kopyalanmış; `slug` ve `seslendirme_metni` eski kalmıştı. Mevcut `ses.wav` olduğu için ses yeniden üretilmedi.
   - Ders: yeni klasör aç, metni sahnelerden üret.
   - Artık önlem var: slug denetimi, metin denetimi, `ses.kaynak` özeti ve ses bekçisi.
2. **Soru klibi cevabı sızdırdı.** Sessizlik bölmesi kaydı ve cevap sesi soru klibine girdi.
   - Ders: soru metninde cevabın kökü olmasın. Sızma kontrolü hata verirse sesi yeniden üret.
3. **Sessiz soru.** En uzun sessizlikler sahne sınırı sanıldı, soru sesi boş kaldı.
   - Önlem: `harf_quiz.py` metin uzunluğuna göre hizalıyor, "ses yok" kontrolü yakalıyor.
4. **Yazı balonlara taştı.** T kartında "3 KASIM 1839 · GÜLHANE HATT-I HÜMAYUNU" satırı E ve T balonlarının üstüne bindi.
   - Önlem: güvenli genişlik ve kiriş sınırı, küçültme ve 2 satır, yerleşim kontrolü.
5. **Alt bilgi eksikti.** Cevabın altındaki bilgi satırı yoktu, bazı kartlarda da başka kartın bilgisi vardı.
   - Ders: `alt_bilgi` 22 harfin hepsi için dolu ve o kartın cevabına ait olmalı.
6. **Filigran kayboldu.** Önce cevap sırasında kaçırıldı, sonra bir kod hatasıyla kart başına tek karede çizildi.
   - Ders: filigran her karede, %17, kesintisiz. Son kontrolde en az 3 karede gözle doğrula.
7. **Yanlış fetih tarihi.** İstanbul'un Fethi 29 Mayıs 1453'tür.
   - Ders: her tarih iki kaynakla doğrulanır ve `kaynaklar` alanına yazılır.

---

## 5. Teslimden önce elle kontrol listesi

- [ ] **Kontrol tablosu:** Her soru karesi (sesin bitimine 0,15 sn kala), her cevap karesi (cevap bitiminden +0,5 sn) ile giriş ve kapanış kareleri çıkarılıp kontrol tablolarında gözle incelendi (22 + 22 + 2 kare). Kontrol edilenler:
  - [ ] Hiçbir yazı balona veya halkaya değmiyor, kesilmiyor.
  - [ ] Her kartta doğru harf kırmızı halkada; önceki harfler yeşil.
  - [ ] Türkçe karakterler doğru (İ, ı, Ş, ş, Ğ, ğ, Ü, Ö, Ç, â, î).
  - [ ] Alt bilgi o kartın cevabına ait.
  - [ ] ZOR etiketleri doğru harflerde (quiz 3+).
- [ ] **Filigran** en az 3 farklı anda görünür, soluk ve ortada.
- [ ] **Ses dökümü:** Giriş ve en az 5 soru (1., 6., 11., 16., 22.) Whisper ile yazıya döküldü, kart metinleriyle karşılaştırıldı. Giriş cümlesi doğru tonda.
- [ ] **Kapak:** "N. BÖLÜM", "22 SORU" ve varsa "N ZOR SORU" doğru.
- [ ] **Videonun kendisi:** Süre 150–210 sn; ses ile görüntü senkron; son kart "KAÇINI BİLDİN?".
- [ ] **Teslim:** Dosyalar `/home/claude/out/Her_Harfe_Tarih_<N>.mp4` ve `Kapak_Her_Harfe_<N>.jpg` olarak kaydedildi, kontrol tabloları `quiz<N>_kontrol_*.jpg` olarak yanında.

## Dış ses (ElevenLabs vb.)

9 formatın hepsinde çalışır. Formda **Ses kaynağı**: "Gemini (otomatik)" (varsayılan) ya da "Kendi ses dosyam (ElevenLabs vb.)".

1. "Kendi ses dosyam" seç → **Seslendirme metnini kopyala**. Metin, workflow'un `seslendirme_metni` ile birebir aynıdır (giriş, her soru satırı, her cevap satırı, kapanış; satır satır, sayılar yazıya çevrili). Kaynak: `dashboard/quiz.js` `qSesMetni` (quiz_studyo.py `hazirla`, harf_bul.py `hazirla` ve api `quizEskiScript` mantığının JS kopyası; biri değişirse ötekini de değiştir).
2. ElevenLabs'e aynen yapıştır, mp3 indir, **Ses dosyası yükle** (mp3/wav/m4a, ≤25 MB).
3. **Onayla ve Üret**: `quiz_uret` script.json'u yazar ama workflow'u başlatmaz; dosya 3 MB'lık parçalarla `quiz_ses_yukle` ile `projects/<slug>/ses_harici.<ext>` (çok parçalıysa `.partNN`) olarak commit edilir, son parçada workflow başlar. (Netlify istek sınırı ~6 MB olduğu için tek commit ya da release asset yerine parçalı commit.)
4. Workflow'un Ses adımında `scripts/harici_ses.py hazirla` dosyayı bulursa (parçaları birleştirir) Gemini TTS atlanır ve ffmpeg ile `ses.wav` yapılır: mono, 24000 Hz, `loudnorm`. Sonrası (sessizlikle bölme, Whisper hizalama, tüm kontroller) aynen çalışır.
5. Kontrol bekçisi düşerse iş kırmızı biter ve şu hata yazılır: **"Yüklenen ses metinle eşleşmiyor: X. sorudan sonra kayma var"**. Metni değiştirmeden tekrar seslendir; satır atlama/ekleme yapma.
