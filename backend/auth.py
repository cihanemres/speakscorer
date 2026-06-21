"""
SpeakScorer — Kimlik Doğrulama ve Yetkilendirme
JWT tabanlı, rol bazlı erişim kontrolü
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES,
    AUTH_COOKIE_NAME, CSRF_COOKIE_NAME, COOKIE_SECURE, COOKIE_SAMESITE, COOKIE_DOMAIN,
)
from database import get_db
from models import User, UserRole, UserStatus

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Bearer token kabul edilir ama OPSİYONEL — birincil yol HttpOnly cookie'dir.
bearer_scheme = HTTPBearer(auto_error=False)

_COOKIE_MAX_AGE = JWT_EXPIRE_MINUTES * 60


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "rol": user.rol.value,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, token: str, csrf_token: str) -> None:
    """JWT'yi HttpOnly cookie'de, CSRF token'ını JS-okunabilir cookie'de yazar."""
    response.set_cookie(
        key=AUTH_COOKIE_NAME, value=token,
        max_age=_COOKIE_MAX_AGE, httponly=True,
        secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, domain=COOKIE_DOMAIN, path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME, value=csrf_token,
        max_age=_COOKIE_MAX_AGE, httponly=False,   # frontend bunu okuyup header'da gönderir
        secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, domain=COOKIE_DOMAIN, path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(AUTH_COOKIE_NAME, domain=COOKIE_DOMAIN, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, domain=COOKIE_DOMAIN, path="/")


def _extract_token(request: Request, creds: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    """Önce HttpOnly cookie, yoksa Authorization: Bearer (API istemcileri için)."""
    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    if creds:
        return creds.credentials
    return None


def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(request, creds)
    if not token:
        raise HTTPException(status_code=401, detail="Kimlik doğrulama gerekli")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Geçersiz token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    if user.status != UserStatus.active:
        raise HTTPException(status_code=403, detail="Hesap aktif değil")
    return user


def require_role(*roles: UserRole):
    """Dependency factory for role-based access."""
    def role_checker(user: User = Depends(get_current_user)):
        if user.rol not in roles:
            raise HTTPException(status_code=403, detail="Yetkisiz erişim")
        return user
    return role_checker
