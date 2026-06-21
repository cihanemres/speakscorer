"""
SpeakScorer — Kimlik Doğrulama Router
Kayıt, giriş, çıkış, profil işlemleri.
Güvenlik: HttpOnly cookie + CSRF, rate-limit, brute-force kilidi, Turnstile CAPTCHA.
"""
import os
import json
import time
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, constr
from typing import Optional

from database import get_db
from models import User, UserRole, UserStatus, UserStreak
from auth import (
    hash_password, verify_password, create_token, get_current_user,
    generate_csrf_token, set_auth_cookies, clear_auth_cookies,
)
from config import (
    PASSWORD_MIN_LENGTH, RATE_LIMIT_AUTH_MAX, RATE_LIMIT_AUTH_WINDOW,
)
from security import enforce_rate_limit, login_guard, verify_turnstile, get_client_ip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Avatar yükleme: sunucunun güvendiği imza (magic-byte) -> uzantı eşlemesi.
_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": ".jpg",                       # JPEG
    b"\x89PNG\r\n\x1a\n": ".png",                  # PNG
}
_AVATAR_MAX_SIZE = 2 * 1024 * 1024                 # 2 MB


# ── Doğrulama yardımcıları ────────────────────────────────
def validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(400, f"Şifre en az {PASSWORD_MIN_LENGTH} karakter olmalıdır")
    if password.isdigit() or password.isalpha():
        raise HTTPException(400, "Şifre hem harf hem rakam içermelidir")


def _detect_image_ext(head: bytes) -> Optional[str]:
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    for sig, ext in _IMAGE_SIGNATURES.items():
        if head.startswith(sig):
            return ext
    return None


# ── Şemalar ───────────────────────────────────────────────
class RegisterRequest(BaseModel):
    ad_soyad: constr(strip_whitespace=True, min_length=2, max_length=100)
    email: EmailStr
    password: constr(min_length=1, max_length=128)
    rol: str = "ogrenci"
    sinif_duzeyi: Optional[int] = None
    sube: Optional[constr(strip_whitespace=True, max_length=10)] = None
    captcha_token: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=1, max_length=128)
    captcha_token: Optional[str] = None


class ProfileUpdate(BaseModel):
    ad_soyad: Optional[constr(strip_whitespace=True, min_length=2, max_length=100)] = None
    email: Optional[EmailStr] = None
    password: Optional[constr(min_length=1, max_length=128)] = None
    current_password: Optional[str] = None
    sinif_duzeyi: Optional[int] = None
    sube: Optional[constr(strip_whitespace=True, max_length=10)] = None


def user_dict(user: User) -> dict:
    permissions = {}
    if user.permissions:
        try:
            permissions = json.loads(user.permissions)
        except Exception:
            pass

    return {
        "id": user.id,
        "ad_soyad": user.ad_soyad,
        "email": user.email,
        "rol": user.rol.value,
        "status": user.status.value,
        "sinif_duzeyi": user.sinif_duzeyi,
        "sube": user.sube,
        "profil_fotografi": user.profil_fotografi,
        "permissions": permissions,
    }


# ── Kayıt ─────────────────────────────────────────────────
@router.post("/register")
async def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth", RATE_LIMIT_AUTH_MAX, RATE_LIMIT_AUTH_WINDOW)

    if not await verify_turnstile(data.captcha_token, get_client_ip(request)):
        raise HTTPException(400, "CAPTCHA doğrulaması başarısız. Lütfen tekrar deneyin.")

    validate_password(data.password)

    try:
        role = UserRole(data.rol)
    except ValueError:
        raise HTTPException(400, "Geçersiz rol")

    # Block admin/mod registration via public API.
    if role in (UserRole.admin, UserRole.moderator):
        raise HTTPException(403, "Yönetici/Moderatör hesabı herkese açık kayıt ile oluşturulamaz")

    if db.query(User).filter(User.email == data.email).first():
        # Enumerasyonu azaltmak için genel mesaj
        raise HTTPException(400, "Kayıt tamamlanamadı. Bilgilerinizi kontrol edin.")

    status_val = UserStatus.pending  # Tüm herkese açık kayıtlar admin onayı bekler

    user = User(
        ad_soyad=data.ad_soyad,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=role,
        status=status_val,
        sinif_duzeyi=data.sinif_duzeyi,
        sube=data.sube,
    )
    db.add(user)
    db.flush()
    db.add(UserStreak(user_id=user.id))
    db.commit()
    db.refresh(user)

    # Pending kullanıcılara token verilmez.
    return {"user": user_dict(user)}


# ── Giriş ─────────────────────────────────────────────────
@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, "auth", RATE_LIMIT_AUTH_MAX, RATE_LIMIT_AUTH_WINDOW)
    login_guard.check_locked(data.email)

    if not await verify_turnstile(data.captcha_token, get_client_ip(request)):
        raise HTTPException(400, "CAPTCHA doğrulaması başarısız. Lütfen tekrar deneyin.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        login_guard.record_failure(data.email)
        raise HTTPException(401, "E-posta veya şifre hatalı")

    if user.status == UserStatus.pending:
        raise HTTPException(403, "Hesabınız henüz onaylanmadı")
    if user.status in (UserStatus.inactive, UserStatus.rejected):
        raise HTTPException(403, "Hesabınız devre dışı")

    login_guard.reset(data.email)

    token = create_token(user)
    csrf = generate_csrf_token()
    set_auth_cookies(response, token, csrf)
    # Token gövdede DÖNMEZ (HttpOnly cookie'de). CSRF token'ı frontend'in
    # header'da geri gönderebilmesi için cookie'de + gövdede verilir.
    return {"user": user_dict(user), "csrf_token": csrf}


# ── Çıkış ─────────────────────────────────────────────────
@router.post("/logout")
def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Çıkış yapıldı"}


@router.get("/me")
def get_profile(user: User = Depends(get_current_user)):
    return user_dict(user)


# ── Profil güncelleme ─────────────────────────────────────
@router.put("/profile")
def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Hassas değişiklikler (e-posta/şifre) için mevcut şifre doğrulaması iste.
    sensitive = (data.password is not None) or (data.email is not None and data.email != user.email)
    if sensitive:
        if not data.current_password or not verify_password(data.current_password, user.password_hash):
            raise HTTPException(403, "Mevcut şifrenizi doğru girmelisiniz")

    if data.ad_soyad:
        user.ad_soyad = data.ad_soyad
    if data.email and data.email != user.email:
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(400, "Bu e-posta zaten kullanılıyor")
        user.email = data.email
    if data.password:
        validate_password(data.password)
        user.password_hash = hash_password(data.password)
    if data.sinif_duzeyi is not None:
        user.sinif_duzeyi = data.sinif_duzeyi
    if data.sube is not None:
        user.sube = data.sube

    db.commit()
    return {"message": "Profil güncellendi", "user": user_dict(user)}


# ── Avatar yükleme (güvenli) ──────────────────────────────
@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Profil fotoğrafı yükler — sunucu tarafı imza (magic-byte) doğrulaması ile."""
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "Boş dosya yüklenemez")
    if len(content) > _AVATAR_MAX_SIZE:
        raise HTTPException(400, "Dosya boyutu 2MB'ı geçemez")

    # İçeriğin gerçekten görsel olduğunu imzadan doğrula; uzantıyı SUNUCU belirler
    # (istemci filename/content_type'ına güvenilmez).
    ext = _detect_image_ext(content[:16])
    if ext is None:
        raise HTTPException(400, "Sadece JPG, PNG veya WEBP yükleyebilirsiniz")

    from config import UPLOAD_DIR
    avatar_dir = os.path.join(UPLOAD_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    filename = f"avatar_{user.id}_{int(time.time())}{ext}"
    filepath = os.path.join(avatar_dir, filename)

    with open(filepath, "wb") as buffer:
        buffer.write(content)

    # Yetkili medya endpoint'i üzerinden servis edilir (statik mount yok).
    user.profil_fotografi = f"/api/media/avatar/{user.id}"
    db.commit()

    return {"message": "Profil fotoğrafı güncellendi", "profil_fotografi": user.profil_fotografi}
