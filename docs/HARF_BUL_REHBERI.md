# Harflerden Bul Rehberi (boşluk doldurma quizi)

İkinci quiz formatı. Kullanıcı yalnızca soruları verir; ses, video, kapak, kontroller ve release GitHub Actions'ta ücretsiz üretilir. Genel quiz kuralları (tarih doğrulama, tekrar yok, ses bekçisi, yeni klasör) için `docs/QUIZ_REHBERI.md` de geçerlidir. Çeliştiği yerde bu dosya geçerlidir.

## 1. Akış
1. `projects/harflerden-bul-<N>/script.json` dosyasını **sıfırdan** aç. Eski bir projeyi kopyalama. Kopyalarsan `ses.wav`, `ses.kaynak` ve `out/` silinir, `slug` düzeltilir.
2. Yalnızca `sorular` listesini ve üst bilgileri yaz. `sahneler`, `seslendirme_metni` ve `alt_bilgi` alanları `harf_bul.py --hazirla` ile üretilir. Elle yazma.
3. Commit at, ardından workflow'u başlat (`gh workflow run` engelli):
```
gh api -X POST repos/lazziya5353/animasyonlu-tarih/actions/workflows/harf_bul.yml/dispatches \
  -f ref=main -f 'inputs[slug]=harflerden-bul-<N>' -f 'inputs[bolum]=<N>'
```
4. Workflow sırası: hazırla (maske kontrolü) → ses (Gemini; metin değişince yeniden üretilir) → `harf_bul.py` → `quiz_kapak.py --format harf-bul` → `harf_bul_kontrol.py --bekci` → release `video-<slug>` (video.mp4 + kapak.jpg). Koşu ~5–7 dk sürer; beklerken sürekli durum sorgulama.
5. Panelde iş türü `harf-bul`.

## 2. script.json
| Alan | Açıklama |
|---|---|
| `slug` | Klasör adının aynısı |
| `format` | `"harf-bul"` |
| `baslik` | "Harflerden Bul N" |
| `ses_stil` | Gemini TTS ton talimatı (enerjik sunucu) |
| `giris`, `cikis` | İsteğe bağlı. Varsayılanlar: "Harflerden bul! Boşlukları doldur, bakalım kaçını çözebileceksin?" / "Kaçını bildin? Yorumlara yaz!" |
| `sorular[]` | Aşağıdaki tablo |
| `kaynaklar`, `kontrol_notlari`, `aciklama`, `hashtagler` | Yayın ve doğrulama bilgileri |

Her soru için:
| Alan | Açıklama |
|---|---|
| `soru` | Ekranda yazar, ses okur. Rakamlar ekranda kalır, seste yazıya çevrilir. Cevabı ya da kökünü içermez. |
| `cevap` | Büyük ya da küçük harfle yazılabilir; Türkçe büyük harfe çevrilir (i→İ, ı→I). Boşluk kelime arası, `-` olduğu gibi gösterilir. |
| `acik_harfler` | Başlangıç maskesi, örn. `"_R__N __Z_"` (cevapla aynı uzunlukta, bosluk/tire aynı yerde, açık harfler cevapla aynı). Ya da açılacak indeks listesi, örn. `[1, 4, 8]`. En az bir harf kapalı kalmalı. |
| `zorluk` | `kolay` / `orta` / `zor`. Zor soruda sayaç yanında ZOR etiketi ve "ZOR SORU" flaşı çıkar, düşünme süresi +1 sn (4 sn) olur. |
| `alt_bilgi` | Cevabın altında çıkan kısa satır, örn. `"1071 · Malazgirt"`. Tarihler iki kaynaktan doğrulanır. |
| `cevap_okunus` | İsteğe bağlı. Sesin cevabı nasıl okuyacağı, örn. `"Kanun-i Esasi"`. Boşsa cevaptan üretilir. |

### Maske kuralı (kontrol zorunlu kılar)
- Harflerin yaklaşık %20–25'i açık olur: kolay ~%25, orta ~%20, zor toplam 1–2 harf. %30'u aşan maske koşuyu durdurur.
- Çok kelimeli cevapta her kelimede en az 1 açık harf bulunur, ama her kelimenin ilk harfi birden açılmaz.
- Cevabı tek başına ele veren harfler açılmaz (baş harf + ayırt edici son ek gibi). Orta ve son harfleri tercih et.
- Örnek: ORHAN GAZİ → `_R___ __Z_`, KONYA → `__N__`, İBRAHİM (zor) → `____H__`.

Önerilen içerik: 12 soru (6 kolay, 4 orta, 2 zor), hedef süre ~90 sn (kontrol 75–115 sn arasını kabul eder).

## 3. Ekran ve zamanlama (`scripts/harf_bul.py`)
- 1080×1920, 30 fps. Kahverengi/altın zemin, Cinzel başlık "HARFLERDEN BUL", alt satırda "kaçını çözebileceksin?". Altta `@animasyon.tarih`. Filigran her karede %17 opaklıkla ortada süzülür.
- Her soruda sırayla şunlar olur:
  - Sayaç ("3 / 12") ve soru metni (en çok 3 satır) görünür, cevap harf kutularıyla gösterilir.
  - Ses soruyu okur.
  - 3 sn'lik kırmızı yay başlar (zor soruda 4 sn). Yay boyunca maske sabit kalır, hiçbir harf açılmaz.
  - Yay bitince tüm kutular birden dolar ve yeşile döner, alt bilgi satırı çıkar. Ses cevabı söyler.
  - 0,6 sn beklenir, sonra sonraki soruya geçilir.
- Kutular güvenli genişliğe (x 70–1010) otomatik sığdırılır. Tek satırda kutu 82 px'ten küçük kalırsa cevap kelime sınırından 2 satıra bölünür, en büyük kutuyu veren bölme seçilir.
- Ses, sessizliklere göre DP hizalamayla 2n+2 parçaya bölünür (harf_quiz ile aynı yöntem). Çıktılar `video.mp4.times.json` ve `video.mp4.kutular.json` dosyalarıdır (kayıtlı karelerdeki tüm metin, kutu ve yay sınırları).

## 4. Kontroller (`scripts/harf_bul_kontrol.py`, biri bozuksa koşu durur)
- **maske:** Uzunluk, boşluk ve tire yerleri, açık harflerin cevapla uyuşması, açık oran ≤ %30, zor soruda ≤ 2 açık harf, çok kelimede her kelimede ≥ 1 açık harf ve tüm ilk harflerin birden açık olmaması kontrol edilir. Kontrol `--hazirla` adımında da yapılır.
- **bekçi:** Giriş ile 1., 6. ve 12. sorunun sesi Whisper ile yazıya dökülür ve kart metniyle eşleşmelidir (oran ≥ 0.6). Whisper yüklenemezse koşu HATA verir. Ses yalnızca bu projenin metninden üretilir.
- **sızma:** Soru sesinin yazısında cevap kelimesi ya da kökü geçmemelidir. Soru sesi ekrandaki soruyla, cevap sesi ekrandaki cevapla uyuşmalıdır.
- **sessiz klip / iç durak:** Her soru ve cevap klibinde ses olmalı, 0,4 sn'den uzun iç durak olmamalıdır.
- **yerleşim:** Sayaç, soru satırları, kutular, yay, ZOR etiketi/flaşı ve alt bilgi birbirine değmemeli, güvenli alanın dışına taşmamalıdır.
- **görsel:** Cevap karesinde yeşil kutular ve alt bilgi satırı görünmelidir.
- Ses/görüntü kayması 0,1 sn'yi, süre 75–115 sn aralığını aşmamalıdır.

## 5. Elle son kontrol
Release'i indir. Her sorunun başlangıç, yay sonu ve cevap karelerinden bir kontak sayfası çıkar. Girişi ve en az 4 soruyu yazıya döküp dinle. Ardından teslim et.
