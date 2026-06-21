"""
SpeakScorer — Güvenlik yardımcıları
In-memory (tek süreç) rate limiting, brute-force hesap kilidi, Cloudflare
Turnstile CAPTCHA doğrulaması ve istemci IP çözümleme.

Not: Sayaçlar süreç-içi tutulur (kullanıcı tercihi: in-memory). Çok-süreç /
çok-sunucu dağıtımı için Redis tabanlı bir backend veya Nginx/Cloudflare
katmanı gerekir (bkz. README / DDoS notları).
"""
from __future__ import annotations

import time
import threading
import logging
from typing import Optional

import httpx
from fastapi import Request, HTTPException

from config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_GLOBAL_MAX,
    RATE_LIMIT_GLOBAL_WINDOW,
    LOGIN_MAX_FAILURES,
    LOGIN_LOCKOUT_SECONDS,
    CAPTCHA_ENABLED,
    TURNSTILE_SECRET_KEY,
)

logger = logging.getLogger(__name__)

_TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


# ── İstemci IP ────────────────────────────────────────────
def get_client_ip(request: Request) -> str:
    """
    İstemci IP'sini döndürür.

    Güvenlik notu: X-Forwarded-For sahtelenebilir; bu yüzden VARSAYILAN olarak
    doğrudan bağlantı IP'si (request.client.host) kullanılır. Uygulama güvenilir
    bir ters proxy (Nginx/Cloudflare) ARKASINDA çalışıyorsa, proxy'nin gerçek IP'yi
    yazdığından emin olun ve burada bilinçli olarak XFF'e geçin.
    """
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


# ── Sabit pencereli (fixed-window) rate limiter ───────────
class FixedWindowRateLimiter:
    """Anahtar başına sabit zaman penceresinde istek sayan basit limiter."""

    def __init__(self) -> None:
        self._buckets: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, max_hits: int, window_seconds: int) -> tuple[bool, int]:
        """
        Bir istek kaydeder.
        Dönüş: (izin_verildi, kalan_saniye_retry_after)
        """
        now = time.monotonic()
        with self._lock:
            window_start, count = self._buckets.get(key, (now, 0))
            # Pencere doldu mu? -> sıfırla
            if now - window_start >= window_seconds:
                window_start, count = now, 0
            count += 1
            self._buckets[key] = (window_start, count)
            if count > max_hits:
                retry_after = int(window_seconds - (now - window_start)) + 1
                return False, max(retry_after, 1)
            return True, 0

    def cleanup(self, window_seconds: int) -> None:
        """Süresi geçmiş kovaları temizler (bellek sızıntısını önlemek için)."""
        now = time.monotonic()
        with self._lock:
            stale = [k for k, (ws, _) in self._buckets.items()
                     if now - ws >= window_seconds * 2]
            for k in stale:
                self._buckets.pop(k, None)


_limiter = FixedWindowRateLimiter()


def check_global_rate_limit(request: Request) -> Optional[int]:
    """
    Global L7 flood koruması. Engellendiyse retry_after (saniye) döner, aksi
    hâlde None. Middleware'den çağrılır (HTTPException yerine değer döndürür).
    """
    if not RATE_LIMIT_ENABLED:
        return None
    ip = get_client_ip(request)
    allowed, retry_after = _limiter.hit(
        f"global:{ip}", RATE_LIMIT_GLOBAL_MAX, RATE_LIMIT_GLOBAL_WINDOW
    )
    return None if allowed else retry_after


def enforce_rate_limit(request: Request, scope: str, max_hits: int, window_seconds: int) -> None:
    """IP+scope için rate limit uygular; aşılırsa 429 fırlatır."""
    if not RATE_LIMIT_ENABLED:
        return
    ip = get_client_ip(request)
    key = f"{scope}:{ip}"
    allowed, retry_after = _limiter.hit(key, max_hits, window_seconds)
    if not allowed:
        logger.warning("Rate limit aşıldı: scope=%s ip=%s", scope, ip)
        raise HTTPException(
            status_code=429,
            detail="Çok fazla istek. Lütfen biraz sonra tekrar deneyin.",
            headers={"Retry-After": str(retry_after)},
        )


# ── Brute-force hesap kilidi (e-posta başına) ─────────────
class LoginGuard:
    """Başarısız giriş denemelerini e-posta başına sayar ve geçici kilitler."""

    def __init__(self) -> None:
        # email -> (fail_count, first_fail_monotonic, lock_until_monotonic|None)
        self._state: dict[str, tuple[int, float, Optional[float]]] = {}
        self._lock = threading.Lock()

    def _key(self, email: str) -> str:
        return (email or "").strip().lower()

    def check_locked(self, email: str) -> None:
        """Hesap kilitliyse 429 fırlatır."""
        now = time.monotonic()
        with self._lock:
            count, first, lock_until = self._state.get(self._key(email), (0, now, None))
            if lock_until is not None and now < lock_until:
                retry_after = int(lock_until - now) + 1
                raise HTTPException(
                    status_code=429,
                    detail="Çok fazla hatalı giriş. Hesap geçici olarak kilitlendi.",
                    headers={"Retry-After": str(retry_after)},
                )

    def record_failure(self, email: str) -> None:
        now = time.monotonic()
        k = self._key(email)
        with self._lock:
            count, first, lock_until = self._state.get(k, (0, now, None))
            # Kilit süresi geçtiyse sayacı sıfırla
            if lock_until is not None and now >= lock_until:
                count, first, lock_until = 0, now, None
            count += 1
            if count >= LOGIN_MAX_FAILURES:
                lock_until = now + LOGIN_LOCKOUT_SECONDS
                logger.warning("Hesap kilitlendi (brute-force): %s", k)
            self._state[k] = (count, first, lock_until)

    def reset(self, email: str) -> None:
        with self._lock:
            self._state.pop(self._key(email), None)


login_guard = LoginGuard()


# ── Cloudflare Turnstile doğrulaması ──────────────────────
async def verify_turnstile(token: Optional[str], remote_ip: Optional[str] = None) -> bool:
    """
    Turnstile token'ını Cloudflare ile doğrular.
    CAPTCHA devre dışıysa (secret yoksa) her zaman True döner — böylece
    yerel/geliştirme ortamı Turnstile anahtarı olmadan çalışır.
    """
    if not CAPTCHA_ENABLED:
        return True
    if not token:
        return False
    data = {"secret": TURNSTILE_SECRET_KEY, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_TURNSTILE_VERIFY_URL, data=data)
            result = resp.json()
            return bool(result.get("success"))
    except Exception as e:  # ağ hatası → güvenli tarafta kal, reddet
        logger.error("Turnstile doğrulama hatası: %s", e)
        return False
