# SpeakScorer — Render Üretim Dağıtım Rehberi (ücretli, kalıcı, kendi web adresin)

Bu rehber, SpeakScorer'yi **Render** üzerinde gerçek bir web uygulaması olarak yayına
alır: **sürekli açık** (uyumaz), **veriler kalıcı** (SQLite + ses kayıtları diskte
kalır), **otomatik HTTPS** ve istersen **kendi alan adın**.

Mimari: `İnternet → Render (otomatik HTTPS) → app konteyneri ($PORT) → SQLite (kalıcı disk)`

Veritabanı: **SQLite** (zaten kurulu, gerçek SQL). Kalıcı diske yazılır, böylece
demo hesaplar ve tüm kullanıcı verileri **kalıcı** olur. Kod değişikliği gerekmez.

> 💸 **Aylık maliyet:** Web Service **Starter $7** + Kalıcı Disk **1 GB ≈ $0.25**
> ≈ **~$7.25/ay**. Gemini API kullanımı ayrı ve genelde ücretsiz kotada kalır.

---

## 0. Genel bakış

| Aşama | Nerede | Süre |
|---|---|---|
| 1. Kodu GitHub'a koy (private, sürükle-bırak) | github.com | ~10 dk |
| 2. Render'da Web Service oluştur | render.com | ~5 dk |
| 3. Kalıcı disk ekle | Render | ~2 dk |
| 4. Ortam değişkenleri + sırlar | Render | ~5 dk |
| 5. Deploy + doğrula | Render | ~5 dk |
| 6. (Opsiyonel) Kendi alan adın | Render + DNS | ~10 dk |

Render Git deposundan deploy eder; bu yüzden önce kodu (private) GitHub deposuna
koyacağız. Terminal gerekmez — GitHub'a da tarayıcıdan sürükle-bırak yüklenir.

---

## 1. Kodu GitHub'a koy (private repo, kod gizli kalır)

> **Neden GitHub?** Render otomatik deploy için bir Git deposuna bağlanır. **Private**
> repo seçersen kodun kimseye görünmez; sadece Render erişir.

1. https://github.com → giriş/üye ol → sağ üst **+ → New repository**.
2. **Repository name:** `speakai` · **Visibility:** **Private** · **Create repository**.
3. Açılan sayfada **uploading an existing file** bağlantısına tıkla.
4. Bilgisayarında **`speakai_hf.zip`'i aç** (Desktop'ta hazır). İçinden çıkan
   klasörün **İÇİNDEKİLERİNİ** GitHub yükleme alanına sürükle-bırak:
   ```
   Dockerfile
   README.md
   KULLANIM_KILAVUZU.md
   backend/      (klasör — alt dosyalarıyla)
   frontend/     (klasör — alt dosyalarıyla)
   ```
   > ⚠️ `speakai_hf` klasörünü olduğu gibi DEĞİL, **içindekileri** yükle —
   > `Dockerfile` deponun **kökünde** olmalı. `venv`, `.env`, `speakai.db` zaten
   > zip'te yok (temiz paket).
5. Alt kısımda **Commit changes**.

> Alternatif: `git` kullanmayı biliyorsan `git init && git add . && git commit &&
> git push` ile de yükleyebilirsin — sonuç aynı.

---

## 2. Render'da Web Service oluştur

1. https://render.com → **GitHub ile giriş yap** (Sign up with GitHub).
2. **New + → Web Service**.
3. **Connect a repository** → GitHub'ı yetkilendir → `speakai` deposunu seç.
   (Render private repo'ya erişmek için izin ister; onayla.)
4. Ayarlar:
   - **Name:** `speakscorer` (adres `https://speakscorer-XXXX.onrender.com` olur)
   - **Region:** ⚠️ **Frankfurt (EU Central)** seç. Hem Türkiye'ye en düşük
     gecikme, hem öğrenci verisi AB'de kalır → **KVKK/GDPR uyumu** (makale için
     savunması kolay). Veriler ABD'ye gitmesin diye US bölgelerini seçme.
   - **Branch:** `main`
   - **Runtime / Language:** **Docker** (Render `Dockerfile`'ı otomatik bulur)
   - **Instance Type:** **Starter ($7/ay)** — ⚠️ Free DEĞİL!
     (Free uyur ve kalıcı disk DESTEKLEMEZ; kalıcı veri için Starter şart.)
5. **Health Check Path** (varsa "Advanced" altında): `/health`
6. Henüz **Create** etme — önce diski ve değişkenleri ekleyeceğiz (aşağıda).
   (Render izin verirse önce oluşturup sonra ekleyebilirsin; sıralama önemli değil,
   yeter ki ilk başarılı deploy'dan ÖNCE hepsi tanımlı olsun.)

---

## 3. Kalıcı disk ekle (veriler burada kalır)

Web Service ayarlarında **Disks → Add Disk**:
- **Name:** `speakai-data`
- **Mount Path:** `/var/data`
- **Size:** `1` GB (≈ $0.25/ay; ses kaydı çoğalırsa büyütürsün)

> Bu disk, SQLite veritabanını ve yüklenen ses kayıtlarını tutar. Konteyner her
> yeniden kurulduğunda bile bu disk **korunur** — veriler silinmez.

⚠️ **Tek instance kuralı:** SQLite tek yazıcıyla çalışır. Render'da bu servisi
**1 instance** olarak bırak (ölçekleme/scaling açma). Pilot ve makale ölçeği için
fazlasıyla yeterli.

---

## 4. Ortam değişkenleri ve sırlar

Web Service → **Environment → Add Environment Variable**. Şunları gir:

### 4a. Kalıcılık (disk yollarını göster — ÇOK ÖNEMLİ)
| Key | Value |
|---|---|
| `DATABASE_URL` | `sqlite:////var/data/speakai.db` |
| `UPLOAD_DIR` | `/var/data/uploads` |

> `sqlite:////var/data/...` — **4 eğik çizgi** (mutlak yol). Bunlar olmadan veri
> diske yazılmaz ve yeniden kurulumda silinir.

### 4b. Sırlar (güvenlik)
| Key | Value |
|---|---|
| `JWT_SECRET` | Aşağıdaki güçlü anahtarı yapıştır (veya yenisini üret) |
| `GEMINI_API_KEY` | Google AI Studio'dan **YENİ** anahtar (eskisini iptal et!) |
| `SEED_ADMIN_PASSWORD` | güçlü bir şifre |
| `SEED_TEACHER_PASSWORD` | güçlü bir şifre |
| `SEED_STUDENT_PASSWORD` | güçlü bir şifre |
| `SEED_PARENT_PASSWORD` | güçlü bir şifre |

Hazır güçlü `JWT_SECRET` (istersen kullan):
```
D-s_uB4AnwQ9gYkd23qYHJw1aUecxqnWzsa7-f6clypDUtYtscN6bYjuH4cUZ-EXnUDTqZMRlZQeZudQ32U_Lg
```

### 4c. Sertleştirme ve davranış
| Key | Value | Neden |
|---|---|---|
| `ENVIRONMENT` | `production` | Secure cookie, /docs kapalı, HSTS |
| `CAPTCHA_REQUIRED` | `false` | Turnstile kurmadan yayına almak için bilinçli muafiyet |
| `COOKIE_SECURE` | `true` | Render HTTPS sunar |
| `SEED_ENABLED` | `true` | İLK deploy'da demo hesapları oluştur (sonra `false` yap — aşağıya bak) |
| `CORS_ORIGINS` | `https://speakscorer.com,https://www.speakscorer.com` | Kendi alan adın (+ ilk testte `onrender.com` adresini de ekleyebilirsin) |

> İlk deploy'da henüz alan adı bağlı değilse geçici olarak `onrender.com`
> adresini de virgülle ekle; alan adı (Adım 6) çalışınca yukarıdaki hâline getir.

---

## 5. Deploy ve doğrula

1. **Create Web Service** (veya **Manual Deploy → Deploy latest commit**).
2. **Logs** sekmesinde build + başlatmayı izle:
   `✅ SpeakScorer başlatıldı!` ve `Application startup complete` görmelisin.
3. Üstteki `https://speakscorer-XXXX.onrender.com` adresine tıkla → giriş ekranı +
   kilit (geçerli HTTPS) görünmeli.
4. Demo hesaplarla gir (Adım 4b'deki şifrelerle):
   - Admin: `admin@speakscorer.com`
   - Öğretmen: `ogretmen@speakscorer.com`
   - Öğrenci: `ogrenci@speakscorer.com`
   - Veli: `veli@speakscorer.com`

### 5a. Demo hesapları kalıcı yap, sonra seed'i kapat
İlk başarılı girişten sonra demo hesaplar artık **diskte kalıcı**. Yanlışlıkla
yeniden oluşturulmalarını (veya sildiklerinin geri gelmesini) önlemek için:
- Render → Environment → `SEED_ENABLED` değerini **`false`** yap → **Save**
  (otomatik yeniden deploy olur).
- Artık veritabanı tamamen senin kontrolünde: kullanıcılar kayıt olur, veriler
  diskte birikir. İleride admin'i veya demo hesapları silersen geri gelmez.

> Not: Seed yalnızca "hiç admin yoksa" çalışır. `SEED_ENABLED=false` ile bu
> davranış tamamen kapanır.

---

## 6. Kendi alan adın: speakscorer.com (Cloudflare → Render)

### 6a. Alan adın hazır (Turhost'tan alındı)
`speakscorer.com`'u Turhost'tan aldın; DNS'i Turhost yönetiyor. Kayıtları
**Turhost müşteri paneli → Alan Adlarım → speakscorer.com → DNS Yönetimi**
(panelde "DNS / Bölge Düzenleyici / Zone Editor" olarak da geçebilir) altından
ekleyeceğiz.

### 6b. Render'da alan adını ekle
Render → Web Service → **Settings → Custom Domains → Add Custom Domain**:
1. `speakscorer.com` gir → **Save**. (İstersen `www.speakscorer.com`'u da ekle.)
2. Render sana eklenecek DNS kayıtlarını gösterir — tipik olarak:
   - **A** kaydı: `speakscorer.com` → Render'ın verdiği IP (örn. `216.24.57.x`)
   - **CNAME** kaydı: `www` → `speakscorer-XXXX.onrender.com`
   (Render ekranındaki **gerçek** değerleri kullan; örnekler değişebilir.)

### 6c. Turhost'ta DNS kayıtlarını gir
Turhost paneli → `speakscorer.com` → **DNS Yönetimi**. Render'ın verdiği kayıtları gir:
- **A kaydı:** Ad/Host `@` (kök alan) → Render'ın IP'si (örn. `216.24.57.x`)
- **CNAME kaydı:** Ad/Host `www` → `speakscorer-XXXX.onrender.com`
(Render ekranındaki **gerçek** değerleri kullan.)

> ℹ️ Turhost'ta Cloudflare gibi "proxy / turuncu bulut" yoktur — kayıtları doğrudan
> eklersin, SSL sertifikasını Render otomatik alır, ekstra ayar gerekmez.
> **Önemli:** Turhost domaininde **nameserver'lar Turhost'ta kalmalı** (Render'a
> nameserver değiştirme YOK; sadece A/CNAME kaydı ekliyoruz). TTL alanı varsa düşük
> bırak (örn. 300 sn) ki değişiklik hızlı yayılsın.

### 6d. Bekle ve doğrula
- DNS yayılması + Render'ın SSL alması birkaç dakika (bazen ~1 saate kadar) sürer.
- Render → Custom Domains'te alan adı **"Verified" + "Certificate Issued"** olunca
  `https://speakscorer.com` açılır (geçerli kilit simgesi).
- `CORS_ORIGINS`'in `https://speakscorer.com,https://www.speakscorer.com` olduğundan
  emin ol (Adım 4c).

---

## 7. Günlük operasyon

| İşlem | Nasıl |
|---|---|
| Logları izle | Render → Web Service → **Logs** |
| Kodu güncelle | GitHub'da dosyayı düzenle/yükle → Render **otomatik** yeniden deploy eder |
| Ortam değiştir | Render → Environment → düzenle → Save (otomatik redeploy) |
| Yedek al | Render → Disk → (Starter+) snapshot, veya periyodik dışa aktarma planla |
| Maliyet izle | Render → Billing |

### Yedekleme (önemli — makale verisi!)
Render Shell (Starter+) veya bir bakım script'iyle veritabanını düzenli yedekle:
`/var/data/speakai.db` (veritabanı) ve `/var/data/uploads/` (ses kayıtları).
Makale çalışmasında veri kaybını önlemek için **haftalık yedek** al.

---

## 8. Sorun giderme

| Belirti | Olası neden / çözüm |
|---|---|
| Deploy "FATAL: JWT_SECRET..." | `JWT_SECRET` eksik/zayıf (≥32 karakter). |
| Deploy "FATAL: CAPTCHA is required..." | `CAPTCHA_REQUIRED=false` ekle (veya Turnstile anahtarları gir). |
| Giriş çalışmıyor (401) | `COOKIE_SECURE=true` + adresi **https** ile aç. |
| Veriler kayboldu | Disk mount yok ya da `DATABASE_URL`/`UPLOAD_DIR` disk yoluna işaret etmiyor (Adım 3-4a). |
| Port hatası / "no open ports" | Dockerfile `$PORT`'u dinler (güncel); Render Docker runtime seçili olmalı. |
| Site açılıyor ama yavaş ilk istek | Starter'da olmaz; Free instance uyuduğu için olur — Starter kullan. |
| AI dönütü gelmiyor | `GEMINI_API_KEY` geçerli mi? Logda "Gemini API error" var mı? |

---

## Yapılandırma özeti

- **Sürekli açık + kalıcı:** Render Starter ($7) + 1 GB disk (~$0.25) ≈ ~$7.25/ay.
- **Veritabanı:** SQLite, `/var/data/speakai.db` kalıcı diskte; ses kayıtları
  `/var/data/uploads/`. Demo hesaplar ve kullanıcı verileri kalıcı.
- **HTTPS:** Render otomatik; kendi alan adın da eklenebilir.
- **Sırlar:** yalnızca Render **Environment**'ta; kodda/dosyada DEĞİL. GitHub repo'su
  **private** (kod gizli).
- **Güvenlik:** `ENVIRONMENT=production` → Secure cookie, /docs kapalı, HSTS, güçlü
  `JWT_SECRET`; CAPTCHA bilinçli olarak `CAPTCHA_REQUIRED=false`.
- **Makale için:** tek instance (SQLite), düzenli yedek, sabit `onrender.com` veya
  özel alan adı — reprodüksiyon ve stabil veri toplama için uygun.
