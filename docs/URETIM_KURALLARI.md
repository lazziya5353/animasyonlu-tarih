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
