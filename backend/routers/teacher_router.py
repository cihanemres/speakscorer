"""
SpeakScorer — Öğretmen Router
Ödev oluşturma, gönderim değerlendirme, puan verme, takdir sistemi
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import (
    User, UserRole, Paragraph, Assignment, Submission,
    TargetType, Commendation, Notification,
    UserStreak, XP_VALUES, get_level_for_xp
)
from auth import require_role

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


# ── Paragraflar ───────────────────────────────────────────

class ParagraphCreate(BaseModel):
    title: str
    text: str
    level: int = 1
    category: str = "Genel"


@router.get("/paragraphs")
def list_paragraphs(
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    paras = db.query(Paragraph).filter(Paragraph.approved == True).order_by(Paragraph.level).all()
    # Ayrıca öğretmenin kendi eklediği onay bekleyen paragrafları da listeyelim
    my_pending_paras = db.query(Paragraph).filter(
        Paragraph.approved == False, 
        Paragraph.created_by == user.id
    ).order_by(Paragraph.level).all()
    
    all_paras = paras + my_pending_paras
    
    return [
        {
            "id": p.id,
            "title": p.title,
            "text": p.text,
            "level": p.level,
            "category": p.category,
            "approved": p.approved,
            "audio_path": p.audio_path,
            "question_count": len(p.questions) if p.questions else 0,
        }
        for p in all_paras
    ]

@router.post("/paragraphs")
def create_paragraph(
    data: ParagraphCreate,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    """Öğretmen paragraf oluşturur, anında approved=False olur."""
    p = Paragraph(
        title=data.title,
        text=data.text,
        level=data.level,
        category=data.category,
        approved=False,
        created_by=user.id,
    )
    db.add(p)
    db.commit()
    return {"message": "Paragraf oluşturuldu, yönetici onayı bekleniyor", "id": p.id}


@router.put("/paragraphs/{para_id}")
def update_paragraph(
    para_id: int,
    data: ParagraphCreate,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    """Öğretmen paragraf düzenler ancak önceden ödev olarak verildiyse izin verilmez."""
    p = db.query(Paragraph).filter(Paragraph.id == para_id).first()
    if not p:
        raise HTTPException(404, "Paragraf bulunamadı")

    # Öğretmen yalnızca KENDİ oluşturduğu paragrafı düzenleyebilir (yetki/IDOR fix).
    # Aksi halde başka öğretmenin veya yöneticinin onaylı paragrafı bozulabilir/yayından kaldırılabilir.
    if p.created_by != user.id:
        raise HTTPException(403, "Yalnızca kendi oluşturduğunuz paragrafları düzenleyebilirsiniz")

    # Ödev olarak gönderilmiş paragraf düzenlenemez (tutarlılık için).
    if len(p.assignments) > 0:
        raise HTTPException(400, "Öğretmen paragrafı öğrenciye ödev gönderdikten sonra düzenleyemez")

    p.title = data.title
    p.text = data.text
    p.level = data.level
    p.category = data.category
    p.approved = False # Düzenleme sonrası tekrar onay gerekir.
    db.commit()
    return {"message": "Paragraf düzenlendi, yeniden onaya gönderildi"}


# ── Öğrenciler ────────────────────────────────────────────

@router.get("/students")
def list_students(
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    # GÜVENLİK (M-1): Yalnızca bu öğretmene bağlı öğrenciler listelenir.
    # Aksi halde bir öğretmen tüm okulun öğrencilerini ve e-postalarını görürdü.
    # Ayrıca e-posta (PII) yanıttan çıkarıldı — roster için ad/sınıf/şube yeterli
    # ve Adım 5'teki ödev atama kısıtlamasıyla tutarlı (sadece kendi öğrencileri).
    students = db.query(User).filter(
        User.rol == UserRole.student,
        User.status == "active",
        User.teacher_id == user.id,
    ).all()
    return [
        {
            "user_id": s.id,
            "ad_soyad": s.ad_soyad,
            "sinif_duzeyi": s.sinif_duzeyi,
            "sube": s.sube,
        }
        for s in students
    ]


class StudentCreate(BaseModel):
    ad_soyad: str
    email: str
    password: str
    sinif_duzeyi: int
    sube: Optional[str] = None
    veli_email: Optional[str] = None


@router.post("/students")
def create_student(
    data: StudentCreate,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    """Öğretmen bireysel öğrenci ekler. Veli e-postası verilirse, veli bağlantısı kurulur."""
    import secrets
    from auth import hash_password
    from models import UserStatus, UserStreak

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Bu e-posta (" + data.email + ") zaten kullanımda.")

    # Veli bağlama opsiyonu
    parent_id = None
    parent_temp_password = None
    if data.veli_email:
        parent = db.query(User).filter(User.email == data.veli_email, User.rol == UserRole.parent).first()
        if not parent:
            # Veli yoksa bekleyen (pending) olarak oluştur. Sabit varsayılan şifre
            # ("veli123") herkesçe bilineceği için hesap ele geçirme riski taşır;
            # bunun yerine tek seferlik rastgele bir şifre üretip öğretmene döneriz.
            parent_temp_password = secrets.token_urlsafe(9)
            parent = User(
                ad_soyad=data.veli_email.split('@')[0] + " (Veli)",
                email=data.veli_email,
                password_hash=hash_password(parent_temp_password),
                rol=UserRole.parent,
                status=UserStatus.pending
            )
            db.add(parent)
            db.flush()
        parent_id = parent.id

    student = User(
        ad_soyad=data.ad_soyad,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=UserRole.student,
        status=UserStatus.active, # Öğretmen eklediği için direkt aktif
        sinif_duzeyi=data.sinif_duzeyi,
        sube=data.sube,
        parent_id=parent_id,
        teacher_id=user.id
    )
    db.add(student)
    db.flush()
    db.add(UserStreak(user_id=student.id))
    db.commit()
    result = {"message": "Öğrenci başarıyla eklendi", "id": student.id}
    if parent_temp_password:
        # Yeni veli hesabı için tek seferlik geçici şifre — öğretmen veliye iletmeli.
        result["parent_email"] = data.veli_email
        result["parent_temp_password"] = parent_temp_password
        result["message"] += " — Veli hesabı oluşturuldu, geçici şifreyi veliye iletin."
    return result


class BadgeAssign(BaseModel):
    student_id: Optional[int] = None
    class_name: Optional[str] = None # Or you can use sinif_duzeyi + sube
    badge_name: str

@router.post("/badges/assign")
def assign_badge(
    data: BadgeAssign,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db)
):
    """Öğretmen bir öğrenciye veya belirli bir sınıfa özel rozet verebilir."""
    from models import Achievement
    from routers.student_router import BADGE_CRITERIA

    # GÜVENLİK (S-07): Yalnızca bilinen rozet türleri atanabilir.
    if data.badge_name not in BADGE_CRITERIA:
        raise HTTPException(400, "Geçersiz rozet türü")

    assigned_count = 0

    if data.student_id:
        # GÜVENLİK (S-07): Hedef gerçekten bir öğrenci mi?
        target = db.query(User).filter(
            User.id == data.student_id, User.rol == UserRole.student
        ).first()
        if not target:
            raise HTTPException(404, "Öğrenci bulunamadı")
        existing = db.query(Achievement).filter(
            Achievement.user_id == data.student_id,
            Achievement.badge_type == data.badge_name
        ).first()
        if not existing:
            db.add(Achievement(user_id=data.student_id, badge_type=data.badge_name))
            assigned_count += 1
    elif data.class_name:
        # Expected format "5-A" -> level=5, sube='A'
        try:
            lvl_str, sube = data.class_name.split("-")
            lvl = int(lvl_str)
            students = db.query(User).filter(
                User.rol == UserRole.student,
                User.sinif_duzeyi == lvl,
                User.sube == sube
            ).all()
            for st in students:
                existing = db.query(Achievement).filter(
                    Achievement.user_id == st.id, 
                    Achievement.badge_type == data.badge_name
                ).first()
                if not existing:
                    db.add(Achievement(user_id=st.id, badge_type=data.badge_name))
                    assigned_count += 1
        except Exception:
            raise HTTPException(400, "Geçersiz sınıf formatı. Örn: '5-A' kullanın")
    else:
        raise HTTPException(400, "Ya student_id ya da class_name belirtilmeli")

    db.commit()
    return {"message": f"{assigned_count} öğrenciye rozet atandı"}


# ── Ödevler ───────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    paragraph_id: int
    target_type: str = "student"
    student_ids: Optional[List[int]] = None
    class_name: Optional[str] = None
    due_date: Optional[str] = None


@router.get("/assignments")
def list_assignments(
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    assignments = db.query(Assignment).filter(
        Assignment.teacher_id == user.id
    ).order_by(Assignment.created_at.desc()).all()

    result = []
    for a in assignments:
        sub_count = db.query(func.count(Submission.id)).filter(
            Submission.assignment_id == a.id
        ).scalar()

        student_name = ""
        if a.student:
            student_name = a.student.ad_soyad

        result.append({
            "id": a.id,
            "paragraph_title": a.paragraph.title if a.paragraph else "",
            "paragraph_id": a.paragraph_id,
            "student_name": student_name,
            "class_name": a.class_name or "",
            "target_type": a.target_type.value if a.target_type else "",
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "submissions_count": sub_count,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result


@router.post("/assignments")
def create_assignment(
    data: AssignmentCreate,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    p = db.query(Paragraph).filter(Paragraph.id == data.paragraph_id).first()
    if not p:
        raise HTTPException(404, "Paragraf bulunamadı")

    due = None
    if data.due_date:
        try:
            due = datetime.fromisoformat(data.due_date)
        except ValueError:
            pass

    created = 0
    if data.target_type == "student" and data.student_ids:
        # GÜVENLİK (H-4): Yalnızca bu öğretmene bağlı öğrencilere ödev atanabilir.
        # Aksi halde herhangi bir öğretmen, başka öğretmenin öğrencilerine ödev
        # enjekte edebilir (cross-student IDOR). class dalı zaten sınıfa göre
        # kısıtlanmış; student dalını da öğretmen-öğrenci sahipliğiyle kısıtlıyoruz.
        valid_ids = {
            row.id for row in db.query(User.id).filter(
                User.id.in_(data.student_ids),
                User.rol == UserRole.student,
                User.teacher_id == user.id,
            ).all()
        }
        invalid = [sid for sid in data.student_ids if sid not in valid_ids]
        if invalid:
            raise HTTPException(403, "Yalnızca kendi öğrencilerinize ödev atayabilirsiniz.")
        for sid in data.student_ids:
            a = Assignment(
                teacher_id=user.id,
                paragraph_id=data.paragraph_id,
                student_id=sid,
                target_type=TargetType.student,
                due_date=due,
            )
            db.add(a)
            created += 1
    elif data.target_type == "class" and data.class_name:
        # GÜVENLİK/DOĞRULUK (S-06/B-02): Yalnızca HEDEF sınıftaki öğrencilere ata.
        # Beklenen biçim "5-A" -> sinif_duzeyi=5, sube='A'.
        try:
            lvl_str, sube = data.class_name.split("-", 1)
            lvl = int(lvl_str.strip())
            sube = sube.strip()
        except (ValueError, AttributeError):
            raise HTTPException(400, "Geçersiz sınıf formatı. Örn: '5-A' kullanın")

        class_students = db.query(User).filter(
            User.rol == UserRole.student,
            User.sinif_duzeyi == lvl,
            User.sube == sube,
        ).all()
        for s in class_students:
            a = Assignment(
                teacher_id=user.id,
                paragraph_id=data.paragraph_id,
                student_id=s.id,
                class_name=data.class_name,
                target_type=TargetType.class_group,
                due_date=due,
            )
            db.add(a)
            created += 1

    db.commit()
    return {"message": f"{created} ödev oluşturuldu"}


# ── Gönderimler ───────────────────────────────────────────

@router.get("/submissions")
def list_submissions(
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    # GÜVENLİK (S-06): Öğretmen YALNIZCA kendi verdiği ödevlerin gönderimlerini
    # görür. Yetim (teacher_id IS NULL) gönderimler artık dahil edilmez.
    subs = db.query(Submission).join(
        Assignment, Submission.assignment_id == Assignment.id
    ).filter(
        Assignment.teacher_id == user.id
    ).order_by(Submission.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "student_name": s.student.ad_soyad if s.student else "",
            "student_id": s.student_id,
            "paragraph_title": s.paragraph.title if s.paragraph else "",
            "paragraph_text": s.paragraph.text if s.paragraph else "",
            "paragraph_id": s.paragraph_id,
            "audio_path": f"/api/media/audio/{s.id}" if s.audio_path else None,
            "transcript": s.transcript,
            "ai_score": s.ai_score,
            "ai_vocabulary": s.ai_vocabulary,
            "ai_grammar": s.ai_grammar,
            "ai_fluency": s.ai_fluency,
            "ai_coherence": s.ai_coherence,
            "ai_feedback": s.ai_feedback,
            "teacher_score": s.teacher_score,
            "teacher_vocabulary": s.teacher_vocabulary,
            "teacher_grammar": s.teacher_grammar,
            "teacher_fluency": s.teacher_fluency,
            "teacher_coherence": s.teacher_coherence,
            "teacher_feedback": s.teacher_feedback,
            "final_score": s.final_score,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in subs
    ]


class ScoreUpdate(BaseModel):
    vocabulary: float
    grammar: float
    fluency: float
    coherence: float
    teacher_feedback: str


@router.put("/submissions/{sub_id}/score")
def update_score(
    sub_id: int,
    data: ScoreUpdate,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    s = db.query(Submission).filter(Submission.id == sub_id).first()
    if not s:
        raise HTTPException(404, "Gönderim bulunamadı")

    # Ownership check: teacher can only score submissions
    # from assignments they created.
    if not s.assignment or s.assignment.teacher_id != user.id:
        raise HTTPException(403, "Bu gönderimi puanlama yetkiniz yok")

    # Validate score ranges (0-25 each)
    for field_name, value in [("vocabulary", data.vocabulary), ("grammar", data.grammar),
                               ("fluency", data.fluency), ("coherence", data.coherence)]:
        if not (0 <= value <= 25):
            raise HTTPException(400, f"{field_name} puanı 0-25 arasında olmalıdır")

    s.teacher_vocabulary = data.vocabulary
    s.teacher_grammar = data.grammar
    s.teacher_fluency = data.fluency
    s.teacher_coherence = data.coherence
    s.teacher_score = data.vocabulary + data.grammar + data.fluency + data.coherence
    s.teacher_feedback = data.teacher_feedback
    s.final_score = s.teacher_score  # Teacher score overrides AI
    s.status = "reviewed"
    db.commit()
    return {
        "message": "Puan güncellendi",
        "teacher_vocabulary": s.teacher_vocabulary,
        "teacher_grammar": s.teacher_grammar,
        "teacher_fluency": s.teacher_fluency,
        "teacher_coherence": s.teacher_coherence,
        "teacher_score": s.teacher_score,
        "final_score": s.final_score,
    }


# ── Takdir Sistemi ────────────────────────────────────────

class CommendationCreate(BaseModel):
    student_id: int
    commendation_type: str = "takdir"
    title: str
    description: Optional[str] = None
    xp_reward: int = 50


@router.post("/commendation")
def give_commendation(
    data: CommendationCreate,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    # GÜVENLİK (S-07): Keyfi XP verilmesini engelle.
    if not (0 <= data.xp_reward <= 200):
        raise HTTPException(400, "XP ödülü 0-200 arasında olmalıdır")

    student = db.query(User).filter(
        User.id == data.student_id,
        User.rol == UserRole.student,
    ).first()
    if not student:
        raise HTTPException(404, "Öğrenci bulunamadı")

    c = Commendation(
        student_id=data.student_id,
        teacher_id=user.id,
        commendation_type=data.commendation_type,
        title=data.title,
        description=data.description,
        xp_reward=data.xp_reward,
    )
    db.add(c)

    # Add XP reward
    if data.xp_reward > 0:
        streak = db.query(UserStreak).filter(UserStreak.user_id == data.student_id).first()
        if streak:
            streak.total_xp += data.xp_reward
            streak.level = get_level_for_xp(streak.total_xp)

    # Notify student
    type_names = {
        "takdir": "Takdir", "tesekkur": "Teşekkür",
        "birincilik": "Birincilik", "ozel_basari": "Özel Başarı"
    }
    n = Notification(
        user_id=data.student_id,
        type="achievement",
        title=f"🏆 {type_names.get(data.commendation_type, 'Takdir')} Aldınız!",
        message=f"{user.ad_soyad}: {data.title}",
    )
    db.add(n)
    db.commit()
    return {"message": "Takdir verildi"}


# ── Sınıf İstatistikleri ─────────────────────────────────

@router.get("/class-stats")
def class_stats(
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
):
    total_assignments = db.query(func.count(Assignment.id)).filter(
        Assignment.teacher_id == user.id
    ).scalar()
    total_submissions = db.query(func.count(Submission.id)).join(
        Assignment, isouter=True
    ).filter(Assignment.teacher_id == user.id).scalar()
    scored = db.query(func.count(Submission.id)).join(
        Assignment, isouter=True
    ).filter(
        Assignment.teacher_id == user.id,
        Submission.final_score != None,
    ).scalar()
    avg = db.query(func.avg(Submission.final_score)).join(
        Assignment, isouter=True
    ).filter(
        Assignment.teacher_id == user.id,
        Submission.final_score != None,
    ).scalar()

    return {
        "total_assignments": total_assignments or 0,
        "total_submissions": total_submissions or 0,
        "scored_submissions": scored or 0,
        "avg_score": round(float(avg), 1) if avg else 0,
    }
