"""
SpeakScorer — Öğrenci Router
Ödevler, ses kaydı gönderimi, AI değerlendirme, ilerleme, rozetler
"""
import os
import logging
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import (
    User, UserRole, Paragraph, Assignment, Submission,
    Achievement, UserStreak, Notification,
    XP_VALUES, get_level_for_xp, get_xp_for_next_level, LEVEL_NAMES
)
from auth import require_role
from config import UPLOAD_DIR, RATE_LIMIT_AI_MAX, RATE_LIMIT_AI_WINDOW
from security import enforce_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/student", tags=["student"])


# ── Badge criteria ────────────────────────────────────────
BADGE_CRITERIA = {
    "ilk_adim": {
        "name": "İlk Adım",
        "description": "İlk gönderimini yaptın!",
        "icon": "🌟",
    },
    "hizli_konusmaci": {
        "name": "Hızlı Konuşmacı",
        "description": "5 gönderim tamamladın",
        "icon": "⚡",
    },
    "pratik_ustasi": {
        "name": "Pratik Ustası",
        "description": "10 gönderim tamamladın",
        "icon": "🎯",
    },
    "soz_ustasi": {
        "name": "Söz Ustası",
        "description": "25 gönderim tamamladın",
        "icon": "📚",
    },
    "yuksek_puan": {
        "name": "Yüksek Puan",
        "description": "80+ puan aldın",
        "icon": "⭐",
    },
    "mukemmel_puan": {
        "name": "Mükemmel Puan",
        "description": "95+ puan aldın",
        "icon": "🏆",
    },
    "istikrarli": {
        "name": "İstikrarlı Öğrenci",
        "description": "Ortalaman 70+ oldu",
        "icon": "💪",
    },
    "yildiz_ogrenci": {
        "name": "Yıldız Öğrenci",
        "description": "Ortalaman 85+ oldu",
        "icon": "🌟",
    },
}


def check_and_award_badges(user_id: int, db: Session):
    """Check and award new badges after a submission."""
    sub_count = db.query(func.count(Submission.id)).filter(
        Submission.student_id == user_id
    ).scalar() or 0

    avg_score = db.query(func.avg(Submission.final_score)).filter(
        Submission.student_id == user_id,
        Submission.final_score != None,
    ).scalar() or 0

    best_score = db.query(func.max(Submission.final_score)).filter(
        Submission.student_id == user_id,
        Submission.final_score != None,
    ).scalar() or 0

    checks = {
        "ilk_adim": sub_count >= 1,
        "hizli_konusmaci": sub_count >= 5,
        "pratik_ustasi": sub_count >= 10,
        "soz_ustasi": sub_count >= 25,
        "yuksek_puan": best_score >= 80,
        "mukemmel_puan": best_score >= 95,
        "istikrarli": avg_score >= 70 and sub_count >= 3,
        "yildiz_ogrenci": avg_score >= 85 and sub_count >= 5,
    }

    new_badges = []
    for badge_type, earned in checks.items():
        if earned:
            exists = db.query(Achievement).filter(
                Achievement.user_id == user_id,
                Achievement.badge_type == badge_type,
            ).first()
            if not exists:
                db.add(Achievement(user_id=user_id, badge_type=badge_type))
                new_badges.append(BADGE_CRITERIA[badge_type])
                # Award badge XP
                add_xp(user_id, "badge_earned", db)

    if new_badges:
        db.commit()
    return new_badges


def update_streak(user_id: int, db: Session) -> dict:
    """Update user's daily streak."""
    streak = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()
    if not streak:
        streak = UserStreak(user_id=user_id)
        db.add(streak)
        db.flush()

    today = date.today()
    if streak.last_activity_date is None:
        streak.current_streak = 1
        streak.longest_streak = 1
        streak.last_activity_date = today
    elif streak.last_activity_date == today:
        pass
    elif streak.last_activity_date == today - timedelta(days=1):
        streak.current_streak += 1
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        streak.last_activity_date = today

        if streak.current_streak == 3:
            add_xp(user_id, "streak_bonus_3", db)
        elif streak.current_streak == 7:
            add_xp(user_id, "streak_bonus_7", db)
        elif streak.current_streak == 30:
            add_xp(user_id, "streak_bonus_30", db)
    else:
        streak.current_streak = 1
        streak.last_activity_date = today

    db.commit()
    return {
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
    }


def add_xp(user_id: int, action: str, db: Session) -> int:
    streak = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()
    if not streak:
        streak = UserStreak(user_id=user_id)
        db.add(streak)
        db.flush()
    xp_amount = XP_VALUES.get(action, 0)
    streak.total_xp += xp_amount
    streak.level = get_level_for_xp(streak.total_xp)
    return xp_amount


# ── Ödevlerim ─────────────────────────────────────────────

@router.get("/tasks")
def get_tasks(
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    assignments = db.query(Assignment).filter(
        Assignment.student_id == user.id
    ).order_by(Assignment.created_at.desc()).all()

    result = []
    for a in assignments:
        existing = db.query(Submission).filter(
            Submission.assignment_id == a.id,
            Submission.student_id == user.id,
        ).first()

        result.append({
            "assignment_id": a.id,
            "paragraph_id": a.paragraph_id,
            "paragraph_title": a.paragraph.title if a.paragraph else "",
            "paragraph_text": a.paragraph.text[:200] + "..." if a.paragraph and len(a.paragraph.text) > 200 else (a.paragraph.text if a.paragraph else ""),
            "paragraph_level": a.paragraph.level if a.paragraph else 1,
            "paragraph_audio": a.paragraph.audio_path if a.paragraph else None,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "submitted": existing is not None,
            "score": existing.final_score if existing else None,
            "status": existing.status if existing else "pending",
        })
    return result


@router.get("/tasks/{assignment_id}")
def get_task_detail(
    assignment_id: int,
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    a = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.student_id == user.id,
    ).first()
    if not a:
        raise HTTPException(404, "Ödev bulunamadı")

    existing = db.query(Submission).filter(
        Submission.assignment_id == a.id,
        Submission.student_id == user.id,
    ).first()

    return {
        "assignment_id": a.id,
        "paragraph": {
            "id": a.paragraph.id,
            "title": a.paragraph.title,
            "text": a.paragraph.text,
            "level": a.paragraph.level,
            "audio_path": a.paragraph.audio_path,
        } if a.paragraph else None,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "submitted": existing is not None,
    }


# ── Ses Kaydı Gönderimi ──────────────────────────────────

def _detect_audio_format(head: bytes) -> str | None:
    """Dosyanın gerçek içeriğine (magic-byte) göre ses formatını döndürür.

    İstemcinin gönderdiği Content-Type başlığı sahte olabilir; bu yüzden
    sunucu yalnızca dosyanın ilk baytlarındaki imzaya güvenir. Tanınmazsa
    None döner ve yükleme reddedilir.
    """
    if head[:4] == b"\x1a\x45\xdf\xa3":            # WebM / Matroska (EBML)
        return "webm"
    if head[:4] == b"OggS":                         # OGG (Opus/Vorbis)
        return "ogg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":  # WAV
        return "wav"
    if head[:3] == b"ID3":                           # MP3 (ID3 etiketli)
        return "mp3"
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:  # MP3 frame sync
        return "mp3"
    if head[4:8] == b"ftyp":                         # MP4 / M4A
        return "mp4"
    return None


@router.post("/submit")
async def submit_recording(
    request: Request,
    assignment_id: int = Form(...),
    audio: UploadFile = File(...),
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    # AI maliyet koruması: pahalı Gemini değerlendirmesini kullanıcı başına
    # sınırla (CLAUDE.md AI kuralı). Anahtar kullanıcı kimliğini içerir.
    enforce_rate_limit(request, f"ai:user:{user.id}", RATE_LIMIT_AI_MAX, RATE_LIMIT_AI_WINDOW)

    # Verify assignment
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.student_id == user.id,
    ).first()
    if not assignment:
        raise HTTPException(404, "Ödev bulunamadı")

    # Check duplicate
    existing = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id == user.id,
    ).first()
    if existing:
        raise HTTPException(400, "Bu ödev için zaten gönderim yapılmış")

    # Save audio — with validation
    MAX_AUDIO_SIZE = 10 * 1024 * 1024   # 10 MB
    ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/mp3", "audio/ogg",
                           "audio/mpeg", "audio/mp4", "audio/x-m4a", "video/webm"}

    # Validate content type — tarayıcı MIME tipine codec parametresi ekleyebilir
    # (örn. "audio/webm;codecs=opus"); karşılaştırmadan önce yalnızca temel tipi al.
    base_type = (audio.content_type or "").split(";")[0].strip().lower()
    if base_type and base_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(400, f"Desteklenmeyen dosya türü: {audio.content_type}. Sadece ses dosyası yüklenebilir.")

    content = await audio.read()

    # Validate file size
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(400, f"Dosya çok büyük ({len(content) // (1024*1024)} MB). Maksimum: 10 MB.")
    if len(content) == 0:
        raise HTTPException(400, "Boş dosya yüklenemez.")

    # GÜVENLİK (M-2): İçeriğin gerçek imzasını doğrula. Content-Type başlığı
    # istemci tarafından serbestçe ayarlanabildiği için tek başına yeterli
    # değil; gizlenmiş bir yürütülebilir/HTML dosyası ".webm" gibi davranabilir.
    if _detect_audio_format(content[:16]) is None:
        raise HTTPException(400, "Geçersiz ses dosyası: içerik tanınmadı. Sadece gerçek ses kaydı yükleyin.")

    audio_dir = os.path.join(UPLOAD_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    filename = f"{user.id}_{assignment_id}_{int(datetime.utcnow().timestamp())}.webm"
    audio_path = os.path.join(audio_dir, filename)

    with open(audio_path, "wb") as f:
        f.write(content)

    # Get paragraph text for AI evaluation
    paragraph = assignment.paragraph

    # Try audio-based evaluation first, fallback to transcript
    from services.ai_service import evaluate_audio_with_gemini, evaluate_with_gemini
    from services.speech_service import transcribe_audio

    try:
        result = await evaluate_audio_with_gemini(audio_path, paragraph.text)
        transcript = result.get("transcript", "")
    except Exception:
        # Fallback: transcribe then evaluate text
        trans_result = await transcribe_audio(audio_path)
        transcript = trans_result.get("transcript", "")
        result = await evaluate_with_gemini(transcript, paragraph.text)

    if "error" in result:
        return {"error": result["error"], "message": result["message"]}

    # Create submission
    submission = Submission(
        student_id=user.id,
        assignment_id=assignment_id,
        paragraph_id=paragraph.id,
        audio_path=f"/uploads/audio/{filename}",
        transcript=transcript or result.get("transcript", ""),
        ai_score=result.get("total", 0),
        ai_vocabulary=result.get("vocabulary", 0),
        ai_grammar=result.get("grammar", 0),
        ai_fluency=result.get("fluency", 0),
        ai_coherence=result.get("coherence", 0),
        ai_feedback=result.get("feedback", ""),
        final_score=result.get("total", 0),  # Will be overridden by teacher
        status="scored",
    )
    db.add(submission)

    # Update streak & XP
    update_streak(user.id, db)
    add_xp(user.id, "submission_complete", db)
    if result.get("total", 0) >= 95:
        add_xp(user.id, "perfect_score", db)
    elif result.get("total", 0) >= 80:
        add_xp(user.id, "high_score", db)

    db.commit()

    # Check badges
    new_badges = check_and_award_badges(user.id, db)

    return {
        "submission_id": submission.id,
        "transcript": submission.transcript,
        "ai_score": submission.ai_score,
        "final_score": submission.final_score,
        "vocabulary": submission.ai_vocabulary,
        "grammar": submission.ai_grammar,
        "fluency": submission.ai_fluency,
        "coherence": submission.ai_coherence,
        "feedback": submission.ai_feedback,
        "new_badges": new_badges,
    }


# ── Gönderimlerim / Sonuçlar ─────────────────────────────

@router.get("/results")
def get_results(
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    subs = db.query(Submission).filter(
        Submission.student_id == user.id
    ).order_by(Submission.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "paragraph_title": s.paragraph.title if s.paragraph else "",
            "transcript": s.transcript,
            "audio_path": f"/api/media/audio/{s.id}" if s.audio_path else None,
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


# ── İlerleme ──────────────────────────────────────────────

@router.get("/progress")
def get_progress(
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(Submission.id)).filter(
        Submission.student_id == user.id
    ).scalar() or 0
    avg = db.query(func.avg(Submission.final_score)).filter(
        Submission.student_id == user.id,
        Submission.final_score != None,
    ).scalar() or 0
    best = db.query(func.max(Submission.final_score)).filter(
        Submission.student_id == user.id,
        Submission.final_score != None,
    ).scalar() or 0

    # Weekly
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_avg = db.query(func.avg(Submission.final_score)).filter(
        Submission.student_id == user.id,
        Submission.final_score != None,
        Submission.created_at >= week_ago,
    ).scalar() or 0

    # Score history
    history = db.query(Submission).filter(
        Submission.student_id == user.id,
        Submission.final_score != None,
    ).order_by(Submission.created_at).limit(20).all()

    return {
        "total_submissions": total,
        "avg_score": round(float(avg), 1),
        "best_score": round(float(best), 1),
        "weekly_avg": round(float(weekly_avg), 1),
        "history": [
            {
                "date": h.created_at.strftime("%d.%m") if h.created_at else "",
                "score": round(h.final_score, 1) if h.final_score else 0,
                "title": h.paragraph.title if h.paragraph else "",
            }
            for h in history
        ],
    }


# ── Rozetler ──────────────────────────────────────────────

@router.get("/badges")
def get_badges(
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    achievements = db.query(Achievement).filter(
        Achievement.user_id == user.id
    ).order_by(Achievement.earned_at.desc()).all()

    return [
        {
            "type": a.badge_type,
            "name": BADGE_CRITERIA.get(a.badge_type, {}).get("name", a.badge_type),
            "description": BADGE_CRITERIA.get(a.badge_type, {}).get("description", ""),
            "icon": BADGE_CRITERIA.get(a.badge_type, {}).get("icon", "🏅"),
            "earned_at": a.earned_at.isoformat() if a.earned_at else None,
        }
        for a in achievements
    ]


# ── Sıralama ──────────────────────────────────────────────

@router.get("/leaderboard")
def get_leaderboard(
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    """Genel Ortalama Puan Sıralaması (Sınıf ve Şube İçi)"""
    # 1. Seviye İçi Sıralama (Aynı sinif_duzeyi olanlar)
    level_rankings = db.query(
        User.id,
        User.ad_soyad,
        func.count(Submission.id).label("submission_count"),
        func.avg(Submission.final_score).label("avg_score"),
    ).join(
        Submission, User.id == Submission.student_id
    ).filter(
        User.rol == UserRole.student,
        User.sinif_duzeyi == user.sinif_duzeyi,
        Submission.final_score != None,
    ).group_by(User.id).order_by(
        func.avg(Submission.final_score).desc()
    ).all()

    # 2. Şube İçi Sıralama (Aynı sinif_duzeyi ve sube olanlar)
    branch_rankings = [r for r in level_rankings if db.query(User.sube).filter(User.id == r.id).scalar() == user.sube]

    def format_rankings(rankings_list):
        return [
            {
                "rank": i + 1,
                "student_name": r.ad_soyad,
                "avg_score": round(float(r.avg_score), 1) if r.avg_score else 0,
                "total_submissions": r.submission_count,
                "is_me": r.id == user.id,
            }
            for i, r in enumerate(rankings_list)
        ]

    return {
        "level_name": f"{user.sinif_duzeyi}. Sınıflar Genelinde",
        "level_rankings": format_rankings(level_rankings[:20]),
        "branch_name": f"{user.sinif_duzeyi}-{user.sube} Sınıfında" if user.sube else "Şube Yok",
        "branch_rankings": format_rankings(branch_rankings[:20])
    }


@router.get("/leaderboard/task/{assignment_id}")
def get_task_leaderboard(
    assignment_id: int,
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    """Ödev (Çalışma) Özelinde Sıralama"""
    rankings = db.query(
        User.id,
        User.ad_soyad,
        User.sube,
        Submission.final_score.label("score"),
    ).join(
        Submission, User.id == Submission.student_id
    ).filter(
        User.rol == UserRole.student,
        User.sinif_duzeyi == user.sinif_duzeyi,
        Submission.assignment_id == assignment_id,
        Submission.final_score != None,
    ).order_by(
        Submission.final_score.desc()
    ).all()

    branch_rankings = [r for r in rankings if r.sube == user.sube]

    def format_rankings(rankings_list):
        return [
            {
                "rank": i + 1,
                "student_name": r.ad_soyad,
                "score": float(r.score),
                "is_me": r.id == user.id,
            }
            for i, r in enumerate(rankings_list)
        ]

    return {
        "level_name": f"{user.sinif_duzeyi}. Sınıflar Genelinde",
        "level_rankings": format_rankings(rankings[:20]),
        "branch_name": f"{user.sinif_duzeyi}-{user.sube} Sınıfında" if user.sube else "Şube Yok",
        "branch_rankings": format_rankings(branch_rankings[:20])
    }


# ── XP & Seviye ───────────────────────────────────────────

@router.get("/gamification")
def get_gamification_stats(
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
):
    streak = db.query(UserStreak).filter(UserStreak.user_id == user.id).first()
    if not streak:
        streak = UserStreak(user_id=user.id)
        db.add(streak)
        db.commit()

    level_progress = get_xp_for_next_level(streak.total_xp, streak.level)
    achievements = db.query(Achievement).filter(Achievement.user_id == user.id).all()
    badges = [
        {
            "type": a.badge_type,
            "name": BADGE_CRITERIA.get(a.badge_type, {}).get("name", a.badge_type),
            "icon": BADGE_CRITERIA.get(a.badge_type, {}).get("icon", "🏅"),
        }
        for a in achievements
    ]

    return {
        "xp": {
            "total": streak.total_xp,
            "level": streak.level,
            "level_name": LEVEL_NAMES.get(streak.level, f"Seviye {streak.level}"),
            "progress": level_progress,
        },
        "streak": {
            "current": streak.current_streak,
            "longest": streak.longest_streak,
            "active_today": streak.last_activity_date == date.today() if streak.last_activity_date else False,
        },
        "badges": {
            "earned": badges,
            "total": len(badges),
            "available": len(BADGE_CRITERIA),
        },
    }
