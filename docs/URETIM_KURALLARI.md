# Higgsfield'lı video üretim kuralları (12 Kasım derslerinden)

1. Seslendirmede sayılar yazıyla (Senarist otomatik yapar). Rakam olursa Whisper tutmaz, altyazı/görüntü sesin önüne geçer.
2. Sahne-klip eşleşmesi: cümle süresi klip parçasının 1,8 katını geçmesin; geçerse komşu sahnelerden pay al.
3. Klip sınırlarında 0,3 sn pay (engine/klip.py otomatik). AI klibinde kesim tam saniyede olmuyor.
4. Uzun cümlede görüntü donmaz, yavaşlar (engine/klip.py).
5. Higgsfield klipli projelerde film filtresi kapalı (sade: true).
6. Kapanış inanç/din sorgulayan soru olmasın; son sahnenin ekrandaki başlığı (big/sub) da metinle uyumlu olsun.
7. Şiddet grafik değil; gerçek kişilerin yüzleri yakından çizilmez.
8. Render sonrası release videosu indirilip kontrol edilir: sahne sınırlarında sızma, senkron, son başlık.
9. Bekleme yok: iş verilir, tahmini süre + 2 dk sonrasına hatırlatma kurulur.
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
