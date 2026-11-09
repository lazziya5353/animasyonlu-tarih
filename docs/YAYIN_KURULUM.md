# Instagram'ı ajanlara bağlama (ücretsiz, bir kerelik ~10 dk)

Yayıncı, Analist ve Yorum ajanları Instagram'ın **resmi** API'sini kullanır. Şifreni hiçbir yere girmezsin;
Meta'nın verdiği bir erişim anahtarını GitHub'a saklarsın. Anahtar yokken bu ajanlar hiçbir şey yapmaz, hata da vermez.

## 1. Hesabı İşletme hesabına çevir
Instagram uygulaması → Profil → ☰ → **Hesap türü ve araçlar** → **Profesyonel hesaba geç** → **İşletme**.
(Reels'i API ile paylaşmak için İşletme hesabı gerekiyor. Takipçi, gönderi hiçbir şey kaybolmaz.)

## 2. Meta geliştirici uygulaması aç
1. **developers.facebook.com** → Facebook hesabınla giriş → **Uygulamalarım → Uygulama oluştur**
2. Kullanım durumu: **Instagram ile mesajları ve içeriği yönet** (Instagram API, *Instagram ile Giriş*)
3. Uygulama adı: `animasyon-tarih-ajan` → oluştur
4. Sol menü **Instagram → API setup with Instagram login**
5. (İstenirse) **App roles → Roles → Instagram Testers**'a @animasyon.tarih'i ekle; daveti Instagram'da
   **Ayarlar → Web siteleri ve uygulamalar → Test kullanıcısı davetleri**'nden kabul et
6. **Generate access tokens** bölümünde **Add account** → @animasyon.tarih ile giriş yap, izinleri onayla
   (içerik yayınlama, yorumları yönetme, istatistikler)
7. Hesabın yanında çıkan **Generate token** → anahtarı kopyala (IGAA… ile başlar, 60 gün geçerli)
8. Aynı satırdaki **Instagram User ID** numarasını da kopyala

Uygulama "Geliştirme" modunda kalabilir; kendi hesabın uygulamaya ekli olduğu için inceleme gerekmez.

## 3. GitHub'a ekle
Repo → **Settings → Secrets and variables → Actions → New repository secret**
- `IG_TOKEN` → 7. adımdaki anahtar
- `IG_USER_ID` → 8. adımdaki numara

## 4. Test et
Panelde **Yayıncı → Bağlantıyı test et**. Kartta "Instagram bağlı: @animasyon.tarih" yazıyorsa tamam.

## Anahtar süresi
Anahtar 60 günde bir yenilenmeli. Süresi dolunca ajanlar panelde "Instagram anahtarının süresi dolmuş" yazar;
**Generate token**'a tekrar basıp GitHub'daki `IG_TOKEN`'ı güncellemen yeterli.

## YouTube (isteğe bağlı, sadece istatistik)
YouTube, denetimden geçmemiş uygulamaların API ile yüklediği videoları **kalıcı olarak gizli** bırakıyor; bu yüzden
yükleme panelden hazır başlık/açıklama/etiketlerle **elle** yapılır. Analistin YouTube izlenmelerini de görmesi için:
1. **console.cloud.google.com** → yeni proje → **YouTube Data API v3**'ü etkinleştir → **Kimlik bilgileri → API anahtarı**
2. GitHub secret: `YT_API_KEY` → bu anahtar
3. GitHub **Variables** sekmesi: `YT_CHANNEL_ID` → kanal kimliğin (YouTube Studio → Ayarlar → Kanal → Gelişmiş, `UC…` ile başlar)

## Zamanlanmış paylaşım nasıl çalışır?
Panelde **Planla** dediğinde iş `data/yayin_kuyrugu.json`'a yazılır. Netlify'daki ücretsiz *zamanlayıcı* fonksiyon
10 dakikada bir bakar, zamanı gelen videoyu Yayıncı'ya verir. Paylaşımdan önce kurgu kontrolüne bakılır; hata varsa paylaşmaz.
