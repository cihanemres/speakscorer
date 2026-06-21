"""
SpeakScorer — Application Configuration
All secrets loaded from environment variables (.env file).
No hardcoded credentials.
"""
import os
import sys
from pathlib import Path

# ── Load .env file ────────────────────────────────────────
# python-dotenv reads the .env file in the same directory as this module.
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

# ── Database ──────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./speakai.db")

# ── JWT ───────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    print("FATAL: JWT_SECRET environment variable is not set.", file=sys.stderr)
    print("       Create a backend/.env file from .env.example.", file=sys.stderr)
    sys.exit(1)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24h

# ── Google APIs ───────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_SPEECH_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# ── Upload paths ──────────────────────────────────────────
# UPLOAD_DIR ortam değişkeniyle ezilebilir: üretimde (Render kalıcı disk vb.)
# yüklenen sesleri host diskine yazmak için /var/data/uploads gibi mutlak bir
# yola işaret ettir. Boşsa yerel ./uploads kullanılır (geliştirme).
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "").strip() or os.path.join(os.path.dirname(__file__), "uploads")
PARAGRAPH_AUDIO_DIR = os.path.join(UPLOAD_DIR, "paragraphs")
SUBMISSION_AUDIO_DIR = os.path.join(UPLOAD_DIR, "submissions")

# Create dirs
for d in [UPLOAD_DIR, PARAGRAPH_AUDIO_DIR, SUBMISSION_AUDIO_DIR]:
    os.makedirs(d, exist_ok=True)

# ── CORS ──────────────────────────────────────────────────
_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:8000")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

# ── Demo mode ─────────────────────────────────────────────
# Explicit override via env, otherwise auto-detect from API key presence.
_demo_env = os.getenv("DEMO_MODE", "").strip().lower()
if _demo_env in ("true", "1", "yes"):
    DEMO_MODE = True
elif _demo_env in ("false", "0", "no"):
    DEMO_MODE = False
else:
    DEMO_MODE = not bool(GEMINI_API_KEY)

# ── Seeding ───────────────────────────────────────────────
SEED_ENABLED = os.getenv("SEED_ENABLED", "false").strip().lower() in ("true", "1", "yes")
SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "")
SEED_TEACHER_PASSWORD = os.getenv("SEED_TEACHER_PASSWORD", "")
SEED_STUDENT_PASSWORD = os.getenv("SEED_STUDENT_PASSWORD", "")
SEED_PARENT_PASSWORD = os.getenv("SEED_PARENT_PASSWORD", "")


def _as_bool(value: str, default: bool = False) -> bool:
    v = (value or "").strip().lower()
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    return default


# ── Environment ───────────────────────────────────────────
# "production" enables hardened defaults (Secure cookies, no /docs, etc.).
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

# ── JWT secret strength validation ────────────────────────
# HS256 means anyone who knows JWT_SECRET can forge a token for ANY user/role
# (full admin takeover). A short or placeholder secret is therefore a critical
# risk. Fatal in production; a warning in development so local setup keeps
# working with a throwaway secret.
_JWT_PLACEHOLDER_MARKERS = (
    "change", "example", "placeholder", "changeme", "secret-key",
    "your-secret", "your_secret", "replace", "todo", "xxxx", "dummy",
)
_jwt_lower = JWT_SECRET.lower()
_jwt_weak = len(JWT_SECRET) < 32 or any(m in _jwt_lower for m in _JWT_PLACEHOLDER_MARKERS)
if _jwt_weak:
    _jwt_msg = (
        "JWT_SECRET is weak or a placeholder (need >=32 chars, no placeholder words). "
        'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )
    if IS_PRODUCTION:
        print(f"FATAL: {_jwt_msg}", file=sys.stderr)
        sys.exit(1)
    print(f"WARNING: {_jwt_msg}", file=sys.stderr)

# ── Auth cookies (JWT is delivered as an HttpOnly cookie, never to JS) ──
# Cookie name for the JWT. A separate, JS-readable CSRF token cookie is used
# for the double-submit CSRF defence.
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "speakai_session")
CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "speakai_csrf")
CSRF_HEADER_NAME = "X-CSRF-Token"
# Secure flag: required over HTTPS. Auto-on in production; overridable for
# local HTTP development where Secure cookies would be dropped.
COOKIE_SECURE = _as_bool(os.getenv("COOKIE_SECURE", ""), default=IS_PRODUCTION)
# SameSite=strict gives strong CSRF protection for this same-origin app.
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "strict").strip().lower()
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "").strip() or None

# ── Rate limiting / brute-force (in-memory, single-process) ──
RATE_LIMIT_ENABLED = _as_bool(os.getenv("RATE_LIMIT_ENABLED", "true"), default=True)
# Global per-IP request budget (L7 flood mitigation).
RATE_LIMIT_GLOBAL_MAX = int(os.getenv("RATE_LIMIT_GLOBAL_MAX", "300"))
RATE_LIMIT_GLOBAL_WINDOW = int(os.getenv("RATE_LIMIT_GLOBAL_WINDOW", "60"))   # seconds
# Stricter budget for authentication endpoints.
RATE_LIMIT_AUTH_MAX = int(os.getenv("RATE_LIMIT_AUTH_MAX", "8"))
RATE_LIMIT_AUTH_WINDOW = int(os.getenv("RATE_LIMIT_AUTH_WINDOW", "60"))       # seconds
# Per-user budget for expensive AI/LLM endpoints (Gemini değerlendirmesi).
# Kaçak maliyeti önlemek için CLAUDE.md kuralı: kullanıcı başına dakikada ~10 istek.
RATE_LIMIT_AI_MAX = int(os.getenv("RATE_LIMIT_AI_MAX", "10"))
RATE_LIMIT_AI_WINDOW = int(os.getenv("RATE_LIMIT_AI_WINDOW", "60"))           # seconds
# LLM çağrılarında çıktı token tavanı (kaçak maliyet/uzayan yanıt koruması).
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048"))
# Account lockout after repeated failed logins (per email).
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "900"))        # 15 min

# ── CAPTCHA (Cloudflare Turnstile) ────────────────────────
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "").strip()
TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "").strip()
# CAPTCHA is enforced only when a secret key is configured, so local/dev
# environments without Turnstile keys keep working.
CAPTCHA_ENABLED = _as_bool(os.getenv("CAPTCHA_ENABLED", ""), default=bool(TURNSTILE_SECRET_KEY))

# Fail closed in production: a public deployment must not silently run with
# bot protection OFF on login/register (verify_turnstile returns True when
# CAPTCHA is disabled). Production requires Turnstile by default; opt out only
# by consciously setting CAPTCHA_REQUIRED=false.
CAPTCHA_REQUIRED = _as_bool(os.getenv("CAPTCHA_REQUIRED", ""), default=IS_PRODUCTION)
if CAPTCHA_REQUIRED and not CAPTCHA_ENABLED:
    print(
        "FATAL: CAPTCHA is required in production but TURNSTILE_SECRET_KEY is not set. "
        "Configure Turnstile keys, or set CAPTCHA_REQUIRED=false to accept the risk.",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Password policy ───────────────────────────────────────
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))

# ── Trusted hosts / allowed origins for security middleware ──
# Reuse CORS_ORIGINS as the allowed front-end origins.
