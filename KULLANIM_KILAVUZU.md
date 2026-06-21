# 🎤 SpeakScorer — Kullanım Kılavuzu

SpeakScorer, yapay zeka destekli İngilizce konuşma becerilerini değerlendiren, sınıf içi ödev takibini kolaylaştıran ve öğrencileri oyunlaştırma ögeleriyle teşvik eden yenilikçi bir eğitim platformudur. Bu kılavuz; **Öğrenci**, **Öğretmen**, **Veli** ve **Yönetici (Admin)** rollerinin sistemi nasıl kullanacağını detaylı bir şekilde açıklamaktadır.

---

## 📑 İçindekiler
1. [Sisteme Giriş ve Kayıt](#1-sisteme-giriş-ve-kayıt)
2. [Öğrenci Kullanım Rehberi](#2-öğrenci-kullanım-rehberi)
3. [Öğretmen Kullanım Rehberi](#3-öğretmen-kullanım-rehberi)
4. [Veli Kullanım Rehberi](#4-veli-kullanım-rehberi)
5. [Yönetici (Admin) Kullanım Rehberi](#5-yönetici-admin-kullanım-rehberi)
6. [Yapay Zeka Değerlendirme Kriterleri](#6-yapay-zeka-değerlendirme-kriterleri)
7. [Oyunlaştırma (XP & Rozet) Sistemi](#7-oyunlaştırma-xp-rozet-sistemi)

---

## 1. Sisteme Giriş ve Kayıt

SpeakScorer web uygulamasına tarayıcınızdan `http://localhost:8000` adresinden erişebilirsiniz.

- **Kayıt Olma:** Giriş ekranındaki "Kayıt Ol" sekmesine tıklayarak Ad Soyad, E-posta, Şifre ve Rolünüzü (Öğrenci, Öğretmen, Veli) belirleyerek yeni bir üyelik talebi oluşturabilirsiniz.
  > [!IMPORTANT]
  > Güvenlik gereği yeni kayıt olan hesaplar, yönetici (admin) tarafından onaylanana kadar sisteme giriş yapamaz.
- **Hazır Kullanıcılar (Demo/Seed):** İlk kurulumda test edebilmeniz için aşağıdaki hazır kullanıcı hesapları oluşturulmuştur:
  - **Öğrenci:** `ogrenci@speakscorer.com` / `ogrenci123`
  - **Öğretmen:** `ogretmen@speakscorer.com` / `ogretmen123`
  - **Veli:** `veli@speakscorer.com` / `veli123`
  - **Yönetici:** `admin@speakscorer.com` / `admin123`

---

## 2. Öğrenci Kullanım Rehberi

Öğrenciler kendilerine atanan ödevleri okur, ses kaydı yapar ve yapay zeka ile öğretmenlerinden geri bildirim alırlar.

### 🎙️ Konuşma Pratiği ve Ses Kaydı Aşamaları:
1. **Giriş Paneli:** Giriş yaptıktan sonra XP seviyenizi, günlük giriş serinizi (streak), rozetlerinizi ve size atanmış aktif ödevleri görürsünüz.
2. **Ödev Seçimi:** Atanan ödevlerden birine tıklayarak kayıt sayfasına yönlendirilirsiniz.
3. **Paragrafı Dinleme:** "🔊 Metni Dinle" butonu yardımıyla paragrafın doğru telaffuzunu yapay zekadan (TTS) dinleyebilirsiniz.
4. **Ses Kaydı Başlatma:** Mikrofon simgesine (🎤) tıklayarak kaydı başlatın. Net ve anlaşılır bir ses tonuyla ekrandaki İngilizce paragrafı okuyun.
5. **Ses Kaydı Bitirme:** Okumanız bittiğinde mikrofon butonuna tekrar basarak kaydı durdurun. Kaydettiğiniz sesi "Oynat" butonuyla dinleyebilirsiniz.
6. **Yapay Zeka Analizine Gönderme:** "📤 AI Değerlendirmesine Gönder" butonuna basarak ses kaydınızı Gemini 2.5 Flash modeline analiz ettirin. Saniyeler içinde detaylı puanınız ve Türkçe geri bildiriminiz ekrana gelecektir.

![Öğrenci Pratik ve Kayıt Arayüzü](file:///C:/Users/cihanemres/.gemini/antigravity-ide/brain/37ec2025-e596-496c-ba07-5507c8bdc70a/student_practice_screen_1781386606116.png)

---

## 3. Öğretmen Kullanım Rehberi

Öğretmenler öğrencilerine ödev atayabilir, öğrencilerin gönderdiği ses kayıtlarını dinleyebilir, yapay zekanın verdiği puanları revize edip kendi puanlarını verebilir ve öğrencilere ödül rozetleri/takdir belgeleri sunabilirler.

### 👨‍🏫 Başlıca Öğretmen İşlevleri:
- **Ödev Tanımlama:** Platformda bulunan hazır paragraflardan seviyeye uygun olanı seçip sınıf veya belirli bir öğrenciye son teslim tarihiyle birlikte atayabilirsiniz.
- **Gönderim Değerlendirme:** Öğrencinin konuşmasını sistem üzerinden dinleyebilir, yapay zekanın çıkardığı transkripti okuyabilir ve 4 temel kriterde (Kelime, Dilbilgisi, Akıcılık, Tutarlılık) 0-25 puan arası kendi puanınızı girerek süreci tamamlayabilirsiniz. Öğretmen puanı, yapay zeka puanını geçersiz kılar ve nihai puan olarak sisteme kaydedilir.
- **Takdir ve Teşekkür:** Üstün başarı gösteren öğrencilerin motivasyonunu artırmak amacıyla XP ödüllü Takdir/Teşekkür belgeleri ve rozetler atayabilirsiniz.

![Öğretmen Değerlendirme ve İstatistik Paneli](file:///C:/Users/cihanemres/.gemini/antigravity-ide/brain/37ec2025-e596-496c-ba07-5507c8bdc70a/teacher_grading_dashboard_1781386618337.png)

---

## 4. Veli Kullanım Rehberi

Veliler, çocuklarının İngilizce konuşma becerisindeki gelişimini güncel olarak ve salt okunur modda takip ederler.

### 📊 İzlenebilen Veriler:
- **Genel Durum:** Çocuğun toplam tamamladığı ödev sayısı, ortalama konuşma puanı ve haftalık aktivite grafiği.
- **Sıralamalar:** Çocuğun sınıf ve okul genelindeki sıralama durumu.
- **Kazanılan Ödüller:** Çocuğun aldığı rozetler ve öğretmenlerinden gelen takdir/teşekkür belgeleri.
- **Detaylı Analiz:** Son ödevlerin ses kayıt transkriptleri, yapay zeka ve öğretmen geri bildirimleri.

---

## 5. Yönetici (Admin) Kullanım Rehberi

Yöneticiler sistemin güvenliğini, veri doğruluğunu ve kullanıcı yönetimini üstlenirler.

- **Kullanıcı Yönetimi:** Yeni kayıt olan öğretmen, öğrenci ve velileri inceler, onaylar veya reddeder. Kullanıcı rollerini günceller.
- **İçerik Yönetimi:** Platforma yeni İngilizce paragraflar ekler. Sistem bu paragraflara ait TTS (sesli okuma) dosyalarını otomatik olarak üretir. Ayrıca öğretmenlerin önerdiği paragrafları onaylayarak müfredata dahil eder.
- **Platform Analitiği:** Sistem genelindeki toplam kullanıcı, gönderim ve genel başarı oranlarını izler.

---

## 6. Yapay Zeka Değerlendirme Kriterleri

SpeakScorer, **Google Gemini 2.5 Flash** multimodal modelini kullanarak ses dosyasını hem işitsel hem de metinsel olarak 4 temel kriter üzerinden 100 tam puan üzerinden değerlendirir:

| Kriter | Puan | Açıklama |
|---|---|---|
| **Kelime Bilgisi (Vocabulary)** | 0 - 25 | Kelime zenginliği, uygunluğu ve bağlamsal doğruluk. |
| **Dilbilgisi (Grammar)** | 0 - 25 | Cümle yapılarının doğruluğu, zamanların ve eklerin doğru kullanımı. |
| **Akıcılık (Fluency)** | 0 - 25 | Konuşma hızı, duraksamaların sıklığı ve genel konuşma temposu. |
| **Tutarlılık (Coherence)** | 0 - 25 | Cümlelerin mantıksal sıralaması ve bağlaçların kullanımı. |

---

## 7. Oyunlaştırma (XP & Rozet) Sistemi

Öğrencileri İngilizce pratik yapmaya teşvik etmek için tasarlanmış ödül mekanizmasıdır.

### ⚡ XP Kazanma Tablosu:
- **Gönderim Tamamlama:** +10 XP
- **Mükemmel Puan (95+):** +25 XP
- **Yüksek Puan (80+):** +15 XP
- **Günlük Giriş (Streak):** +5 XP
- **Öğretmen Rozeti:** +20 XP

### 🏆 Kazanılabilir Rozetler:
- 🌟 **İlk Adım:** İlk ses gönderimi başarıyla tamamlandığında kazanılır.
- ⚡ **Hızlı Konuşmacı:** En az 5 ödev tamamlandığında kazanılır.
- 🎯 **Pratik Ustası:** En az 10 ödev tamamlandığında kazanılır.
- 🏆 **Mükemmel Puan:** Yapay zekadan veya öğretmenden 95+ puan alındığında kazanılır.
- 💪 **İstikrarlı Öğrenci:** 70+ puan ortalamasıyla en az 3 gönderim yapıldığında verilir.

![Oyunlaştırma Rozetler ve İlerleme Grafiği](file:///C:/Users/cihanemres/.gemini/antigravity-ide/brain/37ec2025-e596-496c-ba07-5507c8bdc70a/student_gamification_dashboard_1781386631151.png)
