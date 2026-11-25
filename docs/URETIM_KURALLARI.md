# Higgsfield'lı video üretim kuralları (12 Kasım derslerinden)

> **Quiz üretimi için önce [QUIZ_REHBERI.md](QUIZ_REHBERI.md) okunur** (akış, tasarım, kontroller, geçmiş hatalar, elle kontrol listesi). Senarist quiz konularında bu rehberi otomatik yükler.
> **"Harflerden Bul" (boşluk doldurma) quizi için [HARF_BUL_REHBERI.md](HARF_BUL_REHBERI.md) okunur** (script.json alanları, maske kuralları, harf_bul.yml, kontroller). Senarist `harflerden-bul-*` projelerinde bu rehberi otomatik yükler.

1. Seslendirmede sayılar yazıyla (Senarist otomatik yapar). Rakam olursa Whisper tutmaz, altyazı/görüntü sesin önüne geçer.
2. Sahne-klip eşleşmesi: cümle süresi klip parçasının 1,8 katını geçmesin; geçerse komşu sahnelerden pay al.
3. Klip sınırlarında 0,3 sn pay (engine/klip.py otomatik). AI klibinde kesim tam saniyede olmuyor.
4. Uzun cümlede görüntü donmaz, yavaşlar (engine/klip.py).
5. Higgsfield klipli projelerde film filtresi kapalı (sade: true).
6. Kapanış inanç/din sorgulayan soru olmasın; son sahnenin ekrandaki başlığı (big/sub) da metinle uyumlu olsun.
7. Şiddet grafik değil; gerçek kişilerin yüzleri yakından çizilmez.
8. Render sonrası release videosu indirilip kontrol edilir: sahne sınırlarında sızma, senkron, son başlık.
9. Bekleme yok: iş verilir, tahmini süre + 2 dk sonrasına hatırlatma kurulur.
11. Quiz yerleşimi: soru, cevap ve alt bilgi halkanın içindeki güvenli genişliğe (en çok 720 px, satırın yüksekliğindeki kirişe göre) sığdırılır; sığmazsa küçültülür, gerekirse 2 satıra bölünür. Filigran her zaman görünür, %17 beyaz, ortada sürekli süzülür ve yazıların üstünden soluk geçer (gizleme yok). quiz_kontrol.py metin kutusu bir harf balonuna değerse koşuyu durdurur.
10. Quiz ses bekçisi: quiz.yml, quiz_kontrol.py --bekci ile girişi ve 1., 11., 22. soruyu Whisper ile yazıya döker; her biri script.json'daki kart metniyle bulanık eşleşmezse (oran < 0.6) ya da Whisper yüklenemezse koşu durur. Ses yalnızca projenin kendi metninden üretilir: script.json slug'ı klasörle aynı olmalı, seslendirme_metni sahnelerle uyuşmalı; metin/stil değişince (ses.kaynak özeti) ses yeniden üretilir, ses.wav yoksa koşu hata verir.

# Quiz formatı: "Her Harfe Bir Tarih Sorusu" (ücretsiz, Claude'suz)

Klasör: `projects/her-harfe-tarih-N/` (`script.json`, `project.json`, `images/bg.jpg`; N. bölüm için 1'den kopyala).

`script.json` şeması:
- `baslik`: "Her Harfe Bir Tarih Sorusu N"
- `sahneler`: tam 2·k+2 sahne, her sahnede **tek satır** (`lines: ["..."]`):
  - 0: giriş ("Her harfe bir tarih sorusu. Bakalım kaçını bileceksin?" — önüne kısa, neşeli bir cümle eklenebilir; emoji yok)
  - sonra her harf için iki sahne: soru `"X harfi. <soru>?"` ve cevap `"<Cevap>."` (soru metni cevap kelimesini içermemeli)
  - son: çıkış "Kaçını bildin? Yorumlara yaz. Kaçırmamak için animasyon tarih'i takip et."
- `alt_bilgi`: `{"X": "<tarih · kısa bilgi>"}` her harf için; cevap kartında cevabın altında görünür. Tarihler doğrulanmış olmalı.
- Zorluk karışımı (22 soru): ~10 kolay, ~7 orta, ~5 zor. Önceki quizlerdeki cevaplar tekrar edilmez.

Zamanlama (`scripts/harf_quiz.py` varsayılanları): soru sesinden sonra 2,5 sn yay, cevaptan sonra 0,7 sn bekleme, atempo 1,08, toplam ~3:00. Çizim yok, harf yeşile döner.

Çalıştırma: Actions → "Quiz · Her Harfe Bir Tarih Sorusu" (`quiz.yml`), girdi `slug` (+ isteğe bağlı `ses=1`, `bolum=N`). API:
`gh api -X POST repos/lazziya5353/animasyonlu-tarih/actions/workflows/quiz.yml/dispatches -f ref=main -f 'inputs[slug]=her-harfe-tarih-N' -f 'inputs[bolum]=N'`
Akış: ses (Gemini) → video + kapak (`scripts/quiz_kapak.py`) → `scripts/quiz_kontrol.py` (44 klipte ses, soruda cevap sızması yok, >0,4 sn iç durak yok, ses/görüntü kayması yok, alt bilgi görünüyor, süre 150–210 sn; biri bozuksa çalışma hata verir) → release `video-<slug>` (video.mp4 + kapak.jpg). Panelde iş türü: `quiz`.
12. ZOR soruları (quiz 3'ten itibaren; quiz 2'ye uygulanmaz): script.json'da her soru sahnesine "zorluk": "kolay" | "orta" | "zor". Zor sorular quizin başına, ortasına ve sonuna dağıtılır, sona yığılmaz. Harf balonunun altında baştan küçük kırmızı "ZOR" etiketi görünür; zor soru gelince sayacın üstünde kısa "ZOR SORU" flaşı çıkar ve düşünme süresine +1 sn eklenir. Kapanış "ZORLARIN KAÇINI BİLDİN?" sorar. Kapakta "N ZOR SORU" hapı çıkar (quiz_kapak.py otomatik sayar). Renk ve stil bizim: koyu kırmızı hap, altın çerçeve, krem yazı; rakip kanalın tasarımı kopyalanmaz.
13. Tematik arka plan (isteğe bağlı, quiz 3+): script.json "arkaplan": "images/xxx.jpg" (proje klasörüne göre). Konuya uygun tarihi sahne, %38 parlaklık ve hafif bulanıklıkla halkanın arkasına konur; "arkaplan_kenburns": true ile süre boyunca çok yavaş %8 yakınlaşma yapılır. Boşsa kahverengi/altın gradyan kalır. Tüm yazılar okunur kalmalı; kontrol kareleriyle bakılır.
14. Hareketli @animasyon.tarih filigranı varsayılan olarak açıktır (--no-wm yalnızca test için).
