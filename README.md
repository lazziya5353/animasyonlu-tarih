# Animasyon Tarih (@animasyon.tarih)

60 saniyelik dikey tarih videoları (Tarihte Bugün · Savaşlar · Dünya Tarihi) üreten ajan sistemi ve kontrol paneli.

## Sistem nasıl çalışır?

| Ajan | Ne yapar | Ne zaman çalışır | Ne harcar |
|---|---|---|---|
| 1 · Araştırmacı | Gelecek haftanın "Tarihte Bugün" olaylarını + 1 savaş önerisini yıldız puanıyla çıkarır; analistin ve yorumların bulgularını dikkate alır | Her pazar 20.00 (otomatik) | Claude API (~$0,30) |
| 2 · Senarist | Konu için 60 sn metin, sahneler, Gemini promptları, açıklama + hashtag | Panelde "Yap" → "API yazsın" deyince (ya da metni sohbette birlikte yazarız, ücretsiz) | Claude API (~$0,30) |
| 3 · Ses + Görsel | Gemini ile seslendirme (ücretsiz kota); görseller Gemini uygulamasından elle, panelden toplu yüklenir | Panelde "Onayla" deyince | Ücretsiz |
| 4 · Kurgucu | Harita, zaman çizelgesi, sayaçlar, efektler, müzik ve filigranla videoyu çıkarır | Panelde "Videoyu üret" deyince | Ücretsiz |
| 5 · Kontrolcüler | **Senaryo** (kural tabanlı), **ses** (metinle karşılaştırma, hatalıysa yeniden ürettirir), **görsel** (dönem, yazı, bayrak, yüz, yapay zeka hataları), **kurgu** (taşan yazı, siyah/donuk kare, ses seviyesi, senkron) | Her ajanın arkasından otomatik | Ücretsiz (Gemini ücretsiz kota) |
| 6 · Yayıncı | Videoyu Instagram'a Reels olarak paylaşır; panelden saat planlanır | "Planla" / "Şimdi paylaş" | Ücretsiz (Instagram resmi API) |
| 7 · Analist | İzlenme, kaydetme, takipçi istatistikleri; en iyi video ve paylaşım saati | Her pazartesi 08.15 | Ücretsiz |
| 8 · Yorum ajanı | Yorumları toplar, türünü belirler, cevap taslağı yazar; sen onaylayınca gönderir | Her gün 10.40 | Ücretsiz (Gemini ücretsiz kota) |

Instagram bağlantısı: [docs/YAYIN_KURULUM.md](docs/YAYIN_KURULUM.md)

Hepsini **kontrol panelinden** (Netlify) görür ve yönetirsin: ajanların durumu, haftalık rapor, Yap/Geç, metin onayı, görsel/ses önizleme, video izle/indir, aylık harcama.

## Sabah kurulumu (yaklaşık 10 dakika)

### 1) Repoyu GitHub'a yükle
GitHub'da **private** bir repo aç: `animasyonlu-tarih` (boş, README eklemeden). Gerisini Claude yükler.

### 2) GitHub'a gizli anahtarları ekle
Repo → **Settings → Secrets and variables → Actions → New repository secret**
- `ANTHROPIC_API_KEY` → console.anthropic.com → API Keys → Create Key
- `GEMINI_API_KEY` → (sonra, istersen) aistudio.google.com → Get API key. Eklemezsen görselleri/sesi panelden elle yüklersin.

İsteğe bağlı **Variables** sekmesi: `CLAUDE_MODEL` (varsayılan `claude-sonnet-5-5`; daha ucuz için `claude-haiku-5-5`).

### 3) Panel için GitHub erişim anahtarı (token)
github.com → sağ üst profil → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**
- Repository access: **Only select repositories → animasyonlu-tarih**
- Permissions: **Contents: Read and write**, **Actions: Read and write**
- Oluşan anahtarı kopyala (bir daha gösterilmez).

### 4) Netlify'a bağla
app.netlify.com → **Add new site → Import an existing project → GitHub → animasyonlu-tarih**. Ayarlar `netlify.toml`'dan otomatik gelir, sadece **Deploy**.
Sonra **Site configuration → Environment variables**:
- `GITHUB_TOKEN` → 3. adımdaki anahtar
- `GITHUB_REPO` → `lazziya5353/animasyonlu-tarih`
- `PANEL_SIFRE` → panele girerken kullanacağın şifre (uzun ve sana özel)
- `AYLIK_BUTCE_USD` → örn. `15`

Değişkenleri ekledikten sonra **Deploys → Trigger deploy** bir kez. Panel hazır. Telefonda açıp **Ana ekrana ekle** dersen uygulama gibi açılır.

> Netlify kredisi boşa gitmesin diye panel sadece `dashboard/` klasörü değişince yeniden yayınlanır; ajanların rapor/proje kayıtları yayın tetiklemez.

## Günlük akış
1. Pazar akşamı rapor gelir → panelde konulara **Yap / Geç**.
2. "Yap" dediğin konu için Senarist metni yazar → panelde oku → **Onayla**.
3. Gemini bağlıysa görseller ve ses kendiliğinden üretilir; değilse panelden prompt'ları kopyala, AI Studio'da üret, panelden yükle.
4. **Videoyu üret** → 5-10 dk sonra panelde izle, indir, açıklamayı kopyala, paylaş.

## Klasörler
- `engine/` video motoru (`python engine/render.py projects/<proje>`), harita altlıkları `engine/map/`
- `projects/<proje>/` görseller, ses, `script.json` (metin), `project.json` (motor ayarı)
- `reports/` haftalık raporlar · `data/` ajan durumu ve harcama kaydı
- `scripts/` ajan betikleri · `.github/workflows/` ajanların çalıştığı otomasyonlar · `dashboard/` panel

## Yerelde video üretmek
```bash
pip install -r requirements.txt   # + ffmpeg
python engine/render.py projects/osmanli-1299-1923 --preview 5 20 40   # önizleme kareleri
python engine/render.py projects/osmanli-1299-1923                     # tam video → out/video.mp4
```
