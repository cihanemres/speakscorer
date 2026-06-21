"""
SpeakScorer — Yönetici Router
Kullanıcı yönetimi, paragraf yönetimi, istatistikler
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import (
    User, UserRole, UserStatus, Paragraph, Assignment,
    Submission, Question
)
from auth import get_current_user, require_role
from services.ai_service import generate_paragraph_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


def _parse_enum(enum_cls, value, field_name):
    """Enum değerini güvenle çözer; geçersizse 500 yerine 400 döner."""
    try:
        return enum_cls(value)
    except ValueError:
        valid = ", ".join(e.value for e in enum_cls)
        raise HTTPException(400, f"Geçersiz {field_name}: '{value}'. Geçerli değerler: {valid}")


# ── Kullanıcı Yönetimi ───────────────────────────────────

@router.get("/users")
def list_users(
    user: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    user_list = []
    import json
    for u in users:
        permissions = {}
        if u.permissions:
            try:
                permissions = json.loads(u.permissions)
            except:
                pass
        user_list.append({
            "id": u.id,
            "ad_soyad": u.ad_soyad,
            "email": u.email,
            "rol": u.rol.value,
            "status": u.status.value,
            "sinif_duzeyi": u.sinif_duzeyi,
            "sube": u.sube,
            "permissions": permissions,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return user_list


@router.put("/users/{user_id}/approve")
def approve_user(
    user_id: int,
    admin: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    u.status = UserStatus.active
    db.commit()
    return {"message": "Kullanıcı onaylandı"}


@router.put("/users/{user_id}/reject")
def reject_user(
    user_id: int,
    admin: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    u.status = UserStatus.rejected
    db.commit()
    return {"message": "Kullanıcı reddedildi"}


class StatusUpdate(BaseModel):
    status: str

@router.put("/users/{user_id}/status")
def update_status(
    user_id: int,
    data: StatusUpdate,
    admin: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Sadece yönetici statü değiştirebilir."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    u.status = _parse_enum(UserStatus, data.status, "durum")
    db.commit()
    return {"message": "Durum güncellendi"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Sadece yönetici silebilir."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    db.delete(u)
    db.commit()
    return {"message": "Kullanıcı silindi"}


class UserCreate(BaseModel):
    ad_soyad: str
    email: str
    password: str
    rol: str

@router.post("/users")
def create_user(
    data: UserCreate,
    admin: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Sadece Yönetici (Admin) manuel kullanıcı yaratabilir."""
    from auth import hash_password
    from routers.auth_router import validate_password

    role = _parse_enum(UserRole, data.rol, "rol")
    validate_password(data.password)  # geçersizse HTTPException(400) fırlatır

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Eklemeye çalıştığınız e-posta zaten mevcut")

    new_user = User(
        ad_soyad=data.ad_soyad,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=role,
        status=UserStatus.active
    )
    db.add(new_user)
    db.commit()

    # Ayrıcalıklı hesap oluşturma denetim izi (privilege escalation görünürlüğü)
    if role in (UserRole.admin, UserRole.moderator):
        logger.warning(
            "Ayrıcalıklı hesap olusturuldu: admin_id=%s yeni_kullanici=%s rol=%s",
            admin.id, new_user.id, role.value
        )

    return {"message": "Kullanıcı eklendi", "id": new_user.id}


class PermissionsUpdate(BaseModel):
    permissions: dict

@router.put("/users/{user_id}/permissions")
def update_permissions(
    user_id: int,
    data: PermissionsUpdate,
    admin: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Sadece yönetici yetkileri güncelleyebilir."""
    import json
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    u.permissions = json.dumps(data.permissions)
    db.commit()
    return {"message": "Kullanıcı yetkileri güncellendi"}

# ── Paragraf Yönetimi ─────────────────────────────────────

class ParagraphCreate(BaseModel):
    title: str
    text: str
    level: int = 1
    category: str = "Genel"


@router.get("/paragraphs")
def list_paragraphs(
    user: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    paras = db.query(Paragraph).order_by(Paragraph.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "text": p.text,
            "level": p.level,
            "category": p.category,
            "approved": p.approved,
            "audio_path": p.audio_path,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "question_count": len(p.questions) if p.questions else 0,
        }
        for p in paras
    ]


@router.post("/paragraphs")
async def create_paragraph(
    data: ParagraphCreate,
    user: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    p = Paragraph(
        title=data.title,
        text=data.text,
        level=data.level,
        category=data.category,
        approved=True,
        created_by=user.id,
    )
    db.add(p)
    db.flush()

    # Generate TTS audio
    audio_path = await generate_paragraph_audio(data.text, p.id)
    if audio_path:
        p.audio_path = audio_path

    db.commit()
    return {"message": "Paragraf oluşturuldu", "id": p.id}


@router.put("/paragraphs/{para_id}/approve")
def approve_paragraph(
    para_id: int,
    user: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    p = db.query(Paragraph).filter(Paragraph.id == para_id).first()
    if not p:
        raise HTTPException(404, "Paragraf bulunamadı")
    p.approved = True
    db.commit()
    return {"message": "Paragraf onaylandı"}


@router.put("/paragraphs/{para_id}/reject")
def reject_paragraph(
    para_id: int,
    user: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    p = db.query(Paragraph).filter(Paragraph.id == para_id).first()
    if not p:
        raise HTTPException(404, "Paragraf bulunamadı")
    db.delete(p)
    db.commit()
    return {"message": "Paragraf reddedildi (silindi)"}


@router.post("/paragraphs/{para_id}/regenerate-audio")
async def regenerate_audio(
    para_id: int,
    user: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    p = db.query(Paragraph).filter(Paragraph.id == para_id).first()
    if not p:
        raise HTTPException(404, "Paragraf bulunamadı")
    audio_path = await generate_paragraph_audio(p.text, p.id)
    if audio_path:
        p.audio_path = audio_path
        db.commit()
        return {"message": "Ses dosyası yeniden oluşturuldu", "audio_path": audio_path}
    return {"message": "Ses dosyası oluşturulamadı (Demo modda devre dışı)"}


@router.put("/paragraphs/{para_id}")
async def update_paragraph(
    para_id: int,
    data: ParagraphCreate,
    user: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    p = db.query(Paragraph).filter(Paragraph.id == para_id).first()
    if not p:
        raise HTTPException(404, "Paragraf bulunamadı")

    text_changed = p.text != data.text
    p.title = data.title
    p.text = data.text
    p.level = data.level
    p.category = data.category

    # If text changed, clear old audio (it no longer matches)
    if text_changed and p.audio_path:
        import os
        from config import PARAGRAPH_AUDIO_DIR
        # Yalnızca dosya adını al; lstrip karakter-sıyırma bug'ı ve path traversal'a karşı koru.
        base = os.path.realpath(PARAGRAPH_AUDIO_DIR)
        old_file = os.path.realpath(os.path.join(base, os.path.basename(p.audio_path)))
        if (old_file == base or old_file.startswith(base + os.sep)) and os.path.isfile(old_file):
            os.remove(old_file)
        p.audio_path = None

    # Regenerate audio with new text
    if text_changed:
        audio_path = await generate_paragraph_audio(data.text, p.id)
        if audio_path:
            p.audio_path = audio_path

    db.commit()
    msg = "Paragraf güncellendi"
    if text_changed:
        msg += " — ses dosyası yeniden oluşturuldu" if p.audio_path else " — yeni ses oluşturmak için 'Ses Oluştur' butonunu kullanın"
    return {"message": msg}


@router.delete("/paragraphs/{para_id}")
def delete_paragraph(
    para_id: int,
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    p = db.query(Paragraph).filter(Paragraph.id == para_id).first()
    if not p:
        raise HTTPException(404, "Paragraf bulunamadı")
    db.delete(p)
    db.commit()
    return {"message": "Paragraf silindi"}


# ── Soru Yönetimi ─────────────────────────────────────────

class QuestionCreate(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str


@router.get("/paragraphs/{para_id}/questions")
def list_questions(
    para_id: int,
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    questions = db.query(Question).filter(Question.paragraph_id == para_id).all()
    return [
        {
            "id": q.id,
            "question_text": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "correct_answer": q.correct_answer,
        }
        for q in questions
    ]


@router.post("/paragraphs/{para_id}/questions")
def create_question(
    para_id: int,
    data: QuestionCreate,
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    p = db.query(Paragraph).filter(Paragraph.id == para_id).first()
    if not p:
        raise HTTPException(404, "Paragraf bulunamadı")
    q = Question(
        paragraph_id=para_id,
        question_text=data.question_text,
        option_a=data.option_a,
        option_b=data.option_b,
        option_c=data.option_c,
        option_d=data.option_d,
        correct_answer=data.correct_answer.upper(),
    )
    db.add(q)
    db.commit()
    return {"message": "Soru oluşturuldu", "id": q.id}


@router.delete("/questions/{q_id}")
def delete_question(
    q_id: int,
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    q = db.query(Question).filter(Question.id == q_id).first()
    if not q:
        raise HTTPException(404, "Soru bulunamadı")
    db.delete(q)
    db.commit()
    return {"message": "Soru silindi"}


# ── İstatistikler ─────────────────────────────────────────

@router.get("/stats")
def get_stats(
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    total_users = db.query(func.count(User.id)).scalar()
    pending_users = db.query(func.count(User.id)).filter(User.status == UserStatus.pending).scalar()
    active_users = db.query(func.count(User.id)).filter(User.status == UserStatus.active).scalar()
    students = db.query(func.count(User.id)).filter(User.rol == UserRole.student).scalar()
    teachers = db.query(func.count(User.id)).filter(User.rol == UserRole.teacher).scalar()
    parents = db.query(func.count(User.id)).filter(User.rol == UserRole.parent).scalar()
    total_paragraphs = db.query(func.count(Paragraph.id)).scalar()
    total_submissions = db.query(func.count(Submission.id)).scalar()

    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "active_users": active_users,
        "students": students,
        "teachers": teachers,
        "parents": parents,
        "total_paragraphs": total_paragraphs,
        "total_submissions": total_submissions,
    }


# ── Gönderimler (AI geri bildirimi dahil) ────────────────
@router.get("/submissions")
def list_submissions(
    user: User = Depends(require_role(UserRole.admin, UserRole.moderator)),
    db: Session = Depends(get_db),
):
    """Yönetici tüm gönderimleri ve AI/öğretmen geri bildirimlerini görür."""
    subs = (
        db.query(Submission)
        .order_by(Submission.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": s.id,
            "student_name": s.student.ad_soyad if s.student else "",
            "paragraph_title": s.paragraph.title if s.paragraph else "",
            "transcript": s.transcript,
            "ai_score": s.ai_score,
            "ai_feedback": s.ai_feedback,
            "teacher_score": s.teacher_score,
            "teacher_feedback": s.teacher_feedback,
            "final_score": s.final_score,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in subs
    ]
