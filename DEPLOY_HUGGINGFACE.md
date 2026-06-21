# SpeakAI — Hugging Face Spaces Dağıtım Rehberi

Bu rehber, SpeakAI'yi **ücretsiz** Hugging Face Spaces (Docker) üzerinde yayına
alır. Sunucu, terminal, alan adı, SSL ayarı GEREKMEZ — dosyaları tarayıcıdan
yükler, sırları panelden girersin, HF gerisini halleder (HTTPS dahil).

Mimari: `İnternet → HF (otomatik HTTPS) → app konteyneri (7860)`

---

## ⚠️ Bilmen gereken TEK kritik şey: veri kalıcı DEĞİL

Ücretsiz Space diski **geçicidir**. Space uykuya geçip uyandığında veya her
yeniden kurulumda (rebuild) **veritabanı ve yüklenen ses kayıtları SIFIRLANIR.**


Bu yüzden bu kurulumda **`SEED_ENABLED=true`** kullanıyoruz: her açılışta demo
hesaplar (admin/öğretmen/öğrenci/veli) otomatik yeniden oluşturulur. Yani giriş
her zaman çalışır — ama öğrencilerin biriktirdiği gönderim/puanlar kalıcı olmaz.

> Gerçek, kalıcı kullanım istersen: HF **Settings → Persistent Storage** (~$5/ay)
> ekle ve `DATABASE_URL=sqlite:////data/speakai.db` ver (4 eğik çizgi). Bu rehber
> ücretsiz/geçici senaryoyu anlatır.

---

## 0. Genel bakış

| Aşama | Nerede | Süre |
|---|---|---|
| 1. Space oluştur (Docker) | huggingface.co | ~3 dk |
| 2. Dosyaları yükle (sürükle-bırak) | Space → Files | ~5 dk |
| 3. Sırları gir (Settings) | Space → Settings | ~5 dk |
| 4. Bekle + doğrula | Space build logu | ~3-5 dk |

Hazırlık: Bu repoda zaten var olanlar (sende mevcut, dokunma):
- `Dockerfile` → app'i **7860** portunda çalıştırır (HF varsayılanı).
- `README.md` en üstünde HF yapılandırma başlığı (`sdk: docker`, `app_port: 7860`).

---

## 1. Space oluştur

1. https://huggingface.co → ücretsiz hesap aç / giriş yap.
2. Sağ üst **profil → New Space** (veya https://huggingface.co/new-space).
3. Ayarlar:
   - **Owner:** kendi kullanıcı adın
   - **Space name:** `speakai` (adres `https://<kullanıcı>-speakai.hf.space` olur)
   - **License:** dilediğin (örn. `mit`)
   - **Select the Space SDK:** **Docker** → **Blank** (boş şablon)
   - **Hardware:** **CPU basic (free)**
   - **Visibility:** **Public** (ücretsiz) veya Private
4. **Create Space**. Boş bir Space açılır.

---

## 2. Dosyaları yükle (sürükle-bırak)

Space sayfasında **Files** sekmesi → sağ üst **Contribute / Add file →
Upload files**.

**Kendi bilgisayarından şunları yükle** (klasör yapısını KORUYARAK):
- `backend/` (tüm içeriğiyle — ama `venv/`, `speakai.db`, `uploads/`, `.env` HARİÇ)
- `frontend/` (tüm içeriğiyle)
- `Dockerfile`
- `README.md`
- `KULLANIM_KILAVUZU.md`

> **Yükleme:** `venv`, `speakai.db`, `.env`, `data/` ve `uploads/` KLASÖRLERİNİ
> EKLEME. Sırları dosyayla değil, Adım 3'te panelden gireceğiz.
> En kolayı: bilgisayarında bu klasörleri içermeyen temiz bir kopya hazırla,
> sonra `backend` ve `frontend` klasörlerini olduğu gibi sürükle-bırak yap
> (HF alt klasörleri korur).

Yüklemeyi onayla (**Commit changes to main**). Yükleme bitince HF otomatik
**build** başlatır (Dockerfile'ı kurar). İlk build 3-5 dk sürebilir.

---

## 3. Sırları ve ayarları gir (Settings)

Space → **Settings** → **Variables and secrets** → **New secret / New variable**.

### 3a. Sırlar (gizli — "New secret" ile gir)
| Ad | Değer |
|---|---|
| `JWT_SECRET` | Aşağıdaki üretilmiş anahtarı yapıştır (veya yenisini üret) |
| `GEMINI_API_KEY` | Google AI Studio'dan **YENİ** anahtar (eskisini iptal et!) |
| `SEED_ADMIN_PASSWORD` | güçlü bir şifre (örn. `Adm!n_2026_xK9`) |
| `SEED_TEACHER_PASSWORD` | güçlü bir şifre |
| `SEED_STUDENT_PASSWORD` | güçlü bir şifre |
| `SEED_PARENT_PASSWORD` | güçlü bir şifre |

Hazır güçlü `JWT_SECRET` (istersen kullan):
```
D-s_uB4AnwQ9gYkd23qYHJw1aUecxqnWzsa7-f6clypDUtYtscN6bYjuH4cUZ-EXnUDTqZMRlZQeZudQ32U_Lg
```

### 3b. Ayarlar (gizli değil — "New variable" ile gir)
| Ad | Değer | Neden |
|---|---|---|
| `ENVIRONMENT` | `production` | Sertleştirme: /docs kapalı, HSTS, Secure cookie |
| `CAPTCHA_REQUIRED` | `false` | Turnstile kurmadan yayına almak için bilinçli muafiyet |
| `COOKIE_SECURE` | `true` | HF HTTPS sunduğu için cookie'ler güvenli |
| `SEED_ENABLED` | `true` | Her açılışta demo hesapları yeniden oluştur (geçici disk) |
| `CORS_ORIGINS` | `https://<kullanıcı>-speakai.hf.space` | Kendi Space adresin |

> `<kullanıcı>` yerine HF kullanıcı adını yaz. Adresi Space sayfasında sağ üstteki
> **⋮ → Embed this Space** veya **Open in new tab** ile görebilirsin.

Her sır/ayar eklendiğinde HF Space'i otomatik yeniden başlatır.

> **Gemini Türkçe dönüt:** `GEMINI_API_KEY` girince DEMO_MODE kapanır ve gerçek
> AI değerlendirmesi çalışır. Dönütler artık Türkçe gelir (kod buna göre ayarlı).
> Anahtarı GİRMEZSEN demo modda sahte (yine Türkçe) örnek dönütler gösterilir.

---

## 4. Doğrula

1. Space → **Logs / App** sekmesinde build'in bitmesini bekle
   (`Application startup complete` ve `✅ SpeakAI başlatıldı!` görmelisin).
2. **Önemli:** Uygulamayı **doğrudan adresinden** aç:
   `https://<kullanıcı>-speakai.hf.space`
   (HF Space sayfasındaki gömülü önizleme, güvenlik için `X-Frame-Options: DENY`
   nedeniyle BOŞ görünebilir — bu normaldir. Sağ üstteki **"Open in new tab" /
   genişlet** ile gerçek adresi aç.)
3. Giriş ekranı + kilit simgesi (geçerli HTTPS sertifikası) görünmeli.
4. Demo hesaplarla gir (Adım 3a'da belirlediğin şifrelerle):
   - Admin: `admin@speakai.com`
   - Öğretmen: `ogretmen@speakai.com`
   - Öğrenci: `ogrenci@speakai.com`
   - Veli: `veli@speakai.com`

---

## 5. Güncelleme

Kodu değiştirince: Space → **Files** → ilgili dosyayı aç → **Edit** veya yeni
sürümü **Upload files** ile üzerine yaz → **Commit**. HF otomatik yeniden build
eder. (Veya `git` ile: HF her Space bir git deposudur — `git clone`/`git push`
ile de güncelleyebilirsin.)

---

## 6. Sorun giderme

| Belirti | Olası neden / çözüm |
|---|---|
| Önizleme boş / beyaz | Normal — gömülü iframe engelli. **Doğrudan `*.hf.space` adresini** yeni sekmede aç. |
| Build "FATAL: JWT_SECRET..." | `JWT_SECRET` sırrı eksik/zayıf (≥32 karakter, "change/secret" gibi kelime içermesin). |
| Build "FATAL: CAPTCHA is required..." | `CAPTCHA_REQUIRED=false` ayarını ekle (veya Turnstile anahtarları gir). |
| Giriş çalışmıyor (401) | `COOKIE_SECURE=true` ve adresi **https** ile açtığından emin ol. |
| Konteyner "Permission denied" (db) | Nadiren; `DATABASE_URL=sqlite:////tmp/speakai.db` ayarını ekleyip yeniden başlat. |
| Hesaplar kayboldu | Beklenen davranış (geçici disk). `SEED_ENABLED=true` ile demo hesaplar geri gelir; kalıcılık için Persistent Storage ekle. |
| AI dönütü gelmiyor | `GEMINI_API_KEY` geçerli mi? Logda "Gemini API error" var mı kontrol et. |

---

## Yapılandırma özeti

- **Ücretsiz:** HF Spaces, CPU basic, otomatik HTTPS, sürükle-bırak yükleme.
- **Geçici disk:** veri rebuild/uyku sonrası sıfırlanır; `SEED_ENABLED=true` ile
  demo hesaplar her açılışta yeniden oluşur. Kalıcılık için Persistent Storage.
- **Sırlar:** yalnızca HF **Settings → Secrets**'ta; kodda/dosyada DEĞİL.
- **Güvenlik:** `ENVIRONMENT=production` → Secure cookie, /docs kapalı, HSTS,
  güçlü `JWT_SECRET`; CAPTCHA bilinçli olarak `CAPTCHA_REQUIRED=false` ile kapalı.
- **Adres:** `https://<kullanıcı>-speakai.hf.space` (gerçek kullanım adresi).
