"""
SpeakScorer — Yetkili Medya Router
Öğrenci ses kayıtları ve avatarlar yalnızca yetkili kullanıcılara servis edilir.
Statik /uploads mount'u kaldırıldığı için tüm hassas medya buradan geçer (IDOR fix).
"""
import os
import glob
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserRole, Submission
from auth import get_current_user
from config import UPLOAD_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/media", tags=["media"])

_AUDIO_DIR = os.path.realpath(os.path.join(UPLOAD_DIR, "audio"))
_AVATAR_DIR = os.path.realpath(os.path.join(UPLOAD_DIR, "avatars"))


def _safe_path(base: str, filename: str) -> str:
    """Dizin dışına çıkmayı (path traversal) engelle."""
    candidate = os.path.realpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep) and candidate != base:
        raise HTTPException(404, "Bulunamadı")
    return candidate


def _can_access_submission(user: User, sub: Submission, db: Session) -> bool:
    # Sahibi öğrenci
    if user.rol == UserRole.student and sub.student_id == user.id:
        return True
    # Yönetici / moderatör
    if user.rol in (UserRole.admin, UserRole.moderator):
        return True
    # Gönderimin ödevini veren öğretmen
    if user.rol == UserRole.teacher and sub.assignment and sub.assignment.teacher_id == user.id:
        return True
    # Öğrencinin velisi
    if user.rol == UserRole.parent:
        student = db.query(User).filter(User.id == sub.student_id).first()
        if student and student.parent_id == user.id:
            return True
    return False


def _can_access_avatar(user: User, target_id: int, db: Session) -> bool:
    """Avatar yalnızca kullanıcının kendisine veya ilişkili olduğu kişilere açıktır (IDOR fix)."""
    # Kendi avatarı
    if user.id == target_id:
        return True
    # Yönetici / moderatör tümünü görebilir
    if user.rol in (UserRole.admin, UserRole.moderator):
        return True
    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        return False
    # Öğretmen ↔ öğrencisi (her iki yön)
    if user.rol == UserRole.teacher and target.teacher_id == user.id:
        return True
    if user.rol == UserRole.student and user.teacher_id == target.id:
        return True
    # Veli ↔ çocuğu (her iki yön)
    if user.rol == UserRole.parent and target.parent_id == user.id:
        return True
    if user.rol == UserRole.student and user.parent_id == target.id:
        return True
    return False


@router.get("/audio/{submission_id}")
def get_submission_audio(
    submission_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ses kaydını yalnızca yetkili kullanıcıya döndürür."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub or not sub.audio_path:
        raise HTTPException(404, "Ses kaydı bulunamadı")
    if not _can_access_submission(user, sub, db):
        raise HTTPException(403, "Bu kayda erişim yetkiniz yok")

    filename = os.path.basename(sub.audio_path)
    path = _safe_path(_AUDIO_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "Dosya bulunamadı")
    return FileResponse(path, media_type="audio/webm")


@router.get("/avatar/{user_id}")
def get_avatar(
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Avatarı yalnızca yetkili kullanıcılara servis eder (IDOR fix)."""
    if not _can_access_avatar(user, user_id, db):
        raise HTTPException(403, "Bu avatara erişim yetkiniz yok")
    matches = sorted(glob.glob(os.path.join(_AVATAR_DIR, f"avatar_{user_id}_*")))
    if not matches:
        raise HTTPException(404, "Avatar bulunamadı")
    path = _safe_path(_AVATAR_DIR, os.path.basename(matches[-1]))
    if not os.path.isfile(path):
        raise HTTPException(404, "Dosya bulunamadı")
    return FileResponse(path)
