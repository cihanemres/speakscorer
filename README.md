<!-- Bu blok Hugging Face Spaces için ZORUNLU yapılandırmadır. HF, README'nin
     en üstündeki bu "frontmatter"ı okuyarak Space'i Docker modunda ve 7860
     portunda çalıştırır. SİLMEYİN / aşağı kaydırmayın. -->
---
title: SpeakScorer
emoji: 🎙️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# SpeakScorer — Yapay Zeka Destekli İngilizce Konuşma Değerlendirme Platformu

<p align="center">
  <strong>🎤 SpeakScorer</strong><br>
  <em>TOKFEST — AI-Powered English Speaking Assessment Platform</em>
</p>

---

## 📑 İçindekiler

1. [Proje Hakkında](#proje-hakkında)
2. [Projenin Amacı ve Kapsamı](#projenin-amacı-ve-kapsamı)
3. [Sistem Mimarisi](#sistem-mimarisi)
4. [Teknoloji Yığını](#teknoloji-yığını)
5. [Veritabanı Şeması](#veritabanı-şeması)
6. [Kullanıcı Rolleri ve Yetkilendirme](#kullanıcı-rolleri-ve-yetkilendirme)
7. [API Dokümantasyonu](#api-dokümantasyonu)
8. [Kurulum ve Çalıştırma](#kurulum-ve-çalıştırma)
9. [Yapay Zeka Entegrasyonu](#yapay-zeka-entegrasyonu)
10. [Oyunlaştırma Sistemi](#oyunlaştırma-sistemi)
11. [Kullanım Kılavuzu](#kullanım-kılavuzu)
12. [Güvenlik Değerlendirmesi](#güvenlik-değerlendirmesi)
13. [Sınırlılıklar ve Gelecek Geliştirmeler](#sınırlılıklar-ve-gelecek-geliştirmeler)
14. [Lisans ve İletişim](#lisans-ve-iletişim)

---

## Proje Hakkında

**SpeakScorer**, ortaokul ve lise öğrencilerinin İngilizce konuşma becerilerini yapay zeka teknolojileri kullanarak değerlendiren, geliştiren ve takip eden bir web tabanlı eğitim platformudur. Platform, **Google Gemini 2.5 Flash** dil modelini kullanarak öğrenci konuşmalarını dört temel kriter üzerinden analiz eder ve gerçek zamanlı geri bildirim sağlar.

Proje, TOKFEST (İngilizce Konuşma Festivali) kapsamında, eğitimde yapay zeka entegrasyonunun pratik bir uygulaması olarak geliştirilmiştir. Geleneksel konuşma değerlendirme yöntemlerinin sınırlılıklarını — öğretmen öznelliği, zaman kısıtlaması ve ölçeklenme zorluğu — yapay zeka destekli otomatik değerlendirme ile aşmayı hedefler.

### Temel Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🎙️ **Ses Kaydı ve Analiz** | Tarayıcı tabanlı ses kaydı, Gemini ile doğrudan ses dosyası analizi |
| 🤖 **AI Değerlendirme** | Kelime bilgisi, dilbilgisi, akıcılık, tutarlılık — 4 kriter × 25 puan = 100 |
| 👨‍🏫 **Çift Değerlendirme** | AI puanı + Öğretmen puanı karşılaştırmalı değerlendirme |
| 🎮 **Oyunlaştırma** | XP, seviye, seri (streak), rozetler, sıralama tabloları |
| 👨‍👧 **Veli Takibi** | Veli panelinden çocuk ilerleme izleme |
| 📊 **Detaylı İstatistikler** | Bireysel, sınıf ve okul düzeyinde analitik raporlar |
| 🔊 **TTS (Text-to-Speech)** | gTTS ile paragrafların sesli okunması |

---

## Projenin Amacı ve Kapsamı

### Araştırma Sorusu

> *"Yapay zeka destekli otomatik konuşma değerlendirme sistemleri, ortaöğretim düzeyinde İngilizce konuşma becerilerinin ölçülmesinde geleneksel yöntemlere alternatif olabilir mi?"*

### Hedefler

1. **Nesnel Değerlendirme:** Öğretmen öznelliğini azaltarak standartlaştırılmış bir puanlama rubriği sunmak.
2. **Anlık Geri Bildirim:** Öğrencilere konuşma performansları hakkında detaylı, yapıcı ve Türkçe geri bildirim sağlamak.
3. **Motivasyon Artırma:** Oyunlaştırma mekanikleri (XP, seviye, rozetler, sıralama) ile öğrenci katılımını artırmak.
4. **Veli Katılımı:** Veli paneli aracılığıyla ebeveynlerin çocuklarının gelişimini takip etmesini sağlamak.
5. **Ölçeklenebilirlik:** Tek bir öğretmenin yüzlerce öğrenciyi aynı anda değerlendirebilmesini mümkün kılmak.

### Hedef Kitle

- **Öğrenciler:** 5-12. sınıf düzeyindeki İngilizce öğrenen öğrenciler
- **Öğretmenler:** İngilizce branş öğretmenleri
- **Veliler:** Öğrenci velileri (salt okunur erişim)
- **Yöneticiler:** Okul/platform yöneticileri

---

## Sistem Mimarisi

```
┌──────────────────────────────────────────────────────────────┐
│                      KULLANICI KATMANI                       │
│  ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌──────────────┐ │
│  │ Öğrenci │  │ Öğretmen  │  │  Veli   │  │   Yönetici   │ │
│  └────┬────┘  └─────┬─────┘  └────┬────┘  └──────┬───────┘ │
└───────┼─────────────┼─────────────┼───────────────┼─────────┘
        │             │             │               │
        ▼             ▼             ▼               ▼
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vanilla JS/HTML/CSS)            │
│  ┌───────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐ │
│  │ index.html│  │dashboard │  │ record.html│  │ app.js   │ │
│  │ (Giriş)   │  │.html     │  │ (Kayıt)    │  │(Çekirdek)│ │
│  └───────────┘  └──────────┘  └────────────┘  └──────────┘ │
│  ┌──────────┐  ┌──────────────┐                             │
│  │recorder  │  │ style.css    │                             │
│  │.js       │  │ (Tasarım)    │                             │
│  └──────────┘  └──────────────┘                             │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI / Python)                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                    main.py (Uygulama)                  │  │
│  │  • Lifespan (başlatma/kapanma)                         │  │
│  │  • CORS Middleware                                     │  │
│  │  • Static file serving                                 │  │
│  │  • Seed data (başlangıç verileri)                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────── ROUTERS ───────────────────────────┐   │
│  │ auth_router.py │ admin_router.py │ teacher_router.py  │   │
│  │ student_router │ parent_router.py                     │   │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────── SERVICES ───────────────────────────┐   │
│  │ ai_service.py (Gemini AI + TTS)                       │   │
│  │ speech_service.py (Ses Transkripsiyon)                 │   │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────── CORE ───────────────────────────────┐   │
│  │ config.py │ database.py │ models.py │ auth.py         │   │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌──────────┐ ┌────────┐ ┌──────────┐
        │ SQLite   │ │ Gemini │ │  gTTS    │
        │ Database │ │ 2.5    │ │ (Google  │
        │          │ │ Flash  │ │  TTS)    │
        └──────────┘ └────────┘ └──────────┘
```

### Veri Akışı: Öğrenci Ses Kaydı Gönderimi

```
1. Öğrenci → Paragrafı görüntüler ve TTS ile dinler
2. Öğrenci → Tarayıcı üzerinden ses kaydı başlatır (MediaRecorder API)
3. Kayıt bitince → WebM formatında blob oluşturulur
4. Frontend → FormData ile /api/student/submit endpoint'ine POST
5. Backend → Ses dosyasını sunucuya kaydeder
6. Backend → Gemini 2.5 Flash'a ses dosyasını gönderir (multimodal)
7. Gemini → Ses dosyasını dinler + transkript çıkarır + 4 kriterde puanlar
8. Backend → Puanları, geri bildirimi ve transkripti veritabanına kaydeder
9. Backend → XP, streak, rozet hesaplama
10. Frontend → Sonuç ekranını gösterir (puan dairesi + detaylar)
```

---

## Teknoloji Yığını

### Backend

| Teknoloji | Sürüm | Kullanım Amacı |
|-----------|-------|----------------|
| **Python** | 3.10+ | Ana programlama dili |
| **FastAPI** | 0.109.0 | REST API framework |
| **Uvicorn** | 0.27.0 | ASGI web sunucu |
| **SQLAlchemy** | 2.0.25 | ORM (Object-Relational Mapping) |
| **SQLite** | — | İlişkisel veritabanı |
| **python-jose** | 3.3.0 | JWT token oluşturma/doğrulama |
| **passlib + bcrypt** | 1.7.4 / 4.1.2 | Şifre hashleme (bcrypt algoritması) |
| **google-genai** | 1.0.0 | Gemini API istemcisi |
| **gTTS** | 2.5.4 | Google Text-to-Speech |
| **python-dotenv** | 1.0.1 | Ortam değişkenleri yönetimi |
| **pydantic** | 2.5.3 | Veri doğrulama ve serileştirme |

### Frontend

| Teknoloji | Kullanım Amacı |
|-----------|----------------|
| **HTML5** | Sayfa yapısı |
| **CSS3 (Vanilla)** | Tasarım (dark theme, glassmorphism, animasyonlar) |
| **JavaScript (ES6+)** | Uygulama mantığı, DOM manipülasyonu |
| **MediaRecorder API** | Tarayıcı tabanlı ses kaydı |
| **Web Speech API** | Tarayıcı TTS (istemci tarafı paragraf okuma) |
| **Chart.js 4.4.1** | İlerleme grafikleri (line/bar charts) |
| **Fetch API** | REST API iletişimi |

### Harici API Servisleri

| Servis | Kullanım |
|--------|----------|
| **Google Gemini 2.5 Flash** | Konuşma değerlendirme, ses transkripsiyon, multimodal analiz |
| **Google TTS (gTTS)** | Paragraf sesli okuma dosyası oluşturma (MP3) |

---

## Veritabanı Şeması

Platform 9 adet tablo kullanmaktadır:

```
┌────────────┐     ┌──────────────┐     ┌──────────────┐
│   users     │────▶│  assignments  │────▶│  submissions  │
│             │     │              │     │              │
│ id          │     │ teacher_id   │     │ student_id   │
│ ad_soyad    │     │ paragraph_id │     │ assignment_id│
│ email       │     │ student_id   │     │ paragraph_id │
│ password_hash│    │ class_name   │     │ audio_path   │
│ rol         │     │ target_type  │     │ transcript   │
│ status      │     │ due_date     │     │ ai_score     │
│ sinif_duzeyi│     └──────────────┘     │ teacher_score│
│ sube        │                          │ final_score  │
│ parent_id   │     ┌──────────────┐     └──────────────┘
│ teacher_id  │────▶│  paragraphs   │
└────────────┘     │              │     ┌──────────────┐
      │            │ title        │────▶│  questions    │
      │            │ text         │     │ (Quiz)       │
      │            │ audio_path   │     └──────────────┘
      │            │ level (1-5)  │
      │            │ category     │
      │            └──────────────┘
      │
      ├────▶ achievements (rozetler)
      ├────▶ user_streaks (XP, seviye, seri)
      ├────▶ commendations (takdir/teşekkür)
      └────▶ notifications (bildirimler)
```

### Tablo Detayları

| Tablo | Kayıt Sayısı (Seed) | Açıklama |
|-------|---------------------|----------|
| `users` | 4 | Kullanıcılar (öğrenci, öğretmen, veli, yönetici) |
| `paragraphs` | 6 | İngilizce okuma metinleri (Seviye 1-4) |
| `assignments` | — | Öğretmen→Öğrenci ödev atamaları |
| `submissions` | — | Öğrenci ses kaydı gönderimleri ve puanları |
| `questions` | — | Paragraflara ait çoktan seçmeli sorular |
| `achievements` | — | Kazanılan rozetler |
| `user_streaks` | 4 | XP, seviye ve giriş seri bilgileri |
| `commendations` | — | Öğretmen takdir/teşekkür belgeleri |
| `notifications` | — | Sistem bildirimleri |

---

## Kullanıcı Rolleri ve Yetkilendirme

Platform, JWT (JSON Web Token) tabanlı kimlik doğrulama ve rol bazlı erişim kontrolü (RBAC) kullanmaktadır.

### Rol Matrisi

| Yetki | Öğrenci | Öğretmen | Veli | Yönetici |
|-------|:-------:|:--------:|:----:|:--------:|
| Giriş / Kayıt | ✅ | ✅ | ✅ | ✅ |
| Profil güncelleme | ✅ | ✅ | ✅ | ✅ |
| Paragraf görüntüleme | ✅ | ✅ | — | ✅ |
| Ses kaydı gönderme | ✅ | — | — | — |
| AI değerlendirme alma | ✅ | — | — | — |
| İlerleme görüntüleme | ✅ | — | — | — |
| Sıralama tablosu | ✅ | — | — | — |
| Ödev oluşturma | — | ✅ | — | — |
| Öğrenci puanlama | — | ✅ | — | — |
| Paragraf önerme | — | ✅ | — | ✅ |
| Takdir/Teşekkür verme | — | ✅ | — | — |
| Rozet atama | — | ✅ | — | — |
| Çocuk ilerleme takibi | — | — | ✅ | — |
| Kullanıcı onaylama/reddetme | — | — | — | ✅ |
| Paragraf onaylama | — | — | — | ✅ |
| Sistem istatistikleri | — | — | — | ✅ |
| Kullanıcı CRUD | — | — | — | ✅ |

### Kimlik Doğrulama Akışı

```
1. Kullanıcı → POST /api/auth/login (email + şifre)
2. Backend → bcrypt ile şifre doğrulama
3. Başarılı → JWT token oluşturma (HS256, 24 saat süre)
4. Frontend → Token'ı localStorage'da saklama
5. Sonraki istekler → Authorization: Bearer <token> header'ı
6. Backend → Token decode + kullanıcı sorgulama + durum kontrolü
7. Yetkisiz erişim → 401/403 HTTP yanıtı
```

---

## API Dokümantasyonu

Tüm API endpoint'leri `/api` prefix'i altında gruplandırılmıştır.

### Kimlik Doğrulama (`/api/auth`)

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| POST | `/api/auth/register` | Yeni kullanıcı kaydı (onay beklenir) |
| POST | `/api/auth/login` | Kullanıcı girişi, JWT token döner |
| GET | `/api/auth/me` | Mevcut kullanıcı bilgileri |
| PUT | `/api/auth/profile` | Profil güncelleme |
| POST | `/api/auth/profile/avatar` | Profil fotoğrafı yükleme |

### Öğrenci (`/api/student`)

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| GET | `/api/student/tasks` | Atanan ödevleri listele |
| GET | `/api/student/tasks/{id}` | Ödev detayı |
| POST | `/api/student/submit` | Ses kaydı gönder (multipart/form-data) |
| GET | `/api/student/results` | Geçmiş gönderimler ve puanlar |
| GET | `/api/student/progress` | İlerleme istatistikleri |
| GET | `/api/student/badges` | Kazanılan rozetler |
| GET | `/api/student/leaderboard` | Sınıf ve seviye sıralaması |
| GET | `/api/student/gamification` | XP, seviye, streak bilgileri |

### Öğretmen (`/api/teacher`)

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| GET | `/api/teacher/paragraphs` | Onaylı paragrafları listele |
| POST | `/api/teacher/paragraphs` | Yeni paragraf öner (onay bekler) |
| PUT | `/api/teacher/paragraphs/{id}` | Paragraf düzenle |
| GET | `/api/teacher/students` | Öğrenci listesi |
| POST | `/api/teacher/students` | Yeni öğrenci ekle |
| GET/POST | `/api/teacher/assignments` | Ödev listele/oluştur |
| GET | `/api/teacher/submissions` | Gönderimler |
| PUT | `/api/teacher/submissions/{id}/score` | Öğrenci puanla |
| POST | `/api/teacher/commendation` | Takdir/Teşekkür ver |
| POST | `/api/teacher/badges/assign` | Rozet ata |
| GET | `/api/teacher/class-stats` | Sınıf istatistikleri |

### Veli (`/api/parent`)

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| GET | `/api/parent/children` | Bağlı çocukları listele |
| GET | `/api/parent/children/{id}/progress` | Çocuk ilerleme durumu |
| GET | `/api/parent/children/{id}/scores` | Çocuk puanları |
| GET | `/api/parent/children/{id}/badges` | Çocuk rozetleri |
| GET | `/api/parent/children/{id}/leaderboard` | Çocuk sıralama bilgisi |
| GET | `/api/parent/children/{id}/assignments` | Çocuğun ödevleri |

### Yönetici (`/api/admin`)

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| GET | `/api/admin/users` | Tüm kullanıcıları listele |
| POST | `/api/admin/users` | Yeni kullanıcı oluştur |
| PUT | `/api/admin/users/{id}/approve` | Kullanıcıyı onayla |
| PUT | `/api/admin/users/{id}/reject` | Kullanıcıyı reddet |
| PUT | `/api/admin/users/{id}/status` | Durum güncelle |
| DELETE | `/api/admin/users/{id}` | Kullanıcıyı sil |
| PUT | `/api/admin/users/{id}/permissions` | Yetkileri güncelle |
| GET/POST | `/api/admin/paragraphs` | Paragraf CRUD |
| PUT | `/api/admin/paragraphs/{id}/approve` | Paragraf onayla |
| DELETE | `/api/admin/paragraphs/{id}` | Paragraf sil |
| GET | `/api/admin/stats` | Platform istatistikleri |

### Genel

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| GET | `/` | Ana sayfa (login) |
| GET | `/health` | Sağlık kontrolü (DB bağlantı testi) |
| GET | `/api/config/public` | Genel yapılandırma (demo_mode) |
| GET | `/docs` | Swagger/OpenAPI belgeleri |

---

## Kurulum ve Çalıştırma

### Ön Gereksinimler

- Python 3.10 veya üzeri
- pip (Python paket yöneticisi)
- Modern web tarayıcısı (Chrome, Firefox, Edge)
- Mikrofon (öğrenci ses kaydı için)
- (Opsiyonel) Google Gemini API anahtarı

### Adım 1: Proje Dosyalarını İndirme

```bash
git clone <repo-url>
cd speak_ai
```

### Adım 2: Python Sanal Ortam ve Bağımlılıklar

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### Adım 3: Ortam Değişkenlerini Yapılandırma

```bash
# .env.example dosyasını kopyalayın:
cp .env.example .env  # (Windows: copy .env.example .env)
```

`.env` dosyasını düzenleyin:

```env
# ZORUNLU: Güçlü rastgele bir anahtar oluşturun
JWT_SECRET=<python -c "import secrets; print(secrets.token_urlsafe(64)" ile oluşturun>

# OPSIYONEL: Gerçek AI değerlendirme için Gemini API anahtarı
# Boş bırakırsanız Demo Modu aktif olur (mock AI puanları)
GEMINI_API_KEY=<api-anahtarınız>

# Başlangıç verileri (ilk çalıştırma için)
SEED_ENABLED=true
SEED_ADMIN_PASSWORD=<güçlü-şifre>
SEED_TEACHER_PASSWORD=<güçlü-şifre>
SEED_STUDENT_PASSWORD=<güçlü-şifre>
SEED_PARENT_PASSWORD=<güçlü-şifre>
```

### Adım 4: Uygulamayı Başlatma

```bash
python main.py
# veya
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Uygulama `http://localhost:8000` adresinde erişime açılacaktır.

### Adım 5: Demo Modu

Gemini API anahtarı olmadan çalıştırıldığında platform otomatik olarak **Demo Modu**'na geçer:
- AI değerlendirmeleri simüle edilir (mock puanlar)
- Ses transkripsiyon simüle edilir
- TTS (Text-to-Speech) çalışabilir (internet bağlantısı gerektirir)
- Tüm kullanıcı arayüzü ve iş akışları tam işlevseldir

### Varsayılan Kullanıcılar (Seed Verileri Aktifken)

| Rol | E-posta | Varsayılan Şifre |
|-----|---------|------------------|
| Yönetici | admin@speakai.com | `.env` içinde tanımlı |
| Öğretmen | ogretmen@speakai.com | `.env` içinde tanımlı |
| Öğrenci | ogrenci@speakai.com | `.env` içinde tanımlı |
| Veli | veli@speakai.com | `.env` içinde tanımlı |

---

## Yapay Zeka Entegrasyonu

### Değerlendirme Rubriği

SpeakScorer, her öğrenci konuşmasını **4 temel kriter** üzerinden 100 üzerinden puanlar:

| Kriter | Puan Aralığı | Değerlendirme Odağı |
|--------|:------------:|---------------------|
| **Kelime Bilgisi (Vocabulary)** | 0-25 | Kullanılan kelimelerin çeşitliliği, uygunluğu ve bağlama uyumu |
| **Dilbilgisi (Grammar)** | 0-25 | Cümle yapılarının doğruluğu, zaman ekleri, özne-yüklem uyumu |
| **Akıcılık (Fluency)** | 0-25 | Konuşmanın pürüzsüzlüğü, temposu, duraklamalar ve doğallığı |
| **Tutarlılık (Coherence)** | 0-25 | Fikirlerin mantıksal düzeni, bağlaçlar ve paragraf uyumu |

**Toplam:** Kelime + Dilbilgisi + Akıcılık + Tutarlılık = **Maksimum 100 puan**

### Değerlendirme Süreci

```
┌─────────────────┐     ┌──────────────────────┐
│   Öğrenci Sesi  │────▶│  Gemini 2.5 Flash    │
│   (WebM dosya)  │     │  (Multimodal Model)  │
└─────────────────┘     │                      │
                        │  1. Ses → Transkript  │
┌─────────────────┐     │  2. Orijinal paragraf │
│ Orijinal Metin  │────▶│     ile karşılaştır  │
│   (Paragraf)    │     │  3. 4 kriter puanla  │
└─────────────────┘     │  4. Türkçe geri      │
                        │     bildirim yaz      │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  JSON Yanıt:          │
                        │  {                    │
                        │    vocabulary: 20,    │
                        │    grammar: 18,       │
                        │    fluency: 22,       │
                        │    coherence: 19,     │
                        │    total: 79,         │
                        │    feedback: "...",    │
                        │    suggestions: [...]  │
                        │  }                    │
                        └──────────────────────┘
```

### İki Aşamalı Değerlendirme

1. **AI Değerlendirme (Otomatik):** Gemini modeli ses dosyasını doğrudan analiz eder
2. **Öğretmen Değerlendirme (Manuel):** Öğretmen aynı rubrik üzerinden kendi puanını girer
3. **Nihai Puan:** Öğretmen puanı varsa öğretmen puanı geçerlidir; yoksa AI puanı kullanılır

Bu yaklaşım, AI'ın hız avantajını öğretmenin pedagojik uzmanlığıyla birleştirir.

---

## Oyunlaştırma Sistemi

Platform, öğrenci motivasyonunu artırmak için kapsamlı bir oyunlaştırma sistemi içerir.

### XP (Deneyim Puanı) Sistemi

| Eylem | XP |
|-------|:--:|
| Gönderim tamamlama | 10 |
| Quiz geçme | 15 |
| Mükemmel puan (95+) | 25 |
| Yüksek puan (80+) | 15 |
| Günlük giriş | 5 |
| 3 gün seri bonusu | 10 |
| 7 gün seri bonusu | 25 |
| 30 gün seri bonusu | 100 |
| Rozet kazanma | 20 |

### Seviye Sistemi

| Seviye | Gerekli XP | Unvan |
|:------:|:----------:|-------|
| 1 | 0 | Çırak |
| 2 | 100 | Konuşmacı |
| 3 | 250 | Hikayeci |
| 4 | 500 | Söz Ustası |
| 5 | 1.000 | İleri Konuşmacı |
| 6 | 2.000 | Bilge |
| 7 | 3.500 | Efsane |
| 8 | 5.000 | Şampiyon |
| 9 | 7.500 | Kahraman |
| 10 | 10.000 | Efsanevi Konuşmacı |

### Rozet (Badge) Sistemi

| Rozet | İkon | Kazanım Koşulu |
|-------|:----:|----------------|
| İlk Adım | 🌟 | İlk gönderim |
| Hızlı Konuşmacı | ⚡ | 5 gönderim |
| Pratik Ustası | 🎯 | 10 gönderim |
| Söz Ustası | 📚 | 25 gönderim |
| Yüksek Puan | ⭐ | 80+ puan alma |
| Mükemmel Puan | 🏆 | 95+ puan alma |
| İstikrarlı Öğrenci | 💪 | 70+ ortalama (min. 3 gönderim) |
| Yıldız Öğrenci | 🌟 | 85+ ortalama (min. 5 gönderim) |

### Sıralama Tabloları

- **Sınıf İçi:** Aynı sinif_duzeyi ve şubedeki öğrenciler arası
- **Seviye Geneli:** Aynı sinif_duzeyi'ndeki tüm öğrenciler arası
- **Ödev Özelinde:** Belirli bir ödeve ait puan sıralaması

---

## Kullanım Kılavuzu

### 🎓 Öğrenci Kullanım Kılavuzu

1. **Giriş:** `http://localhost:8000` adresine gidin, e-posta ve şifrenizi girerek oturum açın
2. **Gösterge Paneli:** XP, seviye, seri durumu, son ödevler ve rozetlerinizi görüntüleyin
3. **Ödevlerim:** Öğretmeninizin atadığı ödevleri görün, "Kayıt Başlat" ile ses kaydına gidin
4. **Ses Kaydı:**
   - Paragrafı okuyun veya "🔊 Paragrafı Dinle" ile sesli dinleyin
   - 🎤 butonuna basarak mikrofon kaydı başlatın
   - Konuşmanızı tamamladıktan sonra tekrar basarak durdurun
   - Kaydınızı dinleyip kontrol edin
   - "📤 AI Değerlendirmesine Gönder" butonuna basın
5. **Sonuçlar:** Puanınız (kelime, dilbilgisi, akıcılık, tutarlılık), transkript ve AI geri bildirimi görüntülenir
6. **İlerleme:** Zaman içindeki puan grafiğinizi ve istatistiklerinizi takip edin
7. **Sıralama:** Sınıfınız ve seviyenizdeki sıralamayı görün

### 👨‍🏫 Öğretmen Kullanım Kılavuzu

1. **Gösterge Paneli:** Toplam ödev, gönderim, değerlendirilen gönderim ve ortalama puan istatistikleri
2. **Paragraflar:** Mevcut paragrafları görüntüleyin, yeni paragraf önerin (yönetici onayı gerekir)
3. **Öğrenciler:** Aktif öğrencilerin listesini görüntüleyin
4. **Ödev Oluşturma:**
   - Paragraf seçin
   - Öğrenci veya sınıf seçin
   - Son tarih belirleyin (opsiyonel)
   - "Ödev Oluştur" butonuna basın
5. **Gönderimler:**
   - Öğrenci gönderimlerini sesli dinleyin
   - AI puanını ve transkripti inceleyin
   - 4 kriter üzerinden (her biri 0-25) kendi puanınızı girin
   - Detaylı Türkçe geri bildirim yazın
   - "Puanla" butonuna basın (öğretmen puanı nihai puanı belirler)
6. **Takdir/Teşekkür:** Başarılı öğrencilere takdir belgesi verin (XP ödülü dahil)

### 👨‍👧 Veli Kullanım Kılavuzu

1. **Giriş:** Veli hesabıyla oturum açın
2. **Çocuklarım:** Bağlı çocuklarınızın listesini görüntüleyin
3. **Detay Paneli:** Seçilen çocuğun:
   - Toplam gönderim, ortalama, en iyi puan, haftalık ortalama
   - Sıralama durumu (sınıf ve seviye geneli)
   - Kazanılan rozetler
   - Son değerlendirmeler (AI + öğretmen geri bildirimleri)

### 🔧 Yönetici Kullanım Kılavuzu

1. **Gösterge Paneli:** Platform geneli istatistikler
2. **Kullanıcı Yönetimi:**
   - Yeni kayıtları onaylayın/reddedin
   - Kullanıcıları aktif/devre dışı yapın
   - Yeni kullanıcı oluşturun
3. **Paragraf Yönetimi:**
   - Yeni İngilizce paragraflar ekleyin (TTS otomatik oluşturulur)
   - Öğretmen önerilerini onaylayın/reddedin
   - Paragraflara quiz soruları ekleyin
4. **İstatistikler:** Toplam kullanıcı, gönderim, paragraf sayıları

---

## Güvenlik Değerlendirmesi

### Uygulanan Güvenlik Önlemleri

| Önlem | Durum | Açıklama |
|-------|:-----:|----------|
| Şifre hashleme (bcrypt) | ✅ | Tüm şifreler bcrypt ile hashleniyor |
| JWT token doğrulama | ✅ | Her istekte token doğrulanıyor |
| Rol bazlı erişim kontrolü | ✅ | Her endpoint rol kontrolü yapıyor |
| CORS politikası | ✅ | Belirli origin'ler tanımlı |
| Dosya boyut sınırı | ✅ | Avatar: 2MB, Ses: 10MB |
| Dosya türü doğrulama | ✅ | Content-type kontrolü yapılıyor |
| Path traversal koruması | ✅ | `serve_frontend` endpoint'inde mevcut |
| Admin kayıt koruması | ✅ | Herkese açık API'den admin oluşturulamaz |
| Hesap durumu kontrolü | ✅ | Devre dışı hesaplar giriş yapamaz |
| Ortam değişkenleri | ✅ | Secrets `.env` dosyasında |
| .gitignore | ✅ | `.env`, `.db`, `uploads/` hariç tutulmuş |

### Bilinen Sınırlılıklar

Güvenlik denetimi sonucunda tespit edilen bulgular ve öneriler ayrı bir raporda detaylandırılmıştır. Önemli noktalar:

- Rate limiting uygulanmamıştır (brute force koruması)
- Şifre karmaşıklık kuralı bulunmamaktadır
- XSS koruması frontend tarafında yetersizdir
- JWT token süresi uzundur (24 saat)
- HTTPS üretim ortamında yapılandırılmalıdır

---

## Sınırlılıklar ve Gelecek Geliştirmeler

### Mevcut Sınırlılıklar

1. **Veritabanı:** SQLite kullanılmaktadır; üretim ortamında PostgreSQL/MySQL önerilir
2. **Ölçeklenme:** Tek sunucu mimarisi; yüksek trafik için load balancing gerekir
3. **Telaffuz Değerlendirmesi:** Gemini'nin ses analizi kapsamında olmakla birlikte, fonetik düzeyde ayrıntılı telaffuz geri bildirimi sınırlıdır
4. **Çevrimdışı Çalışma:** Platform tamamen çevrimiçi çalışmaktadır
5. **Mobil Uygulama:** Responsive web tasarımı mevcut, ancak native mobil uygulama yoktur

### Gelecek Geliştirme Önerileri

| Özellik | Öncelik | Açıklama |
|---------|---------|----------|
| PostgreSQL geçişi | Yüksek | Üretim ortamı için ölçeklenebilir veritabanı |
| Rate limiting | Yüksek | Brute force ve DDoS koruması |
| E-posta doğrulama | Yüksek | Kayıt onayı için e-posta aktivasyonu |
| Şifre sıfırlama | Orta | "Şifremi unuttum" akışı |
| Toplu öğrenci yükleme | Orta | CSV/Excel ile toplu kayıt |
| Detaylı telaffuz analizi | Orta | Ses dalgası karşılaştırma |
| Gerçek zamanlı bildirimler | Düşük | WebSocket ile anlık bildirimler |
| Mobil uygulama (PWA) | Düşük | Progressive Web App desteği |
| Çok dilli destek | Düşük | Farklı dillerde konuşma değerlendirme |

---

## Proje Dizin Yapısı

```
speak_ai/
├── .gitignore
├── README.md
├── backend/
│   ├── .env                    # Ortam değişkenleri (gizli)
│   ├── .env.example            # Örnek ortam dosyası
│   ├── main.py                 # FastAPI uygulama giriş noktası
│   ├── config.py               # Yapılandırma (JWT, API, DB, CORS)
│   ├── database.py             # SQLAlchemy engine ve session
│   ├── models.py               # Veritabanı modelleri (9 tablo)
│   ├── auth.py                 # Kimlik doğrulama (JWT + bcrypt)
│   ├── requirements.txt        # Python bağımlılıkları
│   ├── routers/
│   │   ├── auth_router.py      # Giriş, kayıt, profil
│   │   ├── admin_router.py     # Yönetici işlemleri
│   │   ├── teacher_router.py   # Öğretmen işlemleri
│   │   ├── student_router.py   # Öğrenci işlemleri
│   │   └── parent_router.py    # Veli işlemleri
│   ├── services/
│   │   ├── ai_service.py       # Gemini AI değerlendirme + TTS
│   │   └── speech_service.py   # Ses transkripsiyon
│   └── uploads/                # Kullanıcı yüklemeleri
│       ├── audio/              # Öğrenci ses kayıtları
│       ├── avatars/            # Profil fotoğrafları
│       └── paragraphs/         # Paragraf TTS dosyaları
├── frontend/
│   ├── index.html              # Giriş/Kayıt sayfası
│   ├── dashboard.html          # Ana panel (tüm roller)
│   ├── css/
│   │   └── style.css           # Ana stil dosyası (dark theme)
│   ├── js/
│   │   ├── app.js              # Çekirdek JS (API, auth, sidebar)
│   │   └── recorder.js         # Ses kaydedici sınıfı
│   └── student/
│       └── record.html         # Ses kaydı sayfası
```

---

## Lisans ve İletişim

Bu proje eğitim amaçlı geliştirilmiştir.

**Proje:** SpeakScorer — Yapay Zeka Destekli İngilizce Konuşma Değerlendirme Platformu  
**Kapsam:** TOKFEST İngilizce Konuşma Festivali  
**Teknoloji:** FastAPI + Gemini 2.5 Flash + Vanilla JS  
**Sürüm:** 1.0.0

---

<p align="center">
  <em>SpeakScorer — Yapay Zeka ile İngilizce Konuşma Becerilerini Geliştirin 🎤</em>
</p>
