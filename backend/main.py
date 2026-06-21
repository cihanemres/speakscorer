"""
SpeakScorer — Ana FastAPI Uygulaması
TOKFEST İngilizce Konuşma Platformu
"""
import os
import sys
import secrets
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from config import (
    CORS_ORIGINS, UPLOAD_DIR, PARAGRAPH_AUDIO_DIR, DEMO_MODE,
    SEED_ENABLED, SEED_ADMIN_PASSWORD, SEED_TEACHER_PASSWORD,
    SEED_STUDENT_PASSWORD, SEED_PARENT_PASSWORD,
    IS_PRODUCTION, AUTH_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME,
    TURNSTILE_SITE_KEY, CAPTCHA_ENABLED,
)
from security import check_global_rate_limit
from database import init_db, SessionLocal, engine
from models import User, UserRole, UserStatus, Paragraph, UserStreak
from auth import hash_password

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ───────────────────────────────────────
    try:
        init_db()
    except Exception as e:
        logger.critical("FATAL: Database initialization failed: %s", e)
        sys.exit(1)

    if SEED_ENABLED:
        seed_data()

    logger.info("✅ SpeakScorer başlatıldı!")
    yield
    # ── Shutdown ──────────────────────────────────────
    logger.info("🛑 SpeakScorer kapatılıyor...")


app = FastAPI(
    title="SpeakScorer - İngilizce Konuşma Platformu",
    description="Yapay Zeka Destekli İngilizce Konuşma Değerlendirme Platformu (TOKFEST)",
    version="1.0.0",
    lifespan=lifespan,
    # Üretimde API keşif yüzeyini kapat.
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", CSRF_HEADER_NAME],
)

# ── Güvenlik middleware: rate-limit (L7) + CSRF + güvenlik başlıkları ──
_UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
# CSRF muafiyeti: kimlik henüz oluşmadan çağrılan uçlar (cookie yoktur zaten).
# NOT (M-5): /api/auth/logout muafiyetten ÇIKARILDI. Oturum açıkken çağrıldığı
# için CSRF token'ı taşıyabilir ve taşımalıdır; aksi halde saldırgan kurbanı
# zorla logout edebilir (oturum sabitleme/kullanılabilirlik saldırısı).
_CSRF_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/register"}

# CSP: Uygulama satır-içi (inline) script/handler kullandığından 'unsafe-inline'
# gereklidir; bu yüzden XSS'e karşı BİRİNCİL savunma frontend'deki kaçış (escaping)
# işlemidir. CSP burada ek katman sağlar (harici script kaynaklarını ve
# clickjacking'i kısıtlar). Satır-içi JS kaldırıldığında 'unsafe-inline' çıkarılmalı.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://challenges.cloudflare.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "media-src 'self' blob:; "
    "connect-src 'self' https://challenges.cloudflare.com; "
    "frame-src https://challenges.cloudflare.com; "
    "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # 1) Global L7 flood koruması
    retry_after = check_global_rate_limit(request)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            content={"detail": "Çok fazla istek. Lütfen biraz sonra tekrar deneyin."},
            headers={"Retry-After": str(retry_after)},
        )

    # 2) CSRF (double-submit): kimlik cookie'si varken yapılan değiştirici istekler
    if request.method in _UNSAFE_METHODS and request.url.path not in _CSRF_EXEMPT_PATHS:
        if request.cookies.get(AUTH_COOKIE_NAME):  # yalnızca cookie-auth isteklerinde
            header_token = request.headers.get(CSRF_HEADER_NAME, "")
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
            if not header_token or not cookie_token or not secrets.compare_digest(header_token, cookie_token):
                return JSONResponse(status_code=403, content={"detail": "CSRF doğrulaması başarısız"})

    response = await call_next(request)

    # 3) Güvenlik başlıkları
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(self)"
    response.headers["Content-Security-Policy"] = _CSP
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

# ── Static files & Uploads ────────────────────────────────
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PARAGRAPH_AUDIO_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "audio"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "avatars"), exist_ok=True)

# GÜVENLİK: Tüm /uploads dizini ARTIK statik olarak servis EDİLMEZ. Yalnızca
# herkese açık, hassas olmayan paragraf TTS sesleri statik sunulur. Öğrenci ses
# kayıtları ve avatarlar yetkili /api/media/* uçlarından geçer (IDOR fix — S-03).
app.mount("/uploads/paragraphs", StaticFiles(directory=PARAGRAPH_AUDIO_DIR), name="paragraphs")

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# ── Routers ───────────────────────────────────────────────
from routers.auth_router import router as auth_router
from routers.admin_router import router as admin_router
from routers.teacher_router import router as teacher_router
from routers.student_router import router as student_router
from routers.parent_router import router as parent_router
from routers.media_router import router as media_router

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(teacher_router)
app.include_router(student_router)
app.include_router(parent_router)
app.include_router(media_router)


# ── Frontend Serving ──────────────────────────────────────
@app.get("/")
def root():
    index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return HTMLResponse("<h1>SpeakScorer API çalışıyor</h1><p><a href='/docs'>/docs</a></p>")


@app.get("/app/{path:path}")
def serve_frontend(path: str):
    # Resolve the requested path and verify it stays within frontend_dir
    # to prevent directory traversal attacks (e.g., ../../etc/passwd).
    base = os.path.realpath(frontend_dir)
    requested = os.path.realpath(os.path.join(frontend_dir, path))
    if not requested.startswith(base):
        return FileResponse(os.path.join(frontend_dir, "index.html"))
    if os.path.exists(requested) and os.path.isfile(requested):
        return FileResponse(requested)
    return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/health")
def health():
    """Deep health check — verifies database connectivity."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unreachable"},
        )


@app.get("/api/config/public")
def public_config():
    """Expose non-sensitive configuration to the frontend."""
    return {
        "demo_mode": DEMO_MODE,
        "captcha_enabled": CAPTCHA_ENABLED,
        # Site key herkese açıktır (gizli değildir); secret backend'de kalır.
        "turnstile_site_key": TURNSTILE_SITE_KEY,
    }



def seed_data():
    """Veritabanına başlangıç verilerini ekle."""
    db = SessionLocal()
    try:
        if db.query(User).filter(User.rol == UserRole.admin).first():
            return

        logger.info("🌱 Veritabanı tohumlanıyor...")

        # ── Yönetici ──────────────────────────────────────
        if not SEED_ADMIN_PASSWORD:
            logger.warning("⚠️ SEED_ADMIN_PASSWORD not set, skipping seed.")
            return

        admin = User(
            ad_soyad="Sistem Yöneticisi",
            email="admin@speakscorer.com",
            password_hash=hash_password(SEED_ADMIN_PASSWORD),
            rol=UserRole.admin,
            status=UserStatus.active,
        )
        db.add(admin)
        db.flush()
        db.add(UserStreak(user_id=admin.id))

        # ── Öğretmen ─────────────────────────────────────
        teacher = User(
            ad_soyad="Ayşe Öğretmen",
            email="ogretmen@speakscorer.com",
            password_hash=hash_password(SEED_TEACHER_PASSWORD),
            rol=UserRole.teacher,
            status=UserStatus.active,
            brans="İngilizce",
        )
        db.add(teacher)
        db.flush()
        db.add(UserStreak(user_id=teacher.id))

        # ── Öğrenci ───────────────────────────────────────
        student = User(
            ad_soyad="Ali Öğrenci",
            email="ogrenci@speakscorer.com",
            password_hash=hash_password(SEED_STUDENT_PASSWORD),
            rol=UserRole.student,
            status=UserStatus.active,
            sinif_duzeyi=5,
            teacher_id=teacher.id,
        )
        db.add(student)
        db.flush()
        db.add(UserStreak(user_id=student.id))

        # ── Veli ──────────────────────────────────────────
        parent = User(
            ad_soyad="Mehmet Veli",
            email="veli@speakscorer.com",
            password_hash=hash_password(SEED_PARENT_PASSWORD),
            rol=UserRole.parent,
            status=UserStatus.active,
        )
        db.add(parent)
        db.flush()
        db.add(UserStreak(user_id=parent.id))

        # Veli-Öğrenci bağlantısı
        student.parent_id = parent.id

        # ── İngilizce Paragraflar ─────────────────────────
        paragraphs = [
            {
                "title": "A Sunny Day",
                "text": "Today the weather is sunny and warm. The temperature is about twenty-five degrees. There are no clouds in the sky. It is a perfect day to go outside and play in the park. I like sunny days because I can ride my bicycle.",
                "level": 1,
                "category": "Nature",
            },
            {
                "title": "My Daily Routine",
                "text": "Every morning, I wake up at seven o'clock. I brush my teeth and take a shower. Then I have breakfast with my family. I usually eat toast and drink orange juice. After breakfast, I go to school by bus.",
                "level": 1,
                "category": "Daily Life",
            },
            {
                "title": "Library Visit",
                "text": "Last week, I went to the library with my friends. We found many interesting books about animals and space. The librarian helped us choose some good stories. I borrowed two books about dinosaurs. Reading is my favorite hobby.",
                "level": 2,
                "category": "Education",
            },
            {
                "title": "Technology and Future",
                "text": "Technology has changed our lives in many ways. We use computers and smartphones every day for communication and learning. In the future, robots might help us with housework and artificial intelligence will make education more personalized.",
                "level": 3,
                "category": "Technology",
            },
            {
                "title": "Friendship",
                "text": "Having good friends is very important. Friends help each other when they are sad or in trouble. They share happy moments together and make life more enjoyable. A true friend is someone who accepts you for who you are.",
                "level": 2,
                "category": "Values",
            },
            {
                "title": "Global Warming",
                "text": "Global warming is one of the biggest challenges facing our planet today. Rising temperatures cause ice caps to melt and sea levels to rise. We can help by reducing energy consumption, recycling, and using public transportation. Every small action matters.",
                "level": 4,
                "category": "Science",
            },
        ]

        for p in paragraphs:
            db.add(Paragraph(
                title=p["title"],
                text=p["text"],
                level=p["level"],
                category=p["category"],
                approved=True,
                created_by=admin.id,
            ))

        db.commit()
        logger.info("✅ Tohum veriler oluşturuldu (4 kullanıcı, %d paragraf).", len(paragraphs))

    except Exception as e:
        logger.error(f"Tohum hatası: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
